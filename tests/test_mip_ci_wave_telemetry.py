"""Native telemetry controls for identities, timing, width and depth."""

import pytest

from tools.mip_ci_wave_telemetry import TERMINAL_CONCLUSIONS, summarize

SHA = "a" * 40


def run(
    identity=101,
    *,
    attempt=1,
    created_at="2026-10-15T08:00:00Z",
    status="completed",
    conclusion="success",
    name="CI",
):
    """Construct a native workflow-run-shaped fixture."""
    return {
        "id": identity,
        "run_attempt": attempt,
        "head_sha": SHA,
        "created_at": created_at,
        "status": status,
        "conclusion": conclusion,
        "name": name,
    }


def job(
    identity=1,
    *,
    conclusion="success",
    status="completed",
    started_at="2026-10-15T08:01:00Z",
    completed_at="2026-10-15T08:03:00Z",
    created_at=None,
    steps_marker=None,
    runner_id=None,
):
    """Construct a native job-shaped fixture."""
    item = {
        "id": identity,
        "run_id": 101,
        "run_attempt": 1,
        "head_sha": SHA,
        "status": status,
        "conclusion": conclusion,
        "started_at": started_at,
        "completed_at": completed_at,
    }
    if created_at is not None:
        item["created_at"] = created_at
    if steps_marker is not None:
        item["steps"] = steps_marker
    if runner_id is not None:
        item["runner_id"] = runner_id
    return item


def step(name, conclusion="success", status="completed"):
    return {"name": name, "status": status, "conclusion": conclusion}


def test_measured_duration_and_unknown_authority():
    """Fallback to run creation without manufacturing Crew evidence."""
    result = summarize({"source_sha": SHA, "runs": [run()], "jobs": [job()]})
    assert result["terminal_by_outcome"]["success"] == 1
    assert result["workflow_terminal_by_outcome"]["success"] == 1
    assert result["workflow_records_observed"] == 1
    assert result["workflow_names_observed"] == 1
    assert result["queue_seconds_p95"] == 60
    assert result["queue_source_counts"]["workflow_run_created_at_fallback"] == 1
    assert result["runtime_seconds_sum"] == 120
    assert result["runtime_seconds_p50"] == 120
    assert result["runtime_seconds_p95"] == 120
    assert result["runtime_wall_span_seconds"] == 120
    assert result["peak_runtime_concurrency_observed"] == 1
    assert result["realized_parallelism_factor"] == 1
    assert result["crew_dispatch_authenticated"] is None
    assert result["rex_receipts_accepted"] is None
    assert result["independent_process_observations"] is None


def test_native_job_created_at_is_preferred_for_queue_latency():
    """Use the native job queue timestamp when GitHub supplies it."""
    result = summarize(
        {
            "source_sha": SHA,
            "runs": [run(created_at="2026-10-15T07:50:00Z")],
            "jobs": [job(created_at="2026-10-15T08:00:30Z")],
        }
    )
    assert result["queue_seconds_p50"] == 30
    assert result["queue_source_counts"]["job_created_at"] == 1
    assert result["queue_source_counts"]["workflow_run_created_at_fallback"] == 0


def test_width_depth_runner_and_parallelism_metrics():
    """Measure native structural fan-out without calling it process independence."""
    jobs = [
        job(
            1,
            created_at="2026-10-15T08:00:30Z",
            started_at="2026-10-15T08:01:00Z",
            completed_at="2026-10-15T08:03:00Z",
            steps_marker=[step("checkout"), step("pytest")],
            runner_id=501,
        ),
        job(
            2,
            conclusion="failure",
            created_at="2026-10-15T08:01:00Z",
            started_at="2026-10-15T08:01:30Z",
            completed_at="2026-10-15T08:02:30Z",
            steps_marker=[
                step("checkout"),
                step("negative-control", conclusion="failure"),
            ],
            runner_id=502,
        ),
    ]
    result = summarize({"source_sha": SHA, "runs": [run()], "jobs": jobs})

    assert result["jobs_observed"] == 2
    assert result["job_run_groups_observed"] == 1
    assert result["jobs_per_run_p50"] == 2
    assert result["jobs_per_run_p95"] == 2
    assert result["jobs_per_run_max"] == 2
    assert result["terminal_by_outcome"]["success"] == 1
    assert result["terminal_by_outcome"]["failure"] == 1

    assert result["step_detail_jobs_observed"] == 2
    assert result["steps_observed"] == 4
    assert result["steps_per_job_p50"] == 2
    assert result["steps_per_job_max"] == 2
    assert result["step_terminal_by_outcome"]["success"] == 3
    assert result["step_terminal_by_outcome"]["failure"] == 1

    assert result["native_runner_assignments_observed"] == 2
    assert result["native_runner_ids_observed"] == 2
    assert result["runtime_seconds_sum"] == 180
    assert result["runtime_seconds_p50"] == 90
    assert result["runtime_seconds_p95"] == 120
    assert result["runtime_wall_span_seconds"] == 120
    assert result["peak_runtime_concurrency_observed"] == 2
    assert result["realized_parallelism_factor"] == 1.5
    assert result["independent_process_observations"] is None


