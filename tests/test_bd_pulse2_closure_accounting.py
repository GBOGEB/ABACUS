"""Adversarial accounting tests: issue housekeeping != causal-root closure."""

import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
s = importlib.util.spec_from_file_location(
    "bd_pulse2", ROOT / "triage/validate_bd_pulse2.py"
)
engine = importlib.util.module_from_spec(s)
s.loader.exec_module(engine)


class BDPulseTwoContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(
            (ROOT / "triage/ABACUS_BD_PULSE2_20261017.json").read_text(encoding="utf-8")
        )

    def test_native_closure_math(self):
        x = engine.validate(self.data)
        self.assertEqual(x["open_issue_delta"], -15)
        self.assertEqual(x["duplicate_ticket_closures"], 9)
        self.assertEqual(x["other_issue_completions"], 6)
        self.assertIsNone(x["causal_root_closed_count"])

    def test_four_repo_scope_not_global(self):
        x = engine.validate(self.data)
        self.assertEqual(x["scoped_four_repo_open"], 136)
        self.assertIsNone(x["global_total"])

    def test_no_duplicate_root_credit(self):
        d = copy.deepcopy(self.data)
        d["closure_evidence"]["nine_this_pulse"][0]["engineering_root_credit"] = 1
        with self.assertRaises(ValueError):
            engine.validate(d)

    def test_no_extra_repository_total(self):
        d = copy.deepcopy(self.data)
        d["latest"]["scoped_repo_issue_open"]["GBOGEB/newrepo"] = 1
        with self.assertRaises(ValueError):
            engine.validate(d)

    def test_no_root_closed_zero_forgery(self):
        d = copy.deepcopy(self.data)
        d["latest"]["canonical_engineering_roots_closed"] = 0
        with self.assertRaises(ValueError):
            engine.validate(d)

    def test_duplicate_ticket_must_keep_native_source(self):
        d = copy.deepcopy(self.data)
        d["closure_evidence"]["nine_this_pulse"][0]["source_run_id"] = 0
        with self.assertRaises(ValueError):
            engine.validate(d)

    def test_abacus_age_bin_totals_reconciled(self):
        d = copy.deepcopy(self.data)
        d["latest"]["ABACUS_issue_ages"]["30_plus"] += 1
        with self.assertRaises(ValueError):
            engine.validate(d)

    def test_source_repair_not_automatically_accepted(self):
        d = copy.deepcopy(self.data)
        d["closure_evidence"]["source_repair_accepted"] = True
        with self.assertRaises(ValueError):
            engine.validate(d)

    def test_duplicate_native_ticket_never_counts_twice(self):
        d = copy.deepcopy(self.data)
        d["closure_evidence"]["nine_this_pulse"][1]["issue"] = d["closure_evidence"][
            "nine_this_pulse"
        ][0]["issue"]
        with self.assertRaises(ValueError):
            engine.validate(d)

    def test_no_authority_waiver(self):
        d = copy.deepcopy(self.data)
        d["authority_transfer"] = True
        with self.assertRaises(ValueError):
            engine.validate(d)


if __name__ == "__main__":
    unittest.main()
