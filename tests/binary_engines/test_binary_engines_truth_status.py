"""truth_status: a pure matcher of inventory rows against a pin map, covering all five statuses."""

from __future__ import annotations

import ast
import json
import shutil
import unittest

from tests.binary_engines import _env

H = {k: (k * 64)[:64] for k in "abcdef"}  # synthetic sha256 values


def _row(name, family, sha, tip=True, root="MI", typ="DOCX"):
    return {
        "root_id": root,
        "name": name,
        "type": typ,
        "family": family,
        "sha256": sha,
        "family_tip": tip,
        "epic_final": "E1_PROJECT_ALPHA",
        "age_days": 10.0,
    }


ROWS = [
    _row(
        "spec_v1.docx", "SPEC", H["a"], tip=False
    ),  # pinned canonical although older: the pin decides
    _row("spec_v2.docx", "SPEC", H["b"]),  # newest, unpinned, family pinned
    _row("plan_v1.docx", "PLAN", H["c"], tip=False),  # older, nothing pinned
    _row("plan_v2.docx", "PLAN", H["d"]),  # newest, nothing pinned
    _row(
        "deck_v1.pptx", "DECK", H["e"], tip=False, typ="PPTX"
    ),  # pinned only in custody
    _row(
        "deck_v2.pptx", "DECK", H["f"], typ="PPTX"
    ),  # newest; its family has a custody pin
    _row("online_only.docx", "ONLINE", ""),  # not hashed (cloud-only): never matched
]
PINS = {
    H["a"]: [
        "hub:release/SHA256SUMS",
        "hub:archive/2026/SHA256SUMS",
        "proj:canonical/binaries.json",
        "proj:triage/receipt.json",
        "proj:ssot/pins.yaml",
    ],
    H["e"]: ["proj:archive/old_manifest.json", "proj:receipts/r1.json"],
}
EXPECTED = {
    "spec_v1.docx": "AUTHORITATIVE",
    "spec_v2.docx": "STALE_RELEVANT",
    "plan_v1.docx": "SUPERSEDED",
    "plan_v2.docx": "UNPINNED",
    "deck_v1.pptx": "RECORDED",
    "deck_v2.pptx": "STALE_RELEVANT",
    "online_only.docx": "UNPINNED",
}


class Classify(unittest.TestCase):
    def setUp(self):
        self.ts = _env.engine("truth_status")

    def test_all_five_statuses(self):
        out = self.ts.classify(ROWS, self.ts.load_pins(PINS))
        self.assertEqual({r["name"]: r["truth"] for r in out}, EXPECTED)
        self.assertEqual({r["truth"] for r in out}, set(self.ts.STATUSES))
        self.assertEqual(
            [r["name"] for r in out], [r["name"] for r in ROWS], "row order is kept"
        )

    def test_canonical_pins_listed_first(self):
        out = {r["name"]: r for r in self.ts.classify(ROWS, PINS)}
        self.assertEqual(
            out["spec_v1.docx"]["pinned_in"],
            [
                "hub:release/SHA256SUMS",
                "proj:canonical/binaries.json",
                "proj:ssot/pins.yaml",
            ],
        )
        self.assertEqual(out["deck_v1.pptx"]["pinned_in"], PINS[H["e"]])
        self.assertEqual(out["plan_v2.docx"]["pinned_in"], [])

    def test_family_tips_override_the_rows(self):
        tips = {
            ("MI", "plan_v1.docx")
        }  # the caller says v1 is the tip, so v2 is the older one
        out = {
            r["name"]: r["truth"]
            for r in self.ts.classify(ROWS, PINS, family_tips=tips)
        }
        self.assertEqual(out["plan_v1.docx"], "UNPINNED")
        self.assertEqual(out["plan_v2.docx"], "SUPERSEDED")
        self.assertEqual(out["spec_v1.docx"], "AUTHORITATIVE")

    def test_rows_from_other_roots_keep_their_root(self):
        rows = [
            _row("same.docx", "SAME", H["a"], root="DOCS"),
            _row("same.docx", "SAME", H["a"], root="DL"),
        ]
        out = self.ts.classify(rows, PINS)
        self.assertEqual(
            [(r["root"], r["truth"]) for r in out],
            [("DOCS", "AUTHORITATIVE"), ("DL", "AUTHORITATIVE")],
        )


class PinMap(unittest.TestCase):
    def setUp(self):
        self.ts = _env.engine("truth_status")

    def test_accepts_map_and_wrapped_map(self):
        upper = {
            H["a"].upper(): ["hub:release/SHA256SUMS"],
            H["a"]: ["hub:release/SHA256SUMS", "x:ssot.json"],
        }
        self.assertEqual(
            self.ts.load_pins(upper),
            {H["a"]: ["hub:release/SHA256SUMS", "x:ssot.json"]},
        )
        self.assertEqual(
            self.ts.load_pins({"pins": PINS, "heads": {"hub": "main " + "0" * 40}}),
            PINS,
        )

    def test_rejects_malformed_maps(self):
        bad = [
            [],
            {"not-a-hash": ["r:p"]},
            {H["a"]: "r:p"},
            {H["a"]: []},
            {H["a"]: [""]},
            {H["a"]: [1]},
        ]
        for data in bad:
            with self.subTest(data=str(data)[:40]):
                with self.assertRaises(ValueError):
                    self.ts.load_pins(data)

    def test_no_git_and_no_subprocess(self):
        tree = ast.parse((_env.CODE / "truth_status.py").read_text("utf-8"))
        imported = {
            a.name.split(".")[0]
            for n in ast.walk(tree)
            if isinstance(n, ast.Import)
            for a in n.names
        }
        imported |= {
            n.module.split(".")[0]
            for n in ast.walk(tree)
            if isinstance(n, ast.ImportFrom) and n.module
        }
        self.assertFalse(
            imported & {"subprocess", "git_readonly", "os", "shutil"}, imported
        )


class Cli(unittest.TestCase):
    def setUp(self):
        _env.require("yaml")
        spec = _env.engine("estate_spec")
        self.inv = spec.inv_dir("DOCS")
        self.inv.mkdir(parents=True, exist_ok=True)
        rows = [{k: v for k, v in r.items() if k != "root_id"} for r in ROWS]
        (self.inv / "root_inventory_final.json").write_text(json.dumps(rows), "utf-8")
        self.addCleanup(shutil.rmtree, _env.HOME / "roots" / "DOCS", True)

    def test_writes_the_report(self):
        pins = _env.HOME / "pins_test.json"
        pins.write_text(
            json.dumps({"pins": PINS, "heads": {"hub": "origin/main " + "0" * 40}}),
            "utf-8",
        )
        dest = _env.HOME / "deep" / "authority_test.json"
        code, out = _env.run_main(
            "truth_status", "--pins", str(pins), "--out", str(dest)
        )
        self.assertEqual(code, 0, out)
        report = json.loads(dest.read_text("utf-8"))
        self.assertEqual(report["pinned_hashes"], 2)
        self.assertEqual(report["heads"], {"hub": "origin/main " + "0" * 40})
        docs = {r["name"]: r["truth"] for r in report["rows"] if r["root"] == "DOCS"}
        self.assertEqual(docs, EXPECTED)


if __name__ == "__main__":
    unittest.main()
