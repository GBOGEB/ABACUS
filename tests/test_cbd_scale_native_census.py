"""CBD observational-scale regression checks; no merge or dispatch credit."""

import copy
import json
import unittest
from pathlib import Path

from scripts import cbd_workflow_failure_waves as cbd

ROOT = Path(__file__).resolve().parents[1]
COHORT = ROOT / "docs/ci/CBD_16PR_43_NATIVE_FAILED_RUN_ATTEMPTS_20261017.json"


class CBDScaleCohortTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(COHORT.read_text(encoding="utf-8"))

    def test_source_bound_native_denominator(self):
        result = cbd.produce(self.data)
        self.assertEqual(result["observed"]["pr_count"], 16)
        self.assertEqual(result["observed"]["run_attempt_count"], 43)
        self.assertEqual(result["observed"]["conclusions"]["failure"], 43)

    def test_actual_rerun_attempts_are_preserved(self):
        records = self.data["observations"]
        self.assertEqual(sum(row["attempt"] > 1 for row in records), 5)
        self.assertEqual(len({(r["run_id"], r["attempt"]) for r in records}), 43)

    def test_results_do_not_imply_closure(self):
        result = cbd.produce(self.data)
        self.assertIsNone(result["observed"]["confirmed_causal_root_count"])
        self.assertIsNone(result["observed"]["accepted_closed_root_count"])
        self.assertIsNone(result["observed"]["matched_coverage_delta"])
        self.assertFalse(any(x["root_confirmed"] for x in result["candidate_families"]))

    def test_no_parallel_source_mutation(self):
        result = cbd.produce(self.data)
        waves = result["candidate_disjoint_waves"]
        self.assertTrue(any(x["scheduler_status"] == "SERIALIZE_PATH_COLLISION" for x in waves))
        self.assertFalse(any(x["source_mutation_authorized"] for x in waves))

    def test_determinism_and_input_immutability(self):
        original = copy.deepcopy(self.data)
        self.assertEqual(cbd.produce(self.data), cbd.produce(self.data))
        self.assertEqual(self.data, original)

    def test_duplicate_identity_is_rejected(self):
        self.data["observations"].append(copy.deepcopy(self.data["observations"][0]))
        with self.assertRaises(ValueError):
            cbd.produce(self.data)

    def test_bad_provenance_is_rejected(self):
        for field, value in (("sha", "short"), ("attempt", 0)):
            changed = copy.deepcopy(self.data)
            changed["observations"][0][field] = value
            with self.assertRaises(ValueError):
                cbd.produce(changed)

    def test_observed_manifestations_are_not_causal_roots(self):
        result = cbd.produce(self.data)
        self.assertEqual(
            sum(row["failed_run_attempts"] for row in result["candidate_families"]), 43
        )
        self.assertTrue(all(not row["first_red_confirmed"] for row in result["candidate_families"]))


if __name__ == "__main__":
    unittest.main()
