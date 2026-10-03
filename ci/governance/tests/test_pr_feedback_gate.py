import importlib.util
import pathlib
import sys
import unittest


MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / "pr_feedback_gate.py"
SPEC = importlib.util.spec_from_file_location("pr_feedback_gate", MODULE_PATH)
gate = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = gate
assert SPEC.loader is not None
SPEC.loader.exec_module(gate)


class FeedbackGateTests(unittest.TestCase):
    def test_codex_summary_requires_exact_head(self):
        head = "abcdef0123456789abcdef0123456789abcdef01"
        comments = [
            {
                "body": (
                    "<!-- codex-pull-request-review-summary -->\n"
                    '<!-- codex-security-review:v1 '
                    '{"headSha":"abcdef0123456789abcdef0123456789abcdef01",'
                    '"status":"completed"} -->\n'
                    "| Review | Status | Commit | Review trigger |\n"
                    "| --- | --- | --- | --- |\n"
                    "| 📝 **Code Review** | ✅ **Completed** now | "
                    "`abcdef0` | Manual request |\n"
                ),
                "updated_at": "2026-10-03T10:00:00Z",
            }
        ]
        self.assertTrue(gate.codex_code_review_complete(comments, head))
        colliding_prefix = "abcdef0fffffffffffffffffffffffffffffffff"
        self.assertFalse(
            gate.codex_code_review_complete(comments, colliding_prefix)
        )

    def test_security_marker_requires_exact_head(self):
        head = "abcdef0123456789abcdef0123456789abcdef01"
        comments = [
            {
                "body": (
                    '<!-- codex-security-review:v1 '
                    '{"headSha":"abcdef0123456789abcdef0123456789abcdef01",'
                    '"status":"completed"} -->'
                ),
                "updated_at": "2026-10-03T10:00:00Z",
            }
        ]
        self.assertTrue(gate.codex_security_review_complete(comments, head))
        self.assertFalse(
            gate.codex_security_review_complete(comments, "0" * 40)
        )

    def test_ci_pending_and_red_fail_closed(self):
        pending, failed, seen = gate.classify_runs(
            [
                {
                    "name": "CI - ABACUS Matrix",
                    "event": "pull_request",
                    "status": "in_progress",
                    "conclusion": None,
                    "run_started_at": "2026-10-03T10:00:00Z",
                },
                {
                    "name": "CodeQL",
                    "event": "pull_request",
                    "status": "completed",
                    "conclusion": "failure",
                    "run_started_at": "2026-10-03T10:00:00Z",
                },
            ]
        )
        self.assertEqual(seen, 2)
        self.assertEqual(len(pending), 1)
        self.assertEqual(len(failed), 1)

    def test_gate_state_order_is_failure_then_pending_then_success(self):
        base = dict(
            head_sha="a" * 40,
            code_review_complete=True,
            security_review_complete=True,
            unresolved_threads=0,
            ci_pending=(),
            ci_failed=(),
            ci_seen=2,
            deferred_comments=(),
        )
        self.assertEqual(gate.Evidence(**base).state, "success")

        pending = dict(base)
        pending["code_review_complete"] = False
        self.assertEqual(gate.Evidence(**pending).state, "pending")

        failed = dict(pending)
        failed["unresolved_threads"] = 1
        self.assertEqual(gate.Evidence(**failed).state, "failure")


if __name__ == "__main__":
    unittest.main()
