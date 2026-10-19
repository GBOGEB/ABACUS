"""V3 temporal synthetic adversarial and N+2 forecast tests."""
import importlib.util
from pathlib import Path
import unittest

FILE = (
    Path(__file__).resolve().parents[1]
    / "tools"
    / "triage"
    / "mip_v3_temporal.py"
)
SPEC = importlib.util.spec_from_file_location("mip_v3_temporal", FILE)
mip = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mip)


def pulse(index, covered=10, **overrides):
    obj = {
        "schema": mip.SCHEMA,
        "pulse_index": index,
        "head_sha": f"{index + 1:040x}",
        "cohort_sha256": "a" * 64,
        "instrumentation_sha256": "b" * 64,
        "artifact_sha256": f"{index + 1:064x}",
        "observed_at": f"2026-10-19T12:{index:02d}:00Z",
        "coverage": {
            "statements": {"covered": covered, "eligible": 100},
            "branches": {"covered": 0, "eligible": 20},
        },
        "native": {
            "run_id": index + 1,
            "attempt": 1,
            "job_id": index + 101,
            "terminal": True,
            "conclusion": "success",
        },
        "root_cohort_sha256": "c" * 64,
        "root_ids_open": ["r01", "r02"],
        "triage_cohort_sha256": "d" * 64,
        "disposition": {"candidates": 10, "resolved": 3, "unknown": 7},
        "workers": [
            {
                "owner": "owner-a",
                "paths": ["src/a.py"],
                "queue_seconds": 10,
                "execution_seconds": 15,
            }
        ],
        "governance": {
            "merged_observed": False,
            "effective_controls_verified": None,
            "security_waiver": False,
        },
    }
    obj.update(overrides)
    return obj


def forecast(from_index, target_index, low, high, issued="12:00:10"):
    return {
        "schema": mip.FORECAST_SCHEMA,
        "issued_after": from_index,
        "target_index": target_index,
        "issued_at": "2026-10-19T" + issued + "Z",
        "issuer_head_sha": f"{from_index + 1:040x}",
        "gain_lower": low,
        "gain_upper": high,
        "rule_id": "frozen-v3",
    }


class TemporalTest(unittest.TestCase):
    def test_matched_progress(self):
        x = mip.rollup([pulse(0), pulse(1, 14)])
        self.assertEqual(x["transitions"][0]["covered_delta"], 4)
        self.assertAlmostEqual(x["transitions"][0]["gain_pp"], 3.333333)
        self.assertFalse(x["formal_coverage_credit"])

    def test_denominator_cohort_drift(self):
        p = pulse(1, 14, cohort_sha256="e" * 64)
        x = mip.rollup([pulse(0), p])
        self.assertIsNone(x["transitions"][0]["gain_pp"])

    def test_instrumentation_drift(self):
        p = pulse(1, 14, instrumentation_sha256="e" * 64)
        x = mip.rollup([pulse(0), p])
        self.assertFalse(x["transitions"][0]["matched"])

    def test_same_head_poll_rejected(self):
        p = pulse(1, head_sha=pulse(0)["head_sha"])
        with self.assertRaisesRegex(ValueError, "reused head"):
            mip.rollup([pulse(0), p])

    def test_replayed_job_rejected(self):
        p = pulse(1, native=pulse(0)["native"])
        with self.assertRaisesRegex(ValueError, "replayed native"):
            mip.rollup([pulse(0), p])

    def test_worker_parent_child_lock(self):
        p = pulse(
            0,
            workers=[
                {"owner": "a", "paths": ["src"]},
                {"owner": "b", "paths": ["src/x.py"]},
            ],
        )
        with self.assertRaisesRegex(ValueError, "overlapping worker"):
            mip.rollup([p])

    def test_governance_red_overrides_progress(self):
        p = pulse(
            1,
            15,
            governance={
                "merged_observed": True,
                "effective_controls_verified": None,
                "security_waiver": False,
            },
        )
        x = mip.rollup([pulse(0), p])
        self.assertEqual(x["control"], "ESCALATE_MERGE_WITHOUT_PROOF")

    def test_negative_coverage_regression(self):
        x = mip.rollup([pulse(0, 40), pulse(1, 38)])
        self.assertEqual(x["control"], "REPAIR_COVERAGE_REGRESSION")

    def test_four_distinct_plateau_pulses(self):
        x = mip.rollup([pulse(i) for i in range(4)])
        self.assertEqual(x["control"], "STOP_LOCAL_PLATEAU")

    def test_unknown_roots_block_plateau(self):
        xs = [pulse(i, root_ids_open=None) for i in range(4)]
        self.assertNotEqual(mip.rollup(xs)["control"], "STOP_LOCAL_PLATEAU")

    def test_forecast_one_step(self):
        xs = [pulse(0), pulse(1, 14)]
        item = forecast(0, 1, 2, 7)
        score = mip.rollup(xs, [item])["frozen_forecast_scores"][0]
        self.assertEqual(score["actual_covered_delta"], 4)
        self.assertTrue(score["interval_hit"])

    def test_forecast_two_steps_uses_cumulative_delta(self):
        xs = [pulse(0), pulse(1, 13), pulse(2, 17)]
        item = forecast(0, 2, 6, 8)
        score = mip.rollup(xs, [item])["frozen_forecast_scores"][0]
        self.assertEqual(score["actual_covered_delta"], 7)
        self.assertTrue(score["interval_hit"])

    def test_hindsight_forecast_rejected(self):
        xs = [pulse(0), pulse(1)]
        item = forecast(0, 1, 0, 3, issued="12:01:30")
        with self.assertRaisesRegex(ValueError, "hindsight"):
            mip.rollup(xs, [item])

    def test_nonterminal_never_qualifies(self):
        p = pulse(0)
        p["native"]["terminal"] = False
        with self.assertRaisesRegex(ValueError, "nonterminal"):
            mip.rollup([p])

    def test_p95_sample_count_reported(self):
        x = mip.rollup([pulse(0)])
        self.assertEqual(x["p95_execution_seconds"], 15)
        self.assertEqual(x["execution_sample_count"], 1)


if __name__ == "__main__":
    unittest.main()
