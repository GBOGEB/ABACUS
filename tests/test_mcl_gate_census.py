"""Negative controls for source-bound gate census."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mission_control_lite.gate_census import summarize, main

SHA = "77a359bbdb742e9145c38b5f94ad882cc40f7ac4"


class GateCensusTests(unittest.TestCase):
    def test_empty_denominator_not_success(self):
        report = summarize(SHA, [])
        self.assertIsNone(report["success_fraction"])
        self.assertEqual(report["gate_admission"], "HOLD")

    def test_mixed_terminal_observations(self):
        runs = [
            {"id": 3, "head_sha": SHA, "status": "completed", "conclusion": "failure"},
            {"id": 2, "head_sha": SHA, "status": "completed", "conclusion": "success"},
            {"id": 4, "head_sha": SHA, "status": "completed", "conclusion": "cancelled"},
        ]
        report = summarize(SHA, runs)
        self.assertEqual(report["observations"], 3)
        self.assertEqual(report["successful"], 1)
        self.assertEqual(report["failed"], 1)
        self.assertEqual(report["cancelled"], 1)
        self.assertEqual(report["success_fraction"], 1 / 3)
        self.assertEqual([r["run_id"] for r in report["records"]], [2, 3, 4])
        self.assertEqual(report["gate_admission"], "HOLD")

    def test_moving_head_rejected(self):
        with self.assertRaisesRegex(ValueError, "source differs"):
            summarize(SHA, [{"id": 1, "head_sha": "a" * 40,
                             "status": "completed", "conclusion": "success"}])

    def test_duplicate_run_id_rejected(self):
        row = {"id": 1, "head_sha": SHA, "status": "completed", "conclusion": "success"}
        with self.assertRaisesRegex(ValueError, "duplicate"):
            summarize(SHA, [row, row])

    def test_running_success_not_terminal(self):
        with self.assertRaisesRegex(ValueError, "nonterminal"):
            summarize(SHA, [{"id": 1, "head_sha": SHA,
                             "status": "in_progress", "conclusion": "success"}])

    def test_cli_writes_explicit_terminal_denominators(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            records = [
                {"id": 10, "head_sha": SHA, "status": "completed", "conclusion": "success"},
                {"id": 11, "head_sha": SHA, "status": "completed", "conclusion": "failure"},
            ]
            (root / "runs.json").write_text(json.dumps(records), encoding="utf-8")
            with patch.object(sys, "argv", [
                "gate_census", "--head-sha", SHA,
                "--runs-json", str(root / "runs.json"),
                "--out-json", str(root / "receipt.json"),
            ]):
                main()
            result = json.loads((root / "receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(result["source_sha"], SHA)
            self.assertEqual(result["observations"], 2)
            self.assertEqual(result["successful"], 1)
            self.assertEqual(result["failed"], 1)
            self.assertEqual(result["success_fraction"], 0.5)
            self.assertEqual(result["gate_admission"], "HOLD")

    def test_cli_fails_closed_on_nonlist_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "runs.json").write_text('{"id": 1}', encoding="utf-8")
            with patch.object(sys, "argv", [
                "gate_census", "--head-sha", SHA,
                "--runs-json", str(root / "runs.json"),
                "--out-json", str(root / "receipt.json"),
            ]), self.assertRaisesRegex(ValueError, "JSON list"):
                main()
            self.assertFalse((root / "receipt.json").exists())

    def test_invalid_run_id_types_are_rejected(self):
        for value in (True, -1, "3", 0):
            with self.subTest(value=value), self.assertRaisesRegex(
                ValueError, "invalid or duplicate"
            ):
                summarize(SHA, [
                    {"id": value, "head_sha": SHA, "status": "completed",
                     "conclusion": "success"}
                ])

    def test_invalid_head_rejected(self):
        with self.assertRaisesRegex(ValueError, "full hexadecimal"):
            summarize("short", [])


if __name__ == "__main__":
    unittest.main()
