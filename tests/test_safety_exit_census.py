import unittest

from tools.recovery.safety_exit_census import classify


class SafetyExitTests(unittest.TestCase):
    def test_exit64_fails_closed(self):
        result = classify(64, None)
        self.assertIsNone(result["finding_count"])
        self.assertEqual(result["failure_class"], "SCAN_OR_POLICY_FAILURE_UNCLASSIFIED")
        self.assertEqual(result["admission"], "HOLD")

    def test_zero_is_not_global_admission(self):
        result = classify(0, {"vulnerabilities": []})
        self.assertEqual(result["failure_class"], "SUCCESS")
        self.assertEqual(result["admission"], "HOLD")


if __name__ == "__main__":
    unittest.main()
