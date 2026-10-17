"""Negative and valid receipts for the BD E0-E3 telemetry contract."""
import unittest

from mission_control_lite.bd_telemetry import SCHEMA, evidence_digest, validate


class BdTelemetryTests(unittest.TestCase):
    def record(self):
        return {
            "schema": SCHEMA, "mode": "E3",
            "source_sha": "a" * 40, "base_sha": "b" * 40,
            "root_id": "DOCS-SELECTOR", "attempt": 1,
            "artifact_digest": "sha256:" + "c" * 64,
            "line_covered": 75, "line_total": 100,
            "branch_covered": 13, "branch_total": 20,
            "queue_seconds": 3.5, "result": "PASS",
        }

    def test_native_receipt_is_deterministic(self):
        r = self.record()
        self.assertIs(validate(r), r)
        self.assertEqual(evidence_digest(r), evidence_digest(dict(reversed(list(r.items())))))

    def test_missing_provenance_rejected(self):
        r = self.record()
        r.pop("source_sha")
        with self.assertRaises(ValueError):
            validate(r)

    def test_invalid_coverage_denominators_rejected(self):
        r = self.record()
        r["line_covered"] = 101
        with self.assertRaisesRegex(ValueError, "coverage"):
            validate(r)

    def test_native_pass_missing_digest_rejected(self):
        r = self.record()
        r["artifact_digest"] = None
        with self.assertRaisesRegex(ValueError, "complete evidence"):
            validate(r)

    def test_replay_unknown_metrics_preserved(self):
        r = self.record()
        r.update(mode="E0", result="UNKNOWN", artifact_digest=None,
                 line_covered=None, line_total=None,
                 branch_covered=None, branch_total=None, queue_seconds=None)
        validate(r)


if __name__ == "__main__":
    unittest.main()
