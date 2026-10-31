"""Native GitHub evidence replay: positive, negative and boundary tests."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from cbd_native_evidence_metrics import replay

SOURCE = ROOT / "docs/ci/CBD_W2_NATIVE_EVIDENCE_20261017.json"


class NativeEvidenceMetricsTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(SOURCE.read_text(encoding="utf-8"))

    def assert_rejected(self, term):
        with self.assertRaisesRegex(ValueError, term):
            replay(self.data)

    def test_native_66_run_denominators(self):
        o = replay(self.data)
        self.assertEqual(o["schema"], "cbd.read_only_native_pulse.v1")
        self.assertEqual(o["first_red_step_reach"]["numerator"], 64)
        self.assertEqual(o["first_red_step_reach"]["denominator"], 66)
        self.assertEqual(o["log_sampling_reach"]["numerator"], 23)
        self.assertEqual(o["terminal_failed_latest_attempts"]["numerator"], 63)
        self.assertEqual(o["head_currentness"]["numerator"], 18)
        self.assertEqual(o["head_currentness"]["denominator"], 20)
        self.assertEqual(o["failed_jobs"], 125)
        self.assertEqual(o["failed_steps"], 135)
        self.assertEqual(o["resolver_attribution"]["signature_runs"], 13)
        self.assertEqual(o["resolver_attribution"]["pr_upper_bound"], 8)
        self.assertEqual(o["admission"], "HOLD")
        self.assertIsNone(o["matched_branch_coverage"])
        self.assertIsNone(o["queue_p95_seconds"])

    def test_repeatability_and_no_source_mutation(self):
        copy_before = copy.deepcopy(self.data)
        self.assertEqual(replay(self.data), replay(self.data))
        self.assertEqual(self.data, copy_before)

    def test_forged_schema_rejected(self):
        self.data["schema"] = "cbd.falsegreen.v1"
        self.assert_rejected("schema")

    def test_foreign_repository_rejected(self):
        self.data["repository"] = "OTHER/REPO"
        self.assert_rejected("foreign repository")

    def test_forged_atomic_rate_rejected(self):
        self.data["source_snapshot_rate_eligible"] = True
        self.assert_rejected("false atomic")

    def test_forged_merge_grant_rejected(self):
        self.data["authority"]["merge_admission"] = "PASS"
        self.assert_rejected("unauthorized")

    def test_forged_security_waiver_rejected(self):
        self.data["authority"]["security_waiver"] = True
        self.assert_rejected("unauthorized")

    def test_forged_source_writer_rejected(self):
        self.data["authority"]["source_mutation_authorized"] = True
        self.assert_rejected("unauthorized")

    def test_duplicate_run_id_rejected(self):
        self.data["run_evidence"][1]["run_id"] = self.data["run_evidence"][0]["run_id"]
        self.assert_rejected("duplicate")

    def test_boolean_run_id_rejected(self):
        self.data["run_evidence"][0]["run_id"] = True
        self.assert_rejected("invalid run ID")

    def test_bad_source_sha_rejected(self):
        self.data["run_evidence"][0]["source_sha"] = "bad"
        self.assert_rejected("invalid source SHA")

    def test_cross_sha_run_binding_rejected(self):
        self.data["run_evidence"][0]["head"] = "0" * 40
        self.assert_rejected("provenance mismatch")

    def test_negative_current_attempt_rejected(self):
        self.data["run_evidence"][0]["attempt"] = -1
        self.assert_rejected("provenance mismatch")

    def test_false_terminal_latest_verdict_rejected(self):
        self.data["run_evidence"][0]["authenticated"] = True
        self.assert_rejected("latest-attempt verdict")

    def test_false_terminal_success_rejected(self):
        row = next(r for r in self.data["run_evidence"] if r["authenticated"])
        row["result"] = "success"
        self.assert_rejected("latest-attempt verdict")

    def test_jobset_must_match_same_attempt(self):
        self.data["run_evidence"][0]["jobs"]["job_attempt_verified"] = False
        self.assert_rejected("exact-attempt")

    def test_missing_job_page_rejected(self):
        self.data["run_evidence"][0]["jobs"]["jobs_reported"] += 1
        self.assert_rejected("job denominator")

    def test_invalid_failed_step_count_rejected(self):
        row = next(r for r in self.data["run_evidence"] if r["jobs"]["failed_jobs"])
        row["jobs"]["failed_steps"] = 0
        self.assert_rejected("job/step denominator")

    def test_fabricated_first_red_number_rejected(self):
        self.data["metrics"]["observed_first_failed_step"] += 1
        self.assert_rejected("numerator/denominator")

    def test_first_red_identity_invalid_rejected(self):
        row = next(r for r in self.data["run_evidence"] if r["jobs"]["first_failed_step"])
        row["jobs"]["first_failed_step"]["step_number"] = True
        self.assert_rejected("first-red step")

    def test_log_must_bind_first_failed_job(self):
        row = next(r for r in self.data["run_evidence"] if r.get("log_evidence"))
        row["log_evidence"]["job_id"] = 42
        self.assert_rejected("log/first-red")

    def test_resolver_signature_requires_log_text(self):
        row = next(r for r in self.data["run_evidence"]
                   if "MATPLOTLIB_RESOLVER" in r.get("log_evidence", {}).get("signals", []))
        row["log_evidence"]["excerpt"] = []
        self.assert_rejected("supporting log text")

    def test_resolver_signature_requires_install_step(self):
        row = next(r for r in self.data["run_evidence"]
                   if "MATPLOTLIB_RESOLVER" in r.get("log_evidence", {}).get("signals", []))
        row["jobs"]["first_failed_step"]["step_name"] = "Run unrelated step"
        self.assert_rejected("resolver step")

    def test_fabricated_matplotlib_pr_reach_rejected(self):
        self.data["metrics"]["matplotlib_affected_prs"] = [2027]
        self.assert_rejected("aliases, stale heads or signature reach")

    def test_unreported_duplicate_aliases_rejected(self):
        self.data["metrics"]["aliases"] = 0
        self.assert_rejected("aliases")

    def test_stale_head_cannot_be_hidden(self):
        self.data["metrics"]["heads_stale"] = []
        self.assert_rejected("stale heads")

    def test_head_boolean_contradiction_rejected(self):
        self.data["head_readbacks"][0]["head_matches"] = False
        self.assert_rejected("false current-head")

    def test_duplicate_pr_head_record_rejected(self):
        self.data["head_readbacks"][1]["pr"] = self.data["head_readbacks"][0]["pr"]
        self.assert_rejected("duplicate head manifest")

    def test_invalid_declared_denominator_rejected(self):
        self.data["metrics"]["failed_jobs"] = 127
        self.assert_rejected("numerator/denominator")

    def test_false_accepted_root_closure_rejected(self):
        self.data["metrics"]["accepted_closed_roots"] = 1
        self.assert_rejected("unverified closure")

    def test_false_coverage_credit_rejected(self):
        self.data["metrics"]["validated_main_coverage_delta"] = 0.25
        self.assert_rejected("unverified closure")

    def test_snapshot_scope_unchanged(self):
        o = replay(self.data)
        self.assertEqual(o["observation_kind"], "NONATOMIC_LATEST_ATTEMPT_CENSUS")
        self.assertEqual(o["accepted_closures"], 0)
        self.assertIsNone(o["matched_statement_coverage"])
        self.assertNotIn("p_value", o)
        self.assertNotIn("fleet_failure_rate", o)


if __name__ == "__main__":
    unittest.main()
