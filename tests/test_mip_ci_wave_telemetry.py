"""Native telemetry negative controls: identities, SHA and censored jobs."""

import pytest

from tools.mip_ci_wave_telemetry import TERMINAL_CONCLUSIONS, summarize

SHA = "a" * 40


def run(identity=101, *, attempt=1, created_at="2026-10-15T08:00:00Z"):
    """Construct a native workflow-run-shaped fixture."""
    return {
        "id": identity,
        "run_attempt": attempt,
        "head_sha": SHA,
        "created_at": created_at,
    }


def job(identity=1, *, conclusion="success", status="completed"):
    """Construct a native job-shaped fixture; no synthetic job created_at."""
    return {
        "id": identity,
        "run_id": 101,
        "run_attempt": 1,
        "head_sha": SHA,
        "status": status,
        "conclusion": conclusion,
        "started_at": "2026-10-15T08:01:00Z",
        "completed_at": "2026-10-15T08:03:00Z",
    }


def test_measured_duration_and_unknown_authority():
    """Join native run creation to job start without manufacturing Crew evidence."""
    result = summarize({"source_sha": SHA, "runs": [run()], "jobs": [job()]})
    assert result["terminal_by_outcome"]["success"] == 1
    assert result["run_records_observed"] == 1
    assert result["queue_basis"] == "workflow_run.created_at -> job.started_at"
    assert result["queue_seconds_p95"] == 60
    assert result["runtime_seconds_sum"] == 120
    assert result["crew_dispatch_authenticated"] is None
    assert result["rex_receipts_accepted"] is None


def test_native_job_without_joined_run_keeps_queue_unknown():
    """REST jobs alone do not contain a native queue-start timestamp."""
    result = summarize({"source_sha": SHA, "jobs": [job()]})
    assert result["queue_samples"] == 0
    assert result["queue_seconds_p50"] is None
    assert result["queue_seconds_p95"] is None
    assert result["runtime_seconds_sum"] == 120


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


def test_unobserved_completed_duration_is_unknown():
    """Do not infer elapsed seconds for missing source timestamps."""
    item = job()
    item["started_at"] = None
    result = summarize({"source_sha": SHA, "runs": [run()], "jobs": [item]})
    assert result["runtime_seconds_sum"] is None
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


def test_nonterminal_job_cannot_claim_terminal_conclusion():
    item = job(status="in_progress", conclusion="success")
    with pytest.raises(ValueError, match="nonterminal"):
        summarize({"source_sha": SHA, "runs": [run()], "jobs": [item]})


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
