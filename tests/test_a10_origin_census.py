import unittest

from tools.recovery.a10_origin_census import summarize


class A10OriginTests(unittest.TestCase):
    def test_redacted_blocks(self):
        report = summarize(
            "2026-10-14T20:13:30Z   BLOCK  ci/policy.json   (restricted term in content)\n"
        )
        self.assertEqual(len(report["blocked_files"]), 1)
        self.assertEqual(report["blocked_files"][0]["path"], "ci/policy.json")
        self.assertIsNone(report["blocked_files"][0]["match_text"])
        self.assertFalse(report["verified_clearance"])
        self.assertFalse(report["security_waiver"])

    def test_no_matches_not_a_clearance(self):
        self.assertEqual(summarize("all done")["admission"], "HOLD")


if __name__ == "__main__":
    unittest.main()
