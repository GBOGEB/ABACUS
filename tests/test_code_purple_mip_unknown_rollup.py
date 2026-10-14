"""Tests for MIP UNKNOWN ledger validation and KPI rollup."""
import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("mip_rollup", ROOT / "scripts/code_purple_mip_unknown_rollup.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class RollupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "MIP/code_purple_unknown_backlog.json").read_text(encoding="utf-8"))

    def test_sixteen_unknowns_are_not_zero_or_verified(self):
        r = m.rollup(self.data, "2026-10-14")
        self.assertEqual(16, r["states"]["UNKNOWN"])
        self.assertEqual(0, r["evidence_completeness"])
        self.assertEqual("HOLD", r["merge_admission"])

    def test_age_is_computed_from_source_date(self):
        r = m.rollup(self.data, "2026-10-16")
        self.assertTrue(all(x["age_days"] == 2 for x in r["aged"]))

    def test_duplicates_fail_closed(self):
        d = copy.deepcopy(self.data)
        d["items"][1]["id"] = "U01"
        with self.assertRaises(ValueError):
            m.rollup(d, "2026-10-14")

    def test_fake_pass_without_proof_is_refused(self):
        d = copy.deepcopy(self.data)
        d["items"][0]["evidence_state"] = "VERIFIED_PASS"
        d["items"][0]["measurement_value"] = 1
        with self.assertRaises(ValueError):
            m.rollup(d, "2026-10-14")

    def test_unknown_with_measurement_fails(self):
        d = copy.deepcopy(self.data)
        d["items"][0]["measurement_value"] = 0
        with self.assertRaises(ValueError):
            m.rollup(d, "2026-10-14")

    def test_valid_native_proof_counts_without_admitting(self):
        d = copy.deepcopy(self.data)
        d["items"][0].update(evidence_state="VERIFIED_PASS", measurement_value=1,
                             proof_reference="https://github.com/GBOGEB/ABACUS/actions/runs/123")
        r = m.rollup(d, "2026-10-14")
        self.assertEqual(1, r["evidence_completeness"])
        self.assertEqual("HOLD", r["merge_admission"])

    def test_stale_age_fails(self):
        d = copy.deepcopy(self.data)
        d["items"][0]["age"]["days"] = 4
        with self.assertRaises(ValueError):
            m.rollup(d, "2026-10-14")


if __name__ == "__main__":
    unittest.main()
