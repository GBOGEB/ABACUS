"""MIP M1/M2/M3 native provenance and statistical maturity controls."""

import importlib.util
import unittest
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "scripts/mip_statistical_readiness.py"
spec = importlib.util.spec_from_file_location("mip_statistical_readiness", p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def row(i=1, numerator=1, denominator=1, quality="NATIVE"):
    return {
        "schema": "mip.stat.observation.v1",
        "repository": "GBOGEB/ABACUS",
        "family": "ci_reliability",
        "metric": "workflow_failure_rate",
        "metric_version": "1.0",
        "exact_sha": f"{i:040x}",
        "run_id": i,
        "job_id": i + 100,
        "observed_at": f"2026-10-{(i % 28)+1:02d}T12:00:00Z",
        "evidence_url": f"https://github.com/GBOGEB/ABACUS/actions/runs/{i}",
        "collection_quality": quality,
        "status": "FAIL" if numerator else "PASS",
        "numerator": numerator,
        "denominator": denominator,
    }


class ReadinessTests(unittest.TestCase):
    def test_no_evidence_never_certifies(self):
        result = mod.evaluate([])
        self.assertEqual(7, len(result["missing_families"]))
        self.assertEqual("HOLD", result["merge_admission"])

    def test_duplicate_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            mod.evaluate([row(), row()])

    def test_unknown_not_coerced_to_zero(self):
        r = row()
        r.update(status="UNKNOWN", numerator=None, denominator=None)
        result = mod.evaluate([r])
        self.assertEqual(0, result["series"][0]["native_marked_records"])
        self.assertFalse(result["series"][0]["MEASUREMENT_VALID"])

    def test_forged_receipt_rejected(self):
        r = row()
        r["evidence_url"] = "https://example.com/fake"
        with self.assertRaises(ValueError):
            mod.evaluate([r])

    def test_non_native_numeric_receipt_rejected(self):
        with self.assertRaises(ValueError):
            mod.evaluate([row(quality="UNVERIFIED")])

    def test_not_enough_independent_runs(self):
        result = mod.evaluate([row(i, numerator=i % 2) for i in range(1, 9)])
        x = result["series"][0]
        self.assertFalse(x["STABILITY_ASSESSABLE"])
        self.assertFalse(x["BACKTEST_ELIGIBLE"])

    def test_multiple_jobs_same_run_do_not_certify_independence(self):
        a, b = row(1), row(2)
        b["run_id"] = a["run_id"]
        b["evidence_url"] = a["evidence_url"]
        b["exact_sha"] = a["exact_sha"]
        result = mod.evaluate([a, b])
        self.assertFalse(result["series"][0]["MEASUREMENT_VALID"])

    def test_unequal_denominators_block_backtest(self):
        rows = [row(i, numerator=0, denominator=i + 1) for i in range(1, 31)]
        for r in rows:
            r.update(family="coverage", metric="statement_coverage")
        result = mod.evaluate(rows, minimum=20, holdout=5)
        self.assertFalse(result["series"][0]["BACKTEST_ELIGIBLE"])

    def test_full_history_still_not_auto_certified_process_stable(self):
        rows = [row(i, numerator=0) for i in range(1, 31)]
        result = mod.evaluate(rows, minimum=20, holdout=5)
        x = result["series"][0]
        self.assertFalse(x["STABILITY_ASSESSABLE"])
        self.assertFalse(x["PROCESS_STABLE"])
        self.assertFalse(x["CAPABILITY_ASSESSABLE"])
        self.assertFalse(x["BACKTEST_ELIGIBLE"])
        self.assertTrue(x["diagnostic_sample_threshold_met"])
        self.assertEqual(5, x["diagnostic_backtest"]["forecast_count"])


if __name__ == "__main__":
    unittest.main()
