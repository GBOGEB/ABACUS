"""G3A W16 canonical epoch re-pin: drift, native measurement and refusals."""

import contextlib
import io
import json
import tempfile
import unittest
import unittest.mock as mock
from pathlib import Path

from scripts import g3a_w16_repin as rp

SAFE_BLOB = "98d466e02836ea786379524bb322faa143ea7626"  # git hash-object
MAIN = "c" * 40


class RepinCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / ".github/workflows").mkdir(parents=True)
        (self.root / "ci/governance").mkdir(parents=True)
        (self.root / "src").mkdir()
        (self.root / "src/kept.py").write_text("print('safe')\n", encoding="utf-8")
        (self.root / "src/moved.py").write_text("x = 1\n", encoding="utf-8")
        for name in ("a.yml", "b.yml", "c.yaml", "loose.yml"):
            (self.root / ".github/workflows" / name).write_text("on: push\n")
        rules = [
            {"pattern": "^a[.]yml$", "cluster": "core", "lifecycle": "pr"},
            {"pattern": "^b[.]yml$", "cluster": "core", "lifecycle": "sched"},
            {"pattern": "^c[.]yaml$", "cluster": "docs", "lifecycle": "pr"},
        ]
        (self.root / "ci/governance/workflow_policy.json").write_text(
            json.dumps({"rules": rules}), encoding="utf-8"
        )
        self.manifest = {
            "schema": rp.SCHEMA,
            "source_epoch": "OLD",
            "lineage": [],
            "coverage_version": "7.16.2",
            "pythons": ["3.10", "3.12"],
            "status": rp.PINNED,
            "files": {
                "src/kept.py": self.entry("kpi", SAFE_BLOB, 10, 4),
                "src/moved.py": self.entry("kpi", "d" * 40, 20, 5),
                "src/ctl.py": self.entry("control", SAFE_BLOB, 8, 8),
            },
        }
        (self.root / "src/ctl.py").write_text("print('safe')\n", encoding="utf-8")
        # Blob ids come from git; a content-keyed fake keeps these tests
        # independent of git and of temp-directory ownership rules.
        fake_git = mock.patch.object(rp._preflight, "_git", side_effect=self.fake_git)
        self.git = fake_git.start()
        self.addCleanup(fake_git.stop)

    def fake_git(self, root, command, path):
        content = (root / path).read_text(encoding="utf-8")
        return SAFE_BLOB if content == "print('safe')\n" else "e" * 40

    @staticmethod
    def entry(role, blob, branches, floor):
        return {
            "role": role,
            "blob": blob,
            "category": "carried",
            "branches": {"3.10": branches, "3.12": branches},
            "covered": {"3.10": None, "3.12": None},
            "floor": floor,
        }

    def measured(self, python, path, branches, covered, epoch="NEW"):
        record = {
            "epoch": epoch,
            "coverage_version": "7.16.2",
            "python": python,
            "path": path,
            "branches": branches,
            "covered": covered,
        }
        return record


class BlobAndCensusTests(RepinCase):
    def test_blob_id_is_git_hash_object_via_preflight_helper(self):
        self.assertEqual(rp.blob_id(self.root, "src/kept.py"), SAFE_BLOB)
        self.git.assert_called_with(self.root, "hash-object", "src/kept.py")
        self.assertEqual(rp.blob_id(self.root, "src/moved.py"), "e" * 40)

    def test_workflow_census_maps_policy_subcategories(self):
        census = rp.workflow_census(self.root)
        self.assertEqual(census["population"], 4)
        self.assertEqual(
            census["by_cluster"], {"UNCLASSIFIED": 1, "core": 2, "docs": 1}
        )
        self.assertEqual(
            census["by_lifecycle"], {"UNCLASSIFIED": 1, "pr": 2, "sched": 1}
        )
        self.assertEqual(census["unclassified"], ["loose.yml"])


class RepinTests(RepinCase):
    def test_repin_only_invalidates_drifted_files(self):
        out = rp.repin(self.manifest, self.root, epoch="NEW", main_sha=MAIN)
        kept, moved = out["files"]["src/kept.py"], out["files"]["src/moved.py"]
        self.assertEqual(kept["category"], "carried")
        self.assertEqual(kept["branches"]["3.12"], 10)
        self.assertEqual(kept["floor"], 4)
        self.assertEqual(moved["category"], "main_drift_repinned")
        self.assertEqual(moved["previous_blob"], "d" * 40)
        self.assertIsNone(moved["branches"]["3.10"])
        self.assertIsNone(moved["floor"])
        self.assertEqual(out["files"]["src/ctl.py"]["category"], "control")
        self.assertEqual(out["status"], rp.PENDING)
        self.assertEqual(out["lineage"], ["OLD"])
        self.assertEqual(out["pinned_main_sha"], MAIN)
        self.assertEqual(out["workflows"]["population"], 4)
        self.assertEqual(self.manifest["files"]["src/moved.py"]["floor"], 5)

    def test_remeasure_all_clears_every_denominator_but_keeps_carried_floors(self):
        out = rp.repin(
            self.manifest, self.root, epoch="NEW", main_sha=MAIN, remeasure_all=True
        )
        for entry in out["files"].values():
            self.assertEqual(entry["branches"], {"3.10": None, "3.12": None})
        self.assertEqual(out["files"]["src/kept.py"]["floor"], 4)
        self.assertNotIn("previous_blob", out["files"]["src/kept.py"])

    def test_repin_refusals(self):
        for kwargs, match in (
            ({"epoch": "NEW", "main_sha": "short"}, "40-character"),
            ({"epoch": "OLD", "main_sha": MAIN}, "new source epoch"),
        ):
            with (
                self.subTest(match=match),
                self.assertRaisesRegex(rp.RepinError, match),
            ):
                rp.repin(self.manifest, self.root, **kwargs)
        (self.root / "src/kept.py").unlink()
        with self.assertRaisesRegex(rp.RepinError, "missing"):
            rp.repin(self.manifest, self.root, epoch="NEW", main_sha=MAIN)


