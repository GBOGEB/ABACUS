"""G3A W16 five-KPI contract: positive and fail-closed branches."""
import unittest
from MIP.statistics.g3a_w16_kpi import EPOCH, FOUR_BRANCHES, METRIC_NAMES, evaluate

SHA = "a" * 40
BLOB = "18bec722fef537aa74b85295954cf66a002695d0"


def native():
    vals = {"DMAIC_V3/debug_pipeline.py": 94,
            "DMAIC_V3/phases/phase4_improve.py": 50,
            "DMAIC_V3/phases/phase8_todo_management.py": 35,
            "cicd_github_orchestrator.py": 23}
    return {
        "schema": "code-purple.g3a.w16.native.v1",
        "source_epoch": EPOCH,
        "checkout_sha": SHA, "phase4_source_blob": BLOB,
        "run_id": 38901984001, "run_attempt": 1, "tests": 130,
        "files": {k: {"covered": vals[k], "eligible": FOUR_BRANCHES[k]}
                  for k in FOUR_BRANCHES},
        "covered": sum(vals.values()), "eligible": 444,
        "merge_admission": "HOLD"
    }


class W16DecisionMetricTests(unittest.TestCase):
    def test_unmeasured_values_are_null_not_false_green(self):
        x = evaluate(None)
        self.assertEqual(x["metric_count"], 5)
        self.assertEqual(tuple(x["metrics"]), METRIC_NAMES)
        self.assertIsNone(x["metrics"]["matched_coverage"]["ratio"])
        self.assertIsNone(x["metrics"]["time_to_evidence"]["queue_seconds"])
        self.assertEqual(x["native_state"], "NATIVE_NOT_MEASURED")

    def test_valid_current_epoch_is_444_not_historical_446(self):
        x = evaluate(native())
        self.assertEqual(x["metrics"]["matched_coverage"]["d"], 444)
        self.assertEqual(x["metrics"]["matched_coverage"]["k"], 202)
        self.assertEqual(x["metrics"]["matched_coverage"]["uncovered"], 242)
        self.assertIsNone(x["metrics"]["matched_coverage"]["cross_epoch_delta"])
        self.assertEqual(x["metrics"]["proof_yield"]["single_exact_head_focused_proof"], 1.0)

    def test_timing_only_from_bounded_clock_measurement(self):
        x = evaluate(native(), start_s=10.5, end_s=15.1)
        self.assertEqual(x["metrics"]["time_to_evidence"]["measured_test_execution_seconds"], 4.6)
        self.assertIsNone(x["metrics"]["time_to_evidence"]["queue_p95_seconds"])

    def test_clock_reverse_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "clock"):
            evaluate(None, start_s=15.1, end_s=10.5)

    def test_denom_drift_rejected(self):
        x = native()
        x["files"]["DMAIC_V3/phases/phase4_improve.py"]["eligible"] = 134
        with self.assertRaisesRegex(ValueError, "denominator"):
            evaluate(x)

    def test_identity_schema_and_source_guard(self):
        for key, value, match in [
            ("checkout_sha", "invalid", "head"),
            ("phase4_source_blob", "b" * 40, "blob"),
            ("source_epoch", "N14", "epoch"),
            ("merge_admission", "GO", "merge"),
        ]:
            x = native()
            x[key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, match):
                evaluate(x)

    def test_proof_yield_cannot_be_given_by_too_few_tests(self):
        x = native()
        x["tests"] = 98
        with self.assertRaisesRegex(ValueError, "test"):
            evaluate(x)

    def test_root_closure_requires_distinct_authentication(self):
        with self.assertRaisesRegex(ValueError, "closure"):
            evaluate(native(), independently_verified_roots=1)

    def test_no_statistical_certificate_from_six_claimed_pulses(self):
        x = evaluate(native(), comparable_independent_pulses=6)
        state = x["metrics"]["statistical_control"]
        self.assertEqual(state["state"], "REQUIRES_SLOPE_EQUIVALENCE_AND_REVIEW")
        self.assertEqual(state["pca"], "NOT_QUALIFIED")
        self.assertEqual(state["bt"], "NO_PAIRWISE_OUTCOMES")
        self.assertEqual(state["six_sigma"], "NOT_ASSESSED")
        self.assertEqual(x["merge_admission"], "HOLD")


if __name__ == "__main__":
    unittest.main()
