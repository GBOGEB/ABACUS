"""Negative and positive controls for terminal first-red census."""

import unittest

from mission_control_lite.job_first_red import summarize

SHA = "a" * 40


def make_job(job_id, conclusion="failure", step=None, run_id=1):
    steps = []
    if step is not None:
        steps = [
            {
                "number": 1,
                "name": "checkout",
                "status": "completed",
                "conclusion": "success",
            },
            {"number": 2, "name": step, "status": "completed", "conclusion": "failure"},
        ]
    return {
        "id": job_id,
        "run_id": run_id,
        "name": "security",
        "status": "completed",
        "conclusion": conclusion,
        "steps": steps,
    }


class FirstRedCensusTests(unittest.TestCase):
    def test_shared_first_red_is_candidate_not_root(self):
        report = summarize(
            SHA,
            {1: SHA, 2: SHA},
            [
                make_job(11, step="bandit"),
                make_job(12, step="bandit", run_id=2),
                make_job(13),
                make_job(14, conclusion="success"),
            ],
        )
        self.assertEqual(report["failed_jobs"], 3)
        self.assertEqual(report["first_red_observed_jobs"], 2)
        self.assertEqual(report["first_red_unknown_jobs"], 1)
        self.assertAlmostEqual(report["first_red_observed_fraction"], 2 / 3)
        self.assertEqual(report["candidate_groups"][0]["manifestations"], 2)
        self.assertFalse(report["root_cause_confirmed"])
        self.assertEqual(report["merge_admission"], "HOLD")

    def test_empty_fail_denominator_is_unknown(self):
        report = summarize(SHA, {1: SHA}, [make_job(1, conclusion="success")])
        self.assertIsNone(report["first_red_observed_fraction"])

    def test_moving_head_rejected(self):
        with self.assertRaisesRegex(ValueError, "run-head drift"):
            summarize(SHA, {1: "b" * 40}, [])

    def test_missing_run_or_duplicate_job_rejected(self):
        with self.assertRaisesRegex(ValueError, "unbound"):
            summarize(SHA, {}, [make_job(1)])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            summarize(SHA, {1: SHA}, [make_job(1), make_job(1)])

    def test_nonterminal_job_rejected(self):
        job = make_job(1)
        job["status"] = "in_progress"
        with self.assertRaisesRegex(ValueError, "nonterminal"):
            summarize(SHA, {1: SHA}, [job])

    def test_duplicate_step_rejected(self):
        job = make_job(1, step="test")
        job["steps"][1]["number"] = 1
        with self.assertRaisesRegex(ValueError, "duplicate step"):
            summarize(SHA, {1: SHA}, [job])

    def test_nonterminal_first_red_rejected(self):
        job = make_job(1, step="test")
        job["steps"][1]["status"] = "in_progress"
        with self.assertRaisesRegex(ValueError, "nonterminal failed"):
            summarize(SHA, {1: SHA}, [job])

    def test_stale_job_is_terminal_but_not_failed(self):
        report = summarize(SHA, {1: SHA}, [make_job(1, conclusion="stale")])
        self.assertEqual(report["terminal_jobs"], 1)
        self.assertEqual(report["failed_jobs"], 0)
        self.assertEqual(report["records"][0]["result"], "stale")

    def test_nonpositive_run_ids_rejected(self):
        for run_id in (0, -1):
            with self.subTest(run_id=run_id):
                with self.assertRaisesRegex(ValueError, "invalid run-head mapping"):
                    summarize(SHA, {run_id: SHA}, [])
                with self.assertRaisesRegex(ValueError, "invalid run-head mapping"):
                    summarize(
                        SHA, {run_id: SHA}, [make_job(1, step="test", run_id=run_id)]
                    )

    def test_canonical_sha_rejected(self):
        with self.assertRaisesRegex(ValueError, "canonical"):
            summarize(SHA.upper().replace("A", "G"), {1: SHA}, [])
