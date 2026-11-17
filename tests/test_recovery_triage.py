"""Security negative tests for read-only exact-head first-red grouping."""

import copy
import unittest

from mission_control_lite.recovery_triage import fingerprint, reconcile

A = "a" * 40
B = "b" * 40


def obs(head=A, run=42, job=101, message="API rate limit exceeded for installation"):
    return {
        "repository": "GBOGEB/ABACUS",
        "head_sha": head,
        "run_id": run,
        "job_id": job,
        "attempt": 1,
        "status": "completed",
        "conclusion": "failure",
        "first_red": message,
    }


class RecoveryTriageTests(unittest.TestCase):
    def test_shared_root_across_heads_preserved(self):
        items = [obs(A, 1, 11), obs(A, 2, 12), obs(B, 3, 13), obs(B, 4, 14)]
        r = reconcile(items)
        self.assertEqual(r["observations"], 4)
        self.assertEqual(r["distinct_causal_candidates"], 1)
        self.assertEqual(r["quota_failure_manifestations"], 4)
        self.assertEqual(r["exact_heads"], [A, B])
        self.assertEqual(r["roots"][0]["root_id"], "API_QUOTA")
        self.assertEqual(r["roots"][0]["manifestations"], 4)
        self.assertFalse(r["automatic_fanout_authorized"])
        self.assertEqual(r["merge_admission"], "HOLD")

    def test_multiple_independent_roots_in_one_failed_job(self):
        common = obs(A, 7, 99, "Bandit ratchet failed")
        independent = obs(A, 7, 99, "Safety is red")
        report = reconcile([common, independent])
        self.assertEqual(report["observations"], 2)
        self.assertEqual(report["distinct_causal_candidates"], 2)
        self.assertEqual({x["root_id"] for x in report["roots"]}, {"BANDIT", "SAFETY"})
        self.assertEqual(report["merge_admission"], "HOLD")

    def test_dependency_graph_independent_from_quota(self):
        r = reconcile([obs(), obs(B, 99, 102, "Dependency review is not supported")])
        self.assertEqual(r["distinct_causal_candidates"], 2)
        self.assertEqual(
            {x["root_id"] for x in r["roots"]},
            {"API_QUOTA", "DEPENDENCY_GRAPH_DISABLED"},
        )

    def test_recognizes_security_and_formatter_roots(self):
        for message, root in (
            ("Tender guard (new or changed files only)", "A10_REVIEW"),
            ("Safety is red", "SAFETY"),
            ("Bandit ratchet failed", "BANDIT"),
            ("Per-tool black new-debt ratchet failed", "FORMAT"),
        ):
            with self.subTest(root=root):
                self.assertEqual(fingerprint(message), root)

    def test_unknown_root_cannot_be_auto_dispatched(self):
        r = reconcile([obs(message="unrecognized error")])
        self.assertEqual(r["roots"][0]["root_id"], "UNCLASSIFIED")
        self.assertFalse(r["automatic_retry_authorized"])

    def test_ambiguous_signature_remains_unknown(self):
        self.assertEqual(fingerprint("Tender guard / Safety is red"), "UNCLASSIFIED")

    def test_missing_or_invalid_first_red_rejected(self):
        for message in (None, "", 5):
            with self.subTest(message=message), self.assertRaises(ValueError):
                reconcile([obs(message=message)])

    def test_nonterminal_evidence_rejected(self):
        for status, conclusion in (
            ("in_progress", "failure"),
            ("completed", "success"),
        ):
            row = obs()
            row.update(status=status, conclusion=conclusion)
            with (
                self.subTest(row=row),
                self.assertRaisesRegex(ValueError, "terminal failing"),
            ):
                reconcile([row])

    def test_malformed_sha_rejected(self):
        for head in ("f" * 39, "G" * 40, True, "A" * 40):
            with (
                self.subTest(head=head),
                self.assertRaisesRegex(ValueError, "source head"),
            ):
                reconcile([obs(head=head)])

    def test_bad_identity_and_duplicate_rejected(self):
        for key, val in (("run_id", 0), ("job_id", True), ("attempt", -1)):
            r = obs()
            r[key] = val
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "invalid"):
                reconcile([r])
        row = obs()
        with self.assertRaisesRegex(ValueError, "duplicate"):
            reconcile([row, copy.copy(row)])

    def test_out_of_scope_repository_rejected(self):
        row = obs()
        row["repository"] = "GBOGEB/CODEX"
        with self.assertRaisesRegex(ValueError, "out-of-scope"):
            reconcile([row])

    def test_order_independent_members(self):
        rows = [obs(A, 4, 3), obs(B, 1, 2), obs(A, 1, 1)]
        self.assertEqual(reconcile(rows), reconcile(rows[::-1]))

    def test_empty_has_unknown_recovery(self):
        r = reconcile([])
        self.assertEqual(r["observations"], 0)
        self.assertEqual(r["distinct_causal_candidates"], 0)
        self.assertFalse(r["quota_recovery_independently_verified"])

    def test_running_canary_never_authorizes_fanout(self):
        canary = {"status": "IN_PROGRESS", "head_sha": A, "run_id": 1, "attempt": 2}
        r = reconcile([obs()], canary)
        self.assertEqual(r["canary_status"], "IN_PROGRESS")
        self.assertFalse(r["canary_native_terminal"])
        self.assertFalse(r["automatic_fanout_authorized"])

    def test_success_declaration_still_requires_external_attestation(self):
        c = {
            "status": "SUCCESS",
            "head_sha": A,
            "run_id": 1,
            "attempt": 2,
            "receipt_ref": "github-actions-run-1",
        }
        r = reconcile([obs()], c)
        self.assertTrue(r["canary_native_terminal"])
        self.assertFalse(r["quota_recovery_independently_verified"])
        self.assertFalse(r["automatic_retry_authorized"])

    def test_missing_native_success_reference_rejected(self):
        c = {"status": "SUCCESS", "head_sha": A, "run_id": 1, "attempt": 2}
        with self.assertRaisesRegex(ValueError, "native evidence reference"):
            reconcile([obs()], c)

    def test_unknown_canary_and_malformed_canary_rejected(self):
        for c in ([], {"status": "UP", "head_sha": A, "run_id": 1, "attempt": 2}):
            with (
                self.subTest(canary=c),
                self.assertRaisesRegex(ValueError, "invalid canary"),
            ):
                reconcile([], c)

    def test_nonlist_or_nonrecord_series_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "observations must be a list"):
            reconcile({"not": "a list"})
        with self.assertRaisesRegex(ValueError, "observation must be a record"):
            reconcile([None])

    def test_no_merges_waivers_or_security_root_closure(self):
        r = reconcile([obs(), obs(B, 99, 102, "Dependency review is not supported")])
        self.assertEqual(r["security_gates_waived"], 0)
        self.assertEqual(r["merge_admission"], "HOLD")
        self.assertFalse(r["automatic_retry_authorized"])


if __name__ == "__main__":
    unittest.main()
