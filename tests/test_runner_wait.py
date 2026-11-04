"""Negative controls for exact-head, right-censored queue and execution telemetry."""

import unittest

from mission_control_lite.runner_wait import summarize

SHA = "a" * 40
CUT = "2026-10-17T16:30:00Z"


def job(job_id=1, status="queued", **extra):
    row = {
        "run_id": 42,
        "job_id": job_id,
        "attempt": 1,
        "head_sha": SHA,
        "status": status,
        "conclusion": None,
        "job_created_at": "2026-10-17T16:20:00Z",
        "job_started_at": None,
        "job_completed_at": None,
    }
    if status == "in_progress":
        row["job_started_at"] = "2026-10-17T16:25:00Z"
    if status == "completed":
        row.update(
            job_started_at="2026-10-17T16:25:00Z",
            job_completed_at="2026-10-17T16:27:00Z",
            conclusion="success",
        )
    row.update(extra)
    return row


class RunnerWaitTests(unittest.TestCase):
    def test_right_censored_queued_job_not_zero_wait(self):
        result = summarize(SHA, CUT, [job()])
        self.assertEqual(result["runner_wait_observed_n"], 0)
        self.assertEqual(result["runner_wait_right_censored_n"], 1)
        self.assertEqual(result["runner_wait_censored_lower_bound_max_seconds"], 600)
        self.assertIsNone(result["runner_wait_p95_nearest_rank_seconds"])
        self.assertEqual(result["merge_admission"], "HOLD")

    def test_running_and_completed_keep_execution_censoring_separate(self):
        out = summarize(SHA, CUT, [job(1, "in_progress"), job(2, "completed")])
        self.assertEqual(out["runner_wait_p50_nearest_rank_seconds"], 300)
        self.assertEqual(out["runner_wait_p95_nearest_rank_seconds"], 300)
        self.assertEqual(out["execution_completed_n"], 1)
        self.assertEqual(out["execution_right_censored_n"], 1)
        self.assertEqual(out["execution_p95_completed_only_seconds"], 120)
        self.assertFalse(out["runner_wait_p95_qualified"])

    def test_p95_requires_twenty_measured_jobs_and_no_censoring(self):
        data = [job(i, "completed") for i in range(1, 21)]
        out = summarize(SHA, CUT, data)
        self.assertTrue(out["runner_wait_p95_qualified"])
        self.assertEqual(out["runner_wait_observed_n"], 20)
        out = summarize(SHA, CUT, data + [job(21, "queued")])
        self.assertFalse(out["runner_wait_p95_qualified"])

    def test_unordered_inputs_are_deterministic(self):
        a, b, c = job(3, "completed"), job(1), job(2, "in_progress")
        self.assertEqual(summarize(SHA, CUT, [a, b, c]), summarize(SHA, CUT, [c, a, b]))

    def test_head_drift_rejected(self):
        with self.assertRaisesRegex(ValueError, "head drift"):
            summarize(SHA, CUT, [job(head_sha="b" * 40)])

    def test_bad_sha_and_bad_cutoff_rejected(self):
        with self.assertRaisesRegex(ValueError, "canonical"):
            summarize("short", CUT, [])
        with self.assertRaisesRegex(ValueError, "naive"):
            summarize(SHA, "2026-10-17T16:30:00", [])

    def test_malformed_timestamp_and_missing_timestamp_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid timestamp"):
            summarize(SHA, "2026-99-99T99:99:99Z", [])
        with self.assertRaisesRegex(ValueError, "missing timestamp"):
            summarize(SHA, CUT, [job(job_created_at=None)])
        with self.assertRaisesRegex(ValueError, "naive timestamp"):
            summarize(SHA, CUT, [job(job_created_at="2026-10-17T16:20:00")])

    def test_duplicate_identity_and_invalid_bool_id_rejected(self):
        row = job()
        with self.assertRaisesRegex(ValueError, "duplicate"):
            summarize(SHA, CUT, [row, row])
        with self.assertRaisesRegex(ValueError, "invalid job ID"):
            summarize(SHA, CUT, [job(job_id=True)])

    def test_future_creation_rejected(self):
        with self.assertRaisesRegex(ValueError, "after observation cutoff"):
            summarize(SHA, CUT, [job(job_created_at="2026-10-17T16:40:00Z")])

    def test_impossible_start_order_rejected(self):
        with self.assertRaisesRegex(ValueError, "impossible job start"):
            summarize(
                SHA,
                CUT,
                [job(status="completed", job_started_at="2026-10-17T16:15:00Z")],
            )

    def test_impossible_completion_order_rejected(self):
        with self.assertRaisesRegex(ValueError, "impossible completion"):
            summarize(
                SHA,
                CUT,
                [job(status="completed", job_completed_at="2026-10-17T16:35:00Z")],
            )

    def test_queued_with_start_or_terminal_result_rejected(self):
        with self.assertRaisesRegex(ValueError, "queued job cannot"):
            summarize(SHA, CUT, [job(job_started_at="2026-10-17T16:24:00Z")])
        with self.assertRaisesRegex(ValueError, "nonterminal conclusion"):
            summarize(SHA, CUT, [job(conclusion="success")])

    def test_nonterminal_completion_and_terminal_missing_conclusion_rejected(self):
        with self.assertRaisesRegex(ValueError, "running job cannot"):
            summarize(
                SHA,
                CUT,
                [job(status="in_progress", job_completed_at="2026-10-17T16:27:00Z")],
            )
        with self.assertRaisesRegex(ValueError, "missing terminal conclusion"):
            summarize(SHA, CUT, [job(status="completed", conclusion=None)])

    def test_invalid_job_objects_and_unknown_status_rejected(self):
        with self.assertRaisesRegex(ValueError, "jobs must be"):
            summarize(SHA, CUT, {})
        with self.assertRaisesRegex(ValueError, "job must be"):
            summarize(SHA, CUT, [None])
        with self.assertRaisesRegex(ValueError, "unsupported job status"):
            summarize(SHA, CUT, [job(status="starting")])

    def test_zero_denominator_does_not_pass(self):
        out = summarize(SHA, CUT, [])
        self.assertEqual(out["observations"], 0)
        self.assertIsNone(out["runner_wait_p95_nearest_rank_seconds"])
        self.assertEqual(out["merge_admission"], "HOLD")


if __name__ == "__main__":
    unittest.main()
