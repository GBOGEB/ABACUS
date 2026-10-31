import importlib.util
import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

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
                    "<!-- codex-security-review:v1 "
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
        self.assertFalse(gate.codex_code_review_complete(comments, colliding_prefix))

    def test_code_review_rejects_colliding_display_prefix(self):
        head = "abcdef0123456789abcdef0123456789abcdef01"
        other = "abcdef0fffffffffffffffffffffffffffffffff"
        comments = [
            {
                "body": (
                    "<!-- codex-pull-request-review-summary -->\n"
                    "<!-- codex-security-review:v1 "
                    + '{"headSha":"'
                    + other
                    + '","status":"completed"} -->\n'
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
                    "<!-- codex-security-review:v1 "
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
        self.assertFalse(gate.codex_security_review_complete(comments, "0" * 40))

    def test_forged_codex_markers_are_rejected(self):
        head = "abcdef0123456789abcdef0123456789abcdef01"
        body = (
            "<!-- codex-pull-request-review-summary -->\n"
            "<!-- codex-security-review:v1 "
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
                "<!-- codex-security-review:v1 "
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
            "<!-- codex-security-review:v1 "
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
        runs = [run for run in runs if run["name"] != "CI - ABACUS Matrix"]
        workflow_id, path = gate.TRUSTED_WORKFLOW_IDENTITIES["CI - ABACUS Matrix"]
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
        workflow_id, path = gate.TRUSTED_WORKFLOW_IDENTITIES["CI - ABACUS Matrix"]
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
            run for run in self.blocking_runs() if run["name"] != "CI - ABACUS Matrix"
        ]
        workflow_id, path = gate.TRUSTED_WORKFLOW_IDENTITIES["CI - ABACUS Matrix"]
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
        workflow_id, path = gate.TRUSTED_WORKFLOW_IDENTITIES["CI - ABACUS Matrix"]
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
        runs = [run for run in runs if run["name"] != "DAB Flake8 Census"]
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

    # --- owner-attestation fallback (Codex unavailable) -------------------

    HEAD = "1234567890abcdef1234567890abcdef12345678"

    @staticmethod
    def owner_comment(payload: str, **overrides):
        comment = {
            "body": f"Owner sign-off\n<!-- owner-security-attestation:v1 {payload} -->",
            "updated_at": "2026-10-11T20:00:00Z",
            "author_association": "OWNER",
            "user": {"login": "GBOGEB", "type": "User"},
        }
        comment.update(overrides)
        return comment

    def valid_payload(self, head=None):
        return (
            '{"headSha":"%s","status":"completed","scope":"code+security",'
            '"reason":"codex_unavailable","reviewer":"GBOGEB"}' % (head or self.HEAD)
        )

    HEAD_AT = "2026-10-11T19:00:00Z"

    def current_head_request(self, at="2026-10-11T19:10:00Z", head=None, **overrides):
        comment = {
            "body": "@codex security review\n\nExact head \\`%s\\`"
            % (head or self.HEAD),
            "created_at": at,
            "updated_at": at,
            "user": {"login": "GBOGEB", "type": "User"},
            "author_association": "OWNER",
        }
        comment.update(overrides)
        return comment

    def test_current_head_request_binding_and_order(self):
        since = self.HEAD_AT
        outage_at = "2026-10-11T19:30:00Z"
        good = self.current_head_request()
        self.assertTrue(
            gate.current_head_codex_request([good], self.HEAD, since, outage_at)
        )
        for wrong in (
            self.current_head_request(head="a" * 40),
            self.current_head_request(at="2026-10-11T18:59:59Z"),
            self.current_head_request(at=since),
            self.current_head_request(at=outage_at),
            self.current_head_request(
                performed_via_github_app={"id": gate.CODEX_APP_ID}
            ),
            self.current_head_request(author_association="COLLABORATOR"),
            self.current_head_request(user={"login": "attacker", "type": "User"}),
        ):
            self.assertFalse(
                gate.current_head_codex_request([wrong], self.HEAD, since, outage_at)
            )

    def test_delayed_old_head_outage_does_not_enable_fallback(self):
        # A requested before B became head; Codex replies late, after B.
        # A new exact-head owner attestation must not inherit the stale request.
        class FakeGitHub:
            def issue_comments(self, number):
                return [
                    self_outer.current_head_request(
                        at="2026-10-11T18:30:00Z", head="a" * 40
                    ),
                    self_outer.outage(),
                    self_outer.owner_comment(self_outer.valid_payload()),
                ]

            def review_threads(self, number):
                return []

            def actions_runs(self, head_sha):
                return [
                    {
                        "event": "pull_request",
                        "head_sha": self_outer.HEAD,
                        "created_at": self_outer.HEAD_AT,
                        "pull_requests": [{"number": 1}],
                    }
                ]

            def pull_files(self, number):
                return ["README.md"]

            def pull_file_records(self, number):
                return [{"filename": "README.md"}]

            def issue(self, number):
                return {"state": "open"}

        self_outer = self
        pull = {
            "state": "open",
            "base": {"ref": "main"},
            "head": {"sha": self.HEAD},
            "changed_files": 1,
        }
        evidence = gate.evaluate(FakeGitHub(), 1, pull)
        self.assertEqual(evidence.review_source, "codex")
        self.assertFalse(evidence.security_review_complete)

    def test_outage_without_explicit_current_head_request_fails_closed(self):
        self.assertFalse(
            gate.current_head_codex_request(
                [self.outage()], self.HEAD, self.HEAD_AT, "2026-10-11T19:30:00Z"
            )
        )

    def outage(self, at="2026-10-11T19:30:00Z"):
        comment = self.trusted_codex_comment(
            "You have reached your Codex usage limits for code reviews. You can "
            "see your limits in the [Codex usage dashboard]"
            "(https://chatgpt.com/codex/cloud/settings/usage).\n",
            at,
        )
        comment["created_at"] = at
        return comment

    def test_owner_attestation_accepted_for_exact_head(self):
        comments = [self.outage(), self.owner_comment(self.valid_payload())]
        self.assertTrue(gate.codex_unavailable(comments, self.HEAD_AT))
        self.assertTrue(gate.owner_attestation_complete(comments, self.HEAD))

    def test_owner_attestation_rejects_other_head(self):
        comments = [self.owner_comment(self.valid_payload("f" * 40))]
        self.assertFalse(gate.owner_attestation_complete(comments, self.HEAD))

    def test_owner_attestation_rejects_non_owner_and_apps(self):
        payload = self.valid_payload()
        for override in (
            {"user": {"login": "someone-else", "type": "User"}},
            {"author_association": "COLLABORATOR"},
            {"user": {"login": "GBOGEB", "type": "Bot"}},
            {"performed_via_github_app": {"id": 1, "slug": "x"}},
        ):
            comments = [self.owner_comment(payload, **override)]
            self.assertFalse(
                gate.owner_attestation_complete(comments, self.HEAD), override
            )

    def test_owner_attestation_requires_full_scope_reason_and_reviewer(self):
        for bad in (
            '{"headSha":"%s","status":"completed","scope":"code",'
            '"reason":"codex_unavailable","reviewer":"GBOGEB"}',
            '{"headSha":"%s","status":"completed","scope":"code+security",'
            '"reason":"convenience","reviewer":"GBOGEB"}',
            '{"headSha":"%s","status":"completed","scope":"code+security",'
            '"reason":"codex_unavailable","reviewer":"  "}',
            '{"headSha":"%s","status":"pending","scope":"code+security",'
            '"reason":"codex_unavailable","reviewer":"GBOGEB"}',
        ):
            comments = [self.owner_comment(bad % self.HEAD)]
            self.assertFalse(gate.owner_attestation_complete(comments, self.HEAD))

    def test_latest_owner_attestation_wins(self):
        newer_wrong = self.owner_comment(
            self.valid_payload("e" * 40), updated_at="2026-10-11T21:00:00Z"
        )
        comments = [self.owner_comment(self.valid_payload()), newer_wrong]
        self.assertFalse(gate.owner_attestation_complete(comments, self.HEAD))

    def test_codex_unavailable_requires_trusted_codex_identity(self):
        forged = {
            "body": "You have reached your Codex usage limits for code reviews.",
            "user": {"login": "GBOGEB", "id": 1},
        }
        self.assertFalse(gate.codex_unavailable([forged], self.HEAD_AT))

    def test_head_time_comes_from_server_runs_not_commit_metadata(self):
        runs = [
            {
                "event": "pull_request",
                "head_sha": self.HEAD,
                "created_at": "2026-10-11T19:05:00Z",
                "pull_requests": [{"number": 7}],
            },
            {
                "event": "pull_request",
                "head_sha": self.HEAD,
                "created_at": "2026-10-11T19:00:00Z",
                "pull_requests": [{"number": 7}],
            },
            {
                "event": "push",
                "head_sha": self.HEAD,
                "created_at": "2026-10-11T10:00:00Z",
                "pull_requests": [],
            },
            {
                "event": "pull_request",
                "head_sha": self.HEAD,
                "created_at": "2026-10-11T09:00:00Z",
                "pull_requests": [{"number": 8}],
            },
            {
                "event": "pull_request",
                "head_sha": "f" * 40,
                "created_at": "2026-10-11T08:00:00Z",
                "pull_requests": [{"number": 7}],
            },
        ]
        self.assertEqual(
            gate.head_current_since(runs, self.HEAD, 7), "2026-10-11T19:05:00Z"
        )

    def test_force_push_back_to_old_sha_rebinds_to_new_transition(self):
        # A ran at 18:00, B got an outage at 18:30, PR force-pushed back to A
        # at 19:00 (fresh runs). The 18:30 outage must not cover A.
        runs = [
            {
                "event": "pull_request",
                "head_sha": self.HEAD,
                "created_at": "2026-10-11T18:00:00Z",
                "pull_requests": [{"number": 7}],
            },
            {
                "event": "pull_request",
                "head_sha": self.HEAD,
                "created_at": "2026-10-11T19:00:00Z",
                "pull_requests": [{"number": 7}],
            },
        ]
        since = gate.head_current_since(runs, self.HEAD, 7)
        self.assertFalse(
            gate.codex_unavailable([self.outage(at="2026-10-11T18:30:00Z")], since)
        )

    def test_reused_head_disables_break_glass_fallback(self):
        h1 = self.HEAD
        h2 = "f" * 40
        runs = [
            {
                "event": "pull_request",
                "head_sha": h1,
                "created_at": "2026-10-11T18:00:00Z",
                "pull_requests": [{"number": 7}],
            },
            {
                "event": "pull_request",
                "head_sha": h2,
                "created_at": "2026-10-11T18:20:00Z",
                "pull_requests": [{"number": 7}],
            },
            {
                "event": "pull_request",
                "head_sha": h1,
                "created_at": "2026-10-11T19:00:00Z",
                "pull_requests": [{"number": 7}],
            },
        ]
        self.assertTrue(gate.head_reused_across_transitions(runs, h1, 7))
        self.assertFalse(gate.head_reused_across_transitions(runs[:1], h1, 7))
        self.assertTrue(gate.head_reused_across_transitions([], h1, 7))
        self.assertTrue(gate.head_reused_across_transitions(runs, h2, 7))

    def test_no_server_head_time_keeps_fallback_closed(self):
        self.assertEqual(gate.head_current_since([], self.HEAD, 7), "")
        self.assertFalse(gate.codex_unavailable([self.outage()], ""))

    def test_review_quoting_outage_text_is_not_an_outage(self):
        quoting = self.trusted_codex_comment(
            "### Codex Review\nThe gate matches 'You have reached your Codex "
            "usage limits for code reviews. You can see your limits in the "
            "[Codex usage dashboard](https://chatgpt.com/codex/cloud/settings/"
            "usage).' as an outage.",
            "2026-10-11T19:30:00Z",
        )
        self.assertFalse(gate.codex_unavailable([quoting], self.HEAD_AT))

    def test_security_allowance_notice_is_an_outage(self):
        notice = self.trusted_codex_comment(
            "This security review couldn\u2019t start because the paying account "
            "has exhausted its Codex allowance and has insufficient available "
            "credits. The payer can check their balance and add credits in the "
            "[Codex usage dashboard](https://chatgpt.com/codex/cloud/settings/"
            "usage), then try again. If you do not manage the paying account, "
            "contact this repository's admins.",
            "2026-10-11T19:30:00Z",
        )
        self.assertTrue(gate.codex_unavailable([notice], self.HEAD_AT))

    def test_outage_from_earlier_push_does_not_carry_over(self):
        stale = self.outage(at="2026-10-11T18:00:00Z")
        self.assertFalse(gate.codex_unavailable([stale], self.HEAD_AT))

    def test_later_codex_activity_cancels_outage(self):
        recovered = self.trusted_codex_comment(
            "<!-- codex-pull-request-review-summary --> review running",
            "2026-10-11T19:45:00Z",
        )
        self.assertFalse(
            gate.codex_unavailable([self.outage(), recovered], self.HEAD_AT)
        )

    def test_attestation_must_postdate_the_outage(self):
        early = self.owner_comment(
            self.valid_payload(), created_at="2026-10-11T19:10:00Z"
        )
        self.assertFalse(
            gate.owner_attestation_complete(
                [early], self.HEAD, not_before="2026-10-11T19:30:00Z"
            )
        )

    def test_outage_timestamp_tie_with_head_is_rejected(self):
        # GitHub timestamps have one-second resolution: ties prove no order.
        self.assertFalse(
            gate.codex_unavailable([self.outage(at=self.HEAD_AT)], self.HEAD_AT)
        )

    def test_attestation_timestamp_tie_with_outage_is_rejected(self):
        same_second = self.owner_comment(
            self.valid_payload(), created_at="2026-10-11T19:30:00Z"
        )
        self.assertFalse(
            gate.owner_attestation_complete(
                [same_second], self.HEAD, not_before="2026-10-11T19:30:00Z"
            )
        )

    def test_evaluate_uses_attestation_only_during_outage(self):
        class FakeGitHub:
            def __init__(self, comments):
                self._comments = comments

            def issue_comments(self, number):
                return self._comments

            def review_threads(self, number):
                return []

            def actions_runs(self, head_sha):
                return self._runs

            _runs: list = []

            def pull_files(self, number):
                return ["README.md"]

            def pull_file_records(self, number):
                return [{"filename": "README.md"}]

            def issue(self, number):
                return {"state": "open"}

        pull = {
            "state": "open",
            "base": {"ref": "main"},
            "head": {"sha": self.HEAD},
            "changed_files": 1,
        }
        attested = self.owner_comment(self.valid_payload())

        FakeGitHub._runs = [
            {
                "name": "Advisory lint",  # not a required workflow
                "event": "pull_request",
                "head_sha": self.HEAD,
                "created_at": self.HEAD_AT,
                "pull_requests": [{"number": 1}],
            }
        ]
        without_outage = gate.evaluate(FakeGitHub([attested]), 1, pull)
        self.assertEqual(without_outage.review_source, "codex")
        self.assertFalse(without_outage.security_review_complete)

        with_outage = gate.evaluate(
            FakeGitHub([self.current_head_request(), self.outage(), attested]),
            1,
            pull,
        )
        # Security regression: outage + exact-head owner attestation must never
        # replace independent code/security review, even when all evidence is fresh.
        self.assertEqual(with_outage.review_source, "codex")
        self.assertFalse(with_outage.code_review_complete)
        self.assertFalse(with_outage.security_review_complete)
        # CI is still required: with no runs the gate stays pending, never green.
        self.assertEqual(with_outage.state, "pending")
        self.assertTrue(any("CI missing" in r for r in with_outage.pending_reasons))

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
            gate.security_sensitive_change([".github/workflows/pr-feedback-gate.yml"])
        )
        self.assertTrue(
            gate.security_sensitive_change(["ci/governance/pr_feedback_gate.py"])
        )
        self.assertFalse(
            gate.security_sensitive_change(["docs/img/ordinary-figure.png"])
        )

    def test_review_deferral_requires_classifications_and_exact_open_issue(self):
        head = "a" * 40
        issue_body = (
            "<!-- abacus-deferred-security:v1 "
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
                    "user": {"login": "owner"},
                }

            def can_write(self, login):
                return login == "owner"

        marker = {
            "headSha": head,
            "trackingIssue": 1846,
            "codexCodeReviewRequired": True,
            "codexSecurityReviewRequired": True,
            "items": [{"threadId": "THREAD-1", "classification": "S2"}],
        }
        comment = {
            "author_association": "OWNER",
            "user": {"login": "owner"},
            "body": (
                "CODEX_CODE_REVIEW=DEFERRED_BUDGET\n"
                "CODEX_SECURITY_REVIEW=DEFERRED_BUDGET\n"
                "<!-- abacus-review-disposition:v2 " + json.dumps(marker) + " -->"
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
                "comments": {"nodes": [{"createdAt": "2026-10-11T14:00:00Z"}]},
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
            # Same second as the disposition: cannot prove it came first.
            {"createdAt": "2026-10-11T15:00:00Z"},
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
            "<!-- abacus-review-disposition:v2 " + json.dumps(marker) + " -->"
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

    def deferral_result(
        self,
        metadata,
        association="OWNER",
        issue_author="owner",
        comment_author="owner",
    ):
        head = "a" * 40
        body = "<!-- abacus-deferred-security:v1 " + json.dumps(metadata) + " -->"

        class FakeGitHub:
            def issue(self, number):
                return {
                    "number": number,
                    "state": "open",
                    "body": body,
                    "author_association": association,
                    "user": {"login": issue_author},
                }

            def can_write(self, login):
                return login == "owner"

        marker = {
            "headSha": head,
            "trackingIssue": 1846,
            "codexCodeReviewRequired": True,
            "codexSecurityReviewRequired": True,
            "items": [{"threadId": "THREAD-1", "classification": "S2"}],
        }
        comment = {
            "author_association": "OWNER",
            "user": {"login": "owner"},
            "body": (
                "CODEX_CODE_REVIEW=DEFERRED_BUDGET\n"
                "CODEX_SECURITY_REVIEW=DEFERRED_BUDGET\n"
                "<!-- abacus-review-disposition:v2 " + json.dumps(marker) + " -->"
            ),
        }
        comment["user"]["login"] = comment_author
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
        evidence = self.deferral_result({"pr": 42, "headSha": head, "status": "OPEN"})
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
        self.assertIn("write access", evidence[2][0])

    def test_read_only_collaborators_cannot_defer(self):
        metadata = self.full_debt_metadata("a" * 40)
        self.assertTrue(self.deferral_result(metadata)[0])
        # Association alone is not authorization: a read- or triage-only
        # collaborator can open the issue or post the disposition.
        evidence = self.deferral_result(
            metadata, association="COLLABORATOR", issue_author="reader"
        )
        self.assertFalse(evidence[0])
        self.assertIn("write access", evidence[2][0])
        evidence = self.deferral_result(metadata, comment_author="reader")
        self.assertEqual(evidence, (False, (), ()))

    def test_write_permission_lookup_fails_closed(self):
        class FakeGitHub(gate.GitHub):
            def __init__(self, responses):
                super().__init__("token", "GBOGEB/ABACUS")
                self.responses = responses
                self.calls = 0

            def request(self, method, path, payload=None):
                self.calls += 1
                response = self.responses[path.rsplit("/", 2)[-2]]
                if isinstance(response, Exception):
                    raise response
                return response

        github = FakeGitHub(
            {
                "writer": {"permission": "write", "role_name": "write"},
                "maintainer": {"permission": "write", "role_name": "maintain"},
                "triager": {"permission": "read", "role_name": "triage"},
                "outsider": gate.GitHubAPIError("GitHub API GET failed", 404),
                "throttled": gate.GitHubAPIError("GitHub API GET failed", 403),
                "broken": gate.GitHubAPIError("GitHub API GET failed", 502),
            }
        )
        # A lookup that failed for any reason but 404 is not "untrusted":
        # it must fail the job, not silently drop the event.
        with self.assertRaises(gate.GitHubAPIError):
            github.can_write("throttled")
        with self.assertRaises(gate.GitHubAPIError):
            github.can_write("broken")
        github.calls = 0
        self.assertTrue(github.can_write("writer"))
        self.assertTrue(github.can_write("maintainer"))
        self.assertFalse(github.can_write("triager"))
        self.assertFalse(github.can_write("outsider"))
        self.assertTrue(github.can_write("writer"))
        self.assertEqual(github.calls, 4)

    def test_rename_out_of_sensitive_path_is_sensitive(self):
        paths = gate.changed_paths_from_files(
            [
                {
                    "filename": "tools/pr_feedback_gate.py",
                    "previous_filename": "ci/governance/pr_feedback_gate.py",
                    "status": "renamed",
                },
                {"filename": "docs/img/figure.png", "status": "modified"},
            ]
        )
        self.assertEqual(
            paths,
            [
                "tools/pr_feedback_gate.py",
                "ci/governance/pr_feedback_gate.py",
                "docs/img/figure.png",
            ],
        )
        self.assertTrue(gate.security_sensitive_change(paths))
        self.assertFalse(
            gate.security_sensitive_change(
                gate.changed_paths_from_files([{"filename": "docs/img/figure.png"}])
            )
        )

    def test_executable_paths_are_sensitive_by_default(self):
        for path in (
            ".github/scripts/security_dashboard.py",
            ".github/actions/runtime-guard/action.yml",
            "scripts/generate_iteration_report.py",
            "requirements.txt",
            "src/dmaic/federation.py",
            "docs/api/metrics.json",
            "handover/pipelines/SAMPLE_MARKDOWN_PIPELINE.md",
            # Pandoc passes raw HTML in Markdown/reST into published output.
            "README.md",
            "docs/guide.rst",
            # SVG can carry script and docs/** deploys to Pages.
            "docs/img/flow.SVG",
            # PDF can carry JavaScript, embedded files and launch actions.
            "docs/report.PDF",
        ):
            self.assertTrue(gate.security_sensitive_change([path]), path)
        for path in ("docs/img/flow.PNG", "assets/logo.jpg", "a/b.gif"):
            self.assertFalse(gate.security_sensitive_change([path]), path)

    def test_tracking_issue_change_recensuses_only_named_prs(self):
        class FakeGitHub:
            def open_pulls(self):
                raise AssertionError("issue events must not sweep all PRs")

            def can_write(self, login):
                return login == "owner"

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
                "user": {"login": "owner"},
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
                "user": {"login": "owner"},
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

    def test_admitted_tracker_change_recensuses_after_access_loss(self):
        class FakeGitHub:
            def open_pulls(self):
                raise AssertionError("issue events must not sweep all PRs")

            def can_write(self, login):
                return False  # the author has since lost write access

            def pull(self, number):
                return {"head": {"sha": "abc"}}

            def __init__(self, cited_by_latest=True):
                self.cited_by_latest = cited_by_latest

            def check_runs(self, head_sha):
                latest = (
                    "- tracked by open issue #1849"
                    if self.cited_by_latest
                    else "- tracked by open issue #1900"
                )
                return [
                    {
                        "name": gate.GATE_NAME,
                        "status": "completed",
                        "completed_at": "2026-10-12T10:00:00Z",
                        "output": {"text": "- tracked by open issue #1849"},
                    },
                    {
                        "name": gate.GATE_NAME,
                        "status": "completed",
                        "completed_at": "2026-10-12T11:00:00Z",
                        "output": {"text": latest},
                    },
                    {
                        # A census in flight is not yet a result.
                        "name": gate.GATE_NAME,
                        "status": "in_progress",
                        "started_at": "2026-10-12T12:00:00Z",
                        "output": {"text": "evaluating"},
                    },
                ]

        marker = (
            '<!-- abacus-deferred-security:v1 {"pr": 1847, '
            '"headSha": "abc", "status": "OPEN"} -->'
        )
        marker_stripped = {
            "action": "edited",
            "issue": {
                "number": 1849,
                "author_association": "MEMBER",
                "user": {"login": "former-writer"},
                "body": "debt cleared",
            },
            "changes": {"body": {"from": marker}},
        }
        self.assertEqual(
            gate.event_pr_numbers(FakeGitHub(), marker_stripped, None),
            [1847],
        )
        closed = {
            "action": "closed",
            "issue": {
                "number": 1849,
                "author_association": "NONE",
                "user": {"login": "former-writer"},
                "body": marker,
            },
        }
        self.assertEqual(gate.event_pr_numbers(FakeGitHub(), closed, None), [1847])
        # Only an older, superseded result cites #1849: ignore the edit.
        self.assertEqual(
            gate.event_pr_numbers(
                FakeGitHub(cited_by_latest=False), marker_stripped, None
            ),
            [],
        )

    def test_untracked_or_untrusted_issue_change_is_ignored(self):
        class FakeGitHub:
            def open_pulls(self):
                raise AssertionError("issue events must not sweep all PRs")

            def can_write(self, login):
                return login == "owner"

            def pull(self, number):
                return {"head": {"sha": "abc"}}

            def check_runs(self, head_sha):
                # The PR's gate never admitted these issues.
                return [
                    {
                        "name": gate.GATE_NAME,
                        "status": "completed",
                        "output": {"text": "tracked by open issue #18490"},
                    }
                ]

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
        self.assertEqual(gate.event_pr_numbers(FakeGitHub(), plain_issue, None), [])
        untrusted_issue = {
            "action": "edited",
            "issue": {
                "number": 8,
                "author_association": "NONE",
                "body": marker,
            },
        }
        self.assertEqual(gate.event_pr_numbers(FakeGitHub(), untrusted_issue, None), [])
        read_only_member = {
            "action": "edited",
            "issue": {
                "number": 9,
                "author_association": "MEMBER",
                "user": {"login": "reader"},
                "body": marker,
            },
        }
        self.assertEqual(
            gate.event_pr_numbers(FakeGitHub(), read_only_member, None), []
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
        self.assertEqual(gate.event_pr_numbers(FakeGitHub(), public_comment, None), [])

    def test_workflow_subscribes_to_tracking_issue_lifecycle(self):
        workflow = (
            pathlib.Path(__file__).resolve().parents[3]
            / ".github"
            / "workflows"
            / "pr-feedback-gate.yml"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "issues:\n    types: [edited, closed, reopened, deleted, " "transferred]",
            workflow,
        )
        self.assertIn(
            "issue_comment:\n    types: [created, edited, deleted]",
            workflow,
        )
        # Not an Actions-supported trigger; declaring it would be a no-op.
        self.assertNotIn("pull_request_review_thread:", workflow)
        # Every evaluator step shares the run's census stamp, including the
        # failure publication.
        self.assertEqual(
            workflow.count('args+=(--census-started "$CENSUS_STARTED")'), 4
        )
        # Every census of one PR, whatever its trigger, shares that PR's
        # job concurrency group, so two censuses cannot interleave their
        # read and write of the check.
        self.assertIn(
            "group: pr-feedback-gate-pr-${{ matrix.pr }}\n"
            "      cancel-in-progress: false",
            workflow,
        )
        self.assertEqual(workflow.count('args+=(--pr-number "$PR_NUMBER")'), 4)
        # A tracking-issue event invalidates the check outside the PR's
        # census queue, so a census already running cannot leave a success
        # computed from the old issue standing.
        invalidate = workflow.split("  invalidate:\n", 1)[1].split(
            "\n  evaluate:\n", 1
        )[0]
        self.assertIn("github.event_name == 'issues'", invalidate)
        # A head change is invalidated outside the queue too, so a PR moved
        # A -> B -> A never re-exposes A's earlier success (#1878).
        self.assertIn("github.event_name == 'pull_request'", invalidate)
        self.assertIn("github.event.action == 'synchronize'", invalidate)
        self.assertIn("github.event.action == 'reopened'", invalidate)
        self.assertIn(
            "pull_request:\n    types: [opened, synchronize, reopened]",
            workflow,
        )
        self.assertIn("ref: ${{ github.event.repository.default_branch }}", invalidate)
        # The same event's census runs after its invalidation, so the
        # invalidator's newer stamp cannot reject the census result.
        evaluate = workflow.split("  evaluate:\n", 1)[1]
        self.assertIn("needs: [route, invalidate]", evaluate)
        self.assertIn("!cancelled()", evaluate)
        self.assertIn("needs.route.result == 'success'", evaluate)
        self.assertIn("--mark-pending-only", invalidate)
        self.assertNotIn("concurrency:", invalidate)
        # A no-op event must never cancel or displace a run that has PRs to
        # re-census, so nothing may cancel in-progress runs.
        self.assertNotIn("cancel-in-progress: true", workflow)
        self.assertEqual(workflow.count("concurrency:"), 1)

    def test_list_prs_routes_only_open_main_pulls(self):
        class FakeGitHub:
            def pull(self, number):
                return {
                    7: {"state": "open", "base": {"ref": "main"}},
                    8: {"state": "closed", "base": {"ref": "main"}},
                    9: {"state": "open", "base": {"ref": "dev"}},
                }[number]

            def open_pulls(self):
                return [{"number": 9}, {"number": 8}, {"number": 7}]

        self.assertEqual(gate.evaluable_pr_numbers(FakeGitHub(), {}, None), [7])
        self.assertEqual(gate.evaluable_pr_numbers(FakeGitHub(), {}, 8), [])

    def test_deferral_success_is_revalidated_before_publication(self):
        def evidence(**changes):
            base = {
                "head_sha": "a" * 40,
                "code_review_complete": False,
                "security_review_complete": False,
                "unresolved_threads": 0,
                "ci_pending": (),
                "ci_failed": (),
                "ci_seen": 1,
                "deferred_comments": (),
                "review_deferral_valid": True,
            }
            base.update(changes)
            return gate.Evidence(**base)

        deferred = evidence()
        self.assertEqual(deferred.state, "success")
        closed = evidence(
            review_deferral_valid=False,
            review_deferral_details=(
                (
                    "review deferral has no open issue #9 bound to PR #1 "
                    "and the current head"
                ),
            ),
        )
        # The tracker closed mid-census: the stale success is not published.
        with mock.patch.object(gate, "evaluate", return_value=closed):
            result = gate.revalidated_evidence(object(), 1, deferred)
        self.assertEqual(result, closed)
        self.assertEqual(result.state, "failure")
        # An unchanged re-census confirms the success.
        with mock.patch.object(gate, "evaluate", return_value=deferred):
            self.assertEqual(gate.revalidated_evidence(object(), 1, deferred), deferred)
        # Evidence that keeps changing never publishes success.
        flapping = [evidence(ci_seen=n) for n in range(2, 6)]
        with mock.patch.object(gate, "evaluate", side_effect=flapping):
            self.assertEqual(
                gate.revalidated_evidence(object(), 1, deferred).state,
                "pending",
            )
        # A success that rests on completed reviews needs no re-census.
        reviewed = evidence(
            code_review_complete=True,
            security_review_complete=True,
            review_deferral_valid=False,
        )
        with mock.patch.object(gate, "evaluate") as evaluate:
            self.assertEqual(gate.revalidated_evidence(object(), 1, reviewed), reviewed)
        evaluate.assert_not_called()

    def test_incomplete_file_census_fails_closed(self):
        records = [{"filename": "docs/note.md"}]
        self.assertTrue(gate.file_census_complete(records, {"changed_files": 1}))
        self.assertFalse(gate.file_census_complete(records, {"changed_files": 3001}))
        self.assertFalse(gate.file_census_complete(records, {}))
        self.assertFalse(gate.file_census_complete(records, {"changed_files": True}))

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
            any("incomplete PR file census" in item for item in evidence.ci_failed)
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
        self.assertEqual(gate.census_started_from("a=1\ncensus_started=X\n"), "X")
        self.assertIsNone(gate.census_started_from("state=pending"))

    def test_census_stamps_are_fixed_width(self):
        stamp = gate.utc_now()
        self.assertEqual(gate.census_started_arg(stamp), stamp)
        self.assertRegex(stamp, r"\.\d{6}Z$")
        for bad in ("2026-10-11T15:00:01Z", "yesterday"):
            with self.assertRaises(gate.argparse.ArgumentTypeError):
                gate.census_started_arg(bad)

    def test_departing_head_is_invalidated_on_synchronize(self):
        head = "b" * 40
        before = "a" * 40
        event = {
            "action": "synchronize",
            "before": before,
            "after": head,
            "pull_request": {"number": 7},
        }
        self.assertEqual(gate.departing_head_sha(event, 7, head), before)
        for changed in (
            {"action": "opened"},
            {"action": "reopened"},
            {"before": head},
            {"before": "0" * 40},
            {"before": "not-a-sha"},
            {"pull_request": {"number": 8}},
        ):
            self.assertIsNone(
                gate.departing_head_sha({**event, **changed}, 7, head),
                changed,
            )
        self.assertIsNone(gate.departing_head_sha({}, 7, head))

    def test_mark_pending_also_supersedes_departing_head(self):
        head = "b" * 40
        before = "a" * 40
        published = []

        class FakeGitHub:
            def __init__(self, token, repository):
                pass

            def pull(self, number):
                return {
                    "state": "open",
                    "base": {"ref": "main"},
                    "head": {"sha": head},
                }

            def publish_gate(self, sha, state, title, summary, text, **kw):
                published.append((sha, state, kw.get("census_started")))
                return True

        event = {
            "action": "synchronize",
            "before": before,
            "after": head,
            "pull_request": {"number": 7},
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "event.json"
            path.write_text(json.dumps(event), encoding="utf-8")
            argv = [
                "pr_feedback_gate.py",
                "--event-path",
                str(path),
                "--pr-number",
                "7",
                "--census-started",
                "2026-10-17T20:00:00.000000Z",
                "--mark-pending-only",
            ]
            env = {"GITHUB_REPOSITORY": "o/r", "GITHUB_TOKEN": "t"}
            with (
                mock.patch.object(gate, "GitHub", FakeGitHub),
                mock.patch.object(sys, "argv", argv),
                mock.patch.dict(os.environ, env),
            ):
                self.assertEqual(gate.main(), 0)
        self.assertEqual(
            [(sha, state) for sha, state, _ in published],
            [(head, "pending"), (before, "pending")],
        )
        self.assertEqual(len({stamp for _, _, stamp in published}), 1)


if __name__ == "__main__":
    unittest.main()
