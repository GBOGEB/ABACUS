"""N14 debugger branch-obligation flight; source-free, temporary-workspace fixtures.

Every observation is diagnostic only. These tests neither authorize auto-fix on
real source trees nor promote a reproduced symptom to a root closure.
"""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from DMAIC_V3.debug_pipeline import PipelineDebugger


class DebuggerBranchFlight(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.debug = PipelineDebugger(self.root)

    def write(self, relative, text):
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def check(self, method):
        with contextlib.redirect_stdout(io.StringIO()):
            return method()

    def test_output_structure_creates_empty_root(self):
        result = self.check(self.debug._check_output_structure)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["iterations"], [])
        self.assertTrue((self.root / "DMAIC_V3_OUTPUT").is_dir())
        self.assertEqual(len(self.debug.fixes_applied), 1)

    def test_output_structure_skips_bad_iterations_and_counts_phases(self):
        self.write("DMAIC_V3_OUTPUT/iteration_2/phase0_init/part.json", "{}")
        (self.root / "DMAIC_V3_OUTPUT/iteration_bad").mkdir()
        (self.root / "DMAIC_V3_OUTPUT/iteration_3").mkdir()
        result = self.check(self.debug._check_output_structure)
        self.assertEqual(len(result["iterations"]), 2)
        first = next(x for x in result["iterations"] if x["number"] == 2)
        self.assertEqual(first["phases"]["phase0"]["files"], 1)
        self.assertFalse(first["phases"]["phase1"]["exists"])

    def test_empty_phases_distinguishes_empty_invalid_and_absent(self):
        (self.root / "DMAIC_V3_OUTPUT/iteration_1/phase0_init").mkdir(parents=True)
        self.write("DMAIC_V3_OUTPUT/iteration_1/phase1_define/bad.json", "not-json")
        self.write("DMAIC_V3_OUTPUT/iteration_1/phase2_measure/empty.json", "{}")
        self.write("DMAIC_V3_OUTPUT/iteration_1/phase3_analyze/good.json", '{"ok":true}')
        result = self.check(self.debug._check_empty_phases)
        self.assertEqual(result["status"], "warning")
        self.assertEqual({v["reason"] for v in result["empty_phases"]},
                         {"no_json_files", "invalid_json", "empty_json"})

    def test_empty_phase_skips_invalid_iteration_with_warning(self):
        (self.root / "DMAIC_V3_OUTPUT/iteration_nonnumeric/phase0_x").mkdir(parents=True)
        result = self.check(self.debug._check_empty_phases)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(any(x["category"] == "empty_phases" for x in self.debug.issues))

    def test_failed_iterations_reports_incomplete_but_not_complete(self):
        for i in range(9):
            (self.root / f"DMAIC_V3_OUTPUT/iteration_1/phase{i}_ready").mkdir(parents=True)
        (self.root / "DMAIC_V3_OUTPUT/iteration_2/phase0_only").mkdir(parents=True)
        (self.root / "DMAIC_V3_OUTPUT/iteration_bad").mkdir()
        result = self.check(self.debug._check_failed_iterations)
        self.assertEqual(result["status"], "warning")
        self.assertEqual(len(result["failures"]), 1)
        self.assertEqual(result["failures"][0]["iteration"], 2)
        self.assertEqual(result["failures"][0]["completed_phases"], 1)

    def test_canonical_census_checks_missing_then_present(self):
        absent = self.check(self.debug._check_canonical_files)
        self.assertFalse(any(v["exists"] for v in absent["files"].values()))
        for name in ("index.json", "ranking.json", "ranking.yaml", "manifest.json"):
            self.write(name, "{}")
        found = self.check(self.debug._check_canonical_files)
        self.assertTrue(all(v["exists"] for v in found["files"].values()))

    def test_common_import_error_and_corrected_fixture(self):
        file = self.write("DMAIC_V3/phases/phase1_define.py", "ensure_directory('x')\n")
        bad = self.check(self.debug._check_common_errors)
        self.assertEqual(bad["status"], "error")
        self.assertEqual(len(bad["errors"]), 1)
        file.write_text("from ..core.utils import ensure_directory\nensure_directory('x')\n")
        good = self.check(self.debug._check_common_errors)
        self.assertEqual(good["status"], "ok")

    def test_log_scan_handles_failures_success_and_malformed_json(self):
        self.write("DMAIC_V3_OUTPUT/iteration_5/phase0_a/error.json", '{"error":"disk"}')
        self.write("DMAIC_V3_OUTPUT/iteration_5/phase1_b/fail.json", '{"success":false}')
        self.write("DMAIC_V3_OUTPUT/iteration_5/phase2_c/invalid.json", "not-json")
        self.write("DMAIC_V3_OUTPUT/iteration_5/phase3_d/ok.json", '{"success":true}')
        result = self.check(self.debug._analyze_logs)
        self.assertEqual(result["status"], "warning")
        self.assertEqual(len(result["recent_errors"]), 2)
        self.assertEqual({x["error"] for x in result["recent_errors"]},
                         {"disk", "Unknown failure"})

    def test_auto_fix_only_creates_missing_sandbox_templates(self):
        with contextlib.redirect_stdout(io.StringIO()):
            first = self.debug.auto_fix()
            second = self.debug.auto_fix()
        self.assertEqual(len(first), 4)
        self.assertEqual(second, [])
        self.assertTrue((self.root / "DMAIC_V3_OUTPUT").is_dir())
        self.assertEqual(json.loads((self.root / "index.json").read_text())["dmaic_version"], "3.3")

    def test_auto_fix_inserts_phase1_import_once(self):
        source = self.write("DMAIC_V3/phases/phase1_define.py",
                            "from ..core.state import StateManager\nensure_directory('x')\n")
        with contextlib.redirect_stdout(io.StringIO()):
            first = self.debug.auto_fix()
            self.debug.auto_fix()
        self.assertTrue(any("ensure_directory" in note for note in first))
        self.assertEqual(source.read_text().count("from ..core.utils import ensure_directory"), 1)

    def test_phase_census_mixes_executable_missing_and_incomplete(self):
        self.write("DMAIC_V3/phases/phase0_init.py", "def execute(self):\n    pass\n")
        self.write("DMAIC_V3/phases/phase1_define.py", "value=1\n")
        result = self.check(self.debug._check_phase_files)
        self.assertTrue(result["phases"]["phase0_init.py"]["has_execute"])
        self.assertFalse(result["phases"]["phase1_define.py"]["has_execute"])
        self.assertFalse(result["phases"]["phase8_todo_management.py"]["exists"])
        self.assertTrue(any(x["category"] == "phases" for x in self.debug.issues))

    def test_full_diagnostic_keeps_critical_classification(self):
        result = self.check(self.debug.run_full_diagnostic)
        self.assertEqual(len(result["checks"]), 10)
        self.assertEqual(result["status"], "critical")
        self.assertTrue(result["issues"])
        self.assertTrue((self.root / "DMAIC_V3_OUTPUT").is_dir())


if __name__ == "__main__":
    unittest.main()
