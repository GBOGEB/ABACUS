"""Exact-run native queue/exec clock contract; never infer starts for queued jobs.

GitHub sometimes populates started_at equal to created_at for queued jobs.
Therefore a timestamp *alone* does not prove a runner started. All metrics
which govern scale must be from a complete terminal job population with
run/attempt identity and valid monotonic timestamps.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

SHA = re.compile(r"^[0-9a-f]{40}$")


def _seconds(start: Any, stop: Any) -> float | None:
    if not isinstance(start, str) or not isinstance(stop, str):
        return None
    try:
        a = datetime.fromisoformat(start.replace("Z", "+00:00"))
        b = datetime.fromisoformat(stop.replace("Z", "+00:00"))
        if a.tzinfo is None or b.tzinfo is None:
            return None
        value = (b - a).total_seconds()
        return value if value >= 0 else None
    except (TypeError, ValueError, OverflowError):
        return None


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[(95 * len(ordered) + 99) // 100 - 1]


def summarize_jobs(
    jobs: list[dict],
    *,
    run_id: int,
    head_sha: str,
    attempt: int,
    total_count: int | None,
) -> dict:
    """Compute proof-gated queue/exec statistics without authority promotion."""
    if type(run_id) is not int or run_id < 1 or type(attempt) is not int or attempt < 1:
        raise ValueError("run/attempt identity must be positive integers")
    if not isinstance(head_sha, str) or not SHA.fullmatch(head_sha):
        raise ValueError("exact full source SHA required")
    if not isinstance(jobs, list) or any(not isinstance(x, dict) for x in jobs):
        raise ValueError("job list must contain objects")
    if total_count is not None and (type(total_count) is not int or total_count < 0):
        raise ValueError("invalid total_count")
    statuses = {}
    ids = []
    queue = []
    execution = []
    for job in jobs:
        status = job.get("status")
        statuses[str(status)] = statuses.get(str(status), 0) + 1
        ids.append(job.get("id"))
        if status != "completed" or job.get("conclusion") is None:
            continue
        if job.get("run_attempt") not in (None, attempt):
            continue
        queued = _seconds(job.get("created_at"), job.get("started_at"))
        executed = _seconds(job.get("started_at"), job.get("completed_at"))
        if queued is not None:
            queue.append(queued)
        if executed is not None:
            execution.append(executed)
    identity_valid = all(type(x) is int and x > 0 for x in ids) and len(ids) == len(
        set(ids)
    )
    population_complete = (
        total_count is not None
        and total_count > 0
        and len(jobs) == total_count
        and identity_valid
        and len(queue) == total_count
        and len(execution) == total_count
    )
    if population_complete:
        state = "COMPLETE_TERMINAL_JOB_POPULATION"
    elif total_count is None or total_count != len(jobs):
        state = "POPULATION_UNVERIFIED_OR_PAGINATED"
    elif not identity_valid:
        state = "JOB_IDENTITIES_MISSING_OR_DUPLICATED"
    else:
        state = "QUEUED_OR_TIMESTAMP_INCOMPLETE"
    return {
        "schema": "codepurple.native_runner_queue.v1",
        "run_id": run_id,
        "source_sha": head_sha,
        "run_attempt": attempt,
        "jobs_observed": len(jobs),
        "jobs_expected": total_count,
        "statuses": dict(sorted(statuses.items())),
        "terminal_queue_samples": len(queue),
        "terminal_execution_samples": len(execution),
        "evidence_state": state,
        "queue_p95_seconds": _p95(queue) if population_complete else None,
        "execution_p95_seconds": _p95(execution) if population_complete else None,
        "queue_p95_partial_diagnostic_seconds": (
            _p95(queue) if not population_complete else None
        ),
        "scale_authority": False,
        "authenticated_crew_launch_ids": None,
        "accepted_root_closures": None,
    }