def test_absent_step_detail_is_unknown_not_zero():
    result = summarize({"source_sha": SHA, "runs": [run()], "jobs": [job()]})
    assert result["step_detail_jobs_observed"] == 0
    assert result["steps_observed"] is None
    assert result["step_terminal_by_outcome"] is None
    assert result["step_nonterminal"] is None


def test_native_job_without_joined_run_keeps_queue_unknown():
    """REST jobs alone do not provide a workflow fallback if created_at is absent."""
    result = summarize({"source_sha": SHA, "jobs": [job()]})
    assert result["queue_samples"] == 0
    assert result["queue_seconds_p50"] is None
    assert result["queue_seconds_p95"] is None
    assert result["runtime_seconds_sum"] == 120
    assert result["workflow_terminal_by_outcome"] is None


def test_nonterminal_is_not_a_failed_or_finished_job():
    """Queue-only observations do not contribute durations."""
    result = summarize(
        {
            "source_sha": SHA,
            "runs": [run()],
            "jobs": [job(status="queued", conclusion=None)],
        }
    )
    assert result["nonterminal"] == 1
    assert result["runtime_seconds_sum"] is None
    assert result["queue_seconds_p95"] is None


def test_workflow_nonterminal_is_not_failure():
    result = summarize(
        {
            "source_sha": SHA,
            "runs": [run(status="queued", conclusion=None)],
            "jobs": [],
        }
    )
    assert result["workflow_nonterminal"] == 1
    assert result["workflow_terminal_by_outcome"]["failure"] == 0


def test_unobserved_completed_duration_is_unknown():
    """Do not infer elapsed seconds for missing source timestamps."""
    item = job()
    item["started_at"] = None
    result = summarize({"source_sha": SHA, "runs": [run()], "jobs": [item]})
    assert result["runtime_seconds_sum"] is None
    assert result["runtime_wall_span_seconds"] is None
    assert result["realized_parallelism_factor"] is None
    assert result["queue_seconds_p95"] is None


def test_cancelled_run_is_censored_from_runtime_but_counted():
    """A cancelled job is terminal evidence, but not runtime throughput."""
    result = summarize(
        {
            "source_sha": SHA,
            "runs": [run()],
            "jobs": [job(conclusion="cancelled")],
        }
    )
    assert result["terminal_by_outcome"]["cancelled"] == 1
    assert result["runtime_seconds_sum"] is None
    assert result["queue_seconds_p95"] == 60


@pytest.mark.parametrize("conclusion", TERMINAL_CONCLUSIONS)
def test_all_native_terminal_conclusions_are_classified(conclusion):
    """Native terminal states are observations, not parser failures."""
    result = summarize(
        {
            "source_sha": SHA,
            "runs": [run()],
            "jobs": [job(conclusion=conclusion)],
        }
    )
    assert result["terminal_by_outcome"][conclusion] == 1


@pytest.mark.parametrize(
    "mutation",
    [
        {"head_sha": "b" * 40},
        {"id": None},
        {"run_attempt": None},
        {"conclusion": "unknown"},
        {"status": "made_up"},
    ],
)
def test_bad_identity_status_or_result_fails_closed(mutation):
    """Reject records that cannot be authenticated or classified."""
    item = job()
    item.update(mutation)
    with pytest.raises(ValueError):
        summarize({"source_sha": SHA, "runs": [run()], "jobs": [item]})


def test_bad_step_state_fails_closed():
    item = job(steps_marker=[step("bad", conclusion="made_up")])
    with pytest.raises(ValueError, match="step conclusion"):
        summarize({"source_sha": SHA, "runs": [run()], "jobs": [item]})


def test_nonterminal_job_cannot_claim_terminal_conclusion():
    item = job(status="in_progress", conclusion="success")
    with pytest.raises(ValueError, match="nonterminal"):
        summarize({"source_sha": SHA, "runs": [run()], "jobs": [item]})


def test_nonterminal_workflow_cannot_claim_terminal_conclusion():
    with pytest.raises(ValueError, match="nonterminal workflow"):
        summarize(
            {
                "source_sha": SHA,
                "runs": [run(status="queued", conclusion="success")],
                "jobs": [],
            }
        )


def test_duplicate_job_identity_rejected():
    """Multiple appearances of one native run/job cannot inflate counts."""
    with pytest.raises(ValueError, match="duplicate"):
        summarize({"source_sha": SHA, "runs": [run()], "jobs": [job(), job()]})


def test_duplicate_run_identity_rejected():
    with pytest.raises(ValueError, match="duplicate native run"):
        summarize({"source_sha": SHA, "runs": [run(), run()], "jobs": []})


def test_cross_sha_run_rejected():
    item = run()
    item["head_sha"] = "b" * 40
    with pytest.raises(ValueError, match="run SHA"):
        summarize({"source_sha": SHA, "runs": [item], "jobs": []})


@pytest.mark.parametrize("bad", ["abc", "g" * 40, "A" * 40])
def test_bad_source_sha_rejected(bad):
    """Insist on lowercase 40-character hexadecimal source identity."""
    with pytest.raises(ValueError):
        summarize({"source_sha": bad, "jobs": []})
