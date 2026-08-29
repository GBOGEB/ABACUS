import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
POLICY = ROOT / "ci/governance/workflow_policy.json"
WORKFLOWS = ROOT / ".github/workflows"


class ExecutionTierTests(unittest.TestCase):
    def setUp(self):
        self.tiers = json.loads(POLICY.read_text(encoding="utf-8"))["execution_tiers"]

    def test_tier_members_exist_and_do_not_overlap(self):
        slim = set(self.tiers["slim_pr"]["workflows"])
        full = set(self.tiers["full"]["workflows"])
        self.assertFalse(slim & full)
        for filename in slim | full:
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


if __name__ == "__main__":
    unittest.main()
