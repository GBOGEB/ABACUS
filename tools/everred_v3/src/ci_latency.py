"""Source-bound native GitHub Actions latency, without synthetic queue attribution.

All timing inputs are actual GitHub run/job/step timestamps. Aggregate
percentiles are descriptive only; mixed workflows and versions never pool.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import re

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SCHEMA = "abacus.everred.ci-latency.v1"


def demand(condition, message):
    if not condition:
        raise ValueError(message)


def timestamp(value):
    demand(isinstance(value, str) and bool(value), "timestamp missing")
    try:
        result = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("malformed timestamp") from exc
    demand(result.tzinfo is not None, "timezone-less timestamp")
    return result.astimezone(dt.timezone.utc)


def duration(begin, end):
    value = (timestamp(end) - timestamp(begin)).total_seconds()
    demand(math.isfinite(value) and value >= 0, "negative duration")
    return round(value, 3)


def percentile(values, probability):
    demand(
        type(probability) in (float, int) and 0 <= probability <= 1, "invalid quantile"
    )
    demand(isinstance(values, list) and bool(values), "nonempty sample required")
    demand(
        all(type(v) in (int, float) and math.isfinite(v) and v >= 0 for v in values),
        "invalid duration sample",
    )
    sorted_values = sorted(values)
    position = (len(sorted_values) - 1) * probability
    low = int(position)
    high = min(low + 1, len(sorted_values) - 1)
    return round(
        sorted_values[low]
        + (sorted_values[high] - sorted_values[low]) * (position - low),
        3,
    )


def distribution(values):
    if not values:
        return {
            "status": "UNKNOWN_NO_NATIVE_OBSERVATIONS",
            "n": 0,
            "median": None,
            "p5": None,
            "p95": None,
            "p99": None,
            "p95_tail_qualified": False,
            "p99_tail_qualified": False,
        }
    return {
        "status": "OBSERVED_DESCRIPTIVE_ONLY",
        "n": len(values),
        "median": percentile(values, 0.5),
        "p5": percentile(values, 0.05),
        "p95": percentile(values, 0.95),
        "p99": percentile(values, 0.99),
        "method": "type7_linear_interpolation",
        "unit": "seconds",
        "p95_tail_qualified": len(values) >= 20,
        "p99_tail_qualified": len(values) >= 100,
        "independent_sampling_not_established": True,
    }


def _union_seconds(intervals):
    if not intervals:
        return 0.0
    ordered = sorted(intervals)
    start, stop = ordered[0]
    total = 0.0
    for left, right in ordered[1:]:
        if left <= stop:
            stop = max(stop, right)
        else:
            total += (stop - start).total_seconds()
            start, stop = left, right
    return round(total + (stop - start).total_seconds(), 3)


def _stage(name):
    label = name.casefold()
    if "upload-artifact" in label or "download-artifact" in label:
        return "artifact_transfer"
    if "pip install" in label or "install scanner" in label or "install " in label:
        return "dependency_install"
    if "checkout@" in label or "setup-python@" in label or "set up job" in label:
        return "environment_setup"
    if any(
        x in label for x in ("pytest", "regression", "testflight", "unittest", " test")
    ):
        return "test"
    if any(x in label for x in ("bandit", "security", "scanner", "semgrep", "codeql")):
        return "security_scan"
    if "governance" in label or "inventory" in label:
        return "governance"
    return "other"


def measure_run(run, jobs, expected_repo, expected_sha):
    demand(isinstance(run, dict) and isinstance(jobs, list), "invalid GitHub objects")
    demand(
        isinstance(expected_sha, str) and SHA_RE.fullmatch(expected_sha), "invalid SHA"
    )
    demand(run.get("head_sha") == expected_sha, "run exact-head mismatch")
    demand(
        run.get("repository", {}).get("full_name") == expected_repo,
        "run repository mismatch",
    )
    rid = run.get("id")
    demand(type(rid) is int and rid > 0, "invalid run ID")
    attempt = run.get("run_attempt")
    demand(type(attempt) is int and attempt > 0, "invalid run attempt")
    demand(run.get("status") == "completed", "nonterminal run: UNKNOWN")
    start = timestamp(run.get("created_at"))
    finish = timestamp(run.get("updated_at"))
    wall = duration(run["created_at"], run["updated_at"])
    demand(bool(jobs), "empty native job inventory")
    ids = set()
    samples = []
    intervals = []
    stages = {}
    problems = []
    for job in jobs:
        demand(isinstance(job, dict), "bad job record")
        jid = job.get("id")
        demand(type(jid) is int and jid > 0 and jid not in ids, "duplicate/bad job ID")
        ids.add(jid)
        demand(job.get("run_id") == rid, "cross-run job")
        demand(job.get("head_sha") in (None, expected_sha), "cross-source job")
        demand(job.get("run_attempt", attempt) == attempt, "cross-attempt job")
        record = {
            "job_id": jid,
            "name": job.get("name"),
            "conclusion": job.get("conclusion"),
            "queue_seconds": None,
            "runner_seconds": None,
            "steps": [],
        }
        if job.get("status") != "completed":
            problems.append("JOB_NONTERMINAL")
            samples.append(record)
            continue
        try:
            created = timestamp(job.get("created_at"))
            launched = timestamp(job.get("started_at"))
            completed = timestamp(job.get("completed_at"))
            demand(
                start <= created <= launched <= completed <= finish,
                "job timeline invalid",
            )
            record["queue_seconds"] = duration(job["created_at"], job["started_at"])
            record["runner_seconds"] = duration(job["started_at"], job["completed_at"])
            intervals.append((launched, completed))
        except ValueError as exc:
            problems.append("JOB_TIME_UNKNOWN:" + str(exc))
            samples.append(record)
            continue
        for step in job.get("steps") or []:
            begin, ended = step.get("started_at"), step.get("completed_at")
            if not begin or not ended:
                problems.append("STEP_TIME_UNKNOWN")
                continue
            try:
                demand(
                    launched <= timestamp(begin) <= timestamp(ended) <= completed,
                    "step outside native job interval",
                )
                value = duration(begin, ended)
            except ValueError as exc:
                problems.append("STEP_TIME_INVALID:" + str(exc))
                continue
            tag = _stage(str(step.get("name") or ""))
            stages[tag] = round(stages.get(tag, 0.0) + value, 3)
            record["steps"].append(
                {"name": step.get("name"), "stage": tag, "seconds": value}
            )
        samples.append(record)
    timed = [x for x in samples if x["runner_seconds"] is not None]
    status = "MEASURED" if len(timed) == len(jobs) and not problems else "PARTIAL"
    first_started = min((interval[0] for interval in intervals), default=None)
    end_job = max((interval[1] for interval in intervals), default=None)
    running_union = _union_seconds(intervals)
    runner_sum = round(sum(x["runner_seconds"] for x in timed), 3)
    return {
        "schema": SCHEMA + ".run",
        "repository": expected_repo,
        "source_sha": expected_sha,
        "workflow": run.get("name"),
        "event": run.get("event"),
        "run_id": rid,
        "run_attempt": attempt,
        "run_status": run.get("status"),
        "run_conclusion": run.get("conclusion"),
        "state": status,
        "workflow_wall_seconds": wall,
        "pre_first_job_seconds": (
            round((first_started - start).total_seconds(), 3)
            if first_started is not None
            else None
        ),
        "post_last_job_seconds": (
            round((finish - end_job).total_seconds(), 3)
            if end_job is not None
            else None
        ),
        "runner_sum_seconds": runner_sum if timed else None,
        "active_union_seconds": running_union if timed else None,
        "job_count": len(jobs),
        "timed_job_count": len(timed),
        "jobs": samples,
        "step_stage_seconds": stages,
        "stage_totals_not_additive_to_wall": True,
        "problems": sorted(set(problems)),
        "cache_hit": None,
        "wheel_reuse_verified": None,
        "merge_authorized": False,
    }


def cohort(receipts):
    demand(isinstance(receipts, list), "invalid cohort")
    if not receipts:
        return {"status": "UNKNOWN_NO_RUNS", "population": None}
    identities = [
        (r.get("repository"), r.get("source_sha"), r.get("workflow"), r.get("event"))
        for r in receipts
    ]
    if len(set(identities)) != 1:
        return {"status": "INCOMPARABLE_COHORT", "population": None}
    unique = {(r.get("run_id"), r.get("run_attempt")) for r in receipts}
    demand(len(unique) == len(receipts), "duplicate run attempt in cohort")
    usable = [r for r in receipts if r.get("state") == "MEASURED"]
    return {
        "status": "DESCRIPTIVE_ONLY" if usable else "UNKNOWN_NO_COMPLETE_RUNS",
        "population": list(identities[0]),
        "eligible_runs": len(usable),
        "observed_runs": len(receipts),
        "queue": distribution([j["queue_seconds"] for r in usable for j in r["jobs"]]),
        "workflow_wall": distribution([r["workflow_wall_seconds"] for r in usable]),
        "runner_sum": distribution([r["runner_sum_seconds"] for r in usable]),
        "pca": {
            "status": "HANDOFF_REQUIRED_GG_MATH",
            "candidate_features": [
                "workflow_wall_seconds",
                "pre_first_job_seconds",
                "runner_sum_seconds",
            ],
            "sample_count": len(usable),
            "minimum_count_for_candidate": 30,
            "mathematical_validation": "NOT_EXECUTED",
            "owner_decision": "DEFER",
        },
        "inferred_speedup": None,
        "merge_authorized": False,
    }


def digest_receipt(payload):
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()
