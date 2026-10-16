"""Fail-closed native GitHub CI pulse metrics with provenance retention.

Input is an explicit GitHub Actions workflow-run plus jobs JSON export, never a
plan. Unknown or unobserved fields remain None and are not converted to zero.
Queue latency is measured from native workflow_run.created_at to job.started_at;
GitHub job payloads do not contain a native created_at field.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from statistics import median


HEX40 = re.compile(r"^[0-9a-f]{40}$")
NONTERMINAL_STATUSES = {"queued", "in_progress", "waiting", "requested", "pending"}
TERMINAL_CONCLUSIONS = (
    "success",
    "failure",
    "neutral",
    "cancelled",
    "skipped",
    "timed_out",
    "action_required",
    "stale",
    "startup_failure",
)
RUNTIME_CENSORED = {"cancelled", "skipped"}


def _timestamp(value):
    """Parse an observed ISO timestamp without supplying a default clock."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _duration(start, end):
    """Return measured seconds or UNKNOWN when endpoints are absent."""
    first, last = _timestamp(start), _timestamp(end)
    if first is None or last is None:
        return None
    seconds = (last - first).total_seconds()
    return seconds if seconds >= 0 else None


def _percentile(values, percentile):
    """Nearest-rank percentile; reject a missing sample population."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, (len(ordered) * percentile + 99) // 100)
    return ordered[min(len(ordered), rank) - 1]


def _run_created_at_index(payload, source_sha):
    """Join native workflow-run creation timestamps by run ID and attempt."""
    runs = payload.get("runs")
    if runs is None:
        return {}
    if not isinstance(runs, list):
        raise ValueError("runs list required when run observations are supplied")
    index = {}
    for run in runs:
        if not isinstance(run, dict):
            raise ValueError("run object required")
        if run.get("head_sha") != source_sha:
            raise ValueError("run SHA differs from source_sha")
        identity = (run.get("id"), run.get("run_attempt"))
        if any(part is None for part in identity) or identity in index:
            raise ValueError("missing or duplicate native run identity")
        created_at = run.get("created_at")
        if created_at is not None and _timestamp(created_at) is None:
            raise ValueError("invalid native run created_at")
        index[identity] = created_at
    return index


def summarize(payload):
    """Summarize only identity-bound observations from a single source SHA."""
    sha = payload.get("source_sha")
    if not isinstance(sha, str) or HEX40.fullmatch(sha) is None:
        raise ValueError("exact hexadecimal source_sha required")
    jobs = payload.get("jobs")
    if not isinstance(jobs, list):
        raise ValueError("jobs list required")

    run_created_at = _run_created_at_index(payload, sha)
    seen = set()
    queue, elapsed = [], []
    counts = {name: 0 for name in TERMINAL_CONCLUSIONS}
    pending = 0
    runtime_expected = 0

    for job in jobs:
        if not isinstance(job, dict):
            raise ValueError("job object required")
        if job.get("head_sha") != sha:
            raise ValueError("job SHA differs from source_sha")
        identity = (job.get("run_id"), job.get("run_attempt"), job.get("id"))
        if any(part is None for part in identity) or identity in seen:
            raise ValueError("missing or duplicate native job identity")
        seen.add(identity)

        status = job.get("status")
        conclusion = job.get("conclusion")
        if status not in NONTERMINAL_STATUSES | {"completed"}:
            raise ValueError("unrecognized native job status")
        if status != "completed":
            if conclusion is not None:
                raise ValueError("nonterminal job cannot carry terminal conclusion")
            pending += 1
            continue
        if conclusion not in counts:
            raise ValueError("unrecognized terminal conclusion")
        counts[conclusion] += 1

        run_key = (job.get("run_id"), job.get("run_attempt"))
        wait = _duration(run_created_at.get(run_key), job.get("started_at"))
        if wait is not None:
            queue.append(wait)

        if conclusion not in RUNTIME_CENSORED:
            runtime_expected += 1
            runtime = _duration(job.get("started_at"), job.get("completed_at"))
            if runtime is not None:
                elapsed.append(runtime)

    return {
        "source_sha": sha,
        "jobs_observed": len(jobs),
        "run_records_observed": len(run_created_at),
        "terminal_by_outcome": counts,
        "nonterminal": pending,
        "queue_basis": "workflow_run.created_at -> job.started_at",
        "queue_seconds_p50": median(queue) if queue else None,
        "queue_seconds_p95": _percentile(queue, 95),
        "runtime_seconds_sum": (
            sum(elapsed)
            if runtime_expected > 0 and len(elapsed) == runtime_expected
            else None
        ),
        "queue_samples": len(queue),
        "runtime_samples": len(elapsed),
        "crew_dispatch_authenticated": None,
        "rex_receipts_accepted": None,
        "distinct_bd_roots_closed": None,
    }


def main(argv=None):
    """Read local native JSON and print a deterministic telemetry receipt."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    options = parser.parse_args(argv)
    print(
        json.dumps(
            summarize(json.loads(options.input.read_text(encoding="utf-8"))),
            sort_keys=True,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
