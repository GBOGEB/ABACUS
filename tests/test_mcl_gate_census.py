"""Negative controls for source-bound gate census."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mission_control_lite.gate_census import main, summarize

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
            {
                "id": 4,
                "head_sha": SHA,
                "status": "completed",
                "conclusion": "cancelled",
            },
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
            summarize(
                SHA,
                [
                    {
                        "id": 1,
                        "head_sha": "a" * 40,
                        "status": "completed",
                        "conclusion": "success",
                    }
                ],
            )

    def test_duplicate_run_id_rejected(self):
        row = {"id": 1, "head_sha": SHA, "status": "completed", "conclusion": "success"}
        with self.assertRaisesRegex(ValueError, "duplicate"):
            summarize(SHA, [row, row])

    def test_running_success_not_terminal(self):
        with self.assertRaisesRegex(ValueError, "nonterminal"):
            summarize(
                SHA,
                [
                    {
                        "id": 1,
                        "head_sha": SHA,
                        "status": "in_progress",
                        "conclusion": "success",
                    }
                ],
            )

    def test_cli_writes_explicit_terminal_denominators(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            records = [
                {
                    "id": 10,
                    "head_sha": SHA,
                    "status": "completed",
                    "conclusion": "success",
                },
                {
                    "id": 11,
                    "head_sha": SHA,
                    "status": "completed",
                    "conclusion": "failure",
                },
            ]
            (root / "runs.json").write_text(json.dumps(records), encoding="utf-8")
            with patch.object(
                sys,
                "argv",
                [
                    "gate_census",
                    "--head-sha",
                    SHA,
                    "--runs-json",
                    str(root / "runs.json"),
                    "--out-json",
                    str(root / "receipt.json"),
                ],
            ):
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
            with (
                patch.object(
                    sys,
                    "argv",
                    [
                        "gate_census",
                        "--head-sha",
                        SHA,
                        "--runs-json",
                        str(root / "runs.json"),
                        "--out-json",
                        str(root / "receipt.json"),
                    ],
                ),
                self.assertRaisesRegex(ValueError, "JSON list"),
            ):
                main()
            self.assertFalse((root / "receipt.json").exists())

    def test_invalid_run_id_types_are_rejected(self):
        for value in (True, -1, "3", 0):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(ValueError, "invalid or duplicate"),
            ):
                summarize(
                    SHA,
                    [
                        {
                            "id": value,
                            "head_sha": SHA,
                            "status": "completed",
                            "conclusion": "success",
                        }
                    ],
                )

    def test_invalid_head_rejected(self):
        with self.assertRaisesRegex(ValueError, "full hexadecimal"):
            summarize("short", [])

    def test_stale_and_startup_failure_are_terminal_blockers(self):
        runs = [
            {"id": 16, "head_sha": SHA, "status": "completed", "conclusion": "stale"},
            {
                "id": 17,
                "head_sha": SHA,
                "status": "completed",
                "conclusion": "startup_failure",
            },
        ]
        report = summarize(SHA, runs)
        self.assertEqual(report["observations"], 2)
        self.assertEqual(report["stale"], 1)
        self.assertEqual(report["startup_failure"], 1)
        self.assertEqual(report["blocking_terminal"], 2)
        self.assertEqual(report["other_terminal"], 2)
        self.assertEqual(report["successful"], 0)
        self.assertEqual(report["success_fraction"], 0)
        self.assertEqual(report["gate_admission"], "HOLD")

    def test_all_terminal_outcomes_are_denominator_conserved(self):
        reasons = [
            "success",
            "failure",
            "cancelled",
            "skipped",
            "timed_out",
            "action_required",
            "neutral",
            "stale",
            "startup_failure",
        ]
        runs = [
            {
                "id": 101 + i,
                "head_sha": SHA,
                "status": "completed",
                "conclusion": outcome,
            }
            for i, outcome in enumerate(reasons)
        ]
        report = summarize(SHA, runs)
        self.assertEqual(report["observations"], len(reasons))
        self.assertEqual(report["successful"], 1)
        self.assertEqual(report["failed"], 1)
        self.assertEqual(report["cancelled"], 1)
        self.assertEqual(report["stale"], 1)
        self.assertEqual(report["startup_failure"], 1)
        self.assertEqual(report["blocking_terminal"], 6)
        self.assertEqual(report["other_terminal"], 6)
        self.assertEqual(report["success_fraction"], 1 / 9)
        self.assertEqual(report["gate_admission"], "HOLD")

    def test_running_stale_is_rejected_as_nonterminal(self):
        with self.assertRaisesRegex(ValueError, "nonterminal"):
            summarize(
                SHA,
                [
                    {
                        "id": 22,
                        "head_sha": SHA,
                        "status": "in_progress",
                        "conclusion": "stale",
                    }
                ],
            )

    def test_unknown_conclusion_still_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "unsupported"):
            summarize(
                SHA,
                [
                    {
                        "id": 22,
                        "head_sha": SHA,
                        "status": "completed",
                        "conclusion": "start_failure",
                    }
                ],
            )

    def test_cli_preserves_new_terminal_reason_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            records = [
                {
                    "id": 61,
                    "head_sha": SHA,
                    "status": "completed",
                    "conclusion": "stale",
                },
                {
                    "id": 62,
                    "head_sha": SHA,
                    "status": "completed",
                    "conclusion": "startup_failure",
                },
            ]
            (root / "runs.json").write_text(json.dumps(records), encoding="utf-8")
            with patch.object(
                sys,
                "argv",
                [
                    "gate_census",
                    "--head-sha",
                    SHA,
                    "--runs-json",
                    str(root / "runs.json"),
                    "--out-json",
                    str(root / "receipt.json"),
                ],
            ):
                main()
            result = json.loads((root / "receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(result["stale"], 1)
            self.assertEqual(result["startup_failure"], 1)
            self.assertEqual(result["blocking_terminal"], 2)
            self.assertEqual(result["gate_admission"], "HOLD")


if __name__ == "__main__":
    unittest.main()
