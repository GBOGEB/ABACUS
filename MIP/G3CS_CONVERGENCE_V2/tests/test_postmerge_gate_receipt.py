"""Adversarial tests for W7 postmerge read-only evidence boundaries."""
import importlib.util
from pathlib import Path
import unittest

p = Path(__file__).resolve().parents[1] / "tools" / "postmerge_gate_receipt.py"
s = importlib.util.spec_from_file_location("postmerge_gate_receipt", p)
m = importlib.util.module_from_spec(s)
s.loader.exec_module(m)
A = "a" * 40
B = "b" * 40
C = "c" * 40
D = "d" * 64

def run(sha, rid, status="completed", conclusion="success"):
    return {"id": rid, "attempt": 1,
            "url": f"https://github.com/GBOGEB/ABACUS/actions/runs/{rid}",
            "head_sha": sha, "status": status, "conclusion": conclusion}

def sample():
    return {
        "schema": "codepurple.g3cs.postmerge-evidence.v1", "repository": "GBOGEB/ABACUS",
        "pr": {"number": 2235, "url": "https://github.com/GBOGEB/ABACUS/pull/2235",
               "merged": True, "head_sha": A, "parent_main_sha": B,
               "main_sha": C, "merge_commit_sha": C},
        "head_ci": {k: run(A, i + 100) for i, k in enumerate(("B0", "MATRIX", "A10", "SECURITY"))},
        "main_ci": {"B0": run(C, 201), "MATRIX": run(C, 202)},
        "governance": {"required_statuses_enforced": True, "last_push_approval_enforced": True,
                       "thread_resolution_enforced": True, "red_canary_blocked": True,
                       "independent_security_review_verified": True,
                       "required_approvals": 1, "eligible_approvals": 1},
        "coverage": {}, "first_red": {"before": "old-red", "after": "new-red"}
    }

def measure(sha, covered, eligible=100):
    return {"source_sha": sha, "covered": covered, "eligible": eligible,
            "selection_sha256": D, "tool_sha256": D, "scope_sha256": D}

class W7ReceiptTests(unittest.TestCase):
    def test_complete_source_claims_do_not_authorize_merge(self):
        r = m.evaluate(sample())
        self.assertEqual(r["merge_admission"], "HOLD")
        self.assertFalse(r["governed_merge_credit"])
        self.assertTrue(r["source_reported_proofs_complete"])
        self.assertIsNone(r["accepted_rex_receipts"])

    def test_queued_ci_cannot_pass(self):
        p = sample()
        p["head_ci"]["B0"] = run(A, 100, "queued", None)
        r = m.evaluate(p)
        self.assertFalse(r["source_reported_proofs_complete"])
        self.assertIn("head_ci.B0", r["unmet_or_unverified"])

    def test_missing_governance_denied_not_zero(self):
        p = sample()
        p["governance"] = {}
        r = m.evaluate(p)
        self.assertEqual(r["merge_admission"], "HOLD")
        self.assertIn("governance.eligible_approvals", r["unmet_or_unverified"])

    def test_wrong_source_run_rejected(self):
        p = sample()
        p["main_ci"]["B0"]["head_sha"] = A
        with self.assertRaisesRegex(ValueError, "selected source SHA"):
            m.evaluate(p)

    def test_mismatched_merge_sha_rejected(self):
        p = sample()
        p["pr"]["merge_commit_sha"] = D[:40]
        with self.assertRaisesRegex(ValueError, "reconcile"):
            m.evaluate(p)

    def test_native_id_replay_rejected(self):
        p = sample()
        p["head_ci"]["MATRIX"] = run(A, 100)
        with self.assertRaisesRegex(ValueError, "reuses"):
            m.evaluate(p)

    def test_fake_nonterminal_success_rejected(self):
        p = sample()
        p["main_ci"]["B0"] = run(C, 201, "in_progress", "success")
        with self.assertRaisesRegex(ValueError, "nonterminal"):
            m.evaluate(p)

    def test_comparable_coverage_pp(self):
        p = sample()
        p["coverage"]["main"] = {"before": measure(B, 38), "after": measure(C, 46)}
        r = m.evaluate(p)["main_coverage"]
        self.assertEqual(r["delta_covered"], 8)
        self.assertEqual(r["delta_pp"], 8)
        self.assertEqual(r["status"], "PAIRED_SOURCE_REPORTED")

    def test_changed_denominator_noncomparable(self):
        p = sample()
        p["coverage"]["pr_diff"] = {"before": measure(B, 38),
                                   "after": measure(A, 46, eligible=102)}
        self.assertEqual(m.evaluate(p)["pr_diff_coverage"]["status"], "NONCOMPARABLE")

    def test_missing_coverage_unknown(self):
        r = m.evaluate(sample())
        self.assertEqual(r["main_coverage"]["status"], "UNKNOWN")
        self.assertIsNone(r["main_coverage"]["delta_pp"])

    def test_coverage_wrong_sha_rejected(self):
        p = sample()
        p["coverage"]["main"] = {"before": measure(A, 35), "after": measure(C, 42)}
        with self.assertRaisesRegex(ValueError, "pinned baseline"):
            m.evaluate(p)

    def test_negative_coverage_rejected(self):
        p = sample()
        p["coverage"]["pr_broad"] = {"before": measure(B, -1), "after": measure(A, 1)}
        with self.assertRaisesRegex(ValueError, "integer"):
            m.evaluate(p)

    def test_displaced_red_not_root_closure(self):
        r = m.evaluate(sample())
        self.assertEqual(r["first_red_transition"], "CANDIDATE_DISPLACED_NOT_ROOT_CLOSED")
        self.assertIsNone(r["accepted_causal_root_closures"])

    def test_staged_dispatch_not_inferred(self):
        r = m.evaluate(sample())
        self.assertIsNone(r["authenticated_crew_launch_ids"])
        self.assertFalse(r["authority_transfer"])

if __name__ == "__main__":
    unittest.main()
