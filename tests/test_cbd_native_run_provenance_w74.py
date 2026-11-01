"""W74 adversarial, reverse and positive controls for native run identity."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import cbd_workflow_failure_waves as cbd

SOURCE = ROOT / "docs/ci/CBD_6PR_FAILED_RUN_OBSERVATIONS_20261017.json"


def fixture():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    source["observations"] = [copy.deepcopy(source["observations"][0])]
    return source


class NativeRunProvenanceW74(unittest.TestCase):
    def pair(self):
        source = fixture()
        rerun = copy.deepcopy(source["observations"][0])
        rerun["attempt"] = 2
        rerun["conclusion"] = "success"
        source["observations"].append(rerun)
        return source

    def test_valid_rerun_preserves_run_id_and_allows_changed_conclusion(self):
        source = self.pair()
        before = copy.deepcopy(source)
        result = cbd.produce(source)
        self.assertEqual(result["observed"]["run_association_count"], 2)
        self.assertEqual(result["observed"]["conclusions"]["failure"], 1)
        self.assertEqual(result["observed"]["conclusions"]["success"], 1)
        self.assertEqual(source, before)

    def test_reverse_order_same_observations_and_no_root_promotion(self):
        source = self.pair()
        other = copy.deepcopy(source)
        other["observations"].reverse()
        for row in (cbd.produce(source), cbd.produce(other)):
            self.assertIsNone(row["observed"]["confirmed_causal_root_count"])
            self.assertIsNone(row["observed"]["matched_coverage_delta"])
            self.assertTrue(
                all(
                    not w["source_mutation_authorized"]
                    for w in row["candidate_disjoint_waves"]
                )
            )

    def test_different_workflow_same_run_across_attempt_rejected(self):
        source = self.pair()
        source["observations"][1]["workflow"] = "forged-gate"
        with self.assertRaisesRegex(ValueError, "cross.attempt"):
            cbd.produce(source)

    def test_different_source_sha_same_run_across_attempt_rejected(self):
        source = self.pair()
        source["observations"][1]["sha"] = "f" * 40
        with self.assertRaisesRegex(ValueError, "cross.attempt"):
            cbd.produce(source)

    def test_reverse_conflicting_order_also_rejected(self):
        source = self.pair()
        source["observations"][1]["workflow"] = "forged-gate"
        source["observations"].reverse()
        with self.assertRaisesRegex(ValueError, "cross.attempt"):
            cbd.produce(source)

    def test_same_attempt_changed_conclusion_rejected(self):
        source = self.pair()
        source["observations"][1]["attempt"] = None
        with self.assertRaises(ValueError):
            cbd.produce(source)

    def test_boolean_and_zero_attempts_are_not_valid(self):
        for attempt in (True, False, 0, -1):
            with self.subTest(attempt=attempt):
                source = self.pair()
                source["observations"][1]["attempt"] = attempt
                with self.assertRaises(ValueError):
                    cbd.produce(source)

    def test_unauthorized_waiver_cannot_pass(self):
        source = self.pair()
        source["authority"]["security_waiver"] = True
        with self.assertRaises(ValueError):
            cbd.produce(source)


if __name__ == "__main__":
    unittest.main()
