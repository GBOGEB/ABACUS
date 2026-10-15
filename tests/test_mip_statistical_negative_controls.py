"""Negative controls for MIP statistical observation admission."""

import importlib.util
import unittest
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / "scripts/mip_statistical_readiness.py"
SPEC = importlib.util.spec_from_file_location("mip_statistical_readiness_extra", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def observation():
    return {
        "schema": "mip.stat.observation.v1",
        "repository": "GBOGEB/ABACUS",
        "family": "coverage",
        "metric": "covered_statements",
        "metric_version": "1",
        "exact_sha": "a" * 40,
        "run_id": 123,
        "job_id": 456,
        "observed_at": "2026-10-15T07:00:00Z",
        "evidence_url": "https://github.com/GBOGEB/ABACUS/actions/runs/123",
        "collection_quality": "NATIVE",
        "status": "PASS",
        "numerator": 3,
        "denominator": 4,
    }


class AdditionalReceiptNegativeControls(unittest.TestCase):
    def test_invalid_identity_and_schema_fail_closed(self):
        mutations = [
            ("schema", "untrusted"),
            ("repository", "other/repo"),
            ("family", "nonexistent"),
            ("exact_sha", "z" * 40),
            ("exact_sha", "a" * 39),
            ("run_id", 0),
            ("job_id", -1),
            ("run_id", True),
            ("job_id", "456"),
        ]
        for field, value in mutations:
            with self.subTest(field=field, value=value):
                record = observation()
                record[field] = value
                with self.assertRaises(ValueError):
                    MODULE.check(record)

    def test_invalid_counts_fail_closed(self):
        mutations = [
            (None, 4),
            (3, None),
            (-1, 4),
            (5, 4),
            (0, 0),
            (True, 4),
            (3, 4.0),
        ]
        for numerator, denominator in mutations:
            with self.subTest(numerator=numerator, denominator=denominator):
                record = observation()
                record["numerator"] = numerator
                record["denominator"] = denominator
                with self.assertRaises(ValueError):
                    MODULE.check(record)

    def test_missing_metadata_and_bad_timestamp_fail_closed(self):
        for field in ("metric", "metric_version", "evidence_url", "collection_quality"):
            with self.subTest(field=field):
                record = observation()
                record[field] = ""
                with self.assertRaises(ValueError):
                    MODULE.check(record)
        for timestamp in ("2026-10-15T07:00:00+00:00", "not-a-timeZ"):
            with self.subTest(timestamp=timestamp):
                record = observation()
                record["observed_at"] = timestamp
                with self.assertRaises(ValueError):
                    MODULE.check(record)

    def test_unknown_and_unverified_numeric_receipts_fail_closed(self):
        for status, quality in (
            ("UNKNOWN", "NATIVE"),
            ("PASS", "UNVERIFIED"),
            ("PASS", "INCOMPLETE"),
        ):
            with self.subTest(status=status, quality=quality):
                record = observation()
                record["status"] = status
                record["collection_quality"] = quality
                with self.assertRaises(ValueError):
                    MODULE.check(record)

    def test_invalid_thresholds_fail_closed(self):
        for minimum, holdout in ((4, 5), (20, 1)):
            with self.subTest(minimum=minimum, holdout=holdout):
                with self.assertRaises(ValueError):
                    MODULE.evaluate([], minimum=minimum, holdout=holdout)

    def test_accepted_receipt_does_not_grant_merge_authority(self):
        result = MODULE.evaluate([observation()])
        self.assertEqual("HOLD", result["merge_admission"])
        self.assertFalse(result["authority_transfer"])
        self.assertEqual(1, result["series"][0]["native_comparable"])
        self.assertFalse(result["series"][0]["PROCESS_STABLE"])


if __name__ == "__main__":
    unittest.main()
