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
        for name in gate.BLOCKING_IF_PRESENT_WORKFLOWS:
            workflow_id, path = gate.TRUSTED_WORKFLOW_IDENTITIES[name]
            run = {
                "name": name,
                "workflow_id": workflow_id,
                "path": path,
                "event": "pull_request",
                "pull_requests": [{"number": 1760}],
                "status": "completed",
                "conclusion": "success",
                "run_started_at": "2026-10-03T10:00:00Z",
            }
            run.update(overrides.get(name, {}))
            runs.append(run)
        return runs

    def test_required_workflows_follow_changed_paths(self):
        self.assertEqual(
            gate.required_workflows_for_paths(["README.md"]),
            tuple(sorted(gate.ALWAYS_REQUIRED_WORKFLOWS)),
        )
        required = gate.required_workflows_for_paths(
            ["DMAIC_V3/phases/phase6_knowledge.py"]
        )
        self.assertIn("CI - ABACUS Matrix", required)
        self.assertIn("DAB Flake8 Census", required)
        self.assertIn(
            "MIP B0 Test Admission and Coverage Evidence",
            required,
        )

    def test_top_level_python_triggers_dab(self):
        required = gate.required_workflows_for_paths(["tool.py"])
        self.assertIn("DAB Flake8 Census", required)

    def test_only_path_filtered_workflows_are_conditional(self):
        conditional = set(gate.CONDITIONAL_WORKFLOW_PATHS)
        blocking = set(gate.BLOCKING_IF_PRESENT_WORKFLOWS)
        required = set(gate.ALWAYS_REQUIRED_WORKFLOWS)
        self.assertEqual(
            blocking - required,
            conditional,
        )
        self.assertTrue(required.isdisjoint(conditional))

    def test_actions_globstar_matches_zero_or_more_directories(self):
        self.assertTrue(
            gate.github_path_match(
                "DMAIC_V3/foo.py",
                "DMAIC_V3/**/*.py",
            )
        )
        self.assertTrue(
            gate.github_path_match(
                "DMAIC_V3/phases/deep/foo.py",
                "DMAIC_V3/**/*.py",
            )
        )

    def test_actions_single_star_does_not_cross_separator(self):
        pattern = "integration/*/tests/**"
        self.assertTrue(
            gate.github_path_match(
                "integration/alpha/tests/test_one.py",
                pattern,
            )
        )
        self.assertFalse(
            gate.github_path_match(
                "integration/alpha/beta/tests/test_one.py",
                pattern,
            )
        )

    def test_ci_governance_is_not_mip_pr_trigger(self):
        required = gate.required_workflows_for_paths(
            ["ci/governance/pr_feedback_gate.py"]
        )
        self.assertIn("CI - ABACUS Matrix", required)
        self.assertIn("DAB Flake8 Census", required)
        self.assertNotIn(
            "MIP B0 Test Admission and Coverage Evidence",
            required,
        )

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
        self.assertEqual(seen, len(gate.BLOCKING_IF_PRESENT_WORKFLOWS))
        self.assertEqual(len(pending), 1)
        self.assertEqual(len(failed), 1)

    def test_push_run_cannot_satisfy_required_pr_workflow(self):
        runs = self.blocking_runs()
        runs = [
            run
            for run in runs
            if run["name"] != "CI - ABACUS Matrix"
        ]
        workflow_id, path = gate.TRUSTED_WORKFLOW_IDENTITIES[
            "CI - ABACUS Matrix"
        ]
        runs.append(
            {
                "name": "CI - ABACUS Matrix",
                "workflow_id": workflow_id,
                "path": path,
                "event": "push",
                "status": "completed",
                "conclusion": "success",
                "run_started_at": "2026-10-03T10:00:00Z",
            }
        )
        pending, failed, _ = gate.classify_runs(runs)
        self.assertIn("CI missing: CI - ABACUS Matrix", pending)
        self.assertEqual(failed, ())

    def test_push_failure_does_not_poison_green_pr_run(self):
        runs = self.blocking_runs()
        workflow_id, path = gate.TRUSTED_WORKFLOW_IDENTITIES[
            "CI - ABACUS Matrix"
        ]
        runs.append(
            {
                "name": "CI - ABACUS Matrix",
                "workflow_id": workflow_id,
                "path": path,
                "event": "push",
                "status": "completed",
                "conclusion": "failure",
                "run_started_at": "2026-10-03T10:01:00Z",
            }
        )
        pending, failed, _ = gate.classify_runs(runs)
        self.assertEqual(pending, ())
        self.assertEqual(failed, ())

    def test_other_pr_same_sha_cannot_satisfy_required_workflow(self):
        runs = [
            run
            for run in self.blocking_runs()
            if run["name"] != "CI - ABACUS Matrix"
        ]
        workflow_id, path = gate.TRUSTED_WORKFLOW_IDENTITIES[
            "CI - ABACUS Matrix"
        ]
        runs.append(
            {
                "name": "CI - ABACUS Matrix",
                "workflow_id": workflow_id,
                "path": path,
                "event": "pull_request",
                "pull_requests": [{"number": 9999}],
                "status": "completed",
                "conclusion": "success",
                "run_started_at": "2026-10-03T10:01:00Z",
            }
        )
        pending, failed, _ = gate.classify_runs(
            runs,
            pr_number=1760,
        )
        self.assertIn("CI missing: CI - ABACUS Matrix", pending)
        self.assertEqual(failed, ())

    def test_other_pr_same_sha_failure_does_not_poison_current_pr(self):
        runs = self.blocking_runs()
        workflow_id, path = gate.TRUSTED_WORKFLOW_IDENTITIES[
            "CI - ABACUS Matrix"
        ]
        runs.append(
            {
                "name": "CI - ABACUS Matrix",
                "workflow_id": workflow_id,
                "path": path,
                "event": "pull_request",
                "pull_requests": [{"number": 9999}],
                "status": "completed",
                "conclusion": "failure",
                "run_started_at": "2026-10-03T10:01:00Z",
            }
        )
        pending, failed, _ = gate.classify_runs(
            runs,
            pr_number=1760,
        )
        self.assertEqual(pending, ())
        self.assertEqual(failed, ())

    def test_spoofed_required_workflow_identity_fails_closed(self):
        runs = self.blocking_runs(
            {
                "DELTA_1 CodeQL": {
                    "workflow_id": 1,
                    "path": ".github/workflows/codeql.yml",
                },
            }
        )
        pending, failed, _ = gate.classify_runs(runs)
        self.assertIn("CI missing: DELTA_1 CodeQL", pending)
        self.assertTrue(
            any(
                item.startswith("CI identity mismatch: DELTA_1 CodeQL")
                for item in failed
            )
        )

    def test_required_workflow_definition_changes_fail_closed(self):
        changed = gate.required_workflow_definition_changes(
            [
                "README.md",
                ".github/workflows/codeql.yml",
            ],
            gate.ALWAYS_REQUIRED_WORKFLOWS,
        )
        self.assertEqual(
            changed,
            (".github/workflows/codeql.yml",),
        )

    def test_codeql_config_change_fails_closed_as_trusted_input(self):
        changed = gate.required_workflow_definition_changes(
            [".github/codeql/codeql-config.yml"],
            gate.ALWAYS_REQUIRED_WORKFLOWS,
        )
        self.assertEqual(
            changed,
            (".github/codeql/codeql-config.yml",),
        )

    def test_gate_workflow_can_change_without_self_certifying_required_ci(self):
        changed = gate.required_workflow_definition_changes(
            [".github/workflows/pr-feedback-gate.yml"],
            gate.ALWAYS_REQUIRED_WORKFLOWS,
        )
        self.assertEqual(changed, ())

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
        self.assertEqual(seen, len(gate.BLOCKING_IF_PRESENT_WORKFLOWS))
        self.assertEqual(pending, ())
        self.assertEqual(failed, ())

    def test_missing_required_workflow_fails_closed_as_pending(self):
        runs = self.blocking_runs()
        runs = [
            run
            for run in runs
            if run["name"] != "DAB Flake8 Census"
        ]
        pending, failed, seen = gate.classify_runs(
            runs,
            required_workflows=(
                "CI - ABACUS Matrix",
                "DAB Flake8 Census",
            ),
        )
        self.assertEqual(
            seen,
            len(gate.BLOCKING_IF_PRESENT_WORKFLOWS) - 1,
        )
        self.assertIn("CI missing: DAB Flake8 Census", pending)
        self.assertEqual(failed, ())

    def test_missing_nonapplicable_workflow_does_not_deadlock(self):
        runs = [
            run
            for run in self.blocking_runs()
            if run["name"]
            not in {
                "DAB Flake8 Census",
                "MIP B0 Test Admission and Coverage Evidence",
            }
        ]
        pending, failed, _ = gate.classify_runs(
            runs,
            required_workflows=gate.ALWAYS_REQUIRED_WORKFLOWS,
        )
        self.assertEqual(pending, ())
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
