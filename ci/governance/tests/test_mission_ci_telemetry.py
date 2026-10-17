"""Fast native tests for CI telemetry; never impersonate GitHub evidence."""
import importlib.util
import pathlib
import unittest

SOURCE = pathlib.Path(__file__).resolve().parents[1] / "mission_ci_telemetry.py"
SPEC = importlib.util.spec_from_file_location("mission_ci_telemetry", SOURCE)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
SHA = "a" * 40


def run(ident=1, status="completed", conclusion="success"):
    return {"id": ident, "head_sha": SHA, "status": status,
            "conclusion": conclusion, "name": "MIP Coverage"}


def job(ident=1, run_id=1, status="completed"):
    return {"id": ident, "run_id": run_id, "status": status,
            "created_at": "2026-10-15T08:00:00Z",
            "started_at": "2026-10-15T08:00:10Z",
            "completed_at": "2026-10-15T08:00:40Z"}


class MissionTelemetryTests(unittest.TestCase):
    def test_provenance_holds_and_no_admission_credit(self):
        x = M.summarize("GBOGEB/ABACUS", SHA,
                        {"total_count": 1, "workflow_runs": [run()]},
                        {1: [job()]}, 10)
        self.assertFalse(x["merge_admitted"])
        self.assertEqual(x["provenance"], "LIVE_GITHUB_API_READ_ONLY")
        self.assertIsNone(x["coverage_delta_pp"])
        self.assertIsNone(x["distinct_root_closures"])

    def test_terminal_queue_runtime(self):
        out = M.job_metrics([job()])
        self.assertEqual(out["queue_total_s_sample"], 10.0)
        self.assertEqual(out["execution_total_s_sample"], 30.0)
        self.assertIsNone(out["queue_p95_s"])

    def test_five_terminal_jobs_enable_percentiles(self):
        jobs = [job(i + 1) for i in range(5)]
        out = M.job_metrics(jobs)
        self.assertEqual(out["queue_p50_s"], 10)
        self.assertEqual(out["queue_p95_s"], 10)
        self.assertEqual(out["peak_concurrent_jobs_sample"], 5)

    def test_skipped_job_does_not_pollute_latency(self):
        item = job(ident=2)
        item["conclusion"] = "skipped"
        item["started_at"] = item["created_at"]
        item["completed_at"] = item["created_at"]
        report = M.job_metrics([job(), item])
        self.assertEqual(report["skipped_jobs_excluded"], 1)
        self.assertEqual(report["terminal_jobs_with_queue"], 1)
        self.assertEqual(report["queue_total_s_sample"], 10)
        self.assertEqual(report["execution_total_s_sample"], 30)

    def test_pending_is_not_terminal_time(self):
        j = job(status="queued")
        out = M.job_metrics([j])
        self.assertIsNone(out["queue_total_s_sample"])
        self.assertIsNone(out["execution_total_s_sample"])

    def test_duplicate_jobs_rejected(self):
        j = job()
        with self.assertRaises(ValueError):
            M.job_metrics([j, dict(j)])

    def test_duplicate_runs_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate run ID"):
            M.summarize("GBOGEB/ABACUS", SHA,
                        {"total_count": 2, "workflow_runs": [run(), run()]},
                        {}, 10)

    def test_wrong_sha_rejected(self):
        x = run()
        x["head_sha"] = "b" * 40
        with self.assertRaisesRegex(ValueError, "source SHA mismatch"):
            M.summarize("GBOGEB/ABACUS", SHA,
                        {"total_count": 1, "workflow_runs": [x]}, {}, 10)

    def test_foreign_job_run_rejected(self):
        with self.assertRaisesRegex(ValueError, "cross-run job mismatch"):
            M.summarize("GBOGEB/ABACUS", SHA,
                        {"total_count": 1, "workflow_runs": [run()]},
                        {1: [job(run_id=9)]}, 10)

    def test_incomplete_run_page_flagged(self):
        out = M.summarize("GBOGEB/ABACUS", SHA,
                          {"total_count": 200, "workflow_runs": [run()]},
                          {}, 10)
        self.assertFalse(out["run_census_complete"])

    def test_invalid_repository_rejected(self):
        with self.assertRaises(ValueError):
            M.summarize("other/private", SHA,
                        {"total_count": 0, "workflow_runs": []}, {}, 10)

    def test_subsecond_negative_clock_invalid(self):
        self.assertIsNone(M.elapsed(
            "2026-10-15T08:00:40Z", "2026-10-15T08:00:10Z"))
        self.assertIsNone(M.elapsed("bad", "2026-10-15T08:00:10Z"))

    def test_name_taxonomy_is_only_hint(self):
        self.assertEqual(M.family("MIP Coverage"), "MIP")
        self.assertEqual(M.family("3PR Probe"), "THREE_P")
        self.assertEqual(M.family("Cryo build"), "OTHER")

    def test_snapshot_reads_bounded_jobs(self):
        urls = []
        def fake_get(url, token):
            urls.append(url)
            if url.endswith("/jobs?per_page=100"):
                return {"jobs": [job()]}
            return {"total_count": 1, "workflow_runs": [run()]}
        data = M.snapshot("GBOGEB/ABACUS", SHA, "fake", max_jobs_runs=1,
                          get=fake_get)
        self.assertEqual(len(urls), 2)
        self.assertEqual(data["job_metrics"]["sampled_jobs"], 1)

    def test_snapshot_enforces_bounded_sample(self):
        with self.assertRaises(ValueError):
            M.snapshot("GBOGEB/ABACUS", SHA, "fake", max_jobs_runs=41,
                       get=lambda *_: {})

    def test_markdown_calls_unknown_unknown(self):
        x = M.summarize("GBOGEB/ABACUS", SHA,
                        {"total_count": 1, "workflow_runs": [run()]},
                        {}, 10)
        text = M.make_markdown(x)
        self.assertIn("UNKNOWN", text)
        self.assertIn("no synthetic gains", text)


if __name__ == "__main__":
    unittest.main()
