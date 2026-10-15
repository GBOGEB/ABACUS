"""B9 follow-on: fail-closed A10 and B-1 admission edge-case coverage.

All receipt identities here are synthetic unit-test fixtures. A passing test
never confers operational root closure, security clearance or merge authority.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.recovery import a10_origin_census
from tools.recovery import mip_bminus1_admission as admission


class BMinus1AdmissionEdgeCases(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.junit = self.root / "results.xml"
        self.junit.write_text(
            '<testsuite><testcase classname="w" name="required"/></testsuite>'
        )
        self.manifest = {
            "worker_id": "unit-fixture",
            "exact_sha": "a" * 40,
            "required_tests": ["w::required"],
            "code_committed": True,
            "tests_committed": True,
            "evidence": {
                "commit_sha": "a" * 40,
                "run_id": 1,
                "job_id": 2,
                "producer_schema_valid": True,
                "negative_controls_passed": True,
            },
        }

    def test_malformed_manifest_or_sha_fails_closed(self):
        with self.assertRaises(ValueError):
            admission.evaluate([], self.junit)
        for bad_sha in ("short", "g" * 40, 100):
            with self.subTest(value=bad_sha):
                manifest = {**self.manifest, "exact_sha": bad_sha}
                with self.assertRaises(ValueError):
                    admission.evaluate(manifest, self.junit)

    def test_missing_duplicate_or_invalid_required_tests(self):
        for value in ([], ["w::required", "w::required"], [None]):
            with self.subTest(required=value):
                manifest = {**self.manifest, "required_tests": value}
                with self.assertRaises(ValueError):
                    admission.evaluate(manifest, self.junit)

    def test_failed_and_skipped_junit_cannot_be_verified(self):
        for result_tag, status in (("failure", "failed"), ("skipped", "skipped")):
            with self.subTest(status=status):
                self.junit.write_text(
                    '<testsuite><testcase classname="w" name="required">'
                    f"<{result_tag}/></testcase></testsuite>"
                )
                result = admission.evaluate(self.manifest, self.junit)
                self.assertEqual(result["test_counts"][status], 1)
                self.assertFalse(result["decisions"]["VERIFIED"])

    def test_duplicate_or_unidentified_junit_fails_closed(self):
        samples = (
            '<testsuite><testcase classname="w" name="required"/>'
            '<testcase classname="w" name="required"/></testsuite>',
            "<testsuite><testcase/></testsuite>",
        )
        for sample in samples:
            with self.subTest(sample=sample):
                self.junit.write_text(sample)
                with self.assertRaises(ValueError):
                    admission.evaluate(self.manifest, self.junit)

    def test_invalid_first_red_container_rejected(self):
        manifest = {**self.manifest, "first_reds": "not-an-array"}
        with self.assertRaises(ValueError):
            admission.evaluate(manifest, self.junit)

    def test_invalid_records_cannot_claim_verified(self):
        manifest = {**self.manifest, "first_reds": [None]}
        result = admission.evaluate(manifest, self.junit)
        self.assertIn("invalid_record", result["invalid_first_reds"])
        self.assertFalse(result["decisions"]["VERIFIED"])
        self.assertEqual(result["merge_admission"], "HOLD")

    def test_untrusted_metadata_and_incomplete_code_stay_hold(self):
        for variation in (
            {"evidence": "untrusted"},
            {"code_committed": False},
            {"tests_committed": False},
            {"evidence": {"commit_sha": "b" * 40}},
        ):
            with self.subTest(variation=variation):
                manifest = {**self.manifest, **variation}
                result = admission.evaluate(manifest, self.junit)
                self.assertFalse(result["decisions"]["VERIFIED"])
                self.assertEqual(result["merge_admission"], "HOLD")

    def test_verified_fixture_does_not_resolve_root(self):
        result = admission.evaluate(self.manifest, self.junit)
        self.assertEqual(result["test_counts"]["passed"], 1)
        self.assertTrue(result["decisions"]["VERIFIED"])
        self.assertFalse(result["decisions"]["ROOT_RESOLVED"])
        self.assertFalse(result["decisions"]["MERGE_ADMITTED"])
        self.assertEqual(result["merge_admission"], "HOLD")

    def test_root_fix_fixture_still_requires_security_and_review(self):
        evidence = {
            **self.manifest["evidence"],
            "root_fix_native_proof": True,
        }
        manifest = {**self.manifest, "evidence": evidence}
        result = admission.evaluate(manifest, self.junit)
        self.assertTrue(result["decisions"]["ROOT_RESOLVED"])
        self.assertFalse(result["decisions"]["INTEGRATION_ELIGIBLE"])
        self.assertFalse(result["decisions"]["MERGE_ADMITTED"])
        self.assertEqual(result["merge_admission"], "HOLD")

    def test_cli_writes_hold_receipt_and_exits_nonzero(self):
        manifest_path = self.root / "manifest.json"
        out = self.root / "admission.json"
        manifest = {**self.manifest, "required_tests": ["w::missing"]}
        manifest_path.write_text(json.dumps(manifest))
        argv = [
            "mip_bminus1_admission.py",
            "--manifest",
            str(manifest_path),
            "--junit",
            str(self.junit),
            "--out",
            str(out),
        ]
        with patch.object(sys, "argv", argv):
            with self.assertRaises(SystemExit) as raised:
                admission.main()
        self.assertEqual(raised.exception.code, 2)
        result = json.loads(out.read_text())
        self.assertEqual(result["test_counts"]["missing"], 1)
        self.assertEqual(result["merge_admission"], "HOLD")


class A10RedactionEdgeCases(unittest.TestCase):
    def test_unknown_reason_is_redacted_and_not_waived(self):
        report = a10_origin_census.summarize(
            "2026-10-15T08:00:00Z BLOCK docs/example.md "
            "(unexpected confidential marker)"
        )
        self.assertEqual(len(report["blocked_files"]), 1)
        self.assertEqual(
            report["blocked_files"][0]["reason_code"],
            "OTHER_REVIEW_REQUIRED",
        )
        self.assertIsNone(report["blocked_files"][0]["match_text"])
        self.assertFalse(report["verified_clearance"])
        self.assertFalse(report["security_waiver"])

    def test_a10_cli_preserves_empty_is_not_clearance(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source, target = folder / "input.log", folder / "out.json"
            source.write_text("No BLOCK entries seen")
            argv = [
                "a10_origin_census.py",
                str(source),
                "--out",
                str(target),
            ]
            with patch.object(sys, "argv", argv):
                a10_origin_census.main()
            result = json.loads(target.read_text())
            self.assertEqual(result["blocked_files"], [])
            self.assertFalse(result["verified_clearance"])
            self.assertEqual(result["admission"], "HOLD")


if __name__ == "__main__":
    unittest.main()
