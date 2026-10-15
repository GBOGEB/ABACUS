"""Native telemetry negative controls: identities, SHA and censored jobs."""

import pytest

from tools.mip_ci_wave_telemetry import summarize

SHA = "a" * 40


def job(identity=1, *, conclusion="success", status="completed"):
    """Construct a test fixture; not a claimed live GitHub job."""
    return {
        "id": identity,
        "run_id": 101,
        "run_attempt": 1,
        "head_sha": SHA,
        "status": status,
        "conclusion": conclusion,
        "created_at": "2026-10-15T08:00:00Z",
        "started_at": "2026-10-15T08:01:00Z",
        "completed_at": "2026-10-15T08:03:00Z",
    }


def test_measured_duration_and_unknown_authority():
    """Count terminal jobs without manufacturing Crew or closure evidence."""
    result = summarize({"source_sha": SHA, "jobs": [job()]})
    assert result["terminal_by_outcome"]["success"] == 1
    assert result["queue_seconds_p95"] == 60
    assert result["runtime_seconds_sum"] == 120
    assert result["crew_dispatch_authenticated"] is None
    assert result["rex_receipts_accepted"] is None


def test_nonterminal_is_not_a_failed_or_finished_job():
    """Queue-only observations do not contribute durations."""
    result = summarize(
        {
            "source_sha": SHA,
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
    assert (
        summarize(
            {
                "source_sha": SHA,
                "jobs": [item],
            }
        )["runtime_seconds_sum"]
        is None
    )


def test_cancelled_run_does_not_count_as_observed_job_duration():
    """A cancelled job is censored independently from a failed job."""
    result = summarize(
        {
            "source_sha": SHA,
            "jobs": [job(conclusion="cancelled")],
        }
    )
    assert result["terminal_by_outcome"]["cancelled"] == 1
    assert result["queue_seconds_p95"] is None


@pytest.mark.parametrize(
    "mutation",
    [
        {"head_sha": "b" * 40},
        {"id": None},
        {"run_attempt": None},
        {"conclusion": "unknown"},
    ],
)
def test_bad_identity_or_result_fails_closed(mutation):
    """Reject records that cannot be authenticated or classified."""
    item = job()
    item.update(mutation)
    with pytest.raises(ValueError):
        summarize({"source_sha": SHA, "jobs": [item]})


def test_duplicate_job_identity_rejected():
    """Multiple appearances of one native run/job cannot inflate counts."""
    with pytest.raises(ValueError, match="duplicate"):
        summarize({"source_sha": SHA, "jobs": [job(), job()]})


def test_bad_source_sha_rejected():
    """Insist on a complete exact source identity."""
    with pytest.raises(ValueError):
        summarize({"source_sha": "abc", "jobs": []})
