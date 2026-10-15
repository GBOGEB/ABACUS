"""Negative controls for exact-SHA workflow wave transitions."""

import unittest

from tools.w70_workflow_transitions import compare

A = "a" * 40
B = "b" * 40


class TransitionTests(unittest.TestCase):
    def test_exact_matched_cohort(self):
        old = [
            {"name": "docs", "conclusion": "failure"},
            {"name": "B0", "conclusion": "failure"},
            {"name": "security", "conclusion": "failure"},
        ]
        new = [
            {"name": "security", "conclusion": "failure"},
            {"name": "B0", "conclusion": "success"},
            {"name": "docs", "conclusion": "success"},
        ]
        x = compare(old, new, previous_sha=A, current_sha=B)
        self.assertEqual(66.67, x["success_rate_delta_pp"])
        self.assertEqual(["B0", "docs"], x["improved_fail_to_pass"])
        self.assertIsNone(x["unique_bd_roots_closed"])
        self.assertEqual("HOLD", x["governance_admission"])

    def test_nonmatching_cohort_withholds_delta(self):
        x = compare(
            [{"name": "a", "conclusion": "success"}],
            [{"name": "b", "conclusion": "success"}],
            previous_sha=A,
            current_sha=B,
        )
        self.assertIsNone(x["success_rate_delta_pp"])

    def test_pending_withholds_delta(self):
        x = compare(
            [{"name": "a", "conclusion": None}],
            [{"name": "a", "conclusion": "success"}],
            previous_sha=A,
            current_sha=B,
        )
        self.assertIsNone(x["success_rate_delta_pp"])

    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):
            compare(
                [{"name": "a", "conclusion": "success"}] * 2,
                [{"name": "a", "conclusion": "success"}],
                previous_sha=A,
                current_sha=B,
            )

    def test_unknown_outcome_rejected(self):
        with self.assertRaises(ValueError):
            compare(
                [{"name": "a", "conclusion": "whatever"}],
                [{"name": "a", "conclusion": "success"}],
                previous_sha=A,
                current_sha=B,
            )

    def test_sha_rejected(self):
        with self.assertRaises(ValueError):
            compare(
                [{"name": "a", "conclusion": "success"}],
                [{"name": "a", "conclusion": "success"}],
                previous_sha="main",
                current_sha=B,
            )


if __name__ == "__main__":
    unittest.main()
