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
    def test_frozen_three_cohort_source_denominators(self):
        result = produce_cohorts(snapshots())
        rec = result["cohort_reconciliation"]
        self.assertEqual(rec["source_document_count"], 3)
        self.assertEqual(rec["declared_observation_rows"], 78)
        self.assertIsNone(rec["distinct_run_attempts"])
        self.assertEqual(rec["distinct_declared_run_ids"], 66)
        self.assertEqual(rec["cross_source_duplicate_rows"], 12)
        self.assertEqual(rec["unknown_attempt_associations"], 78)
        self.assertEqual(rec["snapshots_without_head_manifests"], 1)
        self.assertEqual(rec["distinct_declared_pr_heads"], 19)
        self.assertIsNone(result["observed"]["run_attempt_count"])
        self.assertEqual(result["observed"]["run_association_count"], 66)
        self.assertEqual(result["observed"]["conclusions"]["failure"], 66)
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
        self.assertIsNone(result["cohort_reconciliation"]["distinct_run_attempts"])
        self.assertEqual(result["cohort_reconciliation"]["distinct_declared_run_ids"], 12)
        self.assertEqual(result["cohort_reconciliation"]["cross_source_duplicate_rows"], 24)
        self.assertEqual(result["cohort_reconciliation"]["distinct_source_documents"], 1)

    def test_same_run_with_different_workflow_rejected(self):
        data = snapshots()
        forged = copy.deepcopy(data[0])
        forged["observations"][0]["workflow"] = "fake-other-workflow"
        with self.assertRaisesRegex(ValueError, "conflicting cross-attempt"):
            produce_cohorts([data[0], forged])

    def test_same_run_with_different_pr_rejected(self):
        data = snapshots()
        forged = copy.deepcopy(data[0])
        forged["observations"][0]["pr"] = 99999
        with self.assertRaisesRegex(ValueError, "conflicting cross-attempt"):
            produce_cohorts([data[0], forged])

    def test_same_pr_with_changed_sha_rejected(self):
        data = snapshots()
        forged = copy.deepcopy(data[0])
        forged["observations"][0]["sha"] = "1" * 40
        with self.assertRaisesRegex(ValueError, "conflicting cross-attempt"):
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


    def test_nonatomic_source_ingestion_pulses_are_not_time_series(self):
        result = produce_cohorts(snapshots())
        rec = result["cohort_reconciliation"]
        pulses = rec["ingestion_pulses"]
        self.assertEqual([12, 49, 78], [p["declared_rows_cumulative"] for p in pulses])
        self.assertEqual([6, 12, 19], [p["distinct_failed_pr_heads_cumulative"] for p in pulses])
        self.assertEqual([12, 37, 66], [p["distinct_run_ids_cumulative"] for p in pulses])
        self.assertTrue(all(p["kind"] == "SOURCE_INGESTION_NOT_TEMPORAL_IMPROVEMENT" for p in pulses))
        self.assertEqual(rec["distinct_manifested_pr_heads"], 20)
        self.assertEqual(rec["manifested_zero_failure_prs"], [2033])
        self.assertEqual(rec["non_atomic_manifest_workflow_associations"], 533)
        self.assertEqual(rec["non_atomic_manifest_failed_associations"], 66)
        self.assertEqual(rec["manifest_comparability"], "NOT_A_DENOMINATOR_FOR_UNION_PASS_RATE")

    def test_unknown_to_known_same_run_attempt_fails_closed(self):
        source = snapshots()[0]
        other = copy.deepcopy(source)
        other["observations"][0]["attempt"] = 1
        with self.assertRaisesRegex(ValueError, "ambiguous unknown/known"):
            produce_cohorts([source, other])

    def test_distinct_known_attempts_are_not_collapsed(self):
        source = snapshots()[0]
        first = copy.deepcopy(source)
        second = copy.deepcopy(source)
        for row in first["observations"]:
            row["attempt"] = 1
        for row in second["observations"]:
            row["attempt"] = 2
        result = produce_cohorts([first, second])
        rec = result["cohort_reconciliation"]
        self.assertEqual(rec["declared_observation_rows"], 24)
        self.assertEqual(rec["distinct_run_attempts"], 24)
        self.assertEqual(rec["distinct_declared_run_ids"], 12)
        self.assertEqual(rec["unknown_attempt_associations"], 0)

    def test_repeated_run_identity_cannot_change_workflow_across_attempt(self):
        first = snapshots()[0]
        second = copy.deepcopy(first)
        for row in second["observations"]:
            row["attempt"] = 1
        second["observations"][0]["workflow"] = "forged-new-workflow"
        with self.assertRaisesRegex(ValueError, "conflicting cross-attempt"):
            produce_cohorts([first, second])

    def test_manifest_conflicts_fail_closed(self):
        first = snapshots()[1]
        second = copy.deepcopy(first)
        second["sampled_pr_heads"][0]["workflow_associations_seen"] += 1
        with self.assertRaisesRegex(ValueError, "conflicting sampled PR head manifest"):
            produce_cohorts([first, second])


    def test_distinct_run_same_pr_conflicting_sha_rejected(self):
        source = snapshots()[0]
        forged = copy.deepcopy(source)
        row = forged["observations"][0]
        row["sha"] = "1" * 40
        row["run_id"] += 10000000000
        row["url"] = "https://github.com/GBOGEB/ABACUS/actions/runs/" + str(row["run_id"])
        with self.assertRaisesRegex(ValueError, "incompatible pull-head"):
            produce_cohorts([forged])


if __name__ == "__main__":
    unittest.main()
