import importlib.util
import json
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

        missing_reviews = dict(base)
        missing_reviews["code_review_complete"] = False
        missing_reviews["security_review_complete"] = False
        evidence = gate.Evidence(**missing_reviews)
        self.assertEqual(evidence.state, "pending")
        self.assertIn(
            "Codex code review is not complete on current head",
            evidence.pending_reasons,
        )
        self.assertIn(
            "Codex security review is not complete on current head",
            evidence.pending_reasons,
        )

        pending = dict(base)
        pending["ci_pending"] = ("CI pending: test",)
        self.assertEqual(gate.Evidence(**pending).state, "pending")

        failed = dict(pending)
        failed["unresolved_threads"] = 1
        self.assertEqual(gate.Evidence(**failed).state, "failure")


    def test_deferred_review_can_satisfy_non_sensitive_pending_review(self):
        base = dict(
            head_sha="a" * 40,
            code_review_complete=False,
            security_review_complete=False,
            unresolved_threads=2,
            ci_pending=(),
            ci_failed=(),
            ci_seen=12,
            deferred_comments=(),
            review_deferral_valid=True,
            security_sensitive=False,
            blocking_review_items=(),
            review_deferral_details=("tracked by issue",),
        )
        evidence = gate.Evidence(**base)
        self.assertEqual(evidence.state, "success")
        self.assertEqual(evidence.failure_reasons, ())
        self.assertEqual(evidence.pending_reasons, ())

    def test_s0_s1_remain_blocking_even_with_deferral(self):
        base = dict(
            head_sha="a" * 40,
            code_review_complete=False,
            security_review_complete=False,
            unresolved_threads=1,
            ci_pending=(),
            ci_failed=(),
            ci_seen=12,
            deferred_comments=(),
            review_deferral_valid=True,
            security_sensitive=False,
            blocking_review_items=("S1 review item remains open",),
            review_deferral_details=(),
        )
        evidence = gate.Evidence(**base)
        self.assertEqual(evidence.state, "failure")
        self.assertIn("S1 review item remains open", evidence.failure_reasons)

    def test_sensitive_change_still_requires_security_review(self):
        base = dict(
            head_sha="a" * 40,
            code_review_complete=False,
            security_review_complete=False,
            unresolved_threads=0,
            ci_pending=(),
            ci_failed=(),
            ci_seen=12,
            deferred_comments=(),
            review_deferral_valid=True,
            security_sensitive=True,
            blocking_review_items=(),
            review_deferral_details=(),
        )
        evidence = gate.Evidence(**base)
        self.assertEqual(evidence.state, "pending")
        self.assertTrue(
            any("mandatory pre-merge" in item for item in evidence.pending_reasons)
        )

    def test_security_sensitive_path_classifier(self):
        self.assertTrue(
            gate.security_sensitive_change(
                [".github/workflows/pr-feedback-gate.yml"]
            )
        )
        self.assertTrue(
            gate.security_sensitive_change(
                ["ci/governance/pr_feedback_gate.py"]
            )
        )
        self.assertFalse(
            gate.security_sensitive_change(["docs/ordinary-note.md"])
        )

    def test_review_deferral_requires_classifications_and_exact_open_issue(self):
        head = "a" * 40
        issue_body = (
            '<!-- abacus-deferred-security:v1 '
            + json.dumps(self.full_debt_metadata(head))
            + " -->"
        )

        class FakeGitHub:
            def __init__(self, body, association="OWNER"):
                self.body = body
                self.association = association

            def issue(self, number):
                return {
                    "number": number,
                    "state": "open",
                    "body": self.body,
                    "author_association": self.association,
                }

        marker = {
            "headSha": head,
            "trackingIssue": 1846,
            "codexCodeReviewRequired": True,
            "codexSecurityReviewRequired": True,
            "items": [{"threadId": "THREAD-1", "classification": "S2"}],
        }
        comment = {
            "author_association": "OWNER",
            "body": (
                "CODEX_CODE_REVIEW=DEFERRED_BUDGET\n"
                "CODEX_SECURITY_REVIEW=DEFERRED_BUDGET\n"
                "<!-- abacus-review-disposition:v2 "
                + json.dumps(marker)
                + " -->"
            ),
        }
        threads = [{"id": "THREAD-1", "isResolved": False}]
        evidence = gate.review_deferral_evidence(
            FakeGitHub(issue_body),
            42,
            head,
            [comment],
            threads,
            False,
            False,
        )
        self.assertTrue(evidence[0])
        self.assertEqual(evidence[1], ())

        timed_comment = dict(comment, updated_at="2026-10-11T15:00:00Z")
        classified_before = [
            {
                "id": "THREAD-1",
                "isResolved": False,
                "comments": {
                    "nodes": [{"createdAt": "2026-10-11T14:00:00Z"}]
                },
            }
        ]
        evidence = gate.review_deferral_evidence(
            FakeGitHub(issue_body),
            42,
            head,
            [timed_comment],
            classified_before,
            False,
            False,
        )
        self.assertTrue(evidence[0])
        for late in (
            {"createdAt": "2026-10-11T15:05:00Z"},
            {
                "createdAt": "2026-10-11T14:00:00Z",
                "lastEditedAt": "2026-10-11T15:05:00Z",
            },
        ):
            changed_after = [
                {
                    "id": "THREAD-1",
                    "isResolved": False,
                    "comments": {"nodes": [late]},
                }
            ]
            evidence = gate.review_deferral_evidence(
                FakeGitHub(issue_body),
                42,
                head,
                [timed_comment],
                changed_after,
                False,
                False,
            )
            self.assertFalse(evidence[0])
            self.assertIn("changed after its classification", evidence[2][0])

        truncated_thread = [
            {
                "id": "THREAD-1",
                "isResolved": False,
                "comments": {
                    "pageInfo": {"hasNextPage": True},
                    "nodes": [{"createdAt": "2026-10-11T14:00:00Z"}],
                },
            }
        ]
        evidence = gate.review_deferral_evidence(
            FakeGitHub(issue_body),
            42,
            head,
            [timed_comment],
            truncated_thread,
            False,
            False,
        )
        self.assertFalse(evidence[0])
        self.assertIn("too long to verify", evidence[2][0])

        unmarked_comment = dict(comment)
        unmarked_comment["body"] = comment["body"].replace(
            "CODEX_SECURITY_REVIEW=DEFERRED_BUDGET\n",
            "",
        )
        evidence = gate.review_deferral_evidence(
            FakeGitHub(issue_body),
            42,
            head,
            [unmarked_comment],
            threads,
            False,
            False,
        )
        self.assertFalse(evidence[0])
        self.assertIn("DEFERRED_BUDGET", evidence[2][0])

        stale_issue = issue_body.replace(head, "b" * 40)
        evidence = gate.review_deferral_evidence(
            FakeGitHub(stale_issue),
            42,
            head,
            [comment],
            threads,
            False,
            False,
        )
        self.assertFalse(evidence[0])
        self.assertIn("no open issue", evidence[2][0])

        wrong_pr_issue = issue_body.replace('"pr": 42', '"pr": 43')
        evidence = gate.review_deferral_evidence(
            FakeGitHub(wrong_pr_issue),
            42,
            head,
            [comment],
            threads,
            False,
            False,
        )
        self.assertFalse(evidence[0])
        self.assertIn("no open issue", evidence[2][0])

        marker["items"] = []
        comment["body"] = (
            "CODEX_CODE_REVIEW=DEFERRED_BUDGET\n"
            "CODEX_SECURITY_REVIEW=DEFERRED_BUDGET\n"
            "<!-- abacus-review-disposition:v2 "
            + json.dumps(marker)
            + " -->"
        )
        evidence = gate.review_deferral_evidence(
            FakeGitHub(issue_body),
            42,
            head,
            [comment],
            threads,
            False,
            False,
        )
        self.assertFalse(evidence[0])
        self.assertIn("every unresolved", evidence[2][0])

    @staticmethod
    def full_debt_metadata(head):
        return {
            "pr": 42,
            "headSha": head,
            "status": "OPEN",
            "reason": "Codex capacity unavailable (DEFERRED_BUDGET)",
            "codexCodeReviewRequired": True,
            "codexSecurityReviewRequired": True,
            "items": [
                {
                    "threadId": "THREAD-1",
                    "classification": "S2",
                    "source": "chatgpt-codex-connector",
                    "finding": "hardening suggestion",
                    "rationale": "does not invalidate the PR",
                }
            ],
        }

    def deferral_result(self, metadata, association="OWNER"):
        head = "a" * 40
        body = (
            "<!-- abacus-deferred-security:v1 " + json.dumps(metadata) + " -->"
        )

        class FakeGitHub:
            def issue(self, number):
                return {
                    "number": number,
                    "state": "open",
                    "body": body,
                    "author_association": association,
                }

        marker = {
            "headSha": head,
            "trackingIssue": 1846,
            "codexCodeReviewRequired": True,
            "codexSecurityReviewRequired": True,
            "items": [{"threadId": "THREAD-1", "classification": "S2"}],
        }
        comment = {
            "author_association": "OWNER",
            "body": (
                "CODEX_CODE_REVIEW=DEFERRED_BUDGET\n"
                "CODEX_SECURITY_REVIEW=DEFERRED_BUDGET\n"
                "<!-- abacus-review-disposition:v2 "
                + json.dumps(marker)
                + " -->"
            ),
        }
        return gate.review_deferral_evidence(
            FakeGitHub(),
            42,
            head,
            [comment],
            [{"id": "THREAD-1", "isResolved": False}],
            False,
            False,
        )

    def test_marker_only_tracking_issue_is_rejected(self):
        head = "a" * 40
        evidence = self.deferral_result(
            {"pr": 42, "headSha": head, "status": "OPEN"}
        )
        self.assertFalse(evidence[0])
        self.assertIn("deferral reason", evidence[2][0])

    def test_tracking_issue_must_retain_each_obligation(self):
        head = "a" * 40
        self.assertTrue(self.deferral_result(self.full_debt_metadata(head))[0])

        no_security = self.full_debt_metadata(head)
        no_security["codexSecurityReviewRequired"] = False
        evidence = self.deferral_result(no_security)
        self.assertFalse(evidence[0])
        self.assertIn("codexSecurityReviewRequired", evidence[2][0])

        thin_item = self.full_debt_metadata(head)
        del thin_item["items"][0]["finding"]
        evidence = self.deferral_result(thin_item)
        self.assertFalse(evidence[0])
        self.assertIn("finding", evidence[2][0])

        downgraded = self.full_debt_metadata(head)
        downgraded["items"][0]["classification"] = "S3"
        evidence = self.deferral_result(downgraded)
        self.assertFalse(evidence[0])
        self.assertIn("downgrades S2", evidence[2][0])

        duplicated = self.full_debt_metadata(head)
        duplicated["items"].append(dict(duplicated["items"][0]))
        duplicated["items"][1]["classification"] = "S3"
        evidence = self.deferral_result(duplicated)
        self.assertFalse(evidence[0])
        self.assertIn("more than once", evidence[2][0])

        missing_s2 = self.full_debt_metadata(head)
        missing_s2["items"] = []
        evidence = self.deferral_result(missing_s2)
        self.assertFalse(evidence[0])
        self.assertIn("THREAD-1", evidence[2][0])

    def test_tracking_issue_from_untrusted_author_is_rejected(self):
        evidence = self.deferral_result(
            self.full_debt_metadata("a" * 40), association="NONE"
        )
        self.assertFalse(evidence[0])
        self.assertIn("trusted", evidence[2][0])

    def test_rename_out_of_sensitive_path_is_sensitive(self):
        paths = gate.changed_paths_from_files(
            [
                {
                    "filename": "tools/pr_feedback_gate.py",
                    "previous_filename": "ci/governance/pr_feedback_gate.py",
                    "status": "renamed",
                },
                {"filename": "docs/note.md", "status": "modified"},
            ]
        )
        self.assertEqual(
            paths,
            [
                "tools/pr_feedback_gate.py",
                "ci/governance/pr_feedback_gate.py",
                "docs/note.md",
            ],
        )
        self.assertTrue(gate.security_sensitive_change(paths))
        self.assertFalse(
            gate.security_sensitive_change(
                gate.changed_paths_from_files([{"filename": "docs/note.md"}])
            )
        )

    def test_privileged_workflow_inputs_are_sensitive(self):
        for path in (
            ".github/scripts/security_dashboard.py",
            ".github/actions/runtime-guard/action.yml",
        ):
            self.assertTrue(gate.security_sensitive_change([path]), path)

    def test_tracking_issue_change_recensuses_only_named_prs(self):
        class FakeGitHub:
            def open_pulls(self):
                raise AssertionError("issue events must not sweep all PRs")

        marker = (
            '<!-- abacus-deferred-security:v1 {"pr": 1847, '
            '"headSha": "abc", "status": "OPEN"} -->'
        )
        closed_issue = {
            "action": "closed",
            "issue": {
                "number": 1849,
                "state": "closed",
                "author_association": "OWNER",
                "body": marker,
            },
        }
        self.assertEqual(
            gate.event_pr_numbers(FakeGitHub(), closed_issue, None),
            [1847],
        )
        marker_stripped = {
            "action": "edited",
            "issue": {
                "number": 1849,
                "author_association": "OWNER",
                "body": "debt cleared",
            },
            "changes": {"body": {"from": marker}},
        }
        self.assertEqual(
            gate.event_pr_numbers(FakeGitHub(), marker_stripped, None),
            [1847],
        )
        pr_comment_deleted = {
            "action": "deleted",
            "issue": {"number": 1847, "pull_request": {"url": "x"}},
        }
        self.assertEqual(
            gate.event_pr_numbers(FakeGitHub(), pr_comment_deleted, None),
            [1847],
        )

    def test_untracked_or_untrusted_issue_change_is_ignored(self):
        class FakeGitHub:
            def open_pulls(self):
                raise AssertionError("issue events must not sweep all PRs")

        marker = (
            '<!-- abacus-deferred-security:v1 {"pr": 1847, '
            '"headSha": "abc", "status": "OPEN"} -->'
        )
        plain_issue = {
            "action": "edited",
            "issue": {
                "number": 7,
                "author_association": "OWNER",
                "body": "no marker here",
            },
        }
        self.assertEqual(
            gate.event_pr_numbers(FakeGitHub(), plain_issue, None), []
        )
        untrusted_issue = {
            "action": "edited",
            "issue": {
                "number": 8,
                "author_association": "NONE",
                "body": marker,
            },
        }
        self.assertEqual(
            gate.event_pr_numbers(FakeGitHub(), untrusted_issue, None), []
        )
        public_comment = {
            "action": "created",
            "issue": {
                "number": 1849,
                "author_association": "OWNER",
                "body": marker,
            },
            "comment": {"author_association": "NONE", "body": "spam"},
        }
        self.assertEqual(
            gate.event_pr_numbers(FakeGitHub(), public_comment, None), []
        )

    def test_workflow_subscribes_to_tracking_issue_lifecycle(self):
        workflow = (
            pathlib.Path(__file__).resolve().parents[3]
            / ".github"
            / "workflows"
            / "pr-feedback-gate.yml"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "issues:\n    types: [edited, closed, reopened, deleted, "
            "transferred]",
            workflow,
        )
        self.assertIn(
            "issue_comment:\n    types: [created, edited, deleted]",
            workflow,
        )
        # Not an Actions-supported trigger; declaring it would be a no-op.
        self.assertNotIn("pull_request_review_thread:", workflow)

    def test_incomplete_file_census_fails_closed(self):
        records = [{"filename": "docs/note.md"}]
        self.assertTrue(
            gate.file_census_complete(records, {"changed_files": 1})
        )
        self.assertFalse(
            gate.file_census_complete(records, {"changed_files": 3001})
        )
        self.assertFalse(gate.file_census_complete(records, {}))
        self.assertFalse(
            gate.file_census_complete(records, {"changed_files": True})
        )

    def test_truncated_census_blocks_deferral_and_requires_all_ci(self):
        head = "a" * 40

        class FakeGitHub:
            def issue_comments(self, number):
                return []

            def review_threads(self, number):
                return []

            def actions_runs(self, head_sha):
                return []

            def pull_file_records(self, number):
                return [{"filename": "docs/note.md"}]

            def check_runs(self, head_sha):
                return []

            def issue(self, number):
                return {}

        pull = {
            "state": "open",
            "base": {"ref": "main"},
            "head": {"sha": head},
            "changed_files": 3001,
        }
        evidence = gate.evaluate(FakeGitHub(), 42, pull)
        self.assertTrue(evidence.security_sensitive)
        self.assertTrue(
            any(
                "incomplete PR file census" in item
                for item in evidence.ci_failed
            )
        )
        self.assertEqual(evidence.state, "failure")
        for workflow in gate.CONDITIONAL_WORKFLOW_PATHS:
            self.assertTrue(
                any(workflow in item for item in evidence.ci_pending),
                workflow,
            )

    def test_older_census_never_overwrites_newer_result(self):
        calls = []

        class FakeGitHub(gate.GitHub):
            def __init__(self, published_summary):
                self.repository = "GBOGEB/ABACUS"
                self.published_summary = published_summary

            def check_runs(self, head_sha):
                return [
                    {
                        "id": 1,
                        "name": gate.GATE_NAME,
                        "status": "completed",
                        "started_at": "2026-10-11T15:00:00Z",
                        "output": {"summary": self.published_summary},
                    }
                ]

            def request(self, method, path, payload=None):
                calls.append((method, path, payload))
                return {}

        newer = "state=failure\ncensus_started=2026-10-11T15:00:05Z"
        self.assertFalse(
            FakeGitHub(newer).publish_gate(
                "a" * 40,
                "success",
                "t",
                "s",
                "x",
                census_started="2026-10-11T15:00:01Z",
            )
        )
        self.assertEqual(calls, [])
        older = "state=failure\ncensus_started=2026-10-11T14:59:00Z"
        self.assertTrue(
            FakeGitHub(older).publish_gate(
                "a" * 40,
                "success",
                "t",
                "s",
                "x",
                census_started="2026-10-11T15:00:01Z",
            )
        )
        self.assertEqual(calls[0][0], "PATCH")
        self.assertEqual(
            gate.census_started_from("a=1\ncensus_started=X\n"), "X"
        )
        self.assertIsNone(gate.census_started_from("state=pending"))


if __name__ == "__main__":
    unittest.main()
