"""Fail-closed native GitHub CI structural telemetry with provenance retention.

Input is an explicit GitHub Actions workflow-run plus jobs JSON export, never a
plan. Unknown or unobserved fields remain None and are not converted to zero.
Queue latency prefers native job.created_at -> job.started_at. Older snapshots
without job.created_at fall back to workflow_run.created_at -> job.started_at.

This producer measures execution structure (runs, jobs, steps, timing, fan-out
and runner breadth). It does not turn repeated jobs or steps on one SHA into
independent process observations, authenticate Mission Control Crew dispatch,
accept REX receipts, close BD roots, or grant merge/security authority.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from statistics import median


HEX40 = re.compile(r"^[0-9a-f]{40}$")
NONTERMINAL_STATUSES = {
    "queued",
    "in_progress",
    "waiting",
    "requested",
    "pending",
}
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


def _outcome_counts():
    return {name: 0 for name in TERMINAL_CONCLUSIONS}


def _classify_status(status, conclusion, counts, *, kind):
    """Classify one native run/job/step without converting pending to failure."""
    if status is None:
        return "unclassified"
    if status not in NONTERMINAL_STATUSES | {"completed"}:
        raise ValueError(f"unrecognized native {kind} status")
    if status != "completed":
        if conclusion is not None:
            raise ValueError(f"nonterminal {kind} cannot carry terminal conclusion")
        return "nonterminal"
    if conclusion not in counts:
        raise ValueError(f"unrecognized terminal {kind} conclusion")
    counts[conclusion] += 1
    return "terminal"


def _run_index(payload, source_sha):
    """Join native workflow-run metadata by run ID and attempt."""
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
        index[identity] = {
            "created_at": created_at,
            "name": run.get("name"),
            "path": run.get("path"),
            "html_url": run.get("html_url"),
            "status": run.get("status"),
            "conclusion": run.get("conclusion"),
        }
    return index


def _peak_overlap(intervals):
    """Maximum observed simultaneous positive-duration runtime intervals."""
    peak = 0
    for start, _end in intervals:
        active = sum(
            1
            for candidate_start, candidate_end in intervals
            if candidate_start <= start < candidate_end
        )
        peak = max(peak, active)
    return peak if intervals else None



# Exact workflow identities, not interchangeable green labels. Bandit, Safety,
# and independent review require their own separately owned evidence; this
# execution-structure producer deliberately cannot promote them.
GATE_DOMAINS = (
    "enterprise_ci",
    "workflow_governance",
    "a10_confidentiality",
    "bandit",
    "safety",
    "independent_review",
)
_ENTERPRISE_JOBS = tuple(
    f"Test Python {version} on {operating_system}"
    for version in ("3.9", "3.10", "3.11", "3.12")
    for operating_system in ("ubuntu-latest", "windows-latest", "macos-latest")
)
_WORKFLOW_GATE_SPECS = {
    "enterprise_ci": {
        "name": "DMAIC V3 Enterprise CI",
        "path": ".github/workflows/dmaic-enterprise-ci.yml",
        "jobs": _ENTERPRISE_JOBS + ("CI Summary",),
        "steps": {"Test Python ": "Run pytest --benchmark-disable with coverage"},
    },
    "workflow_governance": {
        "name": "CI Workflow Governance",
        "path": ".github/workflows/ci-governance.yml",
        "jobs": ("policy-and-inventory",),
        "steps": {"policy-and-inventory": "Fail closed on governance red"},
    },
    "a10_confidentiality": {
        "name": "a10-guard",
        "path": ".github/workflows/a10-guard.yml",
        "jobs": ("a10-guard",),
        "steps": {},
    },
}


def _binding_or_unknown(domain, bindings):
    """Select exactly one native workflow run and attempt, never 'latest'."""
    if domain not in bindings:
        return None
    selection = bindings[domain]
    if not isinstance(selection, dict) or set(selection) != {"run_id", "run_attempt"}:
        raise ValueError("gate binding must contain exact run_id and run_attempt")
    for key in ("run_id", "run_attempt"):
        if type(selection[key]) is not int or selection[key] <= 0:
            raise ValueError("gate binding identity must be positive native integer")
    return selection


def independent_gate_vector(payload, run_index, jobs, source_sha):
    """Observational gate vector; no boolean OR, implicit success, or merge authority.

    A gate PASS requires the explicitly selected exact-head native run, expected
    workflow identity and every mandatory job/step. The three remaining gate
    domains are UNKNOWN until their independent authority supplies proof.
    """
    bindings = payload.get("gate_bindings", {})
    if not isinstance(bindings, dict) or any(
        domain not in _WORKFLOW_GATE_SPECS for domain in bindings
    ):
        raise ValueError("unsupported independent gate binding")
    results = {}
    counts = {key: 0 for key in ("PASS", "FAIL", "PENDING", "BLOCKED", "UNKNOWN")}

    for domain in GATE_DOMAINS:
        row = {
            "status": "UNKNOWN",
            "source_sha": source_sha,
            "run_id": None,
            "run_attempt": None,
            "run_url": None,
            "job_ids": [],
            "blocking_jobs": [],
            "blocking_steps": [],
            "missing_jobs": [],
            "missing_steps": [],
            "evidence_class": "UNOBSERVED",
        }
        if domain in _WORKFLOW_GATE_SPECS:
            binding = _binding_or_unknown(domain, bindings)
            if binding is not None:
                rid, attempt = binding["run_id"], binding["run_attempt"]
                row["run_id"], row["run_attempt"] = rid, attempt
                native = run_index.get((rid, attempt))
                if native is not None:
                    spec = _WORKFLOW_GATE_SPECS[domain]
                    expected_url = (
                        f"https://github.com/GBOGEB/ABACUS/actions/runs/{rid}"
                    )
                    if (
                        native.get("path") != spec["path"]
                        or native.get("name") != spec["name"]
                        or native.get("html_url") != expected_url
                    ):
                        raise ValueError(
                            "gate binding mismatches native workflow identity"
                        )
                    row["run_url"] = expected_url
                    row["evidence_class"] = "NATIVE_RUN_JOB_OBSERVATION"
                    selected_jobs = [
                        job for job in jobs
                        if job["run_id"] == rid and job["run_attempt"] == attempt
                    ]
                    names = [job.get("name") for job in selected_jobs]
                    if any(not isinstance(name, str) or not name for name in names):
                        raise ValueError("gate job names required")
                    if len(names) != len(set(names)):
                        raise ValueError("duplicate job name in exact gate run")
                    by_name = {job["name"]: job for job in selected_jobs}
                    row["job_ids"] = sorted(job["id"] for job in selected_jobs)
                    row["missing_jobs"] = [
                        name for name in spec["jobs"] if name not in by_name
                    ]
                    row["blocking_jobs"] = [
                        job["name"] for job in selected_jobs
                        if job["conclusion"] in (
                            "failure", "timed_out", "startup_failure"
                        )
                    ]
                    status = native.get("status")
                    conclusion = native.get("conclusion")
                    if status != "completed":
                        row["status"] = "PENDING"
                    elif conclusion in ("failure", "timed_out", "startup_failure"):
                        row["status"] = "FAIL"
                    elif conclusion != "success":
                        row["status"] = "BLOCKED"
                    elif row["missing_jobs"]:
                        row["status"] = "UNKNOWN"
                    else:
                        required = [by_name[name] for name in spec["jobs"]]
                        if any(job["status"] != "completed" for job in required):
                            row["status"] = "PENDING"
                        elif any(job["conclusion"] != "success" for job in required):
                            row["status"] = "FAIL"
                        else:
                            for job in required:
                                for prefix, step_name in spec["steps"].items():
                                    if not job["name"].startswith(prefix):
                                        continue
                                    steps = job.get("steps")
                                    if not isinstance(steps, list):
                                        row["missing_steps"].append(
                                            job["name"] + ":" + step_name
                                        )
                                        continue
                                    observed = [
                                        step for step in steps
                                        if isinstance(step, dict)
                                        and step.get("name") == step_name
                                    ]
                                    if len(observed) == 1 and (
                                        observed[0].get("status") == "completed"
                                        and observed[0].get("conclusion") in (
                                            "failure", "timed_out", "startup_failure"
                                        )
                                    ):
                                        row["blocking_steps"].append(
                                            job["name"] + ":" + step_name
                                        )
                                    elif len(observed) != 1 or (
                                        observed[0].get("status") != "completed"
                                        or observed[0].get("conclusion") != "success"
                                    ):
                                        row["missing_steps"].append(
                                            job["name"] + ":" + step_name
                                        )
                            if row["blocking_steps"]:
                                row["status"] = "FAIL"
                            elif row["missing_steps"]:
                                row["status"] = "UNKNOWN"
                            else:
                                row["status"] = "PASS"
        results[domain] = row
        counts[row["status"]] += 1

    return {
        "schema": "abacus.mip.independent-gates.v1",
        "source_sha": source_sha,
        "domains": results,
        "domain_counts": counts,
        "domain_observation_fraction": (
            sum(row["status"] != "UNKNOWN" for row in results.values())
            / len(GATE_DOMAINS)
        ),
        "domain_terminal_fraction": (
            sum(row["status"] in ("PASS", "FAIL", "BLOCKED")
                for row in results.values())
            / len(GATE_DOMAINS)
        ),
        "red_domains": sorted(
            name for name, row in results.items()
            if row["status"] in ("FAIL", "BLOCKED")
        ),
        "unknown_domains": sorted(
            name for name, row in results.items()
            if row["status"] == "UNKNOWN"
        ),
        "admission": "HOLD",
        "coverage_artifact_verified": None,
        "merge_authorized": False,
        "security_waiver": False,
        "independent_review_admitted": None,
    }


def summarize(payload):
    """Summarize identity-bound execution structure from a single source SHA."""
    sha = payload.get("source_sha")
    if not isinstance(sha, str) or HEX40.fullmatch(sha) is None:
        raise ValueError("exact hexadecimal source_sha required")
    jobs = payload.get("jobs")
    if not isinstance(jobs, list):
        raise ValueError("jobs list required")

    runs = _run_index(payload, sha)
    workflow_counts = _outcome_counts()
    workflow_nonterminal = 0
    workflow_unclassified = 0
    workflow_names = set()
    for run in runs.values():
        if isinstance(run.get("name"), str) and run["name"].strip():
            workflow_names.add(run["name"])
        state = _classify_status(
            run.get("status"),
            run.get("conclusion"),
            workflow_counts,
            kind="workflow",
        )
        workflow_nonterminal += state == "nonterminal"
        workflow_unclassified += state == "unclassified"

    seen = set()
    queue = []
    elapsed = []
    intervals = []
    counts = _outcome_counts()
    pending = 0
    runtime_expected = 0
    queue_source_counts = {
        "job_created_at": 0,
        "workflow_run_created_at_fallback": 0,
    }
    jobs_by_run = {}
    runner_ids = set()
    runner_assignments = 0
    runner_detail_jobs = 0
    job_run_links_observed = 0

    step_counts = _outcome_counts()
    step_pending = 0
    step_detail_jobs = 0
    steps_observed = 0
    steps_per_job = []

    for job in jobs:
        if not isinstance(job, dict):
            raise ValueError("job object required")
        if job.get("head_sha") != sha:
            raise ValueError("job SHA differs from source_sha")
        identity = (job.get("run_id"), job.get("run_attempt"), job.get("id"))
        if any(part is None for part in identity) or identity in seen:
            raise ValueError("missing or duplicate native job identity")
        seen.add(identity)

        run_key = (job.get("run_id"), job.get("run_attempt"))
        jobs_by_run[run_key] = jobs_by_run.get(run_key, 0) + 1
        job_run_links_observed += run_key in runs

        if "runner_id" in job:
            runner_detail_jobs += 1
            runner_id = job.get("runner_id")
            if runner_id is not None:
                runner_assignments += 1
                runner_ids.add(runner_id)

        status = job.get("status")
        conclusion = job.get("conclusion")
        state = _classify_status(status, conclusion, counts, kind="job")
        if state == "nonterminal":
            pending += 1
        elif state == "unclassified":
            raise ValueError("native job status required")

        if "steps" in job:
            steps = job["steps"]
            if not isinstance(steps, list):
                raise ValueError("job steps must be a list when supplied")
            step_detail_jobs += 1
            steps_per_job.append(len(steps))
            steps_observed += len(steps)
            for step in steps:
                if not isinstance(step, dict):
                    raise ValueError("step object required")
                step_state = _classify_status(
                    step.get("status"),
                    step.get("conclusion"),
                    step_counts,
                    kind="step",
                )
                step_pending += step_state == "nonterminal"
                if step_state == "unclassified":
                    raise ValueError("native step status required")

        if state != "terminal":
            continue

        queue_start = job.get("created_at")
        queue_source = "job_created_at"
        if queue_start is None:
            queue_start = runs.get(run_key, {}).get("created_at")
            queue_source = "workflow_run_created_at_fallback"
        wait = _duration(queue_start, job.get("started_at"))
        if wait is not None:
            queue.append(wait)
            queue_source_counts[queue_source] += 1

        if conclusion not in RUNTIME_CENSORED:
            runtime_expected += 1
            start = _timestamp(job.get("started_at"))
            end = _timestamp(job.get("completed_at"))
            runtime = _duration(job.get("started_at"), job.get("completed_at"))
            if runtime is not None:
                elapsed.append(runtime)
                if start is not None and end is not None and end > start:
                    intervals.append((start, end))

    jobs_per_run = list(jobs_by_run.values())
    runtime_complete = runtime_expected > 0 and len(elapsed) == runtime_expected
    runtime_sum = sum(elapsed) if runtime_complete else None

    wall_span = None
    parallelism_factor = None
    if runtime_complete and intervals and len(intervals) == runtime_expected:
        first = min(start for start, _end in intervals)
        last = max(end for _start, end in intervals)
        span = (last - first).total_seconds()
        if span >= 0:
            wall_span = span
            if span > 0:
                parallelism_factor = runtime_sum / span

    step_outcomes = step_counts if step_detail_jobs else None
    step_nonterminal = step_pending if step_detail_jobs else None
    observed_steps = steps_observed if step_detail_jobs else None

    return {
        "independent_gates": independent_gate_vector(payload, runs, jobs, sha),
        "schema": "abacus.mip.ci-wave-telemetry.v2",
        "repository": payload.get("repository") or "GBOGEB/ABACUS",
        "source_sha": sha,
        "workflow_records_observed": len(runs),
        "workflow_names_observed": len(workflow_names) if runs else None,
        "workflow_terminal_by_outcome": workflow_counts if runs else None,
        "workflow_nonterminal": workflow_nonterminal if runs else None,
        "workflow_unclassified": workflow_unclassified if runs else None,
        "jobs_observed": len(jobs),
        "job_run_groups_observed": len(jobs_by_run),
        "jobs_per_run_p50": median(jobs_per_run) if jobs_per_run else None,
        "jobs_per_run_p95": _percentile(jobs_per_run, 95),
        "jobs_per_run_max": max(jobs_per_run) if jobs_per_run else None,
        "terminal_by_outcome": counts,
        "nonterminal": pending,
        "step_detail_jobs_observed": step_detail_jobs,
        "step_detail_job_fraction": (
            step_detail_jobs / len(jobs) if jobs else None
        ),
        "steps_observed": observed_steps,
        "steps_per_job_p50": median(steps_per_job) if steps_per_job else None,
        "steps_per_job_p95": _percentile(steps_per_job, 95),
        "steps_per_job_max": max(steps_per_job) if steps_per_job else None,
        "step_terminal_by_outcome": step_outcomes,
        "step_nonterminal": step_nonterminal,
        "job_run_links_observed": job_run_links_observed,
        "job_run_link_fraction": (
            job_run_links_observed / len(jobs) if jobs else None
        ),
        "native_runner_detail_jobs_observed": runner_detail_jobs,
        "native_runner_detail_job_fraction": (
            runner_detail_jobs / len(jobs) if jobs else None
        ),
        "native_runner_assignments_observed": (
            runner_assignments if runner_detail_jobs else None
        ),
        "native_runner_ids_observed": (
            len(runner_ids) if runner_detail_jobs else None
        ),
        "queue_basis": (
            "job.created_at -> job.started_at; "
            "fallback workflow_run.created_at -> job.started_at"
        ),
        "queue_source_counts": queue_source_counts,
        "queue_seconds_p50": median(queue) if queue else None,
        "queue_seconds_p95": _percentile(queue, 95),
        "queue_samples": len(queue),
        "runtime_seconds_sum": runtime_sum,
        "runtime_seconds_p50": median(elapsed) if elapsed else None,
        "runtime_seconds_p95": _percentile(elapsed, 95),
        "runtime_samples": len(elapsed),
        "runtime_expected_samples": runtime_expected,
        "runtime_sample_fraction": (
            len(elapsed) / runtime_expected if runtime_expected else None
        ),
        "runtime_wall_span_seconds": wall_span,
        "peak_runtime_concurrency_observed": _peak_overlap(intervals),
        "realized_parallelism_factor": parallelism_factor,
        "crew_dispatch_authenticated": None,
        "rex_receipts_accepted": None,
        "distinct_bd_roots_closed": None,
        "independent_process_observations": None,
        "authority_transfer": False,
        "merge_authorized": False,
        "security_waiver": False,
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
