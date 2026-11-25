"""Regression tests for the #2746 review threads (estate_probe, estate_inventory, estate_moveplan, public_safety_scan,
git_readonly, truth_status)."""

from __future__ import annotations

import csv
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from tests.binary_engines import _env


class SheetState(unittest.TestCase):
    def test_hidden_state_is_read_in_any_attribute_order(self):
        probe = _env.engine("estate_probe")
        wb = (
            '<workbook><sheets><sheet name="Visible" sheetId="1" r:id="rId1"/>'
            '<sheet name="Hid" sheetId="2" state="hidden" r:id="rId2"/>'
            '<sheet state="veryHidden" name="Deep" sheetId="3" r:id="rId3"/></sheets></workbook>'
        )
        self.assertEqual(
            probe._sheet_entries(wb),
            [("Visible", ""), ("Hid", "hidden"), ("Deep", "veryHidden")],
        )


@_env.gated(kernels=True)
class EqualTimestamps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _env.require_kernels()

    def test_equal_mtime_relatives_go_to_cycle_review(self):
        inv = _env.engine("estate_inventory")
        zips = [
            {
                "name": n,
                "mtime": 1000.0,
                "family": "bundle",
                "zip": {"names_sig": []},
                "age_days": 1,
            }
            for n in ("bundle_v1.zip", "bundle_v2.zip")
        ]
        inv.reverse_kahn(zips)
        self.assertEqual([z["kahn_layer"] for z in zips], [-1, -1])

    def test_strictly_older_is_still_superseded(self):
        inv = _env.engine("estate_inventory")
        zips = [
            {
                "name": "a.zip",
                "mtime": 1000.0,
                "family": "f",
                "zip": {"names_sig": []},
                "age_days": 1,
            },
            {
                "name": "b.zip",
                "mtime": 2000.0,
                "family": "f",
                "zip": {"names_sig": []},
                "age_days": 1,
            },
        ]
        inv.reverse_kahn(zips)
        self.assertEqual(
            {z["name"]: z["kahn_layer"] for z in zips}, {"a.zip": 1, "b.zip": 0}
        )


class EmptyEstate(unittest.TestCase):
    def test_empty_root_writes_header_only_move_plan(self):
        mp = _env.engine("estate_moveplan")
        with tempfile.TemporaryDirectory() as tmp:
            inv = Path(tmp) / "inv"
            inv.mkdir()
            (inv / "root_inventory_final.json").write_text("[]", "utf-8")
            with (
                unittest.mock.patch.object(
                    mp, "ROOTS", {"EMPTY": (Path(tmp) / "root",)}
                ),
                unittest.mock.patch.object(mp, "inv_dir", lambda rid: inv),
            ):
                code, out = _env.run_main("estate_moveplan", "--root-id", "EMPTY")
            self.assertEqual(code, 0, out[-2000:])
            with (inv / "MOVE_PLAN.csv").open(encoding="utf-8") as fh:
                rows = list(csv.reader(fh))
        self.assertEqual(rows, [mp.MOVE_PLAN_FIELDS])


def _fake_stat(mode: int, attributes: int = 0):
    return unittest.mock.Mock(st_mode=mode, st_file_attributes=attributes)


@_env.gated("yaml")
class SecondReview(unittest.TestCase):
    """The 2026-11-16 review threads: junctions in GG_* walks, fail-closed scan, bundle budget, sha case."""

    def test_walk_link_rule_matches_the_top_level_rule(self):
        import stat

        inv = _env.engine("estate_inventory")
        cases = {
            "junction": (_fake_stat(stat.S_IFDIR, 0x400), True),
            "symlink": (_fake_stat(stat.S_IFLNK), True),
            "plain folder": (_fake_stat(stat.S_IFDIR), False),
            "online-only file": (_fake_stat(stat.S_IFREG, 0x400), False),
        }
        for label, (st, expected) in cases.items():
            with self.subTest(label), unittest.mock.patch.object(
                inv.os, "lstat", return_value=st
            ):
                self.assertIs(inv._path_is_link("x"), expected)
        with unittest.mock.patch.object(inv.os, "lstat", side_effect=OSError):
            self.assertTrue(inv._path_is_link("x"), "an unreadable entry is never entered")

    def test_untokenizable_source_holds(self):
        scan = _env.engine("public_safety_scan")
        self.assertEqual(scan.fstring_312_only("x = 1\n"), [])
        self.assertTrue(scan.fstring_312_only('x = 1\ny = """never closed\n'))
        self.assertTrue(scan.fstring_312_only("def f(:\n    (\n"))

    def test_markers_are_literal_words(self):
        scan = _env.engine("public_safety_scan")
        rx = scan.marker_pattern(["a.b", "(x", "", "  "])
        self.assertTrue(rx.search("see A.B here"))
        self.assertFalse(rx.search("see axb here"), "'.' is literal, not any character")
        self.assertFalse(rx.search("nothing private"), "blank markers are dropped, not match-all")
        self.assertFalse(scan.marker_pattern([]).search("anything"))

    def test_bundle_header_is_bounded(self):
        gr = _env.engine("git_readonly")
        with tempfile.TemporaryDirectory() as tmp:
            heads = Path(tmp) / "heads.bundle"
            refs = b"".join(b"%s refs/heads/b%d\n" % (b"a" * 40, i) for i in range(5))
            heads.write_bytes(b"# v2 git bundle\n" + refs + b"\nPACK")
            self.assertEqual(len(gr.bundle_heads(heads, limit=2)), 2)
            self.assertEqual(len(gr.bundle_heads(heads)), 5)
            self.assertEqual(len(gr.bundle_heads(heads, limit=2)), 2, "stops at the limit")
            bloated = Path(tmp) / "bloated.bundle"
            # 300 x 4 KB prerequisite lines (~1.2 MB, far under the line cap) before the only head
            prereqs = (b"-" + b"b" * 4000 + b"\n") * 300
            bloated.write_bytes(b"# v2 git bundle\n" + prereqs + b"a" * 40 + b" refs/heads/x\n\nPACK")
            self.assertEqual(gr.bundle_heads(bloated), [], "a header past the byte budget is unknown")

    def test_row_hash_case_does_not_matter(self):
        ts = _env.engine("truth_status")
        sha = "ab" * 32
        pins = ts.load_pins({sha: ["hub:release/SHA256SUMS"]})
        rows = [
            {"name": n, "type": "SPEC", "family": "F", "sha256": h}
            for n, h in (("lower.docx", sha), ("upper.docx", sha.upper()))
        ]
        out = {r["name"]: r["truth"] for r in ts.classify(rows, pins)}
        self.assertEqual(out["lower.docx"], ts.AUTHORITATIVE)
        self.assertEqual(out["upper.docx"], ts.AUTHORITATIVE)


if __name__ == "__main__":
    unittest.main()
