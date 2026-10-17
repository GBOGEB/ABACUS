import tempfile
import unittest
from pathlib import Path

from tools.recovery.mip_bminus1_admission import evaluate


class AdmissionTests(unittest.TestCase):
    def test_missing_worker_test_not_green(self):
        with tempfile.TemporaryDirectory() as directory:
            xml = Path(directory) / "junit.xml"
            xml.write_text('<testsuite><testcase classname="worker" name="other"/></testsuite>')
            m = {"exact_sha": "a" * 40, "required_tests": ["worker::required"],
                 "code_committed": True, "tests_committed": True, "evidence": {
                     "commit_sha": "a" * 40, "run_id": 1, "job_id": 2,
                     "producer_schema_valid": True, "negative_controls_passed": True}}
            r = evaluate(m, xml)
            self.assertEqual(r["test_counts"]["missing"], 1)
            self.assertFalse(r["decisions"]["VERIFIED"])
            self.assertEqual(r["merge_admission"], "HOLD")

    def test_verified_does_not_close_root(self):
        with tempfile.TemporaryDirectory() as directory:
            xml = Path(directory) / "junit.xml"
            xml.write_text('<testsuite><testcase classname="worker" name="required"/></testsuite>')
            m = {"worker_id": "W2", "exact_sha": "a" * 40,
                 "required_tests": ["worker::required"], "code_committed": True,
                 "tests_committed": True, "first_reds": [{"fingerprint": "safety64",
                 "owner": "W2", "disposition": "OPEN", "origin_run": 4, "origin_job": 5}],
                 "evidence": {"commit_sha": "a" * 40, "run_id": 1, "job_id": 2,
                              "producer_schema_valid": True, "negative_controls_passed": True}}
            r = evaluate(m, xml)
            self.assertTrue(r["decisions"]["VERIFIED"])
            self.assertFalse(r["decisions"]["ROOT_RESOLVED"])
            self.assertEqual(len(r["overflow"]), 1)

    def test_duplicate_ownership_blocks_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            xml = Path(directory) / "junit.xml"
            xml.write_text('<testsuite><testcase classname="w" name="x"/></testsuite>')
            m = {"exact_sha": "a" * 40, "required_tests": ["w::x"],
                 "code_committed": True, "tests_committed": True,
                 "first_reds": [{"fingerprint": "r", "owner": "one"},
                                {"fingerprint": "r", "owner": "two"}],
                 "evidence": {"commit_sha": "a" * 40, "run_id": 1, "job_id": 2,
                              "producer_schema_valid": True, "negative_controls_passed": True}}
            self.assertFalse(evaluate(m, xml)["decisions"]["VERIFIED"])


if __name__ == "__main__":
    unittest.main()
