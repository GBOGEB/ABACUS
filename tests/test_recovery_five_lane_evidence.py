"""Fail-closed five-lane receipt regression tests."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from recovery_five_lane_evidence import (
    bd_roots, coverage, crew, native, reconcile, review,
)

MAIN = "a" * 40
HEAD = "b" * 40


class FiveLaneTests(unittest.TestCase):
    def test_missing_evidence_is_never_zero(self):
        r = reconcile({"main_sha": MAIN, "head_sha": HEAD})
        self.assertIsNone(r["canonical_main_coverage"]["covered"])
        self.assertIsNone(r["changed_line_coverage"]["eligible"])
        self.assertIsNone(r["bd_distinct_roots"]["closed"])
        self.assertIsNone(r["crew_ldab_rex"]["verified_launches"])
        self.assertIsNone(r["governance_review"]["eligible_approval"])
        self.assertEqual(r["rhel8"]["status"], "UNKNOWN")
        self.assertFalse(r["merge_authorized"])

    def test_coverage_matched_scope_and_denominator(self):
        row = {"sha": MAIN, "covered": 201, "eligible": 300,
               "scope_id": "canonical", "config_sha256": "f" * 64,
               "run_id": 125, "artifact_id": 910}
        self.assertEqual(coverage(row, MAIN)["percent"], 67.0)
        with self.assertRaisesRegex(ValueError, "mismatch"):
            coverage(row, HEAD)
        with self.assertRaisesRegex(ValueError, "numerator"):
            coverage(dict(row, covered=301), MAIN)
        with self.assertRaisesRegex(ValueError, "provenance"):
            coverage(dict(row, artifact_id=None), MAIN)

    def test_changed_lines_require_exact_base(self):
        row = {"sha": HEAD, "base_sha": MAIN, "covered": 80,
               "eligible": 100, "scope_id": "diff",
               "config_sha256": "e" * 64, "run_id": 15,
               "artifact_id": 99}
        self.assertEqual(coverage(row, HEAD, MAIN)["percent"], 80)
        with self.assertRaisesRegex(ValueError, "mismatch"):
            coverage(row, HEAD, HEAD)

    def test_bd_root_distinctness_and_config(self):
        row = {"sha": HEAD, "complete": True,
               "scanner_config_sha256": "c" * 64,
               "opened": ["BD-a", "BD-b"], "closed": ["BD-c"],
               "reopened": [], "run_id": 10, "job_id": 99,
               "evidence_url": "https://github.com/x"}
        d = bd_roots(row, HEAD)
        self.assertEqual((d["opened"], d["closed"]), (2, 1))
        with self.assertRaisesRegex(ValueError, "overlap"):
            bd_roots(dict(row, closed=["BD-a"]), HEAD)
        self.assertEqual(bd_roots(dict(row, complete=False), HEAD)["status"],
                         "UNKNOWN")

    def test_unattested_crew_is_unknown(self):
        row = {"sha": HEAD, "authority_verified": False,
               "receipts": [{"launch_id": "forged"}]}
        self.assertIsNone(crew(row, HEAD)["verified_launches"])
        with self.assertRaisesRegex(ValueError, "Unauthenticated"):
            crew(dict(row, authority_verified=True), HEAD)

    def test_authenticated_launch_and_accepted_rex_are_separate(self):
        r = {"launch_id": "L1", "executor_identity_verified": True,
             "run_sha": HEAD, "run_id": 1, "job_id": 2,
             "receipt_url": "https://github.com/launch",
             "rex_status": "ACCEPTED",
             "rex_url": "https://github.com/rex",
             "ldab_session_id": "S1", "runner_id": 3,
             "debug_log_url": "https://github.com/debug"}
        item = {"sha": HEAD, "authority_verified": True, "receipts": [r]}
        self.assertEqual(crew(item, HEAD)["accepted_rex"], 1)
        self.assertEqual(crew(item, HEAD)["ldab_sessions"], 1)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            crew(dict(item, receipts=[r, r]), HEAD)

    def test_comments_and_self_review_cannot_approve(self):
        row = {"sha": HEAD, "reviewer_eligibility_verified": True,
               "pr_author": "owner",
               "reviews": [
                   {"state": "COMMENTED", "commit_id": HEAD,
                    "author": "reviewer", "eligible": True},
                   {"state": "APPROVED", "commit_id": HEAD,
                    "author": "owner", "eligible": True},
               ]}
        self.assertFalse(review(row, HEAD)["eligible_approval"])
        row["reviews"].append({"state": "APPROVED", "commit_id": HEAD,
                               "author": "reviewer", "eligible": True})
        self.assertTrue(review(row, HEAD)["eligible_approval"])
        self.assertFalse(review(row, HEAD)["merge_authorized"])

    def test_skipped_runtime_not_portability_pass(self):
        row = {"sha": HEAD, "status": "completed",
               "conclusion": "skipped", "run_id": 1,
               "job_id": 2, "url": "https://github.com/run"}
        self.assertEqual(native(row, HEAD)["status"], "SKIPPED")
        with self.assertRaisesRegex(ValueError, "mismatch"):
            native(row, MAIN)
        self.assertEqual(native(dict(row, status="queued"), HEAD)["status"],
                         "NONTERMINAL")


if __name__ == "__main__":
    unittest.main()
