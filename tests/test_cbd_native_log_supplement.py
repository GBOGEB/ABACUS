"""Adversarial native first-red supplement contract and classifier tests."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from cbd_native_evidence_metrics import (
    classify_supplement_first_red,
    replay_supplement,
)

SNAPSHOT = ROOT / "docs/ci/CBD_W2_NATIVE_EVIDENCE_20261017.json"
SUPPLEMENT = ROOT / "docs/ci/CBD_W3_NATIVE_LOG_SUPPLEMENT_20261017.json"


class SupplementEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        self.supplement = json.loads(SUPPLEMENT.read_text(encoding="utf-8"))

    def test_native_log_reach_growth_is_attributable_not_recovery(self):
        out = replay_supplement(self.snapshot, self.supplement)
        self.assertEqual(out["log_sampling_reach"]["numerator"], 38)
        self.assertEqual(out["log_sampling_reach"]["denominator"], 66)
        self.assertEqual(out["supplemental_logs"], 15)
        self.assertEqual(out["resolver_attribution"]["signature_runs"], 14)
        self.assertEqual(out["resolver_attribution"]["accepted_root_closures"], 0)
        self.assertEqual(out["admission"], "HOLD")
        self.assertEqual(out["selection_bias"], "TARGETED_NOT_INFERENTIAL")
        self.assertIsNone(out["matched_statement_coverage"])

    def test_determinism_and_no_mutation(self):
        a = copy.deepcopy(self.snapshot)
        b = copy.deepcopy(self.supplement)
        self.assertEqual(replay_supplement(a, b), replay_supplement(a, b))
        self.assertEqual(a, self.snapshot)
        self.assertEqual(b, self.supplement)

    def test_classified_signatures_are_exactly_ten_distinct_families(self):
        out = replay_supplement(self.snapshot, self.supplement)
        c = out["classified_first_red_supplement"]
        self.assertEqual(len(c), 10)
        self.assertEqual(sum(c.values()), 15)
        self.assertEqual(c["GOVERNANCE_POLICY_INVENTORY"], 4)
        self.assertEqual(c["SAFETY_NONZERO"], 3)
        self.assertEqual(c["QUALITY_BLACK_ISORT"], 1)

    def test_naive_isort_mention_is_not_an_isort_failure(self):
        r = {"first_failed_step": "Install dependencies",
             "diagnostic_tail_sanitized": ["pip install pytest isort"],
             "untrusted_broad_search_hits": ["isort"]}
        self.assertEqual(classify_supplement_first_red(r), "UNCLASSIFIED_REQUIRES_REVIEW")

    def test_true_isort_requires_explicit_failing_scan(self):
        r = next(x for x in self.supplement["records"]
                 if x["validated_signature"] == "QUALITY_BLACK_ISORT")
        self.assertEqual(classify_supplement_first_red(r), "QUALITY_BLACK_ISORT")
        spoof = copy.deepcopy(r)
        spoof["diagnostic_tail_sanitized"] = ["pip install isort"]
        self.assertEqual(classify_supplement_first_red(spoof), "UNCLASSIFIED_REQUIRES_REVIEW")

    def test_black_reformat_distinct_from_isort(self):
        r = next(x for x in self.supplement["records"]
                 if x["validated_signature"] == "BLACK_REFORMAT")
        self.assertEqual(classify_supplement_first_red(r), "BLACK_REFORMAT")
        self.assertNotEqual(classify_supplement_first_red(r), "QUALITY_BLACK_ISORT")

    def test_external_api_rate_limit_is_not_code_vulnerability(self):
        r = next(x for x in self.supplement["records"]
                 if x["validated_signature"] == "GITHUB_API_RATE_LIMIT")
        self.assertEqual(classify_supplement_first_red(r), "GITHUB_API_RATE_LIMIT")

    def test_external_actor_forged_snapshot_scope_rejected(self):
        self.supplement["source_snapshot_sha"] = "f" * 40
        with self.assertRaisesRegex(ValueError, "checkpoint"):
            replay_supplement(self.snapshot, self.supplement)

    def test_duplicate_run_id_rejected(self):
        self.supplement["records"][1]["run_id"] = self.supplement["records"][0]["run_id"]
        with self.assertRaisesRegex(ValueError, "duplicate or unbound"):
            replay_supplement(self.snapshot, self.supplement)

    def test_forged_job_id_rejected(self):
        self.supplement["records"][0]["job_id"] = 999
        with self.assertRaisesRegex(ValueError, "run/job/step"):
            replay_supplement(self.snapshot, self.supplement)

    def test_forged_run_attempt_rejected(self):
        self.supplement["records"][0]["attempt"] = 400
        with self.assertRaisesRegex(ValueError, "run/job/step"):
            replay_supplement(self.snapshot, self.supplement)

    def test_forged_first_step_rejected(self):
        self.supplement["records"][0]["first_failed_step"] = "Other unbound step"
        with self.assertRaisesRegex(ValueError, "run/job/step"):
            replay_supplement(self.snapshot, self.supplement)

    def test_forged_witness_for_known_matplotlib_rejected(self):
        r = next(x for x in self.supplement["records"]
                 if x["validated_signature"] == "MATPLOTLIB_RESOLVER")
        r["diagnostic_tail_sanitized"] = ["pytest-asyncio installed"]
        with self.assertRaisesRegex(ValueError, "unsupported first-red"):
            replay_supplement(self.snapshot, self.supplement)

    def test_incidental_word_will_not_count_as_genuine_isort(self):
        r = next(x for x in self.supplement["records"]
                 if x["validated_signature"] == "MATPLOTLIB_RESOLVER")
        r["untrusted_broad_search_hits"] = ["isort", "black", "safety"]
        self.assertEqual(replay_supplement(self.snapshot, self.supplement)
                         ["classified_first_red_supplement"]["MATPLOTLIB_RESOLVER"], 1)

    def test_false_log_sampling_denominator_rejected(self):
        self.supplement["new_logs_downloaded"] += 1
        with self.assertRaisesRegex(ValueError, "denominators"):
            replay_supplement(self.snapshot, self.supplement)

    def test_known_log_cannot_be_counted_twice(self):
        sample = next(x for x in self.snapshot["run_evidence"] if x.get("log_evidence"))
        row = self.supplement["records"][0]
        row["run_id"] = sample["run_id"]
        with self.assertRaisesRegex(ValueError, "duplicates previously sampled"):
            replay_supplement(self.snapshot, self.supplement)

    def test_false_source_root_closure_rejected(self):
        self.supplement["accepted_root_closures"] = 1
        with self.assertRaisesRegex(ValueError, "authority"):
            replay_supplement(self.snapshot, self.supplement)

    def test_missing_raw_crypto_hash_not_mislabeled_as_byte_proof(self):
        self.assertTrue(all(r["raw_log_sha256"] is None
                            for r in self.supplement["records"]))
        out = replay_supplement(self.snapshot, self.supplement)
        self.assertTrue(out["historical_first_red_proof_only"])

    def test_unsupported_class_cannot_claim_admission(self):
        self.supplement["records"][0]["validated_signature"] = "ISORT_SAFETY_PASS"
        with self.assertRaisesRegex(ValueError, "unsupported first-red"):
            replay_supplement(self.snapshot, self.supplement)


if __name__ == "__main__":
    unittest.main()
