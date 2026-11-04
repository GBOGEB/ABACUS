"""No-mutation positive and negative controls for CBD queue-gated rerun plans."""

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import cbd_rerun_wave_planner as p

SHA = "a" * 40
BASE = "b" * 40


def row(
    run=123,
    pr=2093,
    head=SHA,
    status="queued",
    conclusion=None,
    attempt=1,
    first_red=None,
):
    return dict(
        pr=pr,
        head_sha=head,
        run_id=run,
        attempt=attempt,
        workflow="CI/CD Test Suite",
        status=status,
        conclusion=conclusion,
        url=f"https://github.com/GBOGEB/ABACUS/actions/runs/{run}",
        first_red=first_red,
    )


def first(kind, run=123, sig="root"):
    return dict(
        kind=kind,
        verified=True,
        root_signature=sig,
        job_id=run + 9000,
        url=f"https://github.com/GBOGEB/ABACUS/actions/runs/{run}/job/{run+9000}",
    )


def sample(*runs):
    return dict(
        schema=p.SCHEMA,
        repository=p.REPO,
        base_sha=BASE,
        current_pr_heads={str(x["pr"]): x["head_sha"] for x in runs},
        capacity=dict(
            queued=0,
            in_progress=0,
            max_queued=40,
            max_in_progress=12,
            max_new_reruns=2,
            max_attempts=2,
        ),
        authority=copy.deepcopy(p.AUTHORITY),
        observations=list(runs),
    )


