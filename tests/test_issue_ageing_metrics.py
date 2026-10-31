"""Tests for native issue ageing, closure semantics and PR head census.

Mutation cases are synthetic negative controls, never GitHub changes.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "issue_ageing_metrics", ROOT / "triage" / "issue_ageing_metrics.py"
)
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)
ISSUES = ROOT / "triage" / "ABACUS_ISSUE_AGEING_CENSUS_20261017.json"
HEADS = ROOT / "triage" / "ABACUS_PR_HEAD_REGISTER_20261017.json"


class AgeingCensusContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.issues = json.loads(ISSUES.read_text(encoding="utf-8"))
        cls.heads = json.loads(HEADS.read_text(encoding="utf-8"))

    def result(self, issues=None, heads=None):
        return m.summarize(
            self.issues if issues is None else issues,
            self.heads if heads is None else heads,
        )

    def test_verified_live_totals_and_hard_hold(self):
        d = self.result()
        self.assertEqual(d["open_issues"], 53)
        self.assertEqual(d["open_prs"], 122)
        self.assertEqual(d["P0"], "HOLD")
        self.assertFalse(d["authority_transfer"])

    def test_ageing_cohort_and_source_matched_uplift(self):
        d = self.result()
        self.assertEqual(
            d["age_distribution"],
            {"0_to_6": 25, "7_to_13": 4, "14_to_29": 15, "30_plus": 9},
        )
        self.assertEqual(d["source_matched_statement_gain"], 12)
        self.assertEqual(d["source_matched_branch_gain"], 3)

    def test_duplicate_close_not_root_close(self):
        d = self.result()
        self.assertEqual(d["closed_duplicate_tickets"], 6)
        self.assertIsNone(d["engineering_root_closed"])
        self.assertIsNone(d["time_to_engineering_root_closure"])
        self.assertIsNone(d["survival_hazard"])

    def test_wrong_repository_rejected(self):
        d = copy.deepcopy(self.issues)
        d["repository"] = "OTHER/REPO"
        with self.assertRaises(m.CensusError):
            self.result(issues=d)

    def test_duplicate_issue_rejected(self):
        d = copy.deepcopy(self.issues)
        d["issue_records"][1]["issue"] = d["issue_records"][0]["issue"]
        with self.assertRaises(m.CensusError):
            self.result(issues=d)

    def test_out_of_band_age_rejected(self):
        d = copy.deepcopy(self.issues)
        row = next(r for r in d["issue_records"] if r["issue"] == 633)
        row["age_days"] = 2000000
        with self.assertRaises(m.CensusError):
            self.result(issues=d)

    def test_age_cohort_mismatch_rejected(self):
        d = copy.deepcopy(self.issues)
        d["live"]["age_cohorts"]["30_plus"] += 1
        with self.assertRaises(m.CensusError):
            self.result(issues=d)

    def test_non_closed_open_issue_rejected(self):
        d = copy.deepcopy(self.issues)
        d["issue_records"][0]["status"] = "CLOSED"
        with self.assertRaises(m.CensusError):
            self.result(issues=d)

    def test_false_engineering_root_closed_count_rejected(self):
        d = copy.deepcopy(self.issues)
        d["live"]["root_closed_count"] = 0
        with self.assertRaises(m.CensusError):
            self.result(issues=d)

    def test_duplicate_ticket_wrong_reason_rejected(self):
        d = copy.deepcopy(self.issues)
        d["closed_housekeeping"][0]["reason"] = "completed"
        with self.assertRaises(m.CensusError):
            self.result(issues=d)

    def test_undocumented_main_advance_rejected(self):
        d = copy.deepcopy(self.issues)
        d["live"]["current_main_sha"] = "f" * 40
        with self.assertRaises(m.CensusError):
            self.result(issues=d)

    def test_mismatched_coverage_denominator_rejected(self):
        d = copy.deepcopy(self.heads)
        d["bseries_source_matched"]["statement_after"][1] = 70
        with self.assertRaises(m.CensusError):
            self.result(heads=d)

    def test_unbound_pr_sha_rejected(self):
        d = copy.deepcopy(self.heads)
        d["primary_source_heads"][0]["head_sha"] = "NOT_A_SHA"
        with self.assertRaises(m.CensusError):
            self.result(heads=d)

    def test_feature_merge_must_not_be_open_pr(self):
        d = copy.deepcopy(self.heads)
        d["primary_source_heads"][0]["merged"] = True
        with self.assertRaises(m.CensusError):
            self.result(heads=d)

    def test_no_authority_promotion(self):
        d = copy.deepcopy(self.heads)
        d["authority_transfer"] = True
        with self.assertRaises(m.CensusError):
            self.result(heads=d)


if __name__ == "__main__":
    unittest.main()
