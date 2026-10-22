"""TestPilot local-preflight receipts must not manufacture gate success."""
from __future__ import annotations

import contextlib
import io
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from scripts import testpilot_preflight as pilot


class TestPilotReceiptContractTests(TestCase):
    def test_all_pass_is_pass(self):
        self.assertEqual(("PASS", 0), pilot.receipt_outcome(
            [{"status": "PASS"}], "gate"
        ))

    def test_gate_missing_ruff_is_blocking(self):
        self.assertEqual(("FAIL", 1), pilot.receipt_outcome(
            [{"status": "PASS"}, {"name": "ruff", "status": "SKIP"}], "gate"
        ))

    def test_fast_missing_ruff_is_partial_not_green(self):
        self.assertEqual(("PARTIAL", 0), pilot.receipt_outcome(
            [{"status": "PASS"}, {"name": "ruff", "status": "SKIP"}], "fast"
        ))

    def test_ci_fast_parity_skips_are_blocking(self):
        self.assertEqual(("FAIL", 1), pilot.receipt_outcome(
            [{"status": "PASS"}, {"status": "SKIP"}], "fast", parity=True
        ))

    def test_unknown_check_state_is_never_pass(self):
        self.assertEqual(("FAIL", 1), pilot.receipt_outcome(
            [{"status": "UNKNOWN"}], "gate"
        ))
        self.assertEqual(("PARTIAL", 0), pilot.receipt_outcome(
            [{"status": "UNKNOWN"}], "fast"
        ))

    def test_actual_failure_always_fails(self):
        for mode in ("fast", "full", "gate"):
            self.assertEqual(("FAIL", 1), pilot.receipt_outcome(
                [{"status": "FAIL"}, {"status": "SKIP"}], mode
            ))

    def _assert_invalid_gate_floor(self, floor):
        # Five independent pytest/unittest cases give JUnit one testcase per
        # exercised value. A five-iteration subTest had inflated declared
        # suite totals without five distinct testcase elements.
        with (
            patch.object(sys, "argv", [
                "testpilot_preflight.py", "--mode", "gate",
                "--coverage-floor", floor
            ]),
            patch.object(pilot, "targeted_pytest") as pytest_mock,
            contextlib.redirect_stderr(io.StringIO()),
        ):
            with self.assertRaises(SystemExit) as error:
                pilot.main()
            self.assertEqual(2, error.exception.code)
            pytest_mock.assert_not_called()

    def test_invalid_gate_floor_zero(self):
        self._assert_invalid_gate_floor("0")

    def test_invalid_gate_floor_fractional(self):
        self._assert_invalid_gate_floor("74.9")

    def test_invalid_gate_floor_nan(self):
        self._assert_invalid_gate_floor("nan")

    def test_invalid_gate_floor_infinite(self):
        self._assert_invalid_gate_floor("inf")

    def test_invalid_gate_floor_above_hundred(self):
        self._assert_invalid_gate_floor("101")

    def test_valid_higher_gate_floor_is_permitted(self):
        with TemporaryDirectory() as folder:
            receipt_path = Path(folder) / "receipt.json"
            with (
                patch.object(sys, "argv", [
                    "testpilot_preflight.py", "--mode", "gate", "--parity",
                    "--coverage-floor", "85", "--receipt", str(receipt_path)
                ]),
                patch.object(pilot, "parity_subject_files", return_value=[]),
                patch.object(pilot, "targeted_pytest", return_value=[]),
                patch.object(pilot, "coverage_check", return_value={"status": "PASS"}),
                patch.object(pilot, "source_sha", return_value="a" * 40),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(0, pilot.main())
            payload = json.loads(receipt_path.read_text())
            self.assertEqual(85, payload["checks"][-1].get("coverage_floor_pct", 85))
            self.assertEqual("PASS", payload["status"])

    def test_skipped_fast_receipt_retains_unverified_denominator(self):
        with TemporaryDirectory() as folder:
            receipt_path = Path(folder) / "receipt.json"
            with (
                patch.object(sys, "argv", [
                    "testpilot_preflight.py", "--mode", "fast",
                    "--receipt", str(receipt_path)
                ]),
                patch.object(pilot, "changed_files", return_value=[]),
                patch.object(pilot, "targeted_pytest", return_value=[]),
                patch.object(pilot, "ruff_check", return_value={
                    "name": "ruff", "status": "SKIP"
                }),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(0, pilot.main())
            payload = json.loads(receipt_path.read_text())
            self.assertEqual("PARTIAL", payload["status"])
            self.assertEqual(1, payload["unverified_check_count"])
