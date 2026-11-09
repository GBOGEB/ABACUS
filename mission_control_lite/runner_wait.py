"""Exact-head runner-wait telemetry with explicit right censoring.

Advisory observations only: no externally authenticated proof or admission.
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone

SHA = re.compile(r"[0-9a-f]{40}\Z")
STATUS = {"queued", "in_progress", "completed"}
TERMINAL = {
    "success",
    "failure",
    "cancelled",
    "skipped",
    "neutral",
    "timed_out",
    "action_required",
    "stale",
    "startup_failure",
}


def _time(value, field):
    if not isinstance(value, str):
        raise ValueError("missing timestamp: " + field)
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid timestamp: " + field) from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("naive timestamp: " + field)
    return dt.astimezone(timezone.utc)


def _id(value, field):
    if type(value) is not int or value < 1:
        raise ValueError("invalid " + field)
    return value


def summarize(head_sha, cutoff, jobs):
    """Describe native job queue residence; no assumption of IID samples.

    Queue residence is job.started_at - job.created_at. Queued jobs have
    right-censored lower bounds as of cutoff. Running execution durations are
    also right-censored. A run-created-to-job-start metric is *not* used.
    """
    if not isinstance(head_sha, str) or not SHA.fullmatch(head_sha):
        raise ValueError("canonical exact head SHA required")
    end = _time(cutoff, "cutoff")
    if not isinstance(jobs, list):
        raise ValueError("jobs must be a list")
    seen = set()
    observed_wait = []
    censored_wait = []
    completed_execution = []
    censored_execution = []
    states = {s: 0 for s in sorted(STATUS)}
    records = []
    for job in jobs:
        if not isinstance(job, dict):
            raise ValueError("job must be an object")
        if job.get("head_sha") != head_sha:
            raise ValueError("head drift / unbound job")
        run_id = _id(job.get("run_id"), "run ID")
        job_id = _id(job.get("job_id"), "job ID")
        attempt = _id(job.get("attempt"), "attempt")
        identity = (run_id, job_id, attempt)
        if identity in seen:
            raise ValueError("duplicate run/job/attempt")
        seen.add(identity)
        status = job.get("status")
        if status not in STATUS:
            raise ValueError("unsupported job status")
        conclusion = job.get("conclusion")
        if status == "completed":
            if conclusion not in TERMINAL:
                raise ValueError("missing terminal conclusion")
        elif conclusion is not None:
            raise ValueError("nonterminal conclusion is not evidence")
        created = _time(job.get("job_created_at"), "job_created_at")
        started_value = job.get("job_started_at")
        completed_value = job.get("job_completed_at")
        if created > end:
            raise ValueError("job creation after observation cutoff")
        row = {
            "run_id": run_id,
            "job_id": job_id,
            "attempt": attempt,
            "status": status,
            "conclusion": conclusion,
            "wait_seconds": None,
            "wait_censored_lower_bound_seconds": None,
            "execution_seconds": None,
            "execution_censored_lower_bound_seconds": None,
        }
        if status == "queued":
            if started_value is not None or completed_value is not None:
                raise ValueError("queued job cannot contain started/completed times")
            wait = (end - created).total_seconds()
            censored_wait.append(wait)
            row["wait_censored_lower_bound_seconds"] = wait
        else:
            started = _time(started_value, "job_started_at")
            if not created <= started <= end:
                raise ValueError("impossible job start order")
            wait = (started - created).total_seconds()
            observed_wait.append(wait)
            row["wait_seconds"] = wait
            if status == "in_progress":
                if completed_value is not None:
                    raise ValueError("running job cannot have completed time")
                duration = (end - started).total_seconds()
                censored_execution.append(duration)
                row["execution_censored_lower_bound_seconds"] = duration
            else:
                completed = _time(completed_value, "job_completed_at")
                if not started <= completed <= end:
                    raise ValueError("impossible completion order")
                duration = (completed - started).total_seconds()
                completed_execution.append(duration)
                row["execution_seconds"] = duration
        states[status] += 1
        records.append(row)
    observed_wait.sort()
    censored_wait.sort()
    completed_execution.sort()
    censored_execution.sort()
    n = len(observed_wait)
    return {
        "schema": "code-purple.runner-wait-censored.v1",
        "source_sha": head_sha,
        "cutoff_utc": end.isoformat(),
        "observations": len(jobs),
        "status_counts": states,
        "runner_wait_observed_n": n,
        "runner_wait_right_censored_n": len(censored_wait),
        "runner_wait_p50_nearest_rank_seconds": (
            observed_wait[math.ceil(n * 0.50) - 1] if n else None
        ),
        "runner_wait_p95_nearest_rank_seconds": (
            observed_wait[math.ceil(n * 0.95) - 1] if n else None
        ),
        "runner_wait_p95_qualified": n >= 20 and not censored_wait,
        "runner_wait_censored_lower_bound_max_seconds": (
            censored_wait[-1] if censored_wait else None
        ),
        "execution_completed_n": len(completed_execution),
        "execution_right_censored_n": len(censored_execution),
        "execution_p95_completed_only_seconds": (
            completed_execution[math.ceil(0.95 * len(completed_execution)) - 1]
            if completed_execution
            else None
        ),
        "records": sorted(
            records, key=lambda r: (r["run_id"], r["attempt"], r["job_id"])
        ),
        "independent_trials_assumed": False,
        "external_receipts_authenticated": False,
        "verified_root_closures": 0,
        "merge_admission": "HOLD",
        "note": "Empirical quantiles of observed jobs, not unbiased censored-event estimates.",
    }
