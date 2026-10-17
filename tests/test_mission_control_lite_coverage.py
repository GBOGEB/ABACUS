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
        p = self.make(new, previous=old)
        self.assertEqual(p["comparison"]["status"], "COMPARABLE")
        self.assertEqual(p["comparison"]["line_delta_pp"], 10)
        self.assertEqual(p["comparison"]["branch_delta_pp"], 25)
        self.assertEqual(p["comparison"]["new_covered_lines"], 5)

    def test_mismatched_denominator_or_scope_is_incomparable(self):
        old = self.make()
        new = coverage()
        new["totals"]["num_statements"] = 60
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

    def test_verbose_unique_id_census_with_duplicate_execution(self):
        def result(*names):
            body = "".join(
                f"{n.rsplit('.', 1)[-1]} ({n}) ... ok\n" for n in names
            )
            return body + f"Ran {len(names)} tests in 0.001s\n\nOK\n"
        a = "test_core.Mod.test_case"
        b = "test_rex.Mod.test_other"
        output = self.make(logs={"core": result(a, b),
                                 "telemetry": result(a)})
        self.assertEqual(output["tests_passed"], 3)
        self.assertEqual(output["test_execution_count"], 3)
        self.assertEqual(output["unique_test_cases"], 2)
        self.assertEqual(output["duplicate_case_executions"], 1)
        self.assertEqual(output["test_id_status"], "COMPLETE")
        self.assertEqual(len(output["test_case_id_sha256"]), 64)

    def test_summary_only_never_invents_distinct_cases(self):
        result = self.make()
        self.assertEqual(result["tests_passed"], 9)
        self.assertEqual(result["test_id_status"], "SUMMARY_ONLY")
        self.assertIsNone(result["unique_test_cases"])
        self.assertIsNone(result["duplicate_case_executions"])

    def test_partial_or_forged_case_identity_fails_closed(self):
        partial = ("test_abc (pkg.Class.test_abc) ... ok\n"
                   "Ran 2 tests in 0.001s\n\nOK\n")
        with self.assertRaisesRegex(ValueError, "identity count differs"):
            self.make(logs={"telemetry": partial})
        malformed = ("test_abc (pkg.Class.test_different) ... ok\n"
                     "Ran 1 test in 0.001s\n\nOK\n")
        with self.assertRaisesRegex(ValueError, "malformed case identity"):
            self.make(logs={"telemetry": malformed})

    def test_suite_population_change_blocks_test_delta(self):
        previous = self.make()
        new = self.make(logs={"core": OK, "rex": OK, "metrics": OK,
                              "telemetry": OK}, previous=previous)
        self.assertEqual(new["comparison"]["status"], "COMPARABLE")
        self.assertIsNone(new["comparison"]["test_delta"])
        self.assertIsNone(new["comparison"]["new_unique_case_ids"])
        self.assertEqual(new["comparison"]["test_census_status"],
                         "INCOMPARABLE_SUITE_POPULATION")

    def test_rejects_invalid_sha_and_baseline(self):
        with self.assertRaises(ValueError):
            build(coverage(), {"core": OK}, "not-a-sha", OTHER, 123)
        with self.assertRaises(ValueError):
            compare({"schema": "invalid"}, self.make())


if __name__ == "__main__":
    unittest.main()