class RerunContract(unittest.TestCase):
    def test_queued_is_not_a_candidate(self):
        self.assertEqual(
            p.plan(sample(row()))["proposals"][0]["action"], "WAIT_TERMINAL"
        )

    def test_capacity_backpressure(self):
        x = sample(
            row(
                status="completed",
                conclusion="failure",
                first_red=first("transient_runner"),
            )
        )
        x["capacity"]["queued"] = 323
        x["capacity"]["in_progress"] = 7
        result = p.plan(x)
        self.assertTrue(result["backpressure"])
        self.assertEqual(result["proposed_reruns"], 0)
        self.assertEqual(result["proposals"][0]["action"], "BACKPRESSURE_HOLD")

    def test_transient_first_red_one_failed_jobs_candidate(self):
        x = sample(
            row(
                status="completed",
                conclusion="failure",
                first_red=first("transient_runner"),
            )
        )
        result = p.plan(x)
        self.assertEqual(result["proposals"][0]["action"], "RERUN_FAILED_JOBS")
        self.assertFalse(result["proposals"][0]["executed"])

    def test_verified_flake_is_job_specific(self):
        x = sample(
            row(
                status="completed",
                conclusion="failure",
                first_red=first("flake_candidate"),
            )
        )
        self.assertEqual(p.plan(x)["proposals"][0]["action"], "RERUN_ONE_JOB")

    def test_security_a10_governance_source_are_not_retried(self):
        for kind in ("security", "a10", "governance", "source"):
            with self.subTest(kind=kind):
                x = sample(
                    row(status="completed", conclusion="failure", first_red=first(kind))
                )
                self.assertEqual(p.plan(x)["proposals"][0]["action"], "REPAIR_SOURCE")

    def test_rate_limit_is_not_blind_retry(self):
        x = sample(
            row(status="completed", conclusion="failure", first_red=first("rate_limit"))
        )
        self.assertEqual(p.plan(x)["proposals"][0]["action"], "BACKOFF_RATE_LIMIT")

    def test_max_attempts(self):
        x = sample(
            row(
                status="completed",
                conclusion="failure",
                attempt=2,
                first_red=first("transient_runner"),
            )
        )
        self.assertEqual(p.plan(x)["proposals"][0]["action"], "RETRY_LIMIT")

    def test_unverified_first_red_not_authority(self):
        x = sample(row(status="completed", conclusion="failure"))
        result = p.plan(x)
        self.assertEqual(result["proposals"][0]["action"], "INSPECT_FIRST_RED")
        self.assertIsNone(result["coverage_main_delta"])
        self.assertIsNone(result["formal_bd_roots_closed"])
        self.assertIsNone(result["accepted_rex"])

    def test_stale_sha_never_reuses_green(self):
        x = sample(row(status="completed", conclusion="success"))
        x["current_pr_heads"]["2093"] = "c" * 40
        self.assertEqual(p.plan(x)["proposals"][0]["action"], "STALE_SOURCE")

    def test_shared_root_serial_canary(self):
        x = sample(
            row(
                status="completed",
                conclusion="failure",
                first_red=first("transient_runner", 123, "same"),
            ),
            row(
                run=124,
                pr=2094,
                head=BASE,
                status="completed",
                conclusion="failure",
                first_red=first("transient_runner", 124, "same"),
            ),
        )
        self.assertEqual(
            [y["action"] for y in p.plan(x)["proposals"]],
            ["RERUN_FAILED_JOBS", "WAIT_SHARED_ROOT_CANARY"],
        )

    def test_authority_forgery_rejected(self):
        for field, value in (
            ("merge_admission", "PASS"),
            ("security_waiver", True),
            ("authenticated_worker_dispatch", "CLAIMED"),
        ):
            x = sample(row())
            x["authority"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                p.plan(x)

    def test_duplicate_run_and_bad_job_url_rejected(self):
        with self.assertRaises(ValueError):
            p.plan(sample(row(), row()))
        x = sample(
            row(
                status="completed",
                conclusion="failure",
                first_red=first("transient_runner"),
            )
        )
        x["observations"][0]["first_red"]["url"] = "https://fake.example/"
        with self.assertRaises(ValueError):
            p.plan(x)

    def test_no_first_red_on_queued(self):
        with self.assertRaises(ValueError):
            p.plan(sample(row(first_red=first("source"))))

    def test_partial_transition(self):
        old = sample(row())
        new = sample(row(status="completed", conclusion="failure"))
        events = p.compare(old, new)
        self.assertEqual(events[0]["event"], "TERMINAL_TRANSITION")
        self.assertEqual(events[0]["allowed_downstream_action"], "RECHECK_ONLY")

    def test_first_red_change_is_observable(self):
        old = sample(row(status="completed", conclusion="failure"))
        new = sample(
            row(status="completed", conclusion="failure", first_red=first("security"))
        )
        self.assertEqual(p.compare(old, new)[0]["event"], "FIRST_RED_UPDATED")

    def test_same_input_no_new_shard(self):
        x = sample(row())
        self.assertEqual(p.compare(x, copy.deepcopy(x)), [])

    def test_terminal_history_immutable(self):
        old = sample(row(status="completed", conclusion="failure"))
        new = sample(row(status="completed", conclusion="success"))
        with self.assertRaises(ValueError):
            p.compare(old, new)

    def test_new_attempt_kept_separate(self):
        old = sample(row(status="completed", conclusion="failure"))
        new = sample(row(attempt=2))
        self.assertEqual(p.compare(old, new)[0]["event"], "NEW_ATTEMPT")

    def test_different_base_or_source_not_matched(self):
        old = sample(row())
        new = sample(row())
        new["base_sha"] = "c" * 40
        with self.assertRaises(ValueError):
            p.compare(old, new)
        new = sample(row(head="c" * 40))
        with self.assertRaises(ValueError):
            p.compare(old, new)

    def test_deterministic(self):
        x = sample(row())
        old = copy.deepcopy(x)
        self.assertEqual(p.plan(x), p.plan(x))
        self.assertEqual(x, old)


if __name__ == "__main__":
    unittest.main()


class W39InputHardening(unittest.TestCase):
    def test_queue_exactly_at_limit_holds_rerun(self):
        x = sample(
            row(
                status="completed",
                conclusion="failure",
                first_red=first("transient_runner"),
            )
        )
        x["capacity"]["queued"] = x["capacity"]["max_queued"]
        out = p.plan(x)
        self.assertEqual(out["proposed_reruns"], 0)
        self.assertEqual(out["proposals"][0]["action"], "BACKPRESSURE_HOLD")

    def test_workflow_identity_cannot_change_with_same_run(self):
        old = sample(row(status="completed", conclusion="failure"))
        new = copy.deepcopy(old)
        new["observations"][0]["workflow"] = "Security Scan"
        with self.assertRaisesRegex(ValueError, "workflow identity"):
            p.compare(old, new)

    def test_invalid_pr_identity_rejected(self):
        for bad in ("0", "02093", "-1", " 2093", "2093.0"):
            with self.subTest(bad=bad):
                x = sample(row())
                x["current_pr_heads"] = {bad: SHA}
                with self.assertRaises(ValueError):
                    p.plan(x)

    def test_non_string_source_identity_rejected(self):
        for bad in (None, True, 123, ["a" * 40]):
            with self.subTest(bad=bad):
                x = sample(row())
                x["current_pr_heads"]["2093"] = bad
                with self.assertRaises(ValueError):
                    p.plan(x)
