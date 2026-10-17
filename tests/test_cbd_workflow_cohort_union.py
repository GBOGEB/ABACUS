"""Positive and adversarial regression tests for CBD multi-cohort reconciliation."""

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from cbd_workflow_cohort_union import produce_cohorts

FILES = (
    "CBD_6PR_FAILED_RUN_OBSERVATIONS_20261017.json",
    "CBD_10PR_A_FAILED_RUN_OBSERVATIONS_20261017.json",
    "CBD_10PR_B_FAILED_RUN_OBSERVATIONS_20261017.json",
)


def snapshots():
    return [json.loads((ROOT / "docs" / "ci" / name).read_text()) for name in FILES]


class CohortUnionTests(unittest.TestCase):
    def test_frozen_three_cohort_native_denominators(self):
        result = produce_cohorts(snapshots())
        rec = result["cohort_reconciliation"]
        self.assertEqual(rec["source_document_count"], 3)
        self.assertEqual(rec["declared_observation_rows"], 78)
        self.assertEqual(rec["distinct_run_attempts"], 78)
        self.assertEqual(rec["distinct_declared_pr_heads"], 19)
        self.assertEqual(result["observed"]["run_attempt_count"], 78)
        self.assertEqual(result["observed"]["conclusions"]["failure"], 78)
        self.assertIsNone(result["observed"]["confirmed_causal_root_count"])
        self.assertIsNone(rec["matched_coverage"])
        self.assertEqual(rec["admission"], "HOLD")

    def test_deterministic_and_does_not_mutate_sources(self):
        data = snapshots()
        before = copy.deepcopy(data)
        self.assertEqual(produce_cohorts(data), produce_cohorts(data))
        self.assertEqual(data, before)

    def test_identical_overlapping_row_deduplicated(self):
        data = snapshots()
        data = [data[0], copy.deepcopy(data[0]), copy.deepcopy(data[0])]
        result = produce_cohorts(data)
        self.assertEqual(result["cohort_reconciliation"]["declared_observation_rows"], 36)
        self.assertEqual(result["cohort_reconciliation"]["distinct_run_attempts"], 12)
        self.assertEqual(result["cohort_reconciliation"]["cross_source_duplicate_rows"], 24)
        self.assertEqual(result["cohort_reconciliation"]["distinct_source_documents"], 1)

    def test_same_run_with_different_workflow_rejected(self):
        data = snapshots()
        forged = copy.deepcopy(data[0])
        forged["observations"][0]["workflow"] = "fake-other-workflow"
        with self.assertRaisesRegex(ValueError, "conflicting run-attempt"):
            produce_cohorts([data[0], forged])

    def test_same_run_with_different_pr_rejected(self):
        data = snapshots()
        forged = copy.deepcopy(data[0])
        forged["observations"][0]["pr"] = 99999
        with self.assertRaisesRegex(ValueError, "conflicting run-attempt"):
            produce_cohorts([data[0], forged])

    def test_same_pr_with_changed_sha_rejected(self):
        data = snapshots()
        forged = copy.deepcopy(data[0])
        forged["observations"][0]["sha"] = "1" * 40
        with self.assertRaisesRegex(ValueError, "incompatible pull-head"):
            produce_cohorts([data[0], forged])

    def test_security_waiver_fails_closed(self):
        data = snapshots()
        data[0]["authority"]["security_waiver"] = True
        with self.assertRaises(ValueError):
            produce_cohorts(data)

    def test_spoofed_url_fails_closed(self):
        data = snapshots()
        data[0]["observations"][0]["url"] = "https://fake.test/run/1"
        with self.assertRaises(ValueError):
            produce_cohorts(data)

    def test_missing_source_fails_closed(self):
        with self.assertRaises(ValueError):
            produce_cohorts([])
        with self.assertRaises(ValueError):
            produce_cohorts([{}])
        with self.assertRaises(ValueError):
            produce_cohorts([None])

    def test_invalid_run_attempt_identity_fails_closed(self):
        data = snapshots()
        data[0]["observations"][0]["run_id"] = True
        with self.assertRaises(ValueError):
            produce_cohorts(data)
        data = snapshots()
        data[0]["observations"][0]["attempt"] = True
        with self.assertRaises(ValueError):
            produce_cohorts(data)

    def test_unverified_coverage_never_promoted_to_zero(self):
        result = produce_cohorts(snapshots())
        rec = result["cohort_reconciliation"]
        self.assertEqual(rec["job_first_red_verification"], "NOT_LIVE_VERIFIED")
        self.assertEqual(rec["current_head_verification"], "NOT_LIVE_VERIFIED")
        self.assertIsNone(rec["root_closure_credit"])
        self.assertTrue(all(not item["root_confirmed"] for item in result["candidate_families"]))
        self.assertTrue(all(not item["source_mutation_authorized"] for item in result["candidate_disjoint_waves"]))


if __name__ == "__main__":
    unittest.main()
