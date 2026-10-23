import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
POLICY = ROOT / "ci/governance/workflow_policy.json"
WORKFLOWS = ROOT / ".github/workflows"
WRITE_SCOPES = (
    "actions: write",
    "checks: write",
    "contents: write",
    "deployments: write",
    "issues: write",
    "packages: write",
    "pages: write",
    "pull-requests: write",
    "security-events: write",
)


class ExecutionTierTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.tiers = self.policy["execution_tiers"]

    def test_tier_members_exist_and_do_not_overlap(self):
        slim = set(self.tiers["slim_pr"]["workflows"])
        full = set(self.tiers["full"]["workflows"])
        scoped = set(self.tiers["path_scoped_pr"]["workflows"])
        self.assertFalse(slim & full)
        self.assertFalse(slim & scoped)
        self.assertFalse(full & scoped)
        for filename in slim | full | scoped:
            self.assertTrue((WORKFLOWS / filename).exists(), filename)

    def test_full_tier_does_not_run_on_pull_requests(self):
        for filename in self.tiers["full"]["workflows"]:
            source = (WORKFLOWS / filename).read_text(encoding="utf-8")
            self.assertNotIn("pull_request:", source, filename)

    def test_full_tier_retains_a_non_pr_trigger(self):
        allowed = ("push:", "schedule:", "workflow_dispatch:", "workflow_run:", "deployment_status:")
        for filename in self.tiers["full"]["workflows"]:
            source = (WORKFLOWS / filename).read_text(encoding="utf-8")
            self.assertTrue(any(trigger in source for trigger in allowed), filename)

    def test_failure_issue_job_ignores_deployment_events(self):
        source = (WORKFLOWS / "ci_monitor_and_issue_creator.yml").read_text(encoding="utf-8")
        condition = "github.event_name == 'workflow_run' && github.event.workflow_run.conclusion == 'failure'"
        self.assertIn(condition, source)

    def test_controlled_push_workflows_are_main_only(self):
        pattern = re.compile(r"(?m)^  push:\n    branches: \[main\]")
        for filename in self.policy["branch_push_controls"]["main_only"]:
            source = (WORKFLOWS / filename).read_text(encoding="utf-8")
            self.assertRegex(source, pattern, filename)

    def test_pr_write_permissions_are_explicitly_approved(self):
        allowed = set(self.policy["permission_controls"]["pr_write_allowed"])
        actual = set()
        for path in WORKFLOWS.glob("*.yml"):
            source = path.read_text(encoding="utf-8")
            if "pull_request:" in source and any(scope in source for scope in WRITE_SCOPES):
                actual.add(path.name)
        self.assertEqual(allowed, actual)

    def test_quality_pilot_pr_scan_has_no_write_permissions(self):
        source = (WORKFLOWS / "code-quality-pilot.yml").read_text(encoding="utf-8")
        pilot = source.split("\n  pilot:\n", 1)[1].split("\n  telemetry:\n", 1)[0]
        telemetry = source.split("\n  telemetry:\n", 1)[1]
        for scope in WRITE_SCOPES:
            self.assertNotIn(scope, pilot)
        self.assertIn("issues: write", telemetry)
        self.assertIn("github.event_name == 'schedule'", telemetry)
        self.assertIn("github.event_name == 'workflow_dispatch'", telemetry)
        self.assertIn("github.ref == 'refs/heads/main'", telemetry)

    def test_pull_request_target_write_permissions_are_not_enabled(self):
        allowed = set(self.policy["permission_controls"]["pull_request_target_write_allowed"])
        actual = set()
        for path in WORKFLOWS.glob("*.yml"):
            source = path.read_text(encoding="utf-8")
            if "pull_request_target:" in source and any(scope in source for scope in WRITE_SCOPES):
                actual.add(path.name)
        self.assertEqual(allowed, actual)


    @staticmethod
    def _sarif_trust_boundary(pr_source, cd_source):
        """Pure negative oracle: PR can scan, only exact main push can publish."""
        marker = "\n  trusted-main-trivy-sarif:\n"
        if (pr_source.count("  pull_request:") != 1
                or "Scan Docker Image" not in pr_source
                or "name: ci-trivy-sarif" not in pr_source
                or "security-events: write" in pr_source
                or "upload-sarif@" in pr_source):
            return False
        if "  pull_request:" in cd_source or cd_source.count(marker) != 1:
            return False
        # Keep requirements inside this job, not in a later unrelated job.
        publisher = re.split(
            r"(?m)^  [A-Za-z_][\w-]*:\s*$",
            cd_source.split(marker, 1)[1], maxsplit=1,
        )[0]
        upload_pins = re.findall(
            r"(?m)^\s*(?:-\s*)?uses:\s*github/codeql-action/upload-sarif@"
            r"([0-9a-f]{40})(?:\s+#.*)?\s*$", publisher,
        )
        return (
            "if: github.event_name == 'push' && github.ref == 'refs/heads/main'"
            in publisher
            and "security-events: write" in publisher
            and "test \"$GITHUB_REF\" = refs/heads/main" in publisher
            and "test \"$(git rev-parse HEAD)\" = \"$GITHUB_SHA\"" in publisher
            and upload_pins == ["6f2ac81f5cd81fe351a197ba0b00d91d03cd2aee"]
        )

    def test_path_scoped_pr_domain_preserves_actual_triggers(self):
        scope = set(self.tiers["path_scoped_pr"]["workflows"])
        self.assertEqual(scope, {"ariana-cicd.yml", "ci-pipeline.yml"})
        for filename in scope:
            src = (WORKFLOWS / filename).read_text(encoding="utf-8")
            self.assertIn("  pull_request:", src)
            self.assertIn("    paths:", src)

    def test_sarif_pr_scan_and_main_publication_have_separate_authorities(self):
        pr = (WORKFLOWS / "ci-pipeline.yml").read_text(encoding="utf-8")
        cd = (WORKFLOWS / "cd-pipeline.yml").read_text(encoding="utf-8")
        self.assertTrue(self._sarif_trust_boundary(pr, cd))

    def test_negative_pr_write_scope_reintroduction_trips(self):
        pr = (WORKFLOWS / "ci-pipeline.yml").read_text(encoding="utf-8")
        cd = (WORKFLOWS / "cd-pipeline.yml").read_text(encoding="utf-8")
        self.assertTrue(self._sarif_trust_boundary(pr, cd))
        self.assertFalse(self._sarif_trust_boundary(
            pr.replace("      actions: read",
                       "      actions: read\n      security-events: write", 1),
            cd,
        ))

    def test_reverse_untrusted_main_publication_condition_trips(self):
        pr = (WORKFLOWS / "ci-pipeline.yml").read_text(encoding="utf-8")
        cd = (WORKFLOWS / "cd-pipeline.yml").read_text(encoding="utf-8")
        self.assertTrue(self._sarif_trust_boundary(pr, cd))
        guard = (
            "if: github.event_name == 'push' && github.ref == 'refs/heads/main'"
        )
        self.assertFalse(self._sarif_trust_boundary(
            pr, cd.replace(guard, "if: github.event_name == 'pull_request'", 1)
        ))

    def test_force_trip_missing_exact_head_guard_trips(self):
        pr = (WORKFLOWS / "ci-pipeline.yml").read_text(encoding="utf-8")
        cd = (WORKFLOWS / "cd-pipeline.yml").read_text(encoding="utf-8")
        self.assertTrue(self._sarif_trust_boundary(pr, cd))
        self.assertFalse(self._sarif_trust_boundary(
            pr, cd.replace('test "$(git rev-parse HEAD)" = "$GITHUB_SHA"',
                           'echo "unchecked SHA"', 1)
        ))


    def test_negative_mutable_or_unapproved_sarif_pin_trips(self):
        pr = (WORKFLOWS / "ci-pipeline.yml").read_text(encoding="utf-8")
        cd = (WORKFLOWS / "cd-pipeline.yml").read_text(encoding="utf-8")
        self.assertTrue(self._sarif_trust_boundary(pr, cd))
        approved = "6f2ac81f5cd81fe351a197ba0b00d91d03cd2aee"
        for replacement in ("v4", "0" * 40):
            with self.subTest(replacement=replacement):
                changed = cd.replace("upload-sarif@" + approved,
                                     "upload-sarif@" + replacement, 1)
                self.assertNotEqual(cd, changed)
                self.assertFalse(self._sarif_trust_boundary(pr, changed))

    def test_negative_guard_in_unrelated_job_cannot_complete_publisher(self):
        pr = (WORKFLOWS / "ci-pipeline.yml").read_text(encoding="utf-8")
        cd = (WORKFLOWS / "cd-pipeline.yml").read_text(encoding="utf-8")
        self.assertTrue(self._sarif_trust_boundary(pr, cd))
        guard = "test \"$(git rev-parse HEAD)\" = \"$GITHUB_SHA\""
        changed = cd.replace(guard, 'echo "unchecked SHA"', 1)
        self.assertNotEqual(cd, changed)
        changed += "\n  unrelated-job:\n    steps:\n      - run: " + guard + "\n"
        self.assertFalse(self._sarif_trust_boundary(pr, changed))


if __name__ == "__main__":
    unittest.main()
