"""Fail-closed and non-dispatching GitHub CI rerun wave planner.

Reads exact-head native observations. Never executes a workflow, approves a
review, suppresses security, credits coverage or closes a canonical BD root.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

SCHEMA = "cbd.rerun_snapshot.v1"
REPO = "GBOGEB/ABACUS"
HEX40 = re.compile(r"^[a-f0-9]{40}$")
STATES = {"queued", "pending", "in_progress", "completed"}
TERMINAL = {
    "success",
    "failure",
    "cancelled",
    "skipped",
    "neutral",
    "timed_out",
    "action_required",
}
KINDS = {
    "transient_runner",
    "flake_candidate",
    "rate_limit",
    "source",
    "security",
    "governance",
    "a10",
    "unknown",
}
AUTHORITY = {
    "merge_admission": "HOLD",
    "security_waiver": False,
    "authority_transfer": False,
    "authenticated_worker_dispatch": None,
}


def fingerprint(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def valid_int(v: Any, minimum: int = 0) -> bool:
    return type(v) is int and v >= minimum


def validate(snapshot: dict) -> None:
    if not isinstance(snapshot, dict) or snapshot.get("schema") != SCHEMA:
        raise ValueError("snapshot schema mismatch")
    if snapshot.get("repository") != REPO or snapshot.get("authority") != AUTHORITY:
        raise ValueError("repository/authority mismatch")
    if not HEX40.fullmatch(str(snapshot.get("base_sha", ""))):
        raise ValueError("missing exact base SHA")
    heads = snapshot.get("current_pr_heads")
    if not isinstance(heads, dict) or not heads:
        raise ValueError("missing live PR heads")
    for key, sha in heads.items():
        if (
            not isinstance(key, str)
            or not re.fullmatch(r"[1-9][0-9]*", key)
            or not isinstance(sha, str)
            or not HEX40.fullmatch(sha)
        ):
            raise ValueError("invalid PR source identity")
    cap = snapshot.get("capacity")
    if not isinstance(cap, dict):
        raise ValueError("missing capacity census")
    for field in (
        "queued",
        "in_progress",
        "max_queued",
        "max_in_progress",
        "max_new_reruns",
        "max_attempts",
    ):
        if not valid_int(cap.get(field)):
            raise ValueError("invalid capacity field: " + field)
    if cap["max_attempts"] < 1:
        raise ValueError("max_attempts cannot be zero")
    observations = snapshot.get("observations")
    if not isinstance(observations, list) or not observations:
        raise ValueError("no run observations")
    seen = set()
    for row in observations:
        if not isinstance(row, dict):
            raise ValueError("invalid run row")
        if not valid_int(row.get("pr"), 1) or str(row["pr"]) not in heads:
            raise ValueError("missing PR head binding")
        if not HEX40.fullmatch(str(row.get("head_sha", ""))):
            raise ValueError("invalid run head")
        if not valid_int(row.get("run_id"), 1) or not valid_int(row.get("attempt"), 1):
            raise ValueError("invalid run/attempt")
        if row["run_id"] in seen:
            raise ValueError("duplicate latest run identity")
        seen.add(row["run_id"])
        if not isinstance(row.get("workflow"), str) or not row["workflow"]:
            raise ValueError("missing workflow identity")
        if row.get("status") not in STATES:
            raise ValueError("invalid run state")
        if row["status"] == "completed":
            if row.get("conclusion") not in TERMINAL:
                raise ValueError("missing terminal conclusion")
        elif row.get("conclusion") is not None:
            raise ValueError("nonterminal run cannot have a conclusion")
        link = f'https://github.com/{REPO}/actions/runs/{row["run_id"]}'
        if row.get("url") != link:
            raise ValueError("invalid native run URL")
        first = row.get("first_red")
        if first is None:
            continue
        if (
            not isinstance(first, dict)
            or first.get("kind") not in KINDS
            or type(first.get("verified")) is not bool
        ):
            raise ValueError("unqualified first-red")
        if first["verified"]:
            if row["status"] != "completed" or row["conclusion"] != "failure":
                raise ValueError("verified first-red without failed terminal run")
            if not valid_int(first.get("job_id"), 1):
                raise ValueError("missing native job ID")
            if first.get("url") != f'{link}/job/{first["job_id"]}':
                raise ValueError("invalid native job URL")
            if (
                not isinstance(first.get("root_signature"), str)
                or not first["root_signature"]
            ):
                raise ValueError("missing root signature")


def classify(row: dict, snapshot: dict) -> str:
    if row["head_sha"] != snapshot["current_pr_heads"][str(row["pr"])]:
        return "STALE_SOURCE"
    if row["status"] != "completed":
        return "WAIT_TERMINAL"
    if row["conclusion"] == "success":
        return "COLLECT_PROOF"
    if row["conclusion"] != "failure":
        return "REVIEW_TERMINAL"
    first = row.get("first_red")
    if not first or not first["verified"] or first["kind"] == "unknown":
        return "INSPECT_FIRST_RED"
    if first["kind"] in {"source", "security", "governance", "a10"}:
        return "REPAIR_SOURCE"
    if first["kind"] == "rate_limit":
        return "BACKOFF_RATE_LIMIT"
    if row["attempt"] >= snapshot["capacity"]["max_attempts"]:
        return "RETRY_LIMIT"
    return (
        "RERUN_ONE_JOB" if first["kind"] == "flake_candidate" else "RERUN_FAILED_JOBS"
    )


def compare(previous: dict, current: dict) -> list[dict]:
    """Append-only *partial* census: no fabricated fleet coverage."""
    validate(previous)
    validate(current)
    if previous["base_sha"] != current["base_sha"]:
        raise ValueError("changed base is a new cohort")
    prior = {r["run_id"]: r for r in previous["observations"]}
    events = []
    for row in sorted(current["observations"], key=lambda r: r["run_id"]):
        earlier = prior.get(row["run_id"])
        if earlier is None:
            change = "NEW_OBSERVATION"
        else:
            if earlier["pr"] != row["pr"] or earlier["head_sha"] != row["head_sha"]:
                raise ValueError("conflicting exact-run source")
            if earlier["workflow"] != row["workflow"]:
                raise ValueError("conflicting exact-run workflow identity")
            if row["attempt"] < earlier["attempt"]:
                raise ValueError("attempt rollback")
            if (
                row["attempt"] == earlier["attempt"]
                and (earlier.get("first_red") or {}).get("verified")
                and earlier.get("first_red") != row.get("first_red")
            ):
                raise ValueError(
                    "verified first-red cannot be replaced within a run attempt"
                )
            if row["attempt"] > earlier["attempt"]:
                change = "NEW_ATTEMPT"
            else:
                if earlier["status"] == "completed" and (
                    earlier["status"],
                    earlier["conclusion"],
                ) != (row["status"], row["conclusion"]):
                    raise ValueError("terminal evidence rewritten")
                if (
                    earlier["status"] == row["status"]
                    and earlier["conclusion"] == row["conclusion"]
                ):
                    if earlier.get("first_red") == row.get("first_red"):
                        continue
                    change = "FIRST_RED_UPDATED"
                else:
                    change = (
                        "TERMINAL_TRANSITION"
                        if row["status"] == "completed"
                        else "STATE_CHANGE"
                    )
        events.append(
            {
                "run_id": row["run_id"],
                "pr": row["pr"],
                "head_sha": row["head_sha"],
                "attempt": row["attempt"],
                "event": change,
                "status": row["status"],
                "conclusion": row["conclusion"],
                "allowed_downstream_action": "RECHECK_ONLY",
            }
        )
    return events


def plan(snapshot: dict, previous: dict | None = None) -> dict:
    validate(snapshot)
    cap = snapshot["capacity"]
    saturated = (
        cap["queued"] >= cap["max_queued"]
        or cap["in_progress"] >= cap["max_in_progress"]
    )
    seen_roots = set()
    slots = 0
    proposed = []
    for row in sorted(snapshot["observations"], key=lambda r: (r["pr"], r["run_id"])):
        decision = classify(row, snapshot)
        first = row.get("first_red") or {}
        root = first.get("root_signature")
        if decision in {"RERUN_ONE_JOB", "RERUN_FAILED_JOBS"}:
            if saturated:
                decision = "BACKPRESSURE_HOLD"
            elif root in seen_roots:
                decision = "WAIT_SHARED_ROOT_CANARY"
            elif slots >= cap["max_new_reruns"]:
                decision = "WAIT_RERUN_BUDGET"
            else:
                slots += 1
                seen_roots.add(root)
        proposed.append(
            {
                "pr": row["pr"],
                "head_sha": row["head_sha"],
                "run_id": row["run_id"],
                "attempt": row["attempt"],
                "workflow": row["workflow"],
                "first_red_root": root,
                "action": decision,
                "executed": False,
                "merge_authorized": False,
            }
        )
    states = {s: 0 for s in sorted(STATES)}
    terminals = {s: 0 for s in sorted(TERMINAL)}
    for row in snapshot["observations"]:
        states[row["status"]] += 1
        if row["status"] == "completed":
            terminals[row["conclusion"]] += 1
    out = {
        "schema": "cbd.rerun_plan.v1",
        "repository": REPO,
        "base_sha": snapshot["base_sha"],
        "input_sha256": fingerprint(snapshot),
        "global_queue": {"queued": cap["queued"], "in_progress": cap["in_progress"]},
        "backpressure": saturated,
        "proposed_reruns": slots,
        "sample": {
            "runs": len(snapshot["observations"]),
            "states": states,
            "terminal_conclusions": terminals,
            "later_attempts": sum(r["attempt"] > 1 for r in snapshot["observations"]),
        },
        "proposals": proposed,
        "authority": AUTHORITY,
        "coverage_main_delta": None,
        "coverage_pr_delta": None,
        "formal_bd_roots_closed": None,
        "accepted_rex": None,
        "full_rerun": "OWNER_REVIEW_ONLY_NOT_AUTOMATED",
        "census_updates": "DEDICATED_BRANCH_ONLY; NOOP_ON_SAME_INPUT; RECHECK_ONLY",
    }
    if previous is not None:
        out["changes"] = compare(previous, snapshot)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    prior = (
        json.loads(args.previous.read_text(encoding="utf-8")) if args.previous else None
    )
    result = plan(snapshot, prior)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "sha256": result["input_sha256"],
                "backpressure": result["backpressure"],
                "proposed_reruns": result["proposed_reruns"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
