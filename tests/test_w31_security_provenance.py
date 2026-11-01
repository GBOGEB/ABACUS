"""Adversarial/fault-injection W31 scanner provenance tests."""

import hashlib
import unittest

from tools.recovery import w31_security_provenance as sp

SHA = "a" * 40


def finding(name, version, cve):
    return {"package": name, "version": version, "cve": cve}


def evidence():
    return {
        "exact_sha": SHA,
        "run_id": 38783468698,
        "run_attempt": 3,
        "job_id": 116932289578,
        "scanner": {
            "scope": "scanner_environment",
            "exit_code": 64,
            "installed_packages": 47,
            "findings": [
                finding("nltk", "3.10.3", "CVE-2026-81726"),
                finding("setuptools", "79.0.1", "CVE-2026-59890"),
            ],
        },
        "application_runtime": None,
        "scanner_artifact_sha256": None,
    }


class ScannerAttributionTests(unittest.TestCase):
    def test_historical_scanner_red_not_application_vulnerability(self):
        out = sp.summarize(evidence())
        self.assertEqual(out["scanner_environment"]["finding_occurrences"], 2)
        self.assertEqual(out["scanner_environment"]["installed_packages"], 47)
        self.assertIsNone(out["application_runtime"])
        self.assertIsNone(out["scanner_only_occurrences"])
        self.assertEqual(out["scanner_environment"]["gate_result"], "FAIL")
        self.assertEqual(out["merge_admission"], "HOLD")
        self.assertIsNone(out["causal_roots_closed"])

    def test_empty_application_cannot_erase_scanner_red(self):
        item = evidence()
        item["application_runtime"] = {
            "scope": "application_runtime",
            "exit_code": 0,
            "installed_packages": 10,
            "findings": [],
        }
        out = sp.summarize(item)
        self.assertEqual(out["scanner_only_occurrences"], 2)
        self.assertEqual(out["shared_occurrences"], 0)
        self.assertEqual(out["scanner_environment"]["gate_result"], "FAIL")

    def test_identical_finding_is_overlap_not_root_closure(self):
        item = evidence()
        item["application_runtime"] = {
            "scope": "application_runtime",
            "exit_code": 64,
            "installed_packages": 15,
            "findings": [item["scanner"]["findings"][0]],
        }
        out = sp.summarize(item)
        self.assertEqual(
            (out["scanner_only_occurrences"], out["shared_occurrences"]), (1, 1)
        )
        self.assertIsNone(out["causal_roots_closed"])

    def test_hash_match_is_not_content_or_security_attestation(self):
        item = evidence()
        raw = b"synthetic-artifact-byte-content"
        item["scanner_artifact_sha256"] = hashlib.sha256(raw).hexdigest()
        out = sp.summarize(item, archive_bytes=raw)
        self.assertTrue(out["artifact_hash_matched_only"])
        self.assertEqual(out["evidence_class"], "HASH_MATCH_ONLY")
        self.assertIsNone(out["independent_artifact_content_assessment"])
        self.assertEqual(out["merge_admission"], "HOLD")

    def test_false_digest_rejected(self):
        item = evidence()
        item["scanner_artifact_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
            sp.summarize(item, archive_bytes=b"not equal")

    def test_hash_without_bytes_cannot_be_called_verified(self):
        item = evidence()
        item["scanner_artifact_sha256"] = "0" * 64
        self.assertIsNone(sp.summarize(item)["artifact_hash_matched_only"])

    def test_archive_without_declared_digest_rejected(self):
        with self.assertRaisesRegex(ValueError, "missing declared digest"):
            sp.summarize(evidence(), archive_bytes=b"unverified")

    def test_wrong_scope_is_not_silent_fallback(self):
        item = evidence()
        item["scanner"]["scope"] = "application_runtime"
        with self.assertRaisesRegex(ValueError, "foreign vulnerability scope"):
            sp.summarize(item)

    def test_false_clean_safety_exit_denied(self):
        item = evidence()
        item["scanner"]["exit_code"] = 0
        with self.assertRaisesRegex(ValueError, "falsely green"):
            sp.summarize(item)

    def test_zero_exit_no_findings_remains_nonadmitted(self):
        item = evidence()
        item["scanner"]["exit_code"] = 0
        item["scanner"]["findings"] = []
        out = sp.summarize(item)
        self.assertEqual(
            out["scanner_environment"]["gate_result"], "SCANNER_EXIT_ZERO_ONLY"
        )
        self.assertEqual(out["merge_admission"], "HOLD")

    def test_duplicate_manifestation_rejected(self):
        item = evidence()
        item["scanner"]["findings"].append(item["scanner"]["findings"][0])
        with self.assertRaisesRegex(ValueError, "duplicate scanner"):
            sp.summarize(item)

    def test_malformed_cve_denied(self):
        item = evidence()
        item["scanner"]["findings"][0]["cve"] = "CVE-unknown"
        with self.assertRaisesRegex(ValueError, "invalid CVE"):
            sp.summarize(item)

    def test_unknown_population_denied(self):
        item = evidence()
        item["scanner"]["installed_packages"] = None
        with self.assertRaisesRegex(ValueError, "unknown installed"):
            sp.summarize(item)

    def test_manifestations_not_source_root_count(self):
        item = evidence()
        item["scanner"]["findings"].append(finding("nltk", "3.10.4", "CVE-2026-81726"))
        out = sp.summarize(item)
        self.assertEqual(out["scanner_environment"]["finding_occurrences"], 3)
        self.assertEqual(out["scanner_environment"]["distinct_cves"], 2)
        self.assertIsNone(out["causal_roots_closed"])

    def test_no_scanner_report_denied(self):
        item = evidence()
        item["scanner"] = None
        with self.assertRaisesRegex(ValueError, "missing scanner_environment"):
            sp.summarize(item)

    def test_invalid_run_identity_denied(self):
        for field in ("run_id", "run_attempt", "job_id"):
            with self.subTest(field=field):
                item = evidence()
                item[field] = 0
                with self.assertRaisesRegex(ValueError, "invalid " + field):
                    sp.summarize(item)

    def test_foreign_sha_rejected(self):
        item = evidence()
        item["exact_sha"] = "BAD"
        with self.assertRaisesRegex(ValueError, "invalid exact"):
            sp.summarize(item)


if __name__ == "__main__":
    unittest.main()
