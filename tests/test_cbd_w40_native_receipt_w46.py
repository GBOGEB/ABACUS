"""W46 regression tests for unchanged W40 exact-head receipt contract."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "cbd_w40_native_receipt.py"


class W40NativeReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.out = self.root / "artifacts" / "w40"
        self.out.mkdir(parents=True)
        self.summary = {
            "num_statements": 214,
            "num_branches": 62,
            "covered_lines": 184,
            "covered_branches": 47,
        }
        self.write_report("baseline-coverage.json", self.summary)
        self.write_report("coverage.json", self.summary)
        self.write_junit("baseline-junit.xml", 1, 0, 0)
        self.write_junit("junit.xml", 1, 42, 12)

    def write_report(self, name, summary):
        payload = {"files": {"tools/qps_binary_bridge.py": {"summary": summary}}}
        (self.out / name).write_text(json.dumps(payload), encoding="utf-8")

    def write_junit(self, name, base, w40, w41, skipped=False):
        root = ET.Element("testsuite")
        for i in range(base):
            ET.SubElement(root, "testcase", classname="old", name=f"case_{i}")
        for i in range(w40):
            test = ET.SubElement(
                root,
                "testcase",
                classname="test_qps_binary_bridge_w40_penetration",
                name=f"case_{i}",
            )
            if skipped and i == 0:
                ET.SubElement(test, "skipped")
        for i in range(w41):
            ET.SubElement(
                root,
                "testcase",
                classname="test_qps_binary_bridge_w41_frontier",
                name=f"case_{i}",
            )
        ET.ElementTree(root).write(self.out / name, encoding="utf-8")

    def execute(self):
        env = os.environ.copy()
        env.update(
            EXACT_HEAD="a" * 40,
            RUN_ID="1234",
            RUN_ATTEMPT="1",
            GITHUB_JOB_NAME="windows-2022-py3.11",
        )
        return subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=self.root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_positive_receipt_retains_all_source_fields(self):
        result = self.execute()
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((self.out / "receipt.json").read_text())
        self.assertEqual(receipt["source_sha"], "a" * 40)
        self.assertEqual(receipt["new_case_total"], 54)
        self.assertEqual(receipt["total_junit_cases"], 55)
        self.assertEqual(receipt["matched_eligible_opportunities"], 276)
        self.assertEqual(receipt["matched_before_covered"], 231)
        self.assertEqual(receipt["matched_after_covered"], 231)
        self.assertEqual(receipt["admission"], "HOLD")
        self.assertIsNone(receipt["formal_main_uplift"])
        self.assertFalse(receipt["security_waiver"])
        manifest = json.loads((self.out / "SHA256.json").read_text())
        self.assertEqual(
            manifest["receipt.json"],
            hashlib.sha256((self.out / "receipt.json").read_bytes()).hexdigest(),
        )

    def test_denominator_mutation_fails_closed(self):
        altered = dict(self.summary, num_branches=61)
        self.write_report("coverage.json", altered)
        result = self.execute()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("changed eligible module denominator", result.stderr)
        self.assertFalse((self.out / "receipt.json").exists())

    def test_skipped_native_case_fails_closed(self):
        self.write_junit("junit.xml", 1, 42, 12, skipped=True)
        result = self.execute()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("native test failure or skip", result.stderr)

    def test_missing_source_coverage_fails_closed(self):
        (self.out / "coverage.json").write_text('{"files": {}}')
        result = self.execute()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing/ambiguous source-bound", result.stderr)


if __name__ == "__main__":
    unittest.main()
