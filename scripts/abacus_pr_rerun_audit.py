#!/usr/bin/env python3
"""ABACUS exact-head GitHub Actions failed-job rerun + lag-diff controller.

Safe PLAN by default. APPLY requires --yes. No merge, waiver, reviewer action,
workflow policy change, or conclusion-to-admission inference is performed.
Python 3.9+; caller needs an authenticated GitHub CLI (`gh`).
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import quote

SHA = re.compile(r"^[0-9a-f]{40}$")
TERMINAL_FAILURE = {"failure"}
NONRETRYABLE_ROOTS = {
    "A10_REVIEW",
    "SAFETY",
    "BANDIT",
    "FORMAT",
    "DEPENDENCY_GRAPH_DISABLED",
    "API_QUOTA",
}
NONTERMINAL = {"queued", "in_progress", "requested", "waiting", "pending"}
SCHEMA = "code-purple.abacus-pr-debug.v1"
DIFF_SCHEMA = "code-purple.abacus-pr-debug-diff.v1"


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def iso(value: dt.datetime) -> str:
    return (
        value.astimezone(dt.timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def parse_time(value: Any) -> dt.datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(dt.timezone.utc)


def seconds_between(earlier: Any, later: Any) -> float | None:
    first, second = parse_time(earlier), parse_time(later)
    if first is None or second is None or first > second:
        return None
    return round((second - first).total_seconds(), 3)


def string(value: Any) -> str:
    return value if isinstance(value, str) else ""


def canonical_sha(value: Any) -> bool:
    return isinstance(value, str) and SHA.fullmatch(value) is not None


def github_api(gh: Any, path: str) -> Any:
    return gh.json(path)


def paged(gh: Any, path: str, item_key: str | None, max_pages: int = 5) -> list[dict]:
    """Explicitly fail on truncated pages rather than silently omit PRs/runs."""
    out: list[dict] = []
    if max_pages < 1:
        raise ValueError("max_pages must be positive")
    for page in range(1, max_pages + 1):
        separator = "&" if "?" in path else "?"
        result = github_api(gh, f"{path}{separator}per_page=100&page={page}")
        items = result.get(item_key) if item_key else result
        if not isinstance(items, list):
            raise ValueError("invalid paginated GitHub response")
        out.extend(items)
        if len(items) < 100:
            return out
    # There may be more data even if exactly 100 on last page. Fail closed.
    raise ValueError(f"GitHub pagination cap reached for {path}; no complete census")


class Gh:
    def __init__(self, executable: str = "gh") -> None:
        self.executable = executable
        self.calls = 0

    def invoke(self, *parts: str) -> str:
        self.calls += 1
        command = [self.executable, *parts]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode:
            # GitHub error text may contain sensitive URL parameters. Do not
            # echo stderr or access tokens into audit artifacts.
            raise RuntimeError(f"gh command failed ({result.returncode}): {parts[0]}")
        return result.stdout

    def json(self, path: str) -> Any:
        return json.loads(self.invoke("api", "-X", "GET", path))

    def rerun_failed(self, repo: str, run_id: int, debug: bool = True) -> None:
        args = ["run", "rerun", str(run_id), "--failed", "--repo", repo]
        if debug:
            args.append("--debug")
        self.invoke(*args)


def linked_to_pr(run: dict, pr: dict) -> bool:
    """Require exact pull head plus PR association or matching branch.

    Synthetic merge heads and other branches are not current-head proof.
    """
    head = pr.get("head") or {}
    sha = head.get("sha")
    if not canonical_sha(sha) or run.get("head_sha") != sha:
        return False
    linked = run.get("pull_requests") or []
    if linked:
        return any(
            isinstance(p, dict) and p.get("number") == pr.get("number") for p in linked
        )
    return run.get("head_branch") == head.get("ref")


def deduplicate_latest(runs: list[dict]) -> tuple[list[dict], int]:
    """Only latest run in each (workflow_id, event) family on exact SHA."""
    sorted_runs = sorted(
        runs,
        key=lambda r: (
            string(r.get("created_at")),
            int(r.get("run_attempt") or 0),
            int(r.get("id") or 0),
        ),
        reverse=True,
    )
    latest, seen = [], set()
    for run in sorted_runs:
        key = (
            run.get("workflow_id") or run.get("path") or run.get("name"),
            run.get("event"),
        )
        if key in seen:
            continue
        seen.add(key)
        latest.append(run)
    return latest, len(runs) - len(latest)


def classify_root(workflow: str, job: str, step: str, text: str = "") -> str:
    blob = " ".join((workflow, job, step, text)).lower()
    # A known scanner name on its own is NOT proof of a rate-limit problem.
    if "api rate limit exceeded for installation" in blob:
        return "API_QUOTA"
    if (
        "dependency review is not supported" in blob
        or "dependency graph is enabled" in blob
    ):
        return "DEPENDENCY_GRAPH_DISABLED"
    if "tender guard" in blob or "a10-guard" in blob:
        return "A10_REVIEW"
    if "safety is red" in blob or "safety check" in blob or "safety" in step.lower():
        return "SAFETY"
    if "bandit" in step.lower() or "bandit" in blob and "ratchet" in blob:
        return "BANDIT"
    if any(
        s in blob
        for s in (
            "black new-debt",
            "code quality checks",
            "isort",
            "format ratchet",
            "quality checks new debt",
        )
    ):
        return "FORMAT"
    if any(s in blob for s in ("unit test", "pytest", "test failure", "testflight")):
        return "TEST_FAILURE"
    return "UNCLASSIFIED"


def first_failure(job: dict) -> dict:
    failing = [
        step
        for step in job.get("steps", [])
        if isinstance(step, dict) and step.get("conclusion") == "failure"
    ]
    failing.sort(key=lambda step: int(step.get("number") or 999999))
    if not failing:
        return {
            "step": None,
            "step_number": None,
            "step_started_at": None,
            "step_completed_at": None,
        }
    step = failing[0]
    return {
        "step": step.get("name"),
        "step_number": step.get("number"),
        "step_started_at": step.get("started_at"),
        "step_completed_at": step.get("completed_at"),
    }


def job_telemetry(job: dict, now: dt.datetime) -> dict:
    start, created, finished = (
        job.get("started_at"),
        job.get("created_at"),
        job.get("completed_at"),
    )
    state = job.get("status")
    now_text = iso(now)
    wait = seconds_between(created, start) if start is not None else None
    censored_wait = seconds_between(created, now_text) if state == "queued" else None
    duration = seconds_between(start, finished) if finished is not None else None
    censored_execution = (
        seconds_between(start, now_text) if state == "in_progress" else None
    )
    return {
        "job_created_at": created,
        "job_started_at": start,
        "job_completed_at": finished,
        "runner_wait_seconds": wait,
        "runner_wait_right_censored_min_seconds": censored_wait,
        "execution_seconds": duration,
        "execution_right_censored_min_seconds": censored_execution,
    }


def capture_failed_jobs(
    gh: Any, repo: str, run: dict, now: dt.datetime, max_pages: int
) -> list[dict]:
    jobs = paged(
        gh,
        f"repos/{repo}/actions/runs/{run['id']}/jobs?filter=latest",
        "jobs",
        max_pages,
    )
    selected = []
    for job in jobs:
        if job.get("conclusion") != "failure":
            continue
        step = first_failure(job)
        selected.append(
            {
                "id": job.get("id"),
                "name": job.get("name"),
                "status": job.get("status"),
                "conclusion": job.get("conclusion"),
                "first_red": step,
                "root_candidate": classify_root(
                    string(run.get("name")),
                    string(job.get("name")),
                    string(step.get("step")),
                ),
                **job_telemetry(job, now),
            }
        )
    return selected


def receipt_for_pr(receipts: dict | None, pr_number: int) -> dict | None:
    if not isinstance(receipts, dict):
        return None
    value = (receipts.get("prs") or {}).get(str(pr_number))
    return value if isinstance(value, dict) else None


def receipt_status(
    rec: dict | None, head_sha: str, last_terminal: str | None, *, channel: str
) -> dict:
    if rec is None:
        return {"state": "NO_RECEIPT", "channel": channel, "lag_seconds": None}
    declared = rec.get("head_sha")
    if declared != head_sha:
        return {
            "state": "STALE_SOURCE_SHA",
            "channel": channel,
            "declared_head": declared,
            "lag_seconds": None,
        }
    emitted = rec.get("observed_at")
    if parse_time(emitted) is None:
        return {
            "state": "NO_TRUSTED_TIMESTAMP",
            "channel": channel,
            "lag_seconds": None,
        }
    lag = seconds_between(emitted, last_terminal) if last_terminal else None
    return {
        "state": (
            "BEHIND_NATIVE"
            if lag is not None and lag > 0
            else "HEAD_MATCHED_UNATTESTED"
        ),
        "channel": channel,
        "lag_seconds": lag,
        "declared_head": declared,
        "observed_at": emitted,
    }


def _pr_lag_tags(pr_state: dict, threshold_minutes: int) -> list[str]:
    flags = []
    if pr_state["current_runs"] == 0:
        flags.append("MISSING_CURRENT_HEAD_CI")
    if pr_state["stale_branch_runs"]:
        flags.append("HISTORICAL_STALE_RUNS_PRESENT")
    if pr_state["pending_runs"]:
        flags.append("GITHUB_CI_NONTERMINAL")
    if pr_state["failed_runs"]:
        flags.append("NATIVE_FAILURE_UNRESOLVED")
    if pr_state["review_pending"]:
        flags.append("REVIEW_OBLIGATION_PENDING")
    if pr_state["agent_receipt"]["state"] == "STALE_SOURCE_SHA":
        flags.append("AGENT_SNAPSHOT_STALE")
    if pr_state["dashboard_receipt"]["state"] == "STALE_SOURCE_SHA":
        flags.append("DASHBOARD_SNAPSHOT_STALE")
    if (
        pr_state["dashboard_receipt"]["state"] == "BEHIND_NATIVE"
        and (pr_state["dashboard_receipt"].get("lag_seconds") or 0)
        >= threshold_minutes * 60
    ):
        flags.append("DASHBOARD_PUBLICATION_LAG")
    if (
        pr_state["agent_receipt"]["state"] == "BEHIND_NATIVE"
        and (pr_state["agent_receipt"].get("lag_seconds") or 0)
        >= threshold_minutes * 60
    ):
        flags.append("AGENT_OBSERVATION_LAG")
    return flags or ["NO_MATERIAL_OBSERVED_LAG"]


def select_run(
    run: dict,
    jobs: list[dict],
    policy: str,
    cooldown_minutes: int,
    now: dt.datetime,
    journal: dict,
    pr_no: int,
) -> tuple[bool, str]:
    if (
        run.get("status") != "completed"
        or run.get("conclusion") not in TERMINAL_FAILURE
    ):
        return False, "NONTERMINAL_OR_NONFAILURE"
    identity = f"{pr_no}:{run['id']}:{run.get('run_attempt', 1)}:{run.get('head_sha')}"
    if identity in journal:
        return False, "JOURNAL_PREVENTS_DUPLICATE_ATTEMPT"
    last_update = parse_time(run.get("updated_at"))
    if last_update and (now - last_update).total_seconds() < 60 * cooldown_minutes:
        return False, "COOLDOWN"
    roots = {job.get("root_candidate") for job in jobs}
    if policy == "retryable" and (not roots or roots & NONRETRYABLE_ROOTS):
        return False, "SOURCE_OWNER_OR_ADMIN_ROOT"
    return True, "ELIGIBLE_EXACT_HEAD_FAILED_RUN"


def scan(
    gh: Any,
    repo: str,
    max_pages: int,
    max_prs: int,
    exclude_drafts: bool,
    agent_receipts: dict | None,
    dashboard_receipts: dict | None,
    policy: str,
    cooldown_minutes: int,
    journal: dict,
    threshold_minutes: int,
    now: dt.datetime,
    only_prs: set[int] | None = None,
) -> dict:
    raw = paged(gh, f"repos/{repo}/pulls?state=open", None, max_pages)
    selected = [x for x in raw if not exclude_drafts or not x.get("draft")]
    if only_prs is not None:
        selected = [x for x in selected if x.get("number") in only_prs]
    if max_prs > 0:
        selected = selected[:max_prs]
    out = {
        "schema": SCHEMA,
        "repository": repo,
        "observed_at": iso(now),
        "all_open_pr_count": len(raw),
        "selected_pr_count": len(selected),
        "selection_complete": max_prs == 0 and only_prs is None and not exclude_drafts,
        "prs": {},
        "rerun_candidates": [],
        "source": "GitHub REST via gh CLI",
        "external_receipts_authenticated": False,
        "merge_admission": "HOLD",
    }
    for pr in selected:
        head = pr.get("head") or {}
        sha = head.get("sha")
        number = pr.get("number")
        if not canonical_sha(sha) or type(number) is not int:
            raise ValueError("invalid current pull head / PR number")
        branch = head.get("ref") or ""
        # `head_sha` makes the current-head cohort authoritative; the branch
        # query independently shows stale historical workflow observations.
        current_pool = paged(
            gh, f"repos/{repo}/actions/runs?head_sha={sha}", "workflow_runs", max_pages
        )
        current_pool = [r for r in current_pool if linked_to_pr(r, pr)]
        history = paged(
            gh,
            f"repos/{repo}/actions/runs?branch={quote(branch, safe='')}",
            "workflow_runs",
            max_pages,
        )
        stale = [
            r
            for r in history
            if r.get("head_sha") != sha and r.get("head_branch") == branch
        ]
        latest, redundant = deduplicate_latest(current_pool)
        last_terminal = (
            max(
                (
                    string(x.get("updated_at"))
                    for x in latest
                    if x.get("status") == "completed"
                ),
                default=None,
            )
            or None
        )
        failed = [
            r
            for r in latest
            if r.get("conclusion") == "failure" and r.get("status") == "completed"
        ]
        pending = [r for r in latest if r.get("status") != "completed"]
        review_pending = bool(pr.get("requested_reviewers"))
        summary = {
            "number": number,
            "title": string(pr.get("title")),
            "head_sha": sha,
            "head_branch": branch,
            "base_sha": (pr.get("base") or {}).get("sha"),
            "draft": bool(pr.get("draft")),
            "url": pr.get("html_url"),
            "pr_created_at": pr.get("created_at"),
            "pr_updated_at": pr.get("updated_at"),
            "last_terminal_ci_updated_at": last_terminal,
            "review_pending": review_pending,
            "requested_reviewers": [
                r.get("login") for r in pr.get("requested_reviewers", [])
            ],
            "current_runs": len(current_pool),
            "current_workflow_families": len(latest),
            "superseded_same_head_runs": redundant,
            "stale_branch_runs": len(stale),
            "latest_stale_head": stale[0].get("head_sha") if stale else None,
            "pending_runs": len(pending),
            "failed_runs": len(failed),
            "successful_runs": sum(x.get("conclusion") == "success" for x in latest),
            "workflows": [],
            "agent_receipt": receipt_status(
                receipt_for_pr(agent_receipts, number),
                sha,
                last_terminal,
                channel="agent",
            ),
            "dashboard_receipt": receipt_status(
                receipt_for_pr(dashboard_receipts, number),
                sha,
                last_terminal,
                channel="dashboard",
            ),
        }
        for run in latest:
            record = {
                "id": run.get("id"),
                "name": run.get("name"),
                "workflow_id": run.get("workflow_id"),
                "event": run.get("event"),
                "head_sha": sha,
                "attempt": run.get("run_attempt") or 1,
                "status": run.get("status"),
                "conclusion": run.get("conclusion"),
                "created_at": run.get("created_at"),
                "updated_at": run.get("updated_at"),
                "url": run.get("html_url"),
                "failed_jobs": [],
            }
            if run in failed:
                record["failed_jobs"] = capture_failed_jobs(
                    gh, repo, run, now, max_pages
                )
                can_run, reason = select_run(
                    run,
                    record["failed_jobs"],
                    policy,
                    cooldown_minutes,
                    now,
                    journal,
                    number,
                )
                record["rerun_eligible"] = can_run
                record["rerun_disposition"] = reason
                if can_run:
                    out["rerun_candidates"].append(
                        {
                            "pr": number,
                            "head_sha": sha,
                            "run_id": run["id"],
                            "attempt": run.get("run_attempt") or 1,
                            "workflow_name": run.get("name"),
                            "first_red_candidates": [
                                x["root_candidate"] for x in record["failed_jobs"]
                            ],
                        }
                    )
            summary["workflows"].append(record)
        # These are failure-job-only observations; they do not represent the
        # entire runner population or native test wall-clock distribution.
        observed_wait = sorted(
            j["runner_wait_seconds"]
            for w in summary["workflows"]
            for j in w["failed_jobs"]
            if j["runner_wait_seconds"] is not None
        )
        total_failed_jobs = sum(len(w["failed_jobs"]) for w in summary["workflows"])
        wait_n = len(observed_wait)
        summary["failure_job_telemetry"] = {
            "failed_jobs_inspected": total_failed_jobs,
            "runner_wait_observed_n": wait_n,
            "runner_wait_unknown_n": total_failed_jobs - wait_n,
            "runner_wait_p50_seconds": (
                observed_wait[(wait_n - 1) // 2] if wait_n else None
            ),
            "runner_wait_p95_seconds": (
                observed_wait[(95 * wait_n + 99) // 100 - 1] if wait_n else None
            ),
            "runner_wait_p95_qualified": wait_n >= 20 and wait_n == total_failed_jobs,
            "scope": "latest_failed_jobs_only_not_all_native_jobs",
            "queue_and_run_censoring": "pending jobs not sampled; global p95 UNKNOWN",
        }
        summary["lag_flags"] = _pr_lag_tags(summary, threshold_minutes)
        out["prs"][str(number)] = summary
    out["summary"] = {
        "current_head_prs": len(out["prs"]),
        "current_workflow_runs": sum(p["current_runs"] for p in out["prs"].values()),
        "latest_failed_workflows": sum(p["failed_runs"] for p in out["prs"].values()),
        "latest_pending_workflows": sum(p["pending_runs"] for p in out["prs"].values()),
        "missing_ci_prs": sum(p["current_runs"] == 0 for p in out["prs"].values()),
        "stale_run_observations": sum(
            p["stale_branch_runs"] for p in out["prs"].values()
        ),
        "eligible_rerun_runs": len(out["rerun_candidates"]),
    }
    return out


def diff_snapshots(before: dict | None, after: dict) -> dict:
    old_prs = before.get("prs", {}) if before else {}
    changes = []
    for key in sorted(set(old_prs) | set(after.get("prs", {})), key=lambda n: int(n)):
        old = old_prs.get(key)
        new = after.get("prs", {}).get(key)
        if new is None:
            changes.append(
                {
                    "pr": int(key),
                    "kind": "PR_LEFT_SCOPE",
                    "before_head": old.get("head_sha"),
                }
            )
            continue
        if old is None:
            changes.append(
                {
                    "pr": int(key),
                    "kind": "PR_NEWLY_OBSERVED",
                    "current_head": new.get("head_sha"),
                }
            )
            continue
        if old.get("head_sha") != new.get("head_sha"):
            changes.append(
                {
                    "pr": int(key),
                    "kind": "SOURCE_HEAD_ADVANCED",
                    "old_head": old.get("head_sha"),
                    "new_head": new.get("head_sha"),
                }
            )
        old_runs = {
            (w.get("workflow_id"), w.get("event")): w for w in old.get("workflows", [])
        }
        new_runs = {
            (w.get("workflow_id"), w.get("event")): w for w in new.get("workflows", [])
        }
        for signature in sorted(set(old_runs) | set(new_runs), key=str):
            a, b = old_runs.get(signature), new_runs.get(signature)
            if b is None:
                changes.append(
                    {
                        "pr": int(key),
                        "kind": "WORKFLOW_MISSING_FROM_HEAD",
                        "workflow": a.get("name"),
                        "previous_run": a.get("id"),
                    }
                )
            elif a is None:
                changes.append(
                    {
                        "pr": int(key),
                        "kind": "NEW_WORKFLOW_EVIDENCE",
                        "workflow": b.get("name"),
                        "new_run": b.get("id"),
                    }
                )
            else:
                if (
                    a.get("attempt"),
                    a.get("status"),
                    a.get("conclusion"),
                    a.get("id"),
                ) != (
                    b.get("attempt"),
                    b.get("status"),
                    b.get("conclusion"),
                    b.get("id"),
                ):
                    changes.append(
                        {
                            "pr": int(key),
                            "kind": "WORKFLOW_ATTEMPT_OR_STATUS_CHANGED",
                            "workflow": b.get("name"),
                            "from": {
                                x: a.get(x)
                                for x in ("id", "attempt", "status", "conclusion")
                            },
                            "to": {
                                x: b.get(x)
                                for x in ("id", "attempt", "status", "conclusion")
                            },
                        }
                    )
                old_red = sorted(
                    (j.get("root_candidate"), j.get("first_red", {}).get("step"))
                    for j in a.get("failed_jobs", [])
                )
                new_red = sorted(
                    (j.get("root_candidate"), j.get("first_red", {}).get("step"))
                    for j in b.get("failed_jobs", [])
                )
                if old_red != new_red:
                    changes.append(
                        {
                            "pr": int(key),
                            "kind": "FIRST_RED_CANDIDATES_CHANGED",
                            "workflow": b.get("name"),
                            "old_candidates": old_red,
                            "new_candidates": new_red,
                        }
                    )
                elif (
                    old_red
                    and new_red
                    and a.get("attempt") != b.get("attempt")
                    and a.get("conclusion") == b.get("conclusion") == "failure"
                    and old.get("head_sha") == new.get("head_sha")
                ):
                    changes.append(
                        {
                            "pr": int(key),
                            "kind": "SAME_HEAD_FIRST_RED_PERSISTED",
                            "workflow": b.get("name"),
                            "candidates": new_red,
                        }
                    )
        for channel in ("agent", "dashboard"):
            a = (old.get(f"{channel}_receipt") or {}).get("state")
            b = (new.get(f"{channel}_receipt") or {}).get("state")
            if a != b:
                changes.append(
                    {
                        "pr": int(key),
                        "kind": channel.upper() + "_TELEMETRY_CHANGED",
                        "from": a,
                        "to": b,
                    }
                )
        if old.get("lag_flags") != new.get("lag_flags"):
            changes.append(
                {
                    "pr": int(key),
                    "kind": "LAG_CLASSIFICATION_CHANGED",
                    "from": old.get("lag_flags"),
                    "to": new.get("lag_flags"),
                }
            )
    return {
        "schema": DIFF_SCHEMA,
        "previous_observed_at": before.get("observed_at") if before else None,
        "current_observed_at": after["observed_at"],
        "changes": changes,
        "counts": dict(Counter(c["kind"] for c in changes)),
        "attribution_note": "Lag flags identify boundaries, not human/agent causality or fault.",
        "merge_admission": "HOLD",
    }


def markdown_diff(report: dict, after: dict) -> str:
    lines = [
        "# ABACUS governed PR rerun and telemetry diff",
        "",
        f"- Observed: `{after['observed_at']}`",
        f"- Repository: `{after['repository']}`",
        f"- Open PRs selected: **{after['selected_pr_count']}** / {after['all_open_pr_count']}",
        f"- Failed current-head workflow families: **{after['summary']['latest_failed_workflows']}**",
        f"- Eligible failed-job reruns: **{after['summary']['eligible_rerun_runs']}**",
        f"- Pending current-head workflows: **{after['summary']['latest_pending_workflows']}**",
        f"- Missing current-head CI: **{after['summary']['missing_ci_prs']} PRs**",
        "- Admission: **HOLD** (not a merge controller)",
        "",
        "| PR | Head | Failed | Pending | Stale historical | Agent receipt | Dashboard receipt | Lag flags |",
        "| --- | --- | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for key in sorted(after["prs"], key=int):
        pr = after["prs"][key]
        lines.append(
            f"| #{key} | `{pr['head_sha'][:12]}` | {pr['failed_runs']} | {pr['pending_runs']} | "
            f"{pr['stale_branch_runs']} | {pr['agent_receipt']['state']} | "
            f"{pr['dashboard_receipt']['state']} | {', '.join(pr['lag_flags'])} |"
        )
    lines.extend(["", "## N-1 to N observed transitions", ""])
    for c in report["changes"]:
        lines.append(
            f"- PR #{c['pr']}: **{c['kind']}** "
            + (f"({c['workflow']})" if c.get("workflow") else "")
        )
    if not report["changes"]:
        lines.append(
            "No transition was observed in the compared samples. This does not prove system stability."
        )
    lines.extend(
        [
            "",
            "## Attribution controls",
            "",
            "- `MISSING_CURRENT_HEAD_CI`: GitHub has no head-bound workflow observation; check triggers/dispatch.",
            "- `GITHUB_CI_NONTERMINAL`: queue or execution pending; runner queue time requires job-created/start timestamps.",
            "- `AGENT_SNAPSHOT_STALE`: a supplied agent receipt has a different source head; not proof of agent fault.",
            "- `DASHBOARD_SNAPSHOT_STALE`: a supplied dashboard receipt identifies a previous source head.",
            "- `DASHBOARD_PUBLICATION_LAG`: native completion newer than dashboard observation, based on supplied receipts.",
            "- `REVIEW_OBLIGATION_PENDING`: requested reviewers exist; no conclusion about human delay without review timestamps.",
            "- Missing agent/dashboard receipts are `NO_RECEIPT`, not zero latency.",
            "- These reports do not authenticate external receipt bytes or waive security/A10/required CI.",
            "",
        ]
    )
    return "\n".join(lines)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    tmp.replace(path)


def read_json(path: Path | None) -> dict | None:
    if path is None:
        return None
    if not path.exists():
        raise FileNotFoundError(str(path))
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("JSON receipt must be an object")
    return obj


def write_reports(
    out: Path, before: dict | None, after: dict, actions: list[dict]
) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    # A distinct UUID prevents overwriting two immutable snapshots made in
    # the same second; timestamps alone do not guarantee uniqueness.
    import uuid

    stamp = after["observed_at"].replace(":", "").replace("-", "")
    snapshots = out / "snapshots"
    snapshot_path = snapshots / f"{stamp}_{uuid.uuid4().hex[:12]}.json"
    write_json(snapshot_path, after)
    write_json(out / "latest.json", after)
    diff = diff_snapshots(before, after)
    write_json(out / "diff.json", diff)
    (out / "diff.md").write_text(markdown_diff(diff, after), encoding="utf-8")
    write_json(
        out / "rerun_actions.json",
        {"schema": SCHEMA, "actions": actions, "observed_at": after["observed_at"]},
    )
    with (out / "bd_queue.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "pr",
                "head",
                "workflow",
                "run_id",
                "attempt",
                "status",
                "conclusion",
                "root_candidates",
                "rerun_eligible",
                "disposition",
                "url",
            ]
        )
        for pr_no, pr in sorted(after["prs"].items(), key=lambda kv: int(kv[0])):
            for item in pr["workflows"]:
                writer.writerow(
                    [
                        pr_no,
                        pr["head_sha"],
                        item.get("name"),
                        item.get("id"),
                        item.get("attempt"),
                        item.get("status"),
                        item.get("conclusion"),
                        ";".join(
                            x.get("root_candidate", "") for x in item["failed_jobs"]
                        ),
                        item.get("rerun_eligible", False),
                        item.get("rerun_disposition", ""),
                        item.get("url"),
                    ]
                )
    manifest = {}
    for filename in (
        "latest.json",
        "diff.json",
        "diff.md",
        "rerun_actions.json",
        "bd_queue.csv",
    ):
        data = (out / filename).read_bytes()
        manifest[filename] = {
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
        }
    data = snapshot_path.read_bytes()
    manifest[str(snapshot_path.relative_to(out))] = {
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }
    write_json(out / "manifest.json", {"files": manifest, "admission": "HOLD"})
    return out


def apply_candidates(
    gh: Any,
    repo: str,
    candidates: list[dict],
    max_reruns: int,
    delay_seconds: float,
    yes: bool,
    audit_dir: Path,
    journal: dict,
    debug: bool,
) -> list[dict]:
    if not yes:
        raise ValueError("APPLY requires --yes and user authorization")
    if max_reruns <= 0 or max_reruns > 100:
        raise ValueError("max-reruns must be 1..100")
    actions = []
    for item in candidates:
        if len(actions) >= max_reruns:
            actions.append(
                {"pr": item["pr"], "run_id": item["run_id"], "result": "SKIPPED_BUDGET"}
            )
            continue
        pr = github_api(gh, f"repos/{repo}/pulls/{item['pr']}")
        current_head = (pr.get("head") or {}).get("sha")
        if pr.get("state") != "open" or current_head != item["head_sha"]:
            actions.append(
                {
                    "pr": item["pr"],
                    "run_id": item["run_id"],
                    "result": "SKIPPED_HEAD_DRIFT",
                }
            )
            continue
        run = github_api(gh, f"repos/{repo}/actions/runs/{item['run_id']}")
        if (
            run.get("head_sha") != current_head
            or run.get("status") != "completed"
            or run.get("conclusion") != "failure"
            or (run.get("run_attempt") or 1) != item["attempt"]
        ):
            actions.append(
                {
                    "pr": item["pr"],
                    "run_id": item["run_id"],
                    "result": "SKIPPED_RUN_ATTEMPT_DRIFT",
                }
            )
            continue
        identity = f"{item['pr']}:{item['run_id']}:{item['attempt']}:{item['head_sha']}"
        if identity in journal:
            actions.append(
                {
                    "pr": item["pr"],
                    "run_id": item["run_id"],
                    "result": "SKIPPED_JOURNAL_DUPLICATE",
                }
            )
            continue
        # Write a journal reservation before the write call to prevent repeat
        # dispatch after a process crash/timeout; operator reconciles errors.
        journal[identity] = {"result": "REQUESTED", "time": iso(utcnow())}
        write_json(audit_dir / "rerun_journal.json", journal)
        result = {
            "pr": item["pr"],
            "head_sha": item["head_sha"],
            "run_id": item["run_id"],
            "original_attempt": item["attempt"],
            "debug": debug,
            "requested_at": iso(utcnow()),
        }
        try:
            gh.rerun_failed(repo, item["run_id"], debug)
            result["result"] = "DISPATCH_ACCEPTED_NOT_COMPLETED"
            journal[identity]["result"] = result["result"]
        except RuntimeError as exc:
            result["result"] = "DISPATCH_ERROR_REQUIRES_RECONCILIATION"
            result["error_type"] = type(exc).__name__
            journal[identity]["result"] = result["result"]
        write_json(audit_dir / "rerun_journal.json", journal)
        actions.append(result)
        # Delay between dispatches only, not after the final item.
        if delay_seconds > 0 and len(actions) < max_reruns:
            time.sleep(delay_seconds)
    return actions


def args_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("plan", "apply", "refresh"), default="plan")
    parser.add_argument("--repo", default="GBOGEB/ABACUS")
    parser.add_argument(
        "--policy", choices=("retryable", "all-failed"), default="retryable"
    )
    parser.add_argument("--max-reruns", type=int, default=8)
    parser.add_argument("--max-prs", type=int, default=0, help="0 means all open PRs")
    parser.add_argument("--max-pages", type=int, default=5)
    parser.add_argument("--exclude-drafts", action="store_true")
    parser.add_argument("--only-pr", type=int, action="append")
    parser.add_argument("--delay-seconds", type=float, default=20)
    parser.add_argument("--cooldown-minutes", type=int, default=45)
    parser.add_argument("--lag-threshold-minutes", type=int, default=30)
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--no-debug", action="store_true")
    parser.add_argument(
        "--audit-dir", type=Path, default=Path(".artifacts/abacus-pr-debug")
    )
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--agent-receipts", type=Path)
    parser.add_argument("--dashboard-receipts", type=Path)
    parser.add_argument("--gh", default="gh")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = args_parser().parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repo):
        raise ValueError("invalid repository selector")
    if args.mode == "apply" and not args.yes:
        raise ValueError("write mode requires explicit --yes")
    if (
        args.max_pages < 1
        or args.max_prs < 0
        or args.cooldown_minutes < 0
        or args.delay_seconds < 0
    ):
        raise ValueError("invalid scan or rate budget")
    output = args.audit_dir
    previous = (
        read_json(args.baseline)
        if args.baseline
        else (
            read_json(output / "latest.json")
            if (output / "latest.json").exists()
            else None
        )
    )
    journal = (
        read_json(output / "rerun_journal.json")
        if (output / "rerun_journal.json").exists()
        else {}
    )
    gh = Gh(args.gh)
    before = scan(
        gh,
        args.repo,
        args.max_pages,
        args.max_prs,
        args.exclude_drafts,
        read_json(args.agent_receipts),
        read_json(args.dashboard_receipts),
        args.policy,
        args.cooldown_minutes,
        journal,
        args.lag_threshold_minutes,
        utcnow(),
        set(args.only_pr) if args.only_pr else None,
    )
    actions: list[dict] = []
    after = before
    if args.mode == "apply":
        actions = apply_candidates(
            gh,
            args.repo,
            before["rerun_candidates"],
            args.max_reruns,
            args.delay_seconds,
            args.yes,
            output,
            journal,
            not args.no_debug,
        )
        after = scan(
            gh,
            args.repo,
            args.max_pages,
            args.max_prs,
            args.exclude_drafts,
            read_json(args.agent_receipts),
            read_json(args.dashboard_receipts),
            args.policy,
            args.cooldown_minutes,
            journal,
            args.lag_threshold_minutes,
            utcnow(),
            set(args.only_pr) if args.only_pr else None,
        )
    write_reports(output, previous, after, actions)
    print(
        json.dumps(
            {
                "mode": args.mode,
                "repository": args.repo,
                "selected_prs": after["selected_pr_count"],
                "failed_workflows": after["summary"]["latest_failed_workflows"],
                "eligible_reruns": after["summary"]["eligible_rerun_runs"],
                "dispatched_requests": sum(
                    a.get("result") == "DISPATCH_ACCEPTED_NOT_COMPLETED"
                    for a in actions
                ),
                "report": str(output / "diff.md"),
                "admission": "HOLD",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        print("ABACUS_PR_DEBUG_ERROR: " + str(exc), file=sys.stderr)
        raise SystemExit(2)
