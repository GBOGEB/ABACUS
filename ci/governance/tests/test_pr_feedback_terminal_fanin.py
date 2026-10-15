"""Regression contract: feedback-gate fan-in awaits terminal upstream CI.

Requested and in-progress workflow_run events have no terminal security or
test disposition and fan out redundant evaluators. Direct PR and review events
still establish immediate pending/invalidation semantics.
"""

from pathlib import Path
import re
import unittest


WORKFLOW = (
    Path(__file__).resolve().parents[3]
    / ".github" / "workflows" / "pr-feedback-gate.yml"
)


class FeedbackTerminalFaninTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")
        prefix = "  workflow_run:\n"
        suffix = "  schedule:\n"
        assert prefix in cls.text and suffix in cls.text
        cls.workflow_run_section = cls.text.split(prefix, 1)[1].split(suffix, 1)[0]

    def test_upstream_fanin_requires_completed_not_requested_or_in_progress(self):
        declarations = re.findall(
            r"^    types:\s*\[([^]]+)\]\s*$",
            self.workflow_run_section,
            flags=re.MULTILINE,
        )
        self.assertEqual(declarations, ["completed"])
        self.assertIn("    workflows:", self.workflow_run_section)

    def test_direct_pending_and_invalidation_triggers_remain(self):
        for source in (
            "  issue_comment:\n",
            "  issues:\n",
            "  pull_request_review:\n",
            "  pull_request_review_comment:\n",
            "  pull_request:\n",
            "  schedule:\n",
            "  workflow_dispatch:\n",
        ):
            with self.subTest(source=source.strip()):
                self.assertIn(source, self.text)

    def test_fail_closed_evaluation_still_publishes_explicit_results(self):
        self.assertIn("--mark-pending-only", self.text)
        self.assertIn("--mark-failure-only", self.text)
        self.assertIn("if: failure()", self.text)
        self.assertIn("cancel-in-progress: false", self.text)


if __name__ == "__main__":
    unittest.main()
