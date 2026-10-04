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
    @staticmethod
    def trusted_codex_comment(body: str, updated_at: str = "2026-10-03T10:00:00Z"):
        return {
            "body": body,
            "updated_at": updated_at,
            "user": {
                "login": gate.CODEX_BOT_LOGIN,
                "id": gate.CODEX_BOT_ID,
            },
            "performed_via_github_app": {
                "id": gate.CODEX_APP_ID,
                "slug": gate.CODEX_APP_SLUG,
            },
        }

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
                "user": {
                    "login": "chatgpt-codex-connector[bot]",
                    "id": 199175422,
                },
                "performed_via_github_app": {
                    "id": 1144995,
                    "slug": "chatgpt-codex-connector",
                },
            }
        ]
        self.assertTrue(gate.codex_code_review_complete(comments, head))
        colliding_prefix = "abcdef0fffffffffffffffffffffffffffffffff"
        self.assertFalse(
            gate.codex_code_review_complete(comments, colliding_prefix)
        )

    def test_code_review_rejects_colliding_display_prefix(self):
        head = "abcdef0123456789abcdef0123456789abcdef01"
        other = "abcdef0fffffffffffffffffffffffffffffffff"
        comments = [
            {
                "body": (
                    "<!-- codex-pull-request-review-summary -->\n"
                    "<!-- codex-security-review:v1 "
                    + '{"headSha":"' + other + '","status":"completed"} -->\n'
                    "| Review | Status | Commit | Review trigger |\n"
                    "| --- | --- | --- | --- |\n"
                    "| 📝 **Code Review** | ✅ **Completed** now | "
                    "`abcdef0` | Manual request |\n"
                ),
                "updated_at": "2026-10-03T10:00:00Z",
                "user": {
                    "login": "chatgpt-codex-connector[bot]",
                    "id": 199175422,
                },
                "performed_via_github_app": {
                    "id": 1144995,
                    "slug": "chatgpt-codex-connector",
                },
            }
        ]
        self.assertFalse(gate.codex_code_review_complete(comments, head))

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
                "user": {
                    "login": "chatgpt-codex-connector[bot]",
                    "id": 199175422,
                },
                "performed_via_github_app": {
                    "id": 1144995,
                    "slug": "chatgpt-codex-connector",
                },
            }
        ]
        self.assertTrue(gate.codex_security_review_complete(comments, head))
        self.assertFalse(
            gate.codex_security_review_complete(comments, "0" * 40)
        )

    def test_forged_codex_markers_are_rejected(self):
        head = "abcdef0123456789abcdef0123456789abcdef01"
        body = (
            "<!-- codex-pull-request-review-summary -->\n"
            '<!-- codex-security-review:v1 '
            '{"headSha":"abcdef0123456789abcdef0123456789abcdef01",'
            '"status":"completed"} -->\n'
            "| Review | Status | Commit | Review trigger |\n"
            "| --- | --- | --- | --- |\n"
            "| 📝 **Code Review** | ✅ **Completed** now | "
            "`abcdef0` | Manual request |\n"
        )
        forged = [
            {
                "body": body,
                "updated_at": "2026-10-03T10:00:00Z",
                "user": {"login": "GBOGEB", "id": 202350393},
                "performed_via_github_app": None,
            }
        ]
        self.assertFalse(gate.codex_code_review_complete(forged, head))
        self.assertFalse(gate.codex_security_review_complete(forged, head))

    def test_forged_codex_summary_is_rejected(self):
        head = "abcdef0123456789abcdef0123456789abcdef01"
        forged = {
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
            "user": {"login": "GBOGEB", "id": 202350393},
            "performed_via_github_app": None,
        }
        self.assertFalse(gate.codex_code_review_complete([forged], head))
        self.assertFalse(gate.codex_security_review_complete([forged], head))

    def test_wrong_codex_app_identity_is_rejected(self):
        head = "abcdef0123456789abcdef0123456789abcdef01"
        comment = self.trusted_codex_comment(
            '<!-- codex-security-review:v1 '
            '{"headSha":"abcdef0123456789abcdef0123456789abcdef01",'
            '"status":"completed"} -->'
        )
        comment["performed_via_github_app"]["id"] = 1
        self.assertFalse(gate.codex_security_review_complete([comment], head))

    def blocking_runs(self, overrides=None):
        overrides = overrides or {}
        runs = []
        for name in gate.BLOCKING_WORKFLOWS:
            run = {
                "name": name,
                "event": "pull_request",
                "status": "completed",
                "conclusion": "success",
                "run_started_at": "2026-10-03T10:00:00Z",
            }
            run.update(overrides.get(name, {}))
            runs.append(run)
        return runs

    def test_ci_pending_and_red_fail_closed(self):
        runs = self.blocking_runs(
            {
                "CI - ABACUS Matrix": {
                    "status": "in_progress",
                    "conclusion": None,
                },
                "DELTA_1 CodeQL": {
                    "conclusion": "failure",
                },
            }
        )
        pending, failed, seen = gate.classify_runs(runs)
        self.assertEqual(seen, len(gate.BLOCKING_WORKFLOWS))
        self.assertEqual(len(pending), 1)
        self.assertEqual(len(failed), 1)

    def test_advisory_workflow_failure_does_not_poison_gate(self):
        runs = self.blocking_runs()
        runs.append(
            {
                "name": "CI/CD Test Suite",
                "event": "pull_request",
                "status": "completed",
                "conclusion": "failure",
                "run_started_at": "2026-10-03T10:00:00Z",
            }
        )
        pending, failed, seen = gate.classify_runs(runs)
        self.assertEqual(seen, len(gate.BLOCKING_WORKFLOWS))
        self.assertEqual(pending, ())
        self.assertEqual(failed, ())

    def test_missing_blocking_workflow_fails_closed_as_pending(self):
        runs = self.blocking_runs()
        runs = [
            run
            for run in runs
            if run["name"] != "DAB Flake8 Census"
        ]
        pending, failed, seen = gate.classify_runs(runs)
        self.assertEqual(seen, len(gate.BLOCKING_WORKFLOWS) - 1)
        self.assertIn("CI missing: DAB Flake8 Census", pending)
        self.assertEqual(failed, ())

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
