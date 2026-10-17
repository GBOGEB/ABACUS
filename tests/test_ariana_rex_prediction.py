"""Adversarial tests for Ariana REX forecasts and source-bound replay.

Runs with the standard library: python -m unittest discover -s tests
-p test_ariana_rex_prediction.py -v
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts.ci.ariana_rex_prediction import (
    evaluate,
    validate_ledger,
    verify_archives,
    wilson,
)

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "triage/rex/ARIANA_CI_N_SERIES_20261017.json"


def source():
    return json.loads(INPUT.read_text(encoding="utf-8"))


class ArianaREXPredictionTests(unittest.TestCase):
    def test_original_exact_run_series_and_forecasts(self):
        result = evaluate(source())
        self.assertEqual([p["label"] for p in result["series"]],
                         ["N-1", "N", "N+1"])
        self.assertEqual([p["run_id"] for p in result["series"]],
                         [39046522554, 39046770415, 39046986905])
        self.assertEqual([p["conclusion"] for p in result["series"]],
                         ["failure", "failure", "success"])
        self.assertEqual(result["directional_forecasts"]["hits"], 3)
        self.assertEqual(result["directional_forecasts"]["n"], 3)
        self.assertEqual(result["directional_forecasts"]["brier"], None)
        self.assertEqual(result["directional_forecasts"]["calibration"],
                         "UNQUALIFIED_SMALL_N")
        self.assertEqual(result["rex"]["observed_source_first_red_roots_in_series"], 2)
        self.assertEqual(result["rex"]["root_manifestations"], 5)

    def test_missing_test_population_is_not_zero_and_n_is_unmatched(self):
        result = evaluate(source())
        self.assertIsNone(result["series"][0]["tested_per_lane"])
        self.assertIsNone(result["series"][0]["focused_statement"])
        self.assertEqual(result["series"][1]["tested_per_lane"], 28)
        self.assertEqual(result["series"][2]["tested_per_lane"], 29)
        self.assertIsNone(result["coverage_deltas"]["N_minus_1_to_N"])
        self.assertIsNone(result["coverage_deltas"]["N_to_N_plus_1"])

    def test_actual_scope_measured_without_unauthorized_credit(self):
        result = evaluate(source())
        n = result["series"][2]
        self.assertEqual(n["focused_statement"],
                         {"numerator": 208, "denominator": 209})
        self.assertEqual(n["focused_branch"],
                         {"numerator": 39, "denominator": 42})
        self.assertEqual(result["governance"]["merge_admission"], "HOLD")
        self.assertEqual(result["governance"]["accepted_N_delta"], 0)
        self.assertIsNone(result["governance"]["remote_keb_or_qps_acceptance"])
        self.assertIsNone(result["prospective"]["observed"])

    def test_forecast_timestamp_after_run_rejected(self):
        d = source()
        d["forecasts"][1]["frozen_at"] = "2026-10-17T15:50:01Z"
        with self.assertRaisesRegex(ValueError, "hindsight leakage"):
            evaluate(d)

    def test_unknown_actual_not_scored_as_miss_or_hit(self):
        d = source()
        d["checkpoints"][0]["milestones"]["legacy_path_bypassed"] = None
        output = evaluate(d)
        self.assertEqual(output["directional_forecasts"]["n"], 2)
        self.assertEqual(output["directional_forecasts"]["hits"], 2)
        self.assertIsNone(output["directional_forecasts"]["scored"][0]["hit"])

    def test_duplicate_sha_or_run_id_rejected(self):
        for field in ("source_sha", "run_id"):
            d = source()
            d["checkpoints"][1][field] = d["checkpoints"][0][field]
            with self.assertRaises(ValueError):
                validate_ledger(d)

    def test_artifact_without_digest_rejected(self):
        d = source()
        d["checkpoints"][2]["artifacts"][0]["sha256"] = "not-a-digest"
        with self.assertRaisesRegex(ValueError, "artifact digest"):
            evaluate(d)

    def test_false_green_remote_qps_acceptance_rejected(self):
        d = source()
        d["checkpoints"][2]["join"]["qps_engineering_acceptance"] = "PASS"
        with self.assertRaisesRegex(ValueError, "QPS acceptance"):
            evaluate(d)
        d = source()
        d["parent"]["merge_admission"] = "GO"
        with self.assertRaisesRegex(ValueError, "admission"):
            evaluate(d)

    def test_fake_combined_coverage_numerator_rejected(self):
        d = source()
        d["checkpoints"][2]["focused_coverage"]["combined"]["numerator"] = 251
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            evaluate(d)

    def test_preserve_null_changed_line_denominator(self):
        d = source()
        d["checkpoints"][2]["focused_coverage"]["changed_line"] = {
            "numerator": 0, "denominator": 0,
        }
        with self.assertRaisesRegex(ValueError, "changed-line"):
            evaluate(d)

    def test_risk_bound_on_only_three_selected_pulses(self):
        limits = wilson(3, 3)
        self.assertAlmostEqual(limits["lower"], 0.438503, places=5)
        self.assertEqual(limits["upper"], 1.0)
        self.assertIsNone(wilson(0, 0))
        result = evaluate(source())
        self.assertEqual(result["rex"]["six_sigma_claim"], "NOT_ESTABLISHED")

    def test_future_cannot_be_invented_or_promoted(self):
        d = source()
        d["prospective"]["run_id"] = 12345
        with self.assertRaisesRegex(ValueError, "future evidence"):
            evaluate(d)
        d = source()
        d["prospective"]["forecast_admission"] = "GO"
        with self.assertRaisesRegex(ValueError, "review/CI/security"):
            evaluate(d)

    def test_zip_archive_replay_and_byte_tamper(self):
        d = source()
        p = d["checkpoints"][-1]
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            for art in p["artifacts"]:
                name = folder / f"github-actions-artifact-{art['id']}.zip"
                with zipfile.ZipFile(name, "w") as z:
                    if art["lane"] == "join":
                        receipt = {
                            "source_sha": p["source_sha"],
                            "merge_admission": "HOLD",
                            "qps_engineering_acceptance": None,
                            "remote_keb_or_qps_receipts": None,
                            "python_lanes": ["3.11", "3.12"],
                        }
                        z.writestr("two-lane-join.json", json.dumps(receipt))
                    else:
                        receipt = {
                            "producer": {
                                "source_sha": p["source_sha"],
                                "run_id": str(p["run_id"]),
                                "run_attempt": str(p["run_attempt"]),
                                "python_version": art["lane"],
                            },
                            "disposition": "LOCAL_TESTED_FEDERATION_HOLD",
                            "native_test_receipt": p["tests"][art["lane"]],
                            "focused_coverage": {
                                "statements": p["focused_coverage"]["statement"],
                                "branches": p["focused_coverage"]["branch"],
                                "combined": p["focused_coverage"]["combined"],
                            },
                        }
                        z.writestr("ariana-dow-receipt.json",
                                   json.dumps(receipt))
                        z.writestr("coverage.json", "{}")
                        z.writestr("junit.xml", "<testsuite/>")
                art["sha256"] = hashlib.sha256(name.read_bytes()).hexdigest()
            result = evaluate(d, folder)
            self.assertEqual(result["archive_byte_replay"]["state"], "VERIFIED")
            self.assertEqual(len(result["archive_byte_replay"]["artifact_ids"]), 3)
            bad = folder / (
                f"github-actions-artifact-{p['artifacts'][0]['id']}.zip"
            )
            bad.write_bytes(bad.read_bytes() + b"tampered")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                verify_archives(d, folder)

    def test_historical_probability_cannot_be_post_hoc_backfilled(self):
        d = source()
        d["forecasts"][0]["probability"] = 0.99
        with self.assertRaisesRegex(ValueError, "not preregistered"):
            evaluate(d)

    def test_recurring_same_root_deduplicates_across_pulses(self):
        d = source()
        d["checkpoints"][1]["root"]["root_id"] = (
            d["checkpoints"][0]["root"]["root_id"]
        )
        result = evaluate(d)
        self.assertEqual(
            result["rex"]["observed_source_first_red_roots_in_series"], 1
        )
        self.assertEqual(
            result["rex"]["repeat_observations_of_existing_root"], 1
        )
        self.assertEqual(result["rex"]["root_manifestations"], 5)


if __name__ == "__main__":
    unittest.main()
