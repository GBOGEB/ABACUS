"""Negative and real-timestamp fixture controls for GitHub CI latency."""

import copy
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from ci_latency import cohort, distribution, measure_run, percentile

A = "a" * 40


def fixture():
    run = {
        "id": 38539036478,
        "run_attempt": 1,
        "name": "Bandit Disjoint Census",
        "event": "pull_request",
        "head_sha": A,
        "repository": {"full_name": "GBOGEB/ABACUS"},
        "status": "completed",
        "conclusion": "success",
        "created_at": "2026-10-14T08:59:12Z",
        "updated_at": "2026-10-14T09:07:35Z",
    }
    job = {
        "id": 115768951567,
        "run_id": run["id"],
        "run_attempt": 1,
        "head_sha": A,
        "name": "census",
        "status": "completed",
        "conclusion": "success",
        "created_at": "2026-10-14T08:59:13Z",
        "started_at": "2026-10-14T09:06:53Z",
        "completed_at": "2026-10-14T09:07:35Z",
        "steps": [
            {
                "name": "Install scanner and test runner",
                "started_at": "2026-10-14T09:07:00Z",
                "completed_at": "2026-10-14T09:07:07Z",
            },
            {
                "name": "Regression contracts",
                "started_at": "2026-10-14T09:07:07Z",
                "completed_at": "2026-10-14T09:07:11Z",
            },
        ],
    }
    return run, [job]


class NativeLatency(unittest.TestCase):
    def test_native_503_second_reconciliation(self):
        run, jobs = fixture()
        r = measure_run(run, jobs, "GBOGEB/ABACUS", A)
        self.assertEqual(r["state"], "MEASURED")
        self.assertEqual(r["workflow_wall_seconds"], 503)
        self.assertEqual(r["pre_first_job_seconds"], 461)
        self.assertEqual(r["jobs"][0]["queue_seconds"], 460)
        self.assertEqual(r["runner_sum_seconds"], 42)
        self.assertEqual(r["active_union_seconds"], 42)
        self.assertEqual(r["step_stage_seconds"]["dependency_install"], 7)
        self.assertEqual(r["step_stage_seconds"]["test"], 4)
        self.assertIsNone(r["cache_hit"])
        self.assertFalse(r["merge_authorized"])

    def test_independent_mip_fixture_time(self):
        run, jobs = fixture()
        run["id"] = 44
        run["name"] = "MIP Wave Pulse Native Testflight"
        run["created_at"] = "2026-10-15T07:27:56Z"
        run["updated_at"] = "2026-10-15T07:28:10Z"
        jobs[0].update(
            {
                "run_id": 44,
                "id": 55,
                "created_at": "2026-10-15T07:27:56Z",
                "started_at": "2026-10-15T07:27:59Z",
                "completed_at": "2026-10-15T07:28:10Z",
                "steps": [],
            }
        )
        r = measure_run(run, jobs, "GBOGEB/ABACUS", A)
        self.assertEqual(
            (
                r["workflow_wall_seconds"],
                r["jobs"][0]["queue_seconds"],
                r["runner_sum_seconds"],
            ),
            (14, 3, 11),
        )

    def test_duplicate_job_rejected(self):
        run, jobs = fixture()
        with self.assertRaisesRegex(ValueError, "duplicate"):
            measure_run(run, jobs + jobs, "GBOGEB/ABACUS", A)

    def test_forged_run_source_rejected(self):
        run, jobs = fixture()
        run["head_sha"] = "b" * 40
        with self.assertRaisesRegex(ValueError, "exact-head"):
            measure_run(run, jobs, "GBOGEB/ABACUS", A)

    def test_cross_run_and_attempt_rejected(self):
        run, jobs = fixture()
        jobs[0]["run_id"] += 1
        with self.assertRaisesRegex(ValueError, "cross-run"):
            measure_run(run, jobs, "GBOGEB/ABACUS", A)
        jobs[0]["run_id"] = run["id"]
        jobs[0]["run_attempt"] += 1
        with self.assertRaisesRegex(ValueError, "cross-attempt"):
            measure_run(run, jobs, "GBOGEB/ABACUS", A)

    def test_missing_job_timestamp_is_unknown_not_zero(self):
        run, jobs = fixture()
        jobs[0]["created_at"] = None
        item = measure_run(run, jobs, "GBOGEB/ABACUS", A)
        self.assertEqual(item["state"], "PARTIAL")
        self.assertIsNone(item["jobs"][0]["queue_seconds"])
        self.assertIsNone(item["runner_sum_seconds"])

    def test_nonterminal_run_rejected(self):
        run, jobs = fixture()
        run["status"] = "in_progress"
        with self.assertRaisesRegex(ValueError, "nonterminal"):
            measure_run(run, jobs, "GBOGEB/ABACUS", A)

    def test_invalid_step_does_not_fabricate_stage_time(self):
        run, jobs = fixture()
        jobs[0]["steps"][0]["completed_at"] = "2026-10-14T10:00:00Z"
        item = measure_run(run, jobs, "GBOGEB/ABACUS", A)
        self.assertEqual(item["state"], "PARTIAL")
        self.assertNotIn("dependency_install", item["step_stage_seconds"])

    def test_parallel_jobs_union_is_not_sum(self):
        run, jobs = fixture()
        second = copy.deepcopy(jobs[0])
        second["id"] = 77
        second["steps"] = []
        item = measure_run(run, jobs + [second], "GBOGEB/ABACUS", A)
        self.assertEqual(item["runner_sum_seconds"], 84)
        self.assertEqual(item["active_union_seconds"], 42)

    def test_quantile_linear_interpolation(self):
        self.assertEqual(percentile([1, 2, 3, 4, 5], 0.5), 3)
        self.assertEqual(percentile([0, 100], 0.95), 95)
        self.assertEqual(distribution([0, 100])["p99"], 99)
        self.assertFalse(distribution([0, 100])["p99_tail_qualified"])

    def test_empty_distribution_unknown(self):
        self.assertIsNone(distribution([])["p95"])
        self.assertEqual(distribution([])["n"], 0)

    def test_malformed_numeric_rejected(self):
        for samples in ([True], [float("nan")], [-1]):
            with self.assertRaisesRegex(ValueError, "invalid duration"):
                distribution(samples)

    def test_small_sample_pca_unqualified(self):
        run, jobs = fixture()
        item = measure_run(run, jobs, "GBOGEB/ABACUS", A)
        a = cohort([item])
        self.assertEqual(a["pca"]["owner_decision"], "DEFER")
        self.assertEqual(a["workflow_wall"]["median"], 503)
        self.assertFalse(a["queue"]["p95_tail_qualified"])

    def test_mixed_workflow_not_pooled(self):
        run, jobs = fixture()
        item = measure_run(run, jobs, "GBOGEB/ABACUS", A)
        other = copy.deepcopy(item)
        other["workflow"] = "different"
        self.assertEqual(cohort([item, other])["status"], "INCOMPARABLE_COHORT")

    def test_repeated_run_attempt_rejected(self):
        run, jobs = fixture()
        item = measure_run(run, jobs, "GBOGEB/ABACUS", A)
        with self.assertRaisesRegex(ValueError, "duplicate run attempt"):
            cohort([item, item])


if __name__ == "__main__":
    unittest.main()
