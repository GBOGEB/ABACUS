"""Negative controls for 3P stability measurement and non-promotion."""
from __future__ import annotations

import contextlib
import io
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from tools.w64_3p_stability_rollup import (
    classify,
    comparable,
    main,
    measurement_errors,
)


def complete_run(identifier: str, *, wall: float = 100.0) -> dict[str, object]:
    return {
        "run_id": identifier,
        "valid": True,
        "source_sha": "a" * 40,
        "stratum": "same-root-item-sample",
        "measurement_contract": "3p-wall-v1",
        "wall_ms_per_root_item": wall,
        "AHT_ms_per_root_item": wall * 0.8,
        "terminal_items_per_worker_hour": 2.0,
        "evidence_yield_per_worker_minute": 1.0,
        "rework_rate": 0.05,
        "information_loss_failures": 0,
        "DoV_gap_after": 1.0,
    }


class StabilityEvidenceGuardTests(TestCase):
    def test_complete_measurement_has_no_errors(self):
        self.assertEqual([], measurement_errors(complete_run("r1")))

    def test_absent_source_or_contract_cannot_compare(self):
        bad = complete_run("r2")
        bad.pop("source_sha")
        bad.pop("measurement_contract")
        self.assertIn("missing_source_sha", measurement_errors(bad))
        self.assertIn("missing_measurement_contract", measurement_errors(bad))

    def test_missing_or_zero_throughput_not_counted_as_valid(self):
        bad = complete_run("r2")
        bad["terminal_items_per_worker_hour"] = 0
        self.assertIn("invalid_terminal_items_per_worker_hour", measurement_errors(bad))
        bad.pop("terminal_items_per_worker_hour")
        self.assertIn("invalid_terminal_items_per_worker_hour", measurement_errors(bad))

    def test_nonfinite_and_boolean_metrics_fail_closed(self):
        for value in [float("nan"), float("inf"), -1, True]:
            with self.subTest(value=str(value)):
                bad = complete_run("invalid")
                bad["wall_ms_per_root_item"] = value
                self.assertIn("invalid_wall_ms_per_root_item", measurement_errors(bad))

    def test_missing_information_loss_cannot_mean_zero(self):
        bad = complete_run("r2")
        bad.pop("information_loss_failures")
        self.assertIn("invalid_information_loss_failures", measurement_errors(bad))

    def test_invalid_flag_rejected(self):
        bad = complete_run("r2")
        bad["valid"] = "true"
        self.assertIn("explicit_valid_true_required", measurement_errors(bad))

    def test_different_measurement_contract_not_comparable(self):
        base = complete_run("r1")
        changed = complete_run("r2")
        changed["measurement_contract"] = "3p-wall-v2"
        self.assertFalse(comparable(base, changed))

    def test_incomplete_latest_receipt_does_not_inherit_prior_green(self):
        earlier = [complete_run(str(i), wall=100-i*5) for i in range(5)]
        invalid_latest = complete_run("last", wall=40)
        invalid_latest["evidence_yield_per_worker_minute"] = None
        with TemporaryDirectory() as folder:
            source = Path(folder) / "history.jsonl"
            dest = Path(folder) / "rollup.json"
            source.write_text(
                "".join(json.dumps(x) + "\n" for x in [*earlier, invalid_latest]),
                encoding="utf-8",
            )
            with patch.object(sys, "argv", [
                "w64_3p_stability_rollup.py", "--history", str(source), "--out", str(dest)
            ]), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(0, main())
            rollup = json.loads(dest.read_text(encoding="utf-8"))
            self.assertEqual("INSUFFICIENT_EVIDENCE", rollup["stability_class"])
            self.assertIsNone(rollup["speed_vs_fixed_baseline"]["wall_speedup_x"])
            self.assertEqual(1, rollup["incomplete_run_count"])
            self.assertEqual("last", rollup["current_run_id"])

    def test_three_comparable_valid_runs_still_produce_measured_direction(self):
        base = [complete_run(str(i), wall=100 - i*10) for i in range(3)]
        state, reasons = classify(base, base[-1])
        self.assertIn(state, {"DIRECTIONAL_IMPROVEMENT", "PROVISIONALLY_STABLE", "NO_STABLE_GAIN_YET"})
        self.assertTrue(reasons)


    def test_out_of_range_rework_and_negative_gap_rejected(self):
        for field, value in (
            ("rework_rate", 1.5),
            ("rework_rate", -0.01),
            ("DoV_gap_after", -1),
        ):
            with self.subTest(field=field, value=value):
                bad = complete_run("invalid")
                bad[field] = value
                self.assertIn("invalid_" + field, measurement_errors(bad))

    def test_direct_classifier_cannot_promote_invalid_current(self):
        a = complete_run("r1")
        invalid = complete_run("r2")
        invalid["information_loss_failures"] = None
        state, reasons = classify([a, invalid, a], invalid)
        self.assertEqual("INSUFFICIENT_EVIDENCE", state)
        self.assertIn("incomplete_or_invalid_run_metrics", reasons)

    def test_empty_history_is_explicit_failure(self):
        with TemporaryDirectory() as folder:
            source = Path(folder) / "history.jsonl"
            output = Path(folder) / "rollup.json"
            source.write_text("", encoding="utf-8")
            with patch.object(sys, "argv", [
                "3p", "--history", str(source), "--out", str(output)
            ]):
                with self.assertRaisesRegex(ValueError, "history contains no runs"):
                    main()

    def test_valid_comparable_history_emits_real_speedup(self):
        runs = [complete_run("r1", wall=100.0),
                complete_run("r2", wall=90.0),
                complete_run("r3", wall=80.0)]
        with TemporaryDirectory() as folder:
            source = Path(folder) / "history.jsonl"
            output = Path(folder) / "rollup.json"
            source.write_text(
                "".join(json.dumps(x) + "\n" for x in runs), encoding="utf-8"
            )
            with patch.object(sys, "argv", [
                "3p", "--history", str(source), "--out", str(output)
            ]), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(0, main())
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(3, result["comparable_valid_run_count"])
            self.assertEqual(0, result["incomplete_run_count"])
            self.assertAlmostEqual(
                1.25, result["speed_vs_fixed_baseline"]["wall_speedup_x"]
            )

    def test_single_complete_run_is_measured_but_not_stable(self):
        with TemporaryDirectory() as folder:
            source = Path(folder) / "history.jsonl"
            output = Path(folder) / "rollup.json"
            source.write_text(
                json.dumps(complete_run("only")) + "\n", encoding="utf-8"
            )
            with patch.object(sys, "argv", [
                "3p", "--history", str(source), "--out", str(output)
            ]), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(0, main())
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual("INSUFFICIENT_EVIDENCE", result["stability_class"])
            self.assertEqual(1, result["comparable_valid_run_count"])
