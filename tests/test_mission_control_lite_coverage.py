import unittest

from mission_control_lite.coverage_pulse import build, compare

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

    def test_rejects_invalid_sha_and_baseline(self):
        with self.assertRaises(ValueError):
            build(coverage(), {"core": OK}, "not-a-sha", OTHER, 123)
        with self.assertRaises(ValueError):
            compare({"schema": "invalid"}, self.make())


if __name__ == "__main__":
    unittest.main()
