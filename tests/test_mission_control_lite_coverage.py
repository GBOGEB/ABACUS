import unittest

from mission_control_lite.coverage_pulse import build, compare, render_summary

SHA = "a" * 40
OTHER = "b" * 40
OK = "Ran 3 tests in 0.002s\n\nOK\n"


def coverage():
    files = {
        "mission_control_lite/" + name: {
            "summary": {
                "covered_lines": 8,
                "num_statements": 10,
                "covered_branches": 2,
                "num_branches": 4,
            }
        }
        for name in ("core.py", "policy.py", "cli.py", "rex.py",
                     "coverage_pulse.py")
    }
    return {
        "meta": {"version": "7.10.7"},
        "files": files,
        "totals": {
            "covered_lines": 40, "num_statements": 50,
            "covered_branches": 10, "num_branches": 20,
        },
    }


class CoveragePulseTests(unittest.TestCase):
    def make(self, report=None, logs=None, previous=None):
        return build(report if report is not None else coverage(),
                     logs if logs is not None else {
                         "core": OK, "rex": OK, "metrics": OK
                     }, SHA, OTHER, 123, previous)

    def test_valid_zero_statement_module_is_reported_without_failing(self):
        data = coverage()
        data["files"]["mission_control_lite/__init__.py"] = {
            "summary": {
                "covered_lines": 0, "num_statements": 0,
                "covered_branches": 0, "num_branches": 0,
            }
        }
        pulse = self.make(data)
        empty = pulse["per_file"]["mission_control_lite/__init__.py"]
        self.assertIsNone(empty["line_percent"])
        self.assertIsNone(empty["branch_percent"])
        self.assertEqual(empty["missing_lines"], 0)
        self.assertEqual(pulse["line_percent"], 80)

    def test_zero_denominator_aggregate_and_invalid_module_stay_red(self):
        data = coverage()
        data["totals"]["num_statements"] = 0
        data["totals"]["covered_lines"] = 0
        with self.assertRaisesRegex(ValueError, "invalid line denominator"):
            self.make(data)
        data = coverage()
        data["files"]["mission_control_lite/__init__.py"] = {
            "summary": {
                "covered_lines": 0, "num_statements": 0,
                "covered_branches": 0, "num_branches": 1,
            }
        }
        with self.assertRaisesRegex(ValueError, "empty module"):
            self.make(data)

    def test_snapshot_is_provenance_bound_and_nonadmitting(self):
        p = self.make()
        self.assertEqual(p["tests_passed"], 9)
        self.assertEqual(p["line_percent"], 80)
        self.assertEqual(p["branch_percent"], 50)
        self.assertEqual(p["source_sha"], SHA)
        self.assertEqual(p["merge_admission"], "HOLD")
        self.assertEqual(p["verified_root_closures"], 0)
        self.assertEqual(p["comparison"]["status"], "UNKNOWN")

    def test_comparable_delta(self):
        old = self.make()
        new = coverage()
        new["totals"]["covered_lines"] = 45
        new["totals"]["covered_branches"] = 15
        for item in new["files"].values():
            item["summary"]["covered_lines"] += 1
            item["summary"]["covered_branches"] += 1
        p = self.make(new, previous=old)
        self.assertEqual(p["comparison"]["status"], "COMPARABLE")
        self.assertEqual(p["comparison"]["line_delta_pp"], 10)
        self.assertEqual(p["comparison"]["branch_delta_pp"], 25)
        self.assertEqual(p["comparison"]["new_covered_lines"], 5)

    def test_mismatched_denominator_or_scope_is_incomparable(self):
        old = self.make()
        new = coverage()
        new["totals"]["num_statements"] = 60
        new["files"]["mission_control_lite/core.py"]["summary"]["num_statements"] = 20
        self.assertEqual(self.make(new, previous=old)["comparison"]["status"],
                         "INCOMPARABLE")
        old["scope_id"] = "different"
        self.assertEqual(self.make(previous=old)["comparison"]["status"],
                         "INCOMPARABLE")

    def test_rejects_missing_logs_and_nonpassing_suites(self):
        for log in ("Ran 3 tests in 0.01s\nFAILED", "OK", "Ran 0 tests in 0.01s\nOK"):
            with self.subTest(log=log), self.assertRaises(ValueError):
                self.make(logs={"core": log})

    def test_rejects_invalid_coverage_and_scope(self):
        bad = coverage()
        bad["totals"]["covered_lines"] = 100
        with self.assertRaises(ValueError):
            self.make(bad)
        bad = coverage()
        bad["files"]["tests/untrusted.py"] = bad["files"].pop(
            "mission_control_lite/core.py")
        with self.assertRaises(ValueError):
            self.make(bad)

    def test_forged_coverage_totals_fail_closed(self):
        data = coverage()
        data["totals"]["covered_lines"] += 1
        with self.assertRaisesRegex(ValueError, "totals disagree"):
            self.make(data)

    def test_backlog_denominators_and_nonadmission(self):
        pulse = self.make()
        self.assertEqual(pulse["uncovered_lines"], 10)
        self.assertEqual(pulse["uncovered_branches"], 10)
        self.assertEqual(len(pulse["coverage_backlog"]), 5)
        self.assertEqual(pulse["coverage_backlog"][0]["triage_score"], 6)
        self.assertEqual(pulse["merge_admission"], "HOLD")

    def test_timed_phases_summary_and_unknown_queue(self):
        phases = [
            {"phase": "coverage-install", "duration_seconds": 1.5,
             "exit_code": 0},
            {"phase": "tests", "duration_seconds": 2.5, "exit_code": 0},
        ]
        report = build(coverage(), {"core": OK, "rex": OK, "metrics": OK},
                       SHA, OTHER, 123, phases=phases)
        self.assertEqual(report["timed_execution_seconds"], 4)
        self.assertEqual(report["job_queue_seconds"], None)
        self.assertEqual(report["wheel_unpack_seconds"], None)
        self.assertEqual(report["tests_per_timed_second"], 2.25)
        markdown = render_summary(report)
        self.assertIn("UNKNOWN (external run metadata needed)", markdown)
        self.assertIn("Merge admission | HOLD", markdown)
        self.assertIn("coverage-install", markdown)

    def test_timing_phase_fails_closed(self):
        good = {"phase": "install", "duration_seconds": 1.0,
                "exit_code": 0}
        bad_cases = [
            [],
            [good, good],
            [{"phase": "bad", "duration_seconds": -1, "exit_code": 0}],
            [{"phase": "bad", "duration_seconds": 1, "exit_code": 1}],
        ]
        for phases in bad_cases:
            with self.subTest(phases=phases), self.assertRaises(ValueError):
                build(coverage(), {"core": OK}, SHA, OTHER, 123,
                      phases=phases)

    def test_rejects_invalid_sha_and_baseline(self):
        with self.assertRaises(ValueError):
            build(coverage(), {"core": OK}, "not-a-sha", OTHER, 123)
        with self.assertRaises(ValueError):
            compare({"schema": "invalid"}, self.make())


if __name__ == "__main__":
    unittest.main()
