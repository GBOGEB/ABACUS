"""Lane A wave 8: MIP/EVIDENCE_TO_ADMISSION_OBSERVATORY/queue_telemetry.py."""

import pytest

from tests.coverage_waves.lane_a._load import load

qt = load("MIP/EVIDENCE_TO_ADMISSION_OBSERVATORY/queue_telemetry.py")

HEAD = "c" * 40


def _job(jid, created="2026-01-01T00:00:00Z", queued=10, executed=30, **over):
    job = {
        "id": jid,
        "status": "completed",
        "conclusion": "success",
        "run_attempt": 1,
        "created_at": created,
        "started_at": "2026-01-01T00:00:%02dZ" % queued,
        "completed_at": "2026-01-01T00:01:%02dZ" % executed,
    }
    job.update(over)
    return job


def _summ(jobs, total=None, attempt=1):
    return qt.summarize_jobs(
        jobs, run_id=7, head_sha=HEAD, attempt=attempt, total_count=total
    )


def test_seconds_valid_and_rejections():
    assert qt._seconds("2026-01-01T00:00:00Z", "2026-01-01T00:00:05Z") == 5.0
    assert qt._seconds(None, "2026-01-01T00:00:05Z") is None
    assert qt._seconds("2026-01-01T00:00:00Z", 5) is None
    # naive timestamps are not accepted
    assert qt._seconds("2026-01-01T00:00:00", "2026-01-01T00:00:05") is None
    # negative durations are rejected
    assert qt._seconds("2026-01-01T00:00:05Z", "2026-01-01T00:00:00Z") is None
    assert qt._seconds("garbage", "2026-01-01T00:00:00Z") is None


def test_p95_nearest_rank():
    assert qt._p95([]) is None
    assert qt._p95([4.0]) == 4.0
    assert qt._p95([float(x) for x in range(1, 21)]) == 19.0
    assert qt._p95([3.0, 1.0, 2.0]) == 3.0


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(run_id=0, head_sha=HEAD, attempt=1, total_count=1),
        dict(run_id=True, head_sha=HEAD, attempt=1, total_count=1),
        dict(run_id=1, head_sha=HEAD, attempt=0, total_count=1),
        dict(run_id=1, head_sha="abc", attempt=1, total_count=1),
        dict(run_id=1, head_sha=HEAD.upper(), attempt=1, total_count=1),
        dict(run_id=1, head_sha=HEAD, attempt=1, total_count=-1),
        dict(run_id=1, head_sha=HEAD, attempt=1, total_count=1.0),
    ],
)
def test_identity_validation(kwargs):
    with pytest.raises(ValueError):
        qt.summarize_jobs([], **kwargs)


def test_job_list_must_hold_objects():
    with pytest.raises(ValueError):
        _summ(["x"], total=1)
    with pytest.raises(ValueError):
        _summ("nope", total=1)


def test_complete_population_reports_p95():
    jobs = [_job(1, queued=10, executed=30), _job(2, queued=20, executed=50)]
    out = _summ(jobs, total=2)
    assert out["evidence_state"] == "COMPLETE_TERMINAL_JOB_POPULATION"
    assert out["queue_p95_seconds"] == 20.0
    assert out["execution_p95_seconds"] == 90.0
    assert out["queue_p95_partial_diagnostic_seconds"] is None
    assert out["statuses"] == {"completed": 2}
    assert out["terminal_queue_samples"] == 2
    assert out["scale_authority"] is False
    assert out["source_sha"] == HEAD and out["run_id"] == 7


def test_run_attempt_none_is_accepted():
    out = _summ([_job(1, run_attempt=None)], total=1)
    assert out["evidence_state"] == "COMPLETE_TERMINAL_JOB_POPULATION"


def test_unknown_total_is_unverified_with_diagnostic():
    out = _summ([_job(1, queued=12)], total=None)
    assert out["evidence_state"] == "POPULATION_UNVERIFIED_OR_PAGINATED"
    assert out["queue_p95_seconds"] is None
    assert out["queue_p95_partial_diagnostic_seconds"] == 12.0


def test_total_mismatch_is_paginated():
    out = _summ([_job(1)], total=3)
    assert out["evidence_state"] == "POPULATION_UNVERIFIED_OR_PAGINATED"


def test_zero_total_with_no_jobs():
    out = _summ([], total=0)
    assert out["evidence_state"] == "QUEUED_OR_TIMESTAMP_INCOMPLETE"
    assert out["queue_p95_partial_diagnostic_seconds"] is None


@pytest.mark.parametrize("ids", [(1, 1), (1, "2"), (0, 1), (True, 2)])
def test_bad_identities(ids):
    jobs = [_job(i) for i in ids]
    out = _summ(jobs, total=2)
    assert out["evidence_state"] == "JOB_IDENTITIES_MISSING_OR_DUPLICATED"


def test_queued_and_wrong_attempt_jobs_are_not_sampled():
    jobs = [
        _job(1),
        _job(2, status="queued", conclusion=None),
        _job(3, conclusion=None),
        _job(4, run_attempt=2),
        _job(5, started_at=None),
    ]
    out = _summ(jobs, total=5)
    assert out["evidence_state"] == "QUEUED_OR_TIMESTAMP_INCOMPLETE"
    assert out["statuses"] == {"completed": 4, "queued": 1}
    # job 5 has no start: neither queue nor execution sample
    assert out["terminal_queue_samples"] == 1
    assert out["terminal_execution_samples"] == 1
    assert out["queue_p95_seconds"] is None


def test_missing_status_counted_as_none_string():
    out = _summ([{"id": 1}], total=1)
    assert out["statuses"] == {"None": 1}
    assert out["terminal_queue_samples"] == 0
