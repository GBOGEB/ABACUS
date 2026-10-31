"""Regression contract for the isolated CODE PURPLE SUT GUI coverage producer.

The project-wide pyproject.toml has [tool.coverage.run] source=["."].
Without an explicit config override, --include is ignored, reporting global
repository coverage as if it were SUT server coverage. This test is independent
of the execution environment and preserves strict threshold semantics.
"""
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
WORKFLOW = ROOT / ".github" / "workflows" / "code-purple-sut-gui.yml"


class CoverageWorkflowContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = WORKFLOW.read_text(encoding="utf-8")

    def test_execution_and_export_use_identical_isolated_configuration(self):
        command = re.sub(r"\\\n\s*", " ", self.source)
        command = re.sub(r" +", " ", command)
        self.assertIn(
            "coverage run --rcfile=/dev/null --branch --include='*/sut_gui/server.py'",
            command,
        )
        self.assertIn("coverage json --rcfile=/dev/null", self.source)

    def test_no_false_positive_repository_denominator(self):
        self.assertIn("len(observed) == 1", self.source)
        self.assertIn("'tools/everred_v3/sut_gui/server.py'", self.source)
        self.assertIn(".endswith(", self.source)
        self.assertIn("totals['num_statements'] > 0", self.source)
        self.assertIn("totals['num_branches'] > 0", self.source)

    def test_threshold_not_relaxed_and_negative_receipt_is_failure(self):
        self.assertIn("totals['percent_statements_covered'] >= 80.0", self.source)
        self.assertIn("totals['percent_branches_covered'] >= 80.0", self.source)
        self.assertIn("if-no-files-found: error", self.source)


if __name__ == "__main__":
    unittest.main()


def test_zz_g_ab_red_canary():
    """Throwaway red canary (method vector D); never merge."""
    assert False
