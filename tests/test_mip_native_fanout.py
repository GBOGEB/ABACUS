"""Native wave-pulse telemetry is read-only and fails closed."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.mip2 import mip_native_fanout as fanout

SHA = "a" * 40


def fixture(run_id=100, durations=((0, 10), (5, 15))):
    run = {
        "id": run_id, "head_sha": SHA, "status": "completed",
        "repository": {"full_name": "GBOGEB/ABACUS"},
    }
    jobs = []
    for index, (start, end) in enumerate(durations, 1):
        jobs.append({
            "id": run_id * 100 + index,
            "run_id": run_id,
            "name": f"DAB proposal worker {index:03}",
            "status": "completed", "conclusion": "success",
            "started_at": f"2026-10-15T08:00:{start:02d}Z",
            "completed_at": f"2026-10-15T08:00:{end:02d}Z",
        })
    return run, {"total_count": len(jobs), "jobs": jobs}


class NativeFanoutTests(unittest.TestCase):
    def test_measures_overlapping_worker_intervals(self):
        run, jobs = fixture()
        report = fanout.observe(run, jobs)
        self.assertEqual(report["worker_count"], 2)
        self.assertEqual(report["successful_workers"], 2)
        self.assertEqual(report["summed_job_seconds"], 20)
        self.assertEqual(report["first_to_last_seconds"], 15)
        self.assertEqual(report["idle_gap_seconds"], 0)
        self.assertEqual(report["peak_concurrency"], 2)
        self.assertAlmostEqual(report["overlap_factor"], 1.3333, places=3)
        self.assertIsNone(report["authenticated_crew_dispatches"])

    def test_detects_gaps_and_peak(self):
        run, jobs = fixture(durations=((0, 10), (15, 25)))
        report = fanout.observe(run, jobs)
        self.assertEqual(report["idle_gap_seconds"], 5)
        self.assertEqual(report["peak_concurrency"], 1)
        self.assertEqual(report["first_to_last_seconds"], 25)

    def test_nonterminal_run_is_not_proof(self):
        run, jobs = fixture()
        run["status"] = "in_progress"
        with self.assertRaisesRegex(ValueError, "nonterminal"):
            fanout.observe(run, jobs)

    def test_duplicate_job_ids_are_rejected(self):
        run, jobs = fixture()
        jobs["jobs"][1]["id"] = jobs["jobs"][0]["id"]
        with self.assertRaisesRegex(ValueError, "duplicate job"):
            fanout.observe(run, jobs)

    def test_truncated_job_list_not_zero(self):
        run, jobs = fixture()
        jobs["total_count"] = 3
        with self.assertRaisesRegex(ValueError, "truncated"):
            fanout.observe(run, jobs)

    def test_rejects_sha_and_repository_mismatch(self):
        run, jobs = fixture()
        run["head_sha"] = "not-sha"
        with self.assertRaisesRegex(ValueError, "invalid SHA"):
            fanout.observe(run, jobs)
        run["head_sha"] = SHA
        run["repository"]["full_name"] = "GBOGEB/CODEX"
        with self.assertRaisesRegex(ValueError, "repository"):
            fanout.observe(run, jobs)

    def test_rejects_wrong_run_id_or_time(self):
        run, jobs = fixture()
        jobs["jobs"][0]["run_id"] = 200
        with self.assertRaisesRegex(ValueError, "job-run"):
            fanout.observe(run, jobs)
        jobs["jobs"][0]["run_id"] = 100
        jobs["jobs"][0]["completed_at"] = "2026-10-15T07:00:00Z"
        with self.assertRaisesRegex(ValueError, "negative worker"):
            fanout.observe(run, jobs)

    def test_no_worker_population_is_not_comparable(self):
        run, jobs = fixture()
        for job in jobs["jobs"]:
            job["name"] = "Unrelated unit test"
        with self.assertRaisesRegex(ValueError, "no DAB"):
            fanout.observe(run, jobs)

    def test_comparison_requires_two_distinct_real_runs(self):
        a = fanout.observe(*fixture(100))
        b = fanout.observe(*fixture(101, ((0, 8), (15, 25))))
        comparison = fanout.compare(a, b)
        self.assertEqual(comparison["delta"]["idle_gap_seconds"], 7)
        self.assertEqual(comparison["admission"], "HOLD")
        self.assertIsNone(comparison["operational_root_closure"])
        with self.assertRaisesRegex(ValueError, "distinct runs"):
            fanout.compare(a, a)

    def test_rendering_offline_and_escapes_strings(self):
        a = fanout.observe(*fixture(100))
        b = fanout.observe(*fixture(101))
        b["run_url"] = "https://example.com/<script>alert(1)</script>"
        report = fanout.compare(a, b)
        output = fanout.render_html(report)
        self.assertIn("&lt;script&gt;", output)
        self.assertNotIn("<script>", output)
        self.assertIn("offline", fanout.render_markdown(report).lower()
                      + " offline")
        self.assertIn("UNKNOWN", fanout.render_markdown(report))

    def test_cli_generates_three_synchronized_surfaces(self):
        a, aj = fixture(100)
        b, bj = fixture(101, ((0, 10), (20, 30)))
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            for name, item in (
                ("a-run.json", a), ("a-jobs.json", aj),
                ("b-run.json", b), ("b-jobs.json", bj),
            ):
                (folder / name).write_text(json.dumps(item))
            args = [
                "mip_native_fanout.py",
                "--previous-run", str(folder / "a-run.json"),
                "--previous-jobs", str(folder / "a-jobs.json"),
                "--current-run", str(folder / "b-run.json"),
                "--current-jobs", str(folder / "b-jobs.json"),
                "--output-dir", str(folder / "out"),
            ]
            with patch.object(sys, "argv", args):
                fanout.main()
            for suffix in ("json", "md", "html"):
                self.assertTrue(
                    (folder / "out" / f"mip_native_fanout.{suffix}").is_file()
                )
            report = json.loads(
                (folder / "out" / "mip_native_fanout.json").read_text()
            )
            self.assertEqual(report["delta"]["idle_gap_seconds"], 10)
            self.assertEqual(len(report["api_input_sha256"]), 4)
            self.assertTrue(all(len(digest) == 64 for digest in
                                report["api_input_sha256"].values()))
            self.assertEqual(report["api_input_integrity"],
                             "HASHED_LOCAL_INPUT_NOT_SIGNED_AUTHORITY")


if __name__ == "__main__":
    unittest.main()
