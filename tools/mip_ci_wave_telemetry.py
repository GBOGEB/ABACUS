"""Fail-closed native GitHub CI pulse metrics with provenance retention.

Input is an explicit GitHub Actions runs/jobs JSON export, never a plan.
Unknown or unobserved fields remain None and are not converted to zero.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from statistics import median


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


def summarize(payload):
    """Summarize only identity-bound observations from a single source SHA."""
    sha = payload.get("source_sha")
    if not isinstance(sha, str) or len(sha) != 40:
        raise ValueError("exact source_sha required")
    jobs = payload.get("jobs")
    if not isinstance(jobs, list):
        raise ValueError("jobs list required")
    seen = set()
    queue, elapsed = [], []
    counts = {"success": 0, "failure": 0, "cancelled": 0, "skipped": 0}
    pending = 0
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
        if status != "completed":
            pending += 1
            continue
        if conclusion not in counts:
            raise ValueError("unrecognized terminal conclusion")
        counts[conclusion] += 1
        if conclusion in ("cancelled", "skipped"):
            continue
        wait = _duration(job.get("created_at"), job.get("started_at"))
        runtime = _duration(job.get("started_at"), job.get("completed_at"))
        if wait is not None:
            queue.append(wait)
        if runtime is not None:
            elapsed.append(runtime)
    return {
        "source_sha": sha,
        "jobs_observed": len(jobs),
        "terminal_by_outcome": counts,
        "nonterminal": pending,
        "queue_seconds_p50": median(queue) if queue else None,
        "queue_seconds_p95": _percentile(queue, 95),
        "runtime_seconds_sum": sum(elapsed) if len(elapsed) == (
            counts["success"] + counts["failure"]
        ) else None,
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
    print(json.dumps(summarize(json.loads(
        options.input.read_text(encoding="utf-8")
    )), sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
