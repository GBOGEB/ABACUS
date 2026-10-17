"""G3A W16 source/CI preflight: deterministic sandbox and negative cases."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import g3a_w16_preflight as pre


class PreflightContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / ".github/workflows").mkdir(parents=True)
        (self.root / "ci/governance").mkdir(parents=True)
        (self.root / "docs/ci").mkdir(parents=True)
        (self.root / "src").mkdir(parents=True)
        (self.root / "src/a.py").write_text("print('safe')\n", encoding="utf-8")
        (self.root / ".github/workflows/demo.yml").write_text("name: demo\n")
        (self.root / "ci/governance/workflow_policy.json").write_text(
            json.dumps({"rules": [{"pattern": r"^demo\\.yml$"}]}), encoding="utf-8")
        self.a = "a" * 40
        self.b = "b" * 40

    def scan(self, *, blob=None, head=None, audit_rc=0):
        if blob is None:
            blob = self.b
        if head is None:
            head = self.a

        def fake_git(root, *args):
            return head if args[0] == "rev-parse" else blob

        with (mock.patch.object(pre, "SOURCE_BLOBS", {"src/a.py": self.b}),
              mock.patch.object(pre, "EXPECTED_WORKFLOWS", 1),
              mock.patch.object(pre, "_git", side_effect=fake_git),
              mock.patch.object(pre.subprocess, "run",
                                return_value=mock.Mock(returncode=audit_rc))):
            return pre.scan(self.root, self.a)

    def test_good_exact_checkout_and_classification(self):
        x = self.scan()
        self.assertEqual(x["status"], "PASS")
        self.assertEqual(x["classified"], 1)
        self.assertIsNone(x["native_coverage"])
        self.assertIsNone(x["queue_seconds"])
        self.assertEqual(x["formal_root_closure"], 0)

    def test_bad_source_hash_stops_before_ci(self):
        x = self.scan(blob="c" * 40)
        self.assertEqual(x["status"], "HOLD")
        self.assertIn("SOURCE_BLOB_DRIFT:src/a.py", x["errors"])

    def test_old_source_head_is_not_accepted(self):
        self.assertIn("NOT_EXACT_HEAD", self.scan(head="c" * 40)["errors"])

    def test_new_unclassified_workflow_fails_closed(self):
        (self.root / ".github/workflows/unclassified.yml").write_text("name: surprise\n")
        x = self.scan()
        self.assertTrue(any(v.startswith("WORKFLOW_POLICY_MATCH_COUNT:unclassified.yml")
                            for v in x["errors"]))
        self.assertIn("WORKFLOW_POPULATION_DRIFT", x["errors"])

    def test_generated_inventory_staleness_not_ignored(self):
        x = self.scan(audit_rc=1)
        self.assertIn("GENERATED_WORKFLOW_INVENTORY_STALE_OR_INVALID", x["errors"])

    def test_policy_unreadable_is_explicit(self):
        (self.root / "ci/governance/workflow_policy.json").write_text("{bad")
        x = self.scan()
        self.assertIn("WORKFLOW_POLICY_UNREADABLE", x["errors"])


if __name__ == "__main__":
    unittest.main()
