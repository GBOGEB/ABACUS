"""Negative and valid receipts for the BD E0-E3 telemetry contract."""
import unittest

from mission_control_lite.bd_telemetry import (
    SCHEMA,
    canonical_json,
    evidence_digest,
    summarize_series,
    validate,
)


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


    def test_rejects_nonfinite_queue_seconds(self):
        for bad in (float("nan"), float("inf"), -float("inf")):
            with self.subTest(value=str(bad)):
                record = self.record()
                record["queue_seconds"] = bad
                with self.assertRaisesRegex(ValueError, "queue seconds"):
                    validate(record)

    def test_rejects_boolean_queue_seconds(self):
        for bad in (True, False):
            with self.subTest(value=bad):
                record = self.record()
                record["queue_seconds"] = bad
                with self.assertRaisesRegex(ValueError, "queue seconds"):
                    validate(record)

    def test_rejects_noncanonical_source_and_base_sha(self):
        for field in ("source_sha", "base_sha"):
            for bad in ("A" * 40, "g" * 40, "f" * 39):
                with self.subTest(field=field, value=bad):
                    record = self.record()
                    record[field] = bad
                    with self.assertRaisesRegex(ValueError, "canonical"):
                        validate(record)

    def test_rejects_noncanonical_artifact_digests(self):
        for bad in (
            "SHA256:" + "c" * 64,
            "sha256:" + "A" * 64,
            "sha256:" + "g" * 64,
            "sha256:" + "c" * 63,
        ):
            with self.subTest(value=bad):
                record = self.record()
                record["artifact_digest"] = bad
                with self.assertRaisesRegex(ValueError, "canonical artifact"):
                    validate(record)

    def test_nonfinite_cannot_be_serialized_as_evidence(self):
        record = self.record()
        record["queue_seconds"] = float("nan")
        with self.assertRaisesRegex(ValueError, "queue seconds"):
            canonical_json(record)

    def test_rejects_boolean_coverage_numerator(self):
        record = self.record()
        record["branch_covered"] = True
        with self.assertRaisesRegex(ValueError, "coverage"):
            validate(record)

    def test_series_counts_declared_native_evidence(self):
        native_pass = self.record()
        native_fail = self.record()
        native_fail.update(attempt=2, result="FAIL", queue_seconds=7.5)
        scout = self.record()
        scout.update(
            mode="E0", result="UNKNOWN", attempt=3,
            artifact_digest=None, line_covered=None, line_total=None,
            branch_covered=None, branch_total=None, queue_seconds=None,
        )
        summary = summarize_series([native_pass, native_fail, scout])
        self.assertEqual(summary["observations"], 3)
        self.assertEqual(summary["e3_pass_claims"], 1)
        self.assertEqual(summary["e3_observations"], 2)
        self.assertEqual(summary["e3_pass_claim_fraction"], 0.5)
        self.assertEqual(summary["mode_outcomes"]["E0"]["UNKNOWN"], 1)
        self.assertEqual(summary["mode_outcomes"]["E3"]["FAIL"], 1)
        self.assertEqual(summary["queue_seconds"]["observations"], 2)
        self.assertEqual(summary["queue_seconds"]["missing"], 1)
        self.assertEqual(summary["queue_seconds"]["median"], 5.5)
        self.assertEqual(summary["queue_seconds"]["p95_nearest_rank"], 7.5)
        self.assertFalse(summary["queue_seconds"]["p95_qualified"])
        self.assertEqual(len(summary["declared_native_coverage"]), 2)
        self.assertEqual(summary["declared_native_coverage"][0]["line_percent"], 75)
        self.assertEqual(summary["declared_native_coverage"][0]["branch_percent"], 65)
        self.assertEqual(summary["externally_verified_artifact_count"], 0)
        self.assertEqual(summary["verified_root_closures"], 0)
        self.assertEqual(summary["merge_admission"], "HOLD")

    def test_series_duplicate_identity_fails_closed(self):
        record = self.record()
        with self.assertRaisesRegex(ValueError, "duplicate source-bound"):
            summarize_series([record, dict(record)])

    def test_series_empty_denominators_are_unknown(self):
        summary = summarize_series([])
        self.assertEqual(summary["observations"], 0)
        self.assertIsNone(summary["e3_pass_claim_fraction"])
        self.assertIsNone(summary["queue_seconds"]["median"])
        self.assertIsNone(summary["queue_seconds"]["p95_nearest_rank"])
        self.assertEqual(summary["merge_admission"], "HOLD")

    def test_series_mixed_heads_do_not_invent_coverage_deltas(self):
        previous = self.record()
        current = self.record()
        current.update(
            source_sha="d" * 40, attempt=2, line_covered=120,
            line_total=200, branch_covered=30, branch_total=40,
        )
        summary = summarize_series([previous, current])
        self.assertEqual(len(summary["source_heads"]), 2)
        self.assertIsNone(summary["cross_head_coverage_delta_pp"])
        self.assertEqual(
            summary["declared_native_coverage"][1]["line_percent"], 60
        )

    def test_series_order_does_not_change_aggregates(self):
        first = self.record()
        second = self.record()
        second.update(attempt=2, queue_seconds=8.0)
        self.assertEqual(
            summarize_series([first, second]),
            summarize_series([second, first]),
        )

    def test_series_rejects_unstructured_or_nonfinite_data(self):
        with self.assertRaisesRegex(ValueError, "must be a list"):
            summarize_series({"record": self.record()})
        record = self.record()
        record["queue_seconds"] = float("inf")
        with self.assertRaisesRegex(ValueError, "queue seconds"):
            summarize_series([record])



if __name__ == "__main__":
    unittest.main()
