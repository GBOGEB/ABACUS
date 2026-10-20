"""Four-pulse source-config/temporal edge tests; mutated cases are synthetic."""
from __future__ import annotations

import copy
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import b_series_nplus1_metrics as metrics  # noqa: E402

FIXTURE = ROOT / "docs/ci/B_SERIES_NATIVE_NPLUS1_20261017.json"


class BSeriesNPlusOne(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_four_native_observations_and_composite(self):
        r = metrics.extend(self.doc)
        self.assertEqual(len(r["pulses"]), 4)
        self.assertEqual(r["four_pulse_metrics"]["sampled_run_success"], [4, 4])
        self.assertEqual(r["four_pulse_metrics"]["native_b0_jobs"], [52, 52])
        self.assertEqual(r["execution_composite"]["index_series"], [100.0] * 4)

    def test_b1_stable_with_four_unique_native_receipts(self):
        r = metrics.extend(self.doc)
        self.assertEqual(r["four_pulse_metrics"]["b1_raw_unguarded_counts"], [139] * 4)
        self.assertEqual(r["four_pulse_metrics"]["b1_velocity_findings_per_hour"], [0.0] * 3)
        self.assertEqual(r["four_pulse_metrics"]["b1_acceleration_findings_per_hour2"], [0.0] * 2)

    def test_runtime_baseline_not_overwritten(self):
        r = metrics.extend(self.doc)
        m = r["four_pulse_metrics"]
        self.assertAlmostEqual(m["duration_prior_three_median_seconds"], 322.81)
        self.assertAlmostEqual(m["duration_median_seconds"], 313.995)
        self.assertAlmostEqual(m["duration_mad_seconds"], 10.175)

    def test_forecast_is_prospective_without_fake_error(self):
        f = metrics.extend(self.doc)["forecast"]
        self.assertEqual(f["origin_run"], 39046191707)
        self.assertEqual(f["point_estimate"], 139)
        self.assertIsNone(f["actual"])
        self.assertIsNone(f["error"])
        self.assertIsNone(f["prediction_interval"])

    def test_no_engineering_authority(self):
        r = metrics.extend(self.doc)
        self.assertEqual(r["merge_admission"], "HOLD")
        self.assertIs(r["authority_transfer"], False)
        self.assertIsNone(r["formal_root_closures"])
        self.assertIsNone(r["four_pulse_metrics"]["accepted_matched_coverage_uplift"])

    def test_source_checksum_relabel_rejected(self):
        d = copy.deepcopy(self.doc)
        d["observations"][0]["b1_scanner_blob_sha"] = "a" * 40
        with self.assertRaises(metrics.core.EvidenceError):
            metrics.extend(d)

    def test_changed_scanner_even_with_consistent_fingerprint_rejected(self):
        d = copy.deepcopy(self.doc)
        row = d["observations"][0]
        row["b1_scanner_blob_sha"] = "a" * 40
        row["b1_source_config_identity"] = (
            f"{row['b1_scanner_blob_sha']}:{row['b0_workflow_blob_sha']}:267"
        )
        with self.assertRaises(metrics.core.EvidenceError):
            metrics.extend(d)

    def test_changed_threshold_rejected(self):
        d = copy.deepcopy(self.doc)
        row = d["observations"][0]
        row["b1_max_unguarded"] = 268
        row["b1_source_config_identity"] = (
            f"{row['b1_scanner_blob_sha']}:{row['b0_workflow_blob_sha']}:268"
        )
        with self.assertRaises(metrics.core.EvidenceError):
            metrics.extend(d)

    def test_b1_clock_later_than_run_completion_rejected(self):
        d = copy.deepcopy(self.doc)
        d["observations"][-1]["b1_observation_at"] = "2026-10-17T16:00:00Z"
        with self.assertRaises(metrics.core.EvidenceError):
            metrics.extend(d)

    def test_non_monotonic_b1_clocks_rejected(self):
        d = copy.deepcopy(self.doc)
        d["observations"][2]["b1_observation_at"] = "2026-10-17T09:00:00Z"
        with self.assertRaises(metrics.core.EvidenceError):
            metrics.extend(d)

    def test_invalid_clock_rejected(self):
        d = copy.deepcopy(self.doc)
        d["observations"][1]["b1_observation_at"] = "not-a-date"
        with self.assertRaises(metrics.core.EvidenceError):
            metrics.extend(d)

    def test_duplicate_native_run_rejected(self):
        d = copy.deepcopy(self.doc)
        d["observations"][-1]["run_id"] = d["observations"][-2]["run_id"]
        with self.assertRaises(metrics.core.EvidenceError):
            metrics.extend(d)

    def test_false_crew_claim_rejected(self):
        d = copy.deepcopy(self.doc)
        d["observations"][-1]["authenticated_crew_launch"] = 1
        with self.assertRaises(metrics.core.EvidenceError):
            metrics.extend(d)

    def test_observation_order_rejected(self):
        d = copy.deepcopy(self.doc)
        d["observations"][-1]["pulse"] = "N+9"
        with self.assertRaises(metrics.core.EvidenceError):
            metrics.extend(d)

    def test_synthetic_negative_rate_reacts(self):
        d = copy.deepcopy(self.doc)
        d["observations"][-1]["b1_unguarded"] = 138
        v = metrics.extend(d)["four_pulse_metrics"]
        self.assertLess(v["b1_velocity_findings_per_hour"][-1], 0.0)
        self.assertLess(v["b1_acceleration_findings_per_hour2"][-1], 0.0)
        self.assertEqual(v["b1_raw_unguarded_counts"][-1], 138)

    def test_missing_denominator_not_forged(self):
        d = copy.deepcopy(self.doc)
        d["observations"][-1]["job_total"] = 0
        with self.assertRaises(metrics.core.EvidenceError):
            metrics.extend(d)


if __name__ == "__main__":
    unittest.main()
