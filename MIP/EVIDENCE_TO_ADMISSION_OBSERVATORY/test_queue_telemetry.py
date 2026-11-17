"""Fail-closed runner-clock telemetry tests: queued jobs never fabricate p95=0."""

from __future__ import annotations

import pytest
import queue_telemetry as q

SHA = "a" * 40


def job(
    jid,
    *,
    status="completed",
    conclusion="success",
    start="2026-10-18T10:00:30Z",
    created="2026-10-18T10:00:00Z",
    end="2026-10-18T10:01:30Z",
    attempt=1,
):
    return {
        "id": jid,
        "status": status,
        "conclusion": conclusion,
        "created_at": created,
        "started_at": start,
        "completed_at": end,
        "run_attempt": attempt,
    }


def receipt(jobs, total=None):
    return q.summarize_jobs(
        jobs,
        run_id=1234,
        head_sha=SHA,
        attempt=1,
        total_count=len(jobs) if total is None else total,
    )


def test_full_population_has_valid_measured_queue_and_execution_p95():
    r = receipt(
        [
            job(1),
            job(2, start="2026-10-18T10:00:40Z"),
            job(3, start="2026-10-18T10:00:49Z"),
        ]
    )
    assert r["queue_p95_seconds"] == 49
    assert r["execution_p95_seconds"] == 60
    assert r["evidence_state"] == "COMPLETE_TERMINAL_JOB_POPULATION"
    assert r["jobs_observed"] == r["jobs_expected"] == 3
    assert r["authenticated_crew_launch_ids"] is None
    assert r["scale_authority"] is False


def test_queued_job_with_equal_created_and_started_is_not_zero_queue_sample():
    rows = [
        job(
            1, status="queued", conclusion=None, start="2026-10-18T10:00:00Z", end=None
        ),
        job(2),
    ]
    r = receipt(rows)
    assert r["evidence_state"] == "QUEUED_OR_TIMESTAMP_INCOMPLETE"
    assert r["queue_p95_seconds"] is None
    assert r["terminal_queue_samples"] == 1
    assert r["queue_p95_partial_diagnostic_seconds"] == 30


def test_all_queued_rows_have_unknown_queue_not_zero():
    r = receipt(
        [
            job(
                1,
                status="queued",
                conclusion=None,
                start="2026-10-18T10:00:00Z",
                end=None,
            )
        ]
    )
    assert r["queue_p95_seconds"] is None
    assert r["terminal_queue_samples"] == 0
    assert r["queue_p95_partial_diagnostic_seconds"] is None


@pytest.mark.parametrize("status", ["queued", "waiting", "in_progress", "pending"])
def test_nonterminal_even_with_populated_timestamps_cannot_grant_p95(status):
    r = receipt([job(1, status=status, conclusion=None)])
    assert r["queue_p95_seconds"] is None
    assert r["terminal_execution_samples"] == 0


@pytest.mark.parametrize(
    "invalid", ["missing_started", "reversed", "naive", "invalid", "missing_end"]
)
def test_terminal_missing_or_nonmonotonic_timestamps_withholds_full_p95(invalid):
    row = job(1)
    if invalid == "missing_started":
        row["started_at"] = None
    elif invalid == "reversed":
        row["completed_at"] = "2026-10-18T09:59:00Z"
    elif invalid == "naive":
        row["started_at"] = "2026-10-18T10:00:30"
    elif invalid == "invalid":
        row["started_at"] = "bad"
    else:
        row["completed_at"] = None
    r = receipt([row])
    assert r["queue_p95_seconds"] is None
    assert r["execution_p95_seconds"] is None


def test_total_count_mismatch_is_explicit_paginated_unknown():
    r = receipt([job(1), job(2)], total=3)
    assert r["jobs_observed"] == 2
    assert r["jobs_expected"] == 3
    assert r["queue_p95_seconds"] is None
    assert r["evidence_state"] == "POPULATION_UNVERIFIED_OR_PAGINATED"


@pytest.mark.parametrize("identifiers", [[None, 2], [1, 1], [0, 2], ["1", 2]])
def test_missing_or_duplicate_native_job_id_withholds_eligibility(identifiers):
    r = receipt([job(i) for i in identifiers])
    assert r["queue_p95_seconds"] is None
    assert r["evidence_state"] == "JOB_IDENTITIES_MISSING_OR_DUPLICATED"


def test_wrong_run_attempt_withholds_queue_clock():
    r = receipt([job(1, attempt=2)])
    assert r["queue_p95_seconds"] is None
    assert r["terminal_queue_samples"] == 0


@pytest.mark.parametrize(
    "key,value",
    [
        ("run_id", 0),
        ("run_id", "12"),
        ("attempt", 0),
        ("attempt", None),
        ("head_sha", "short"),
        ("head_sha", "X" * 40),
        ("total_count", -1),
    ],
)
def test_invalid_run_and_sha_provenance_rejected(key, value):
    kwargs = dict(run_id=1234, head_sha=SHA, attempt=1, total_count=1)
    kwargs[key] = value
    with pytest.raises(ValueError):
        q.summarize_jobs([job(1)], **kwargs)


def test_empty_population_never_has_p95_even_if_declared_zero():
    r = q.summarize_jobs([], run_id=1234, head_sha=SHA, attempt=1, total_count=0)
    assert r["queue_p95_seconds"] is None
    assert r["evidence_state"] == "QUEUED_OR_TIMESTAMP_INCOMPLETE"


def test_nearest_rank_p95_uses_whole_job_index():
    data = [float(n) for n in range(1, 21)]
    assert q._p95(data) == 19.0
    assert q._p95([]) is None
