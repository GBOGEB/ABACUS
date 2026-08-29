import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("audit_ci_workflows", ROOT / "scripts/audit_ci_workflows.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class WorkflowPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads((ROOT / "ci/governance/workflow_policy.json").read_text())

    def test_repository_workflows_are_classified_once(self):
        report = MODULE.audit(ROOT / ".github/workflows", self.policy)
        self.assertEqual([], report["unclassified"])
        self.assertEqual({}, report["multiple_matches"])
        self.assertEqual([], report["missing_canonical"])

    def test_parser_extracts_top_level_jobs_and_events(self):
        source = """name: Example\non:\n  push:\n  pull_request:\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: pytest -q\n  lint:\n    runs-on: ubuntu-latest\n"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "example.yml"
            path.write_text(source)
            workflow = MODULE.parse_workflow(path)
        self.assertEqual(("push", "pull_request"), workflow.events)
        self.assertEqual(("test", "lint"), workflow.jobs)
        self.assertIn("pytest -q", workflow.commands)

    def test_policy_has_one_canonical_per_nonlegacy_cluster(self):
        for cluster, data in self.policy["clusters"].items():
            if cluster != "legacy":
                self.assertTrue(data["canonical"], cluster)

    def test_check_mode_rejects_stale_markdown_without_overwriting_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "report.md"
            report_path.write_text("stale report\n", encoding="utf-8")
            original_argv = sys.argv
            sys.argv = [
                "audit_ci_workflows.py",
                "--policy",
                str(ROOT / "ci/governance/workflow_policy.json"),
                "--workflow-dir",
                str(ROOT / ".github/workflows"),
                "--markdown-output",
                str(report_path),
                "--check",
            ]
            try:
                with contextlib.redirect_stderr(io.StringIO()):
                    result = MODULE.main()
            finally:
                sys.argv = original_argv
            self.assertEqual(1, result)
            self.assertEqual("stale report\n", report_path.read_text(encoding="utf-8"))

    def test_governance_runs_when_generated_inventory_changes(self):
        workflow = (ROOT / ".github/workflows/ci-governance.yml").read_text(encoding="utf-8")
        governed_path = '- "docs/ci/WORKFLOW_RATIONALIZATION.md"'
        self.assertEqual(2, workflow.count(governed_path))

    def test_full_regression_excludes_governance_only_python(self):
        workflow = (ROOT / ".github/workflows/ci-cd-tests.yml").read_text(encoding="utf-8")
        self.assertEqual(2, workflow.count("- '!ci/governance/**'"))


if __name__ == "__main__":
    unittest.main()
