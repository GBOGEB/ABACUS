"""Protect against accidentally suppressing real PR feedback invalidation."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

P = Path(__file__).resolve().parents[1] / "feedback_noop_proof.py"
S = importlib.util.spec_from_file_location("feedback_noop_proof", P)
m = importlib.util.module_from_spec(S)
S.loader.exec_module(m)
SHA = "a" * 40


def event(**overrides):
    run = {
        "status": "completed",
        "head_sha": SHA,
        "head_branch": "main",
        "pull_requests": [],
    }
    run.update(overrides)
    return {"action": "completed", "workflow_run": run}


class NoopTests(unittest.TestCase):
    def test_closed_only_commit_is_diagnostic_noop_candidate(self):
        d = m.classify(event(), SHA, [{"number": 1962, "state": "closed"}])
        self.assertEqual(d["classification"], "PROVEN_NO_OPEN_LINKED_PR")
        self.assertFalse(d["skip_authorized"])
        self.assertFalse(d["authority_transfer"])

    def test_empty_commit_linkage_is_not_approval(self):
        d = m.classify(event(), SHA, [])
        self.assertEqual(d["classification"], "PROVEN_NO_OPEN_LINKED_PR")
        self.assertFalse(d["skip_authorized"])

    def test_open_commit_link_is_evaluable(self):
        d = m.classify(event(), SHA, [{"number": 11, "state": "open"}])
        self.assertEqual(d["classification"], "EVALUATE")

    def test_mixed_open_closed_is_evaluable(self):
        d = m.classify(
            event(),
            SHA,
            [{"number": 1, "state": "closed"}, {"number": 2, "state": "open"}],
        )
        self.assertEqual(d["classification"], "EVALUATE")

    def test_payload_pr_link_blocks_noop(self):
        d = m.classify(event(pull_requests=[{"number": 3}]), SHA, [])
        self.assertEqual(d["classification"], "EVALUATE")

    def test_nonmain_is_evaluable(self):
        d = m.classify(event(head_branch="feature"), SHA, [])
        self.assertEqual(d["classification"], "EVALUATE")

    def test_stale_main_is_evaluable(self):
        d = m.classify(event(head_sha="b" * 40), SHA, [])
        self.assertEqual(d["classification"], "EVALUATE")

    def test_missing_rest_lookup_unknown(self):
        d = m.classify(event(), SHA, None)
        self.assertEqual(d["classification"], "UNKNOWN")

    def test_invalid_main_sha_unknown(self):
        d = m.classify(event(), "abc", [])
        self.assertEqual(d["classification"], "UNKNOWN")

    def test_absent_workflow_run_unknown(self):
        d = m.classify({"action": "completed"}, SHA, [])
        self.assertEqual(d["classification"], "UNKNOWN")

    def test_started_workflow_noop_not_inferred(self):
        d = m.classify(event(status="in_progress"), SHA, [])
        self.assertEqual(d["classification"], "UNKNOWN")

    def test_nonterminal_action_noop_not_inferred(self):
        e = event()
        e["action"] = "requested"
        self.assertEqual(m.classify(e, SHA, [])["classification"], "UNKNOWN")

    def test_missing_event_pull_array_unknown(self):
        d = m.classify(event(pull_requests=None), SHA, [])
        self.assertEqual(d["classification"], "UNKNOWN")

    def test_untrusted_linked_pr_not_noop(self):
        d = m.classify(event(), SHA, [{"number": 1, "state": "UNKNOWN"}])
        self.assertEqual(d["classification"], "UNKNOWN")

    def test_missing_pr_number_unknown(self):
        d = m.classify(event(), SHA, [{"state": "closed"}])
        self.assertEqual(d["classification"], "UNKNOWN")

    def test_boolean_pr_number_unknown(self):
        d = m.classify(event(), SHA, [{"number": True, "state": "closed"}])
        self.assertEqual(d["classification"], "UNKNOWN")

    def test_duplicate_pr_number_unknown(self):
        d = m.classify(
            event(),
            SHA,
            [{"number": 1, "state": "closed"}, {"number": 1, "state": "closed"}],
        )
        self.assertEqual(d["classification"], "UNKNOWN")

    def test_bad_linked_row_unknown(self):
        d = m.classify(event(), SHA, [None])
        self.assertEqual(d["classification"], "UNKNOWN")

    def test_nonmapping_event_unknown(self):
        self.assertEqual(m.classify([], SHA, [])["classification"], "UNKNOWN")

    def test_mixed_pending_action_never_skips(self):
        e = event()
        e["action"] = "edited"
        self.assertFalse(m.classify(e, SHA, [])["skip_authorized"])


if __name__ == "__main__":
    unittest.main()
