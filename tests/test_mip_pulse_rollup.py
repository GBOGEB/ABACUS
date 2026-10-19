"""Synthetic MIP temporal telemetry validation; no external effects."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("pulse", Path(__file__).resolve().parents[1] / "tools" / "triage" / "mip_pulse_rollup.py")
pulse = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pulse)

A = "a"*40
B = "b"*40
P = "c"*64
I = "d"*64


def receipt(i, *, covered=10, population=P, instrument=I, unknown=2, roots=5):
    return {
        "schema": pulse.SCHEMA, "repository": "GBOGEB/ABACUS",
        "head_sha": A if i == 0 else B,
        "population_sha256": population, "instrumentation_sha256": instrument,
        "observed_at": f"2026-10-{19+i:02d}T10:00:00Z",
        "coverage": {"statements": {"covered": covered, "eligible": 100},
                     "branches": {"covered": 0, "eligible": 20}},
        "triage": {"candidates": 10, "linked": 4, "orphan": 1,
                   "other_disposed": 5-unknown, "unknown": unknown},
        "root_reds_open": roots, "root_cohort_id": "fixed-roots",
        "workers": [{"owner": "source-a", "paths": ["a.py"], "queue_seconds": 1,
                     "execution_seconds": 2}],
        "governance": {"merge_admission": "HOLD", "security_waiver": False},
    }


class PulseTest(unittest.TestCase):
    def test_matched_coverage_gain(self):
        t = pulse.transition(receipt(0), receipt(1, covered=22))
        self.assertTrue(t["population_comparable"])
        self.assertEqual(t["newly_covered_opportunities"], 12)
        self.assertAlmostEqual(t["coverage_gain_pp"], 10)

    def test_population_change_not_gain(self):
        t = pulse.transition(receipt(0), receipt(1, covered=100, population="e"*64))
        self.assertFalse(t["population_comparable"])
        self.assertIsNone(t["coverage_gain_pp"])

    def test_plateau_requires_three_valid_moves(self):
        xs = [receipt(i) for i in range(4)]
        self.assertEqual(pulse.rollup(xs)["control"], "RERANK_UNCOVERED")

    def test_unknown_triage_not_zero(self):
        x = receipt(0)
        x["triage"] = None
        self.assertIsNone(pulse.snapshot(x)["triage"])

    def test_no_plateau_without_root_cohort(self):
        xs = [receipt(i) for i in range(4)]
        for x in xs:
            x.pop("root_cohort_id")
        self.assertNotEqual(pulse.rollup(xs)["control"], "STOP_LOCAL_PLATEAU")


if __name__ == "__main__":
    unittest.main()