class MeasurementTests(RepinCase):
    def pending(self):
        return rp.repin(
            self.manifest, self.root, epoch="NEW", main_sha=MAIN, remeasure_all=True
        )

    def full_records(self):
        return [
            self.measured(py, path, den, cov)
            for py in ("3.10", "3.12")
            for path, den, cov in (
                ("src/kept.py", 10, 6),
                ("src/moved.py", 22, 7 if py == "3.10" else 9),
                ("src/ctl.py", 8, 8),
            )
        ]

    def test_full_native_measurement_pins_epoch_and_seeds_floors(self):
        out = rp.apply_measured(self.pending(), self.full_records())
        self.assertEqual(out["status"], rp.PINNED)
        moved = out["files"]["src/moved.py"]
        self.assertEqual(moved["branches"], {"3.10": 22, "3.12": 22})
        self.assertEqual(moved["floor"], 7)
        self.assertEqual(out["files"]["src/kept.py"]["floor"], 4)

    def test_partial_measurement_stays_pending(self):
        out = rp.apply_measured(self.pending(), self.full_records()[:3])
        self.assertEqual(out["status"], rp.PENDING)
        self.assertIsNone(out["files"]["src/moved.py"]["floor"])

    def test_measurement_refusals(self):
        cases = (
            (self.measured("3.12", "src/kept.py", 10, 6, epoch="OLD"), "epoch"),
            (
                {
                    **self.measured("3.12", "src/kept.py", 10, 6),
                    "coverage_version": "7",
                },
                "coverage",
            ),
            (self.measured("3.11", "src/kept.py", 10, 6), "population"),
            (self.measured("3.12", "src/other.py", 10, 6), "population"),
            (self.measured("3.12", "src/kept.py", 10, 11), "arithmetic"),
            (self.measured("3.12", "src/kept.py", 10, 3), "floor"),
        )
        for record, match in cases:
            with (
                self.subTest(match=match),
                self.assertRaisesRegex(rp.RepinError, match),
            ):
                rp.apply_measured(self.pending(), [record])
        first = rp.apply_measured(
            self.pending(), [self.measured("3.12", "src/kept.py", 10, 6)]
        )
        with self.assertRaisesRegex(rp.RepinError, "conflicting"):
            rp.apply_measured(first, [self.measured("3.12", "src/kept.py", 11, 6)])

    def test_parse_measured_reads_ci_log_and_annotation_lines(self):
        record = self.measured("3.12", "src/kept.py", 10, 6)
        text = (
            "noise\n2026-10-22T10:00:00Z ::notice::"
            + rp.MEASURED_PREFIX
            + json.dumps(record)
            + "\n"
        )
        self.assertEqual(rp.parse_measured(text), [record])
        with self.assertRaisesRegex(rp.RepinError, "no W16_MEASURED"):
            rp.parse_measured("nothing here")


class CliTests(RepinCase):
    def test_cli_repins_then_pins_from_measurement_file(self):
        manifest = self.root / rp.MANIFEST
        manifest.parent.mkdir(parents=True)
        manifest.write_text(rp.dump(self.manifest), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rp.main(
                [
                    "--root",
                    str(self.root),
                    "--repin",
                    "NEW",
                    "--main-sha",
                    MAIN,
                    "--remeasure-all",
                ]
            )
        self.assertIn("status=" + rp.PENDING, out.getvalue())
        log = self.root / "measured.txt"
        log.write_text(
            "".join(
                rp.MEASURED_PREFIX + json.dumps(r) + "\n"
                for r in MeasurementTests.full_records(self)
            ),
            encoding="utf-8",
        )
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rp.main(["--root", str(self.root), "--measured", str(log)])
        self.assertIn("G3A_W16_EPOCH=NEW status=PINNED workflows=4", out.getvalue())
        self.assertEqual(rp.load(self.root)["status"], rp.PINNED)

    def test_load_rejects_unknown_schema(self):
        manifest = self.root / rp.MANIFEST
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({"schema": "other"}), encoding="utf-8")
        with self.assertRaisesRegex(rp.RepinError, "schema"):
            rp.load(self.root)


if __name__ == "__main__":
    unittest.main()
