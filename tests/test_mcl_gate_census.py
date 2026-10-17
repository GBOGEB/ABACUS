"""Negative controls for source-bound gate census."""
import unittest

from mission_control_lite.gate_census import summarize

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

    def test_invalid_head_rejected(self):
        with self.assertRaisesRegex(ValueError, "full hexadecimal"):
            summarize("short", [])


if __name__ == "__main__":
    unittest.main()
