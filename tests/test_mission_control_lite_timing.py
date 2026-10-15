import json
import sys
import tempfile
import unittest
from pathlib import Path

from mission_control_lite.timing_pulse import completed_run_metrics, measure

SHA = "a" * 40


def sample():
    run = {
        "id": 17, "head_sha": SHA, "status": "completed",
        "created_at": "2026-10-15T00:00:00Z",
        "run_started_at": "2026-10-15T00:02:30Z",
        "updated_at": "2026-10-15T00:02:53Z",
    }
    job = {
        "id": 19, "run_id": 17, "status": "completed",
        "started_at": "2026-10-15T00:02:45Z",
        "completed_at": "2026-10-15T00:02:52Z",
        "steps": [{"name": "tests", "conclusion": "success",
                   "started_at": "2026-10-15T00:02:47Z",
                   "completed_at": "2026-10-15T00:02:48Z"}],
    }
    return run, job


class TimingPulseTests(unittest.TestCase):
    def test_wall_time_decomposition(self):
        run, job = sample()
        result = completed_run_metrics(run, job)
        self.assertEqual(result["wall_seconds"], 173)
        self.assertEqual(result["run_queue_seconds"], 150)
        self.assertEqual(result["run_to_job_seconds"], 15)
        self.assertEqual(result["job_seconds"], 7)
        self.assertEqual(result["finalization_seconds"], 1)
        self.assertEqual(result["non_job_seconds"], 166)
        self.assertEqual(result["steps"][0]["seconds"], 1)
        self.assertEqual(result["merge_admission"], "HOLD")

    def test_nonterminal_wrong_run_and_unordered_rejected(self):
        run, job = sample()
        for change in (
            ("job", "run_id", 99),
            ("run", "status", "queued"),
            ("run", "run_started_at", "2026-10-14T23:59:00Z"),
            ("job", "completed_at", "2026-10-15T00:02:00Z"),
        ):
            a, b = json.loads(json.dumps(run)), json.loads(json.dumps(job))
            target = a if change[0] == "run" else b
            target[change[1]] = change[2]
            with self.subTest(change=change), self.assertRaises(ValueError):
                completed_run_metrics(a, b)

    def test_measure_persists_success_and_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "steps.json"
            ok = measure(path, "ok", [sys.executable, "-c", "pass"])
            bad = measure(path, "fail", [
                sys.executable, "-c", "raise SystemExit(3)"
            ])
            self.assertEqual((ok, bad), (0, 3))
            rows = json.loads(path.read_text())
            self.assertEqual([row["exit_code"] for row in rows], [0, 3])
            self.assertTrue(all(row["duration_seconds"] >= 0 for row in rows))
            with self.assertRaises(ValueError):
                measure(path, "ok", [sys.executable, "-c", "pass"])


if __name__ == "__main__":
    unittest.main()
