"""G3A W16 source/CI preflight: deterministic sandbox and negative cases."""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
import unittest.mock as mock
from pathlib import Path

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
            json.dumps(
                {
                    "rules": [
                        {"pattern": "^demo[.]yml$", "cluster": "c", "lifecycle": "l"}
                    ]
                }
            ),
            encoding="utf-8",
        )
        self.a = "a" * 40
        self.b = "b" * 40
        self.write_epoch()

    def write_epoch(self, **workflows):
        census = {"population": 1, "by_cluster": {"c": 1}, "by_lifecycle": {"l": 1}}
        census.update(workflows)
        epoch = {
            "source_epoch": "E",
            "files": {"src/a.py": {"blob": self.b}},
            "workflows": census,
        }
        manifest = self.root / pre.MANIFEST
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps(epoch), encoding="utf-8")

    def scan(self, *, blob=None, head=None, audit_rc=0):
        if blob is None:
            blob = self.b
        if head is None:
            head = self.a

        def fake_git(root, *args):
            return head if args[0] == "rev-parse" else blob

        with (
            mock.patch.object(pre, "_git", side_effect=fake_git),
            mock.patch.object(
                pre.subprocess, "run", return_value=mock.Mock(returncode=audit_rc)
            ),
        ):
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
        (self.root / ".github/workflows/unclassified.yml").write_text(
            "name: surprise\n"
        )
        x = self.scan()
        self.assertTrue(
            any(
                v.startswith("WORKFLOW_POLICY_MATCH_COUNT:unclassified.yml")
                for v in x["errors"]
            )
        )
        self.assertIn("WORKFLOW_POPULATION_DRIFT", x["errors"])
        self.assertEqual(
            x["workflow_subcategories"]["by_cluster"], {"UNCLASSIFIED": 1, "c": 1}
        )

    def test_generated_inventory_staleness_not_ignored(self):
        x = self.scan(audit_rc=1)
        self.assertIn("GENERATED_WORKFLOW_INVENTORY_STALE_OR_INVALID", x["errors"])

    def test_policy_unreadable_is_explicit(self):
        (self.root / "ci/governance/workflow_policy.json").write_text("{bad")
        x = self.scan()
        self.assertIn("WORKFLOW_POLICY_UNREADABLE", x["errors"])

    def test_good_scan_reports_workflow_subcategories(self):
        x = self.scan()
        self.assertEqual(x["source_epoch"], "E")
        self.assertEqual(
            x["workflow_subcategories"],
            {"by_cluster": {"c": 1}, "by_lifecycle": {"l": 1}},
        )

    def test_subcategory_drift_requires_repin(self):
        self.write_epoch(by_cluster={"other": 1})
        x = self.scan()
        self.assertEqual(x["status"], "HOLD")
        self.assertIn("WORKFLOW_SUBCATEGORY_DRIFT:by_cluster", x["errors"])
        self.assertNotIn("WORKFLOW_SUBCATEGORY_DRIFT:by_lifecycle", x["errors"])

    def test_unmapped_historical_subcategories_are_not_compared(self):
        self.write_epoch(by_cluster=None, by_lifecycle=None)
        self.assertEqual(self.scan()["status"], "PASS")

    def test_epoch_manifest_unreadable_is_explicit(self):
        (self.root / pre.MANIFEST).write_text("{bad", encoding="utf-8")
        x = self.scan()
        self.assertIsNone(x["source_epoch"])
        self.assertIn("EPOCH_MANIFEST_UNREADABLE", x["errors"])
        self.assertIn("WORKFLOW_POPULATION_DRIFT", x["errors"])

    def test_git_failure_records_no_blob(self):
        error = pre.subprocess.CalledProcessError(128, ["git"])
        with mock.patch.object(pre, "_git", side_effect=error):
            x = pre.scan(self.root, self.a)
        self.assertIsNone(x["checkout_head"])
        self.assertIsNone(x["source_blobs"]["src/a.py"]["actual"])
        self.assertIn("CHECKOUT_NOT_AVAILABLE", x["errors"])
        self.assertIn("SOURCE_BLOB_DRIFT:src/a.py", x["errors"])

    def test_missing_checkout_and_invalid_head_fail_closed(self):
        ceiling = {"GIT_CEILING_DIRECTORIES": str(self.root.parent)}
        with mock.patch.dict(os.environ, ceiling):
            x = pre.scan(self.root, "not-a-sha")
        self.assertIsNone(x["checkout_head"])
        # Outside a repository `git hash-object` may still hash the file
        # (Linux) or fail (Windows temp ACLs); either way it is not the pin.
        self.assertFalse(x["source_blobs"]["src/a.py"]["matches"])
        for error in (
            "EXPECTED_HEAD_INVALID",
            "CHECKOUT_NOT_AVAILABLE",
            "NOT_EXACT_HEAD",
            "SOURCE_BLOB_DRIFT:src/a.py",
        ):
            self.assertIn(error, x["errors"])

    def run_main(self, status):
        result = {
            "status": status,
            "source_epoch": "E",
            "errors": [] if status == "PASS" else ["X"],
        }
        argv = [
            "g3a_w16_preflight.py",
            "--root",
            str(self.root),
            "--expected-head",
            self.a,
            "--out",
            "reports/preflight.json",
        ]
        with (
            mock.patch.object(sys, "argv", argv),
            mock.patch.object(pre, "scan", return_value=result),
            contextlib.redirect_stdout(io.StringIO()) as out,
        ):
            rc = pre.main()
        written = json.loads(
            (self.root / "reports/preflight.json").read_text(encoding="utf-8")
        )
        return rc, out.getvalue(), written

    def test_cli_pass_writes_relative_receipt(self):
        rc, text, written = self.run_main("PASS")
        self.assertEqual(rc, 0)
        self.assertIn("G3A_W16_PREFLIGHT=PASS", text)
        self.assertEqual(written["status"], "PASS")

    def test_cli_hold_exits_two(self):
        rc, text, written = self.run_main("HOLD")
        self.assertEqual(rc, 2)
        self.assertIn("errors=X", text)
        self.assertEqual(written["errors"], ["X"])


if __name__ == "__main__":
    unittest.main()
