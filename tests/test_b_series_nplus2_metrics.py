"""Five-pulse observed-data qualification and negative/fault-injection tests.

Tests use copied native evidence fixtures; mutations are synthetic tests only.
"""

from __future__ import annotations

import copy
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import b_series_nplus2_metrics as engine  # noqa: E402

DATA = ROOT / "docs/ci/B_SERIES_NATIVE_NPLUS2_20261017.json"
PRIOR = ROOT / "docs/ci/B_SERIES_NATIVE_NPLUS1_20261017.json"
B1 = ROOT / "docs/ci/B_SERIES_B1_FINGERPRINT_CENSUS_20261017.json"


class BSeriesFivePulse(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(DATA.read_text(encoding="utf-8"))
        cls.prior = json.loads(PRIOR.read_text(encoding="utf-8"))
        cls.b1 = json.loads(B1.read_text(encoding="utf-8"))

    def result(self, data=None, prior=None, b1=None):
        return engine.extend(
            self.data if data is None else data,
            self.prior if prior is None else prior,
            self.b1 if b1 is None else b1,
        )

    def test_five_distinct_native_runs(self):
        result = self.result()
        self.assertEqual(len(result["pulses"]), 5)
        self.assertEqual(
            result["five_pulse_metrics"]["native_run_pass_fraction"], [5, 5]
        )
        self.assertEqual(
            result["five_pulse_metrics"]["native_job_success_fraction"],
            [65, 65],
        )

    def test_exact_b1_fingerprint_persistence(self):
        result = self.result()["five_pulse_metrics"]
        self.assertEqual(result["b1_fingerprint_jaccard_to_baseline"], [1.0] * 5)
        self.assertEqual(result["b1_unique_reference_fingerprints"], 139)
        self.assertEqual(result["b1_new_fingerprints"], [0] * 5)
        self.assertEqual(result["b1_missing_fingerprints"], [0] * 5)

    def test_scanned_population_drift_visible(self):
        result = self.result()["five_pulse_metrics"]
        self.assertEqual(result["b1_scanned_workflow_files"], [160, 161, 160, 160, 160])
        self.assertEqual(
            result["b1_scope_status"], "SCANNED_WORKFLOW_DENOMINATOR_DRIFT"
        )
        self.assertNotEqual(
            result["b1_findings_per_scanned_file"][0],
            result["b1_findings_per_scanned_file"][1],
        )

    def test_stability_without_six_sigma_claim(self):
        result = self.result()["five_pulse_metrics"]
        self.assertEqual(result["b1_finding_counts"], [139] * 5)
        self.assertEqual(result["b1_raw_velocity_findings_per_hour"], [0.0] * 4)
        self.assertIsNone(result["six_sigma_capability"])
        self.assertIsNone(result["root_closure_credit"])
        self.assertIsNone(result["matched_branch_coverage_delta"])

    def test_runtime_five_pulse_statistics(self):
        result = self.result()
        self.assertAlmostEqual(
            result["five_pulse_metrics"]["duration_median_seconds"], 305.18
        )
        self.assertAlmostEqual(
            result["five_pulse_metrics"]["duration_mad_seconds"], 20.35
        )
        self.assertAlmostEqual(
            result["prior_four_pulse"]["duration_median_seconds"], 313.995
        )

    def test_forecast_never_retroactively_scores(self):
        forecast = self.result()["forecast"]
        self.assertEqual(forecast["origin_run"], 39047236023)
        self.assertEqual(forecast["point_estimate"], 139)
        self.assertIsNone(forecast["forecast_error"])
        self.assertIsNone(forecast["pre_registered_actual"])

    def test_p0_and_crew_remain_unproven(self):
        result = self.result()
        self.assertEqual(result["merge_admission"], "HOLD")
        self.assertIs(result["authority_transfer"], False)
        self.assertIsNone(result["formal_root_closures"])
        self.assertIsNone(result["authenticated_crew_launches"])

    def test_frozen_four_pulse_history_cannot_be_changed(self):
        doc = copy.deepcopy(self.data)
        doc["observations"][2]["b0_tests_passed"] += 1
        with self.assertRaises(engine.core.EvidenceError):
            self.result(data=doc)

    def test_duplicate_native_runs_fail_closed(self):
        doc = copy.deepcopy(self.data)
        doc["observations"][-1]["run_id"] = doc["observations"][0]["run_id"]
        with self.assertRaises(engine.core.EvidenceError):
            self.result(data=doc)

    def test_new_pulse_source_config_spoof_rejected(self):
        doc = copy.deepcopy(self.data)
        doc["observations"][-1]["b1_scanner_blob_sha"] = "a" * 40
        with self.assertRaises(engine.core.EvidenceError):
            self.result(data=doc)

    def test_fingerprint_manifest_has_unique_atoms(self):
        ref = copy.deepcopy(self.b1)
        ref["baseline_unguarded_fingerprints"][1] = copy.deepcopy(
            ref["baseline_unguarded_fingerprints"][0]
        )
        with self.assertRaises(engine.core.EvidenceError):
            self.result(b1=ref)

    def test_fingerprint_manifest_missing_atom_rejected(self):
        ref = copy.deepcopy(self.b1)
        ref["baseline_unguarded_fingerprints"].pop()
        with self.assertRaises(engine.core.EvidenceError):
            self.result(b1=ref)

    def test_unmatched_fingerprint_manifest_rejected(self):
        ref = copy.deepcopy(self.b1)
        ref["comparison"][-1]["baseline_intersection"] -= 1
        with self.assertRaises(engine.core.EvidenceError):
            self.result(b1=ref)

    def test_unmatched_source_head_rejected(self):
        ref = copy.deepcopy(self.b1)
        ref["comparison"][-1]["source_sha"] = "b" * 40
        with self.assertRaises(engine.core.EvidenceError):
            self.result(b1=ref)

    def test_zero_scan_denominator_rejected(self):
        doc = copy.deepcopy(self.data)
        ref = copy.deepcopy(self.b1)
        doc["observations"][-1]["b1_scanned_files"] = 0
        ref["comparison"][-1]["scanned_files"] = 0
        with self.assertRaises(engine.core.EvidenceError):
            self.result(data=doc, b1=ref)

    def test_false_root_closure_claim_rejected(self):
        doc = copy.deepcopy(self.data)
        doc["observations"][-1]["root_closure_count"] = 0
        with self.assertRaises(engine.core.EvidenceError):
            self.result(data=doc)

    def test_repaired_scan_population_changes_scope_diagnostic(self):
        doc = copy.deepcopy(self.data)
        ref = copy.deepcopy(self.b1)
        doc["observations"][1]["b1_scanned_files"] = 160
        ref["comparison"][1]["scanned_files"] = 160
        state = self.result(data=doc, b1=ref)["five_pulse_metrics"]
        self.assertEqual(state["b1_scope_status"], "IDENTICAL_SCANNED_FILE_COUNTS_ONLY")


if __name__ == "__main__":
    unittest.main()
