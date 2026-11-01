"""Contract tests for source-owned CBD workflow manifestation planner."""

import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import cbd_workflow_failure_waves as cbd

BASE = (
    Path(__file__).resolve().parents[1]
    / "docs/ci/CBD_6PR_FAILED_RUN_OBSERVATIONS_20261017.json"
)


class CBDTest(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(BASE.read_text())

    def test_native_sample_counts(self):
        o = cbd.produce(self.data)
        self.assertEqual(12, o["observed"]["run_association_count"])
        self.assertIsNone(o["observed"]["run_attempt_count"])
        self.assertEqual(6, o["observed"]["pr_count"])
        self.assertEqual(12, o["observed"]["conclusions"]["failure"])
        self.assertIsNone(o["observed"]["confirmed_causal_root_count"])

    def test_deterministic_no_mutation(self):
        old = copy.deepcopy(self.data)
        self.assertEqual(cbd.produce(self.data), cbd.produce(self.data))
        self.assertEqual(old, self.data)

    def test_duplicate_attempt_rejected(self):
        self.data["observations"].append(copy.deepcopy(self.data["observations"][0]))
        with self.assertRaises(ValueError):
            cbd.produce(self.data)

    def test_short_sha_rejected(self):
        self.data["observations"][0]["sha"] = "deadbeef"
        with self.assertRaises(ValueError):
            cbd.produce(self.data)

    def test_forged_merge_admission_rejected(self):
        self.data["authority"]["merge_admission"] = "PASS"
        with self.assertRaises(ValueError):
            cbd.produce(self.data)

    def test_forged_security_waiver_rejected(self):
        self.data["authority"]["security_waiver"] = True
        with self.assertRaises(ValueError):
            cbd.produce(self.data)

    def test_forged_url_rejected(self):
        self.data["observations"][0]["url"] = "https://evil.example/"
        with self.assertRaises(ValueError):
            cbd.produce(self.data)

    def test_shared_workflow_not_accepted_root(self):
        o = cbd.produce(self.data)
        root = next(
            x
            for x in o["candidate_families"]
            if x["candidate_family"] == "INTEGRATED_TEST_SUITE"
        )
        self.assertEqual(5, root["unique_prs_affected"])
        self.assertFalse(root["root_confirmed"])
        self.assertFalse(root["first_red_confirmed"])
        self.assertFalse(root["independent_admission"])

    def test_path_collisions_serialized(self):
        o = cbd.produce(self.data)
        rows = [
            x
            for x in o["candidate_disjoint_waves"]
            if x["candidate_family"] in ("MATRIX_COMPATIBILITY", "LEGACY_PIPELINE")
        ]
        self.assertEqual(2, len(rows))
        self.assertTrue(all(x["source_mutation_authorized"] is False for x in rows))

    def test_unknown_workflow_reader_only(self):
        self.data["observations"][0]["workflow"] = "NEW_UNKNOWN_GATE"
        o = cbd.produce(self.data)
        x = next(
            x
            for x in o["candidate_disjoint_waves"]
            if x["candidate_family"].startswith("UNCLASSIFIED_WORKFLOW:")
        )
        self.assertEqual("READER", x["worker_type"])

    def test_no_workflow_success_inferred_from_missing(self):
        self.assertEqual(
            0, cbd.produce(self.data)["observed"]["conclusions"]["success"]
        )
        self.assertIsNone(cbd.produce(self.data)["observed"]["matched_coverage_delta"])


COHORT_A = (
    Path(__file__).resolve().parents[1]
    / "docs/ci/CBD_10PR_A_FAILED_RUN_OBSERVATIONS_20261017.json"
)
COHORT_B = (
    Path(__file__).resolve().parents[1]
    / "docs/ci/CBD_10PR_B_FAILED_RUN_OBSERVATIONS_20261017.json"
)


class LargerCohortTest(unittest.TestCase):
    def setUp(self):
        self.a = json.loads(COHORT_A.read_text(encoding="utf-8"))
        self.b = json.loads(COHORT_B.read_text(encoding="utf-8"))

    def test_20_pr_66_failure_cohort_preserves_denominators(self):
        merged = cbd.combine_sources([self.a, self.b])
        result = cbd.produce(merged)
        measured = result["observed"]
        self.assertEqual(20, measured["pr_count"])
        self.assertEqual(19, measured["prs_with_failed_workflows"])
        self.assertEqual(533, measured["first_page_workflow_associations_seen"])
        self.assertEqual(66, measured["failure_workflow_associations"])
        self.assertEqual(66, measured["distinct_failed_run_ids"])
        self.assertEqual(66, measured["unknown_run_attempt_associations"])
        self.assertIsNone(measured["run_attempt_count"])
        self.assertIsNone(measured["matched_coverage_delta"])
        self.assertEqual(0, measured["duplicate_failed_run_associations"])
        self.assertEqual(19, measured["candidate_family_count"])
        self.assertTrue(
            all(
                not item["source_mutation_authorized"]
                for item in result["candidate_disjoint_waves"]
            )
        )

    def test_zero_failure_pr_retained_in_sampling_denominator(self):
        output = cbd.produce(cbd.combine_sources([self.a, self.b]))
        self.assertEqual(
            0,
            next(
                row["failed_associations_seen"]
                for row in self.b["sampled_pr_heads"]
                if row["pr"] == 2033
            ),
        )
        self.assertEqual(20, output["observed"]["pr_count"])
        self.assertEqual(19, output["observed"]["prs_with_failed_workflows"])

    def test_observation_wrong_pr_head_fails_closed(self):
        self.a["observations"][0]["sha"] = "0" * 40
        with self.assertRaises(ValueError):
            cbd.combine_sources([self.a, self.b])

    def test_denominator_mismatch_fails_closed(self):
        self.a["sampled_pr_heads"][0]["failed_associations_seen"] += 1
        with self.assertRaises(ValueError):
            cbd.combine_sources([self.a, self.b])

    def test_duplicate_pr_across_cohorts_fails_closed(self):
        self.b["sampled_pr_heads"][0] = copy.deepcopy(self.a["sampled_pr_heads"][0])
        with self.assertRaises(ValueError):
            cbd.combine_sources([self.a, self.b])

    def test_forged_attempt_boolean_fails_closed(self):
        self.a["observations"][0]["attempt"] = True
        with self.assertRaises(ValueError):
            cbd.combine_sources([self.a, self.b])

    def test_same_run_alias_not_double_counted_as_distinct_run(self):
        original = json.loads(BASE.read_text(encoding="utf-8"))
        alias = copy.deepcopy(original["observations"][0])
        alias["pr"] = 999
        original["observations"].append(alias)
        result = cbd.produce(original)
        self.assertEqual(13, result["observed"]["run_association_count"])
        self.assertEqual(12, result["observed"]["distinct_failed_run_ids"])
        self.assertEqual(1, result["observed"]["duplicate_failed_run_associations"])
        self.assertIsNone(result["observed"]["run_attempt_count"])

    def test_alias_conflicting_head_is_rejected(self):
        original = json.loads(BASE.read_text(encoding="utf-8"))
        alias = copy.deepcopy(original["observations"][0])
        alias["pr"] = 999
        alias["sha"] = "1" * 40
        original["observations"].append(alias)
        with self.assertRaises(ValueError):
            cbd.produce(original)

    def test_confirmed_attempt_solo_count_is_not_guessed(self):
        original = json.loads(BASE.read_text(encoding="utf-8"))
        original["observations"] = original["observations"][:1]
        original["observations"][0]["attempt"] = 5
        output = cbd.produce(original)
        self.assertEqual(1, output["observed"]["run_attempt_count"])
        self.assertEqual(0, output["observed"]["unknown_run_attempt_associations"])

    def test_multisource_requires_complete_head_manifest(self):
        original = json.loads(BASE.read_text(encoding="utf-8"))
        with self.assertRaises(ValueError):
            cbd.combine_sources([original, self.a])

    def test_unclassified_security_never_promotes_to_merge(self):
        output = cbd.produce(cbd.combine_sources([self.a, self.b]))
        families = {x["candidate_family"]: x for x in output["candidate_families"]}
        self.assertIn("SEMGREP_SECURITY", families)
        self.assertIn("OSV_SECURITY", families)
        for family in ("SEMGREP_SECURITY", "OSV_SECURITY"):
            self.assertFalse(families[family]["root_confirmed"])
            self.assertFalse(families[family]["independent_admission"])


if __name__ == "__main__":
    unittest.main()
