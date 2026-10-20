import unittest

from tools.recovery.os_compat_receipt import validate


class OSReceiptTests(unittest.TestCase):
    def test_empty_receipt_stays_unknown(self):
        result = validate({})
        self.assertFalse(result["native_pass"])
        self.assertIn("job_id", result["missing"])
        self.assertEqual(result["admission"], "HOLD")

    def test_complete_native_success(self):
        receipt = dict(repository="GBOGEB/ABACUS", commit_sha="a" * 40,
                       run_id=2, job_id=3, os_release="RHEL 9", runner="native",
                       image_digest="sha256:" + "b" * 64, conclusion="success")
        self.assertTrue(validate(receipt)["native_pass"])


if __name__ == "__main__":
    unittest.main()
