"""CBD! W38 read-only native PR-feedback event -> routed-PR yield receipt.

This module observes a *successful* trusted gate routing step after --list-prs.
It neither determines eligibility nor changes the existing fail-closed gate,
pending stamps, A-B-A replay guard, event subscriptions or review obligations.
A zero-routed event is a measured routing outcome, not permission to suppress
future review/CI events or close an engineering root.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
from pathlib import Path

REPOSITORY = "GBOGEB/ABACUS"
SCHEMA = "abacus.cbd.feedback-route-yield.w38.v1"
SHA = re.compile(r"[0-9a-f]{40}\Z")
DIRECT_EVENTS = frozenset(
    {
        "issues",
        "issue_comment",
        "pull_request",
        "pull_request_review",
        "pull_request_review_comment",
        "schedule",
        "workflow_dispatch",
    }
)
ALLOWED_EVENTS = DIRECT_EVENTS | {"workflow_run"}
TERMINAL = frozenset(
    {
        "success",
        "failure",
        "cancelled",
        "timed_out",
        "neutral",
        "skipped",
        "action_required",
        "startup_failure",
        "stale",
    }
)


def require(predicate: bool, reason: str) -> None:
    if not predicate:
        raise ValueError(reason)


def canonical(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def identity(value: object, name: str) -> int:
    require(type(value) is int and value > 0, name + "_POSITIVE_INT")
    return value


def sha(value: object, name: str) -> str:
    require(type(value) is str and SHA.fullmatch(value), name + "_EXACT_SHA")
    return value


def parse_route_output(raw: str) -> list[int]:
    require(type(raw) is str and len(raw) <= 16384, "ROUTE_OUTPUT_SIZE")
    try:
        rows = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise ValueError("ROUTE_OUTPUT_JSON") from exc
    require(type(rows) is list and len(rows) <= 300, "ROUTE_OUTPUT_ARRAY")
    for value in rows:
        identity(value, "ROUTED_PR")
    require(len(set(rows)) == len(rows), "DUPLICATE_ROUTED_PR")
    return sorted(rows)


def build(
    event: dict,
    *,
    route_output: str,
    event_name: str,
    repository: str,
    main_sha: str,
    gate_run_id: int,
    gate_attempt: int,
    observed_utc: str,
) -> dict:
    require(type(event) is dict, "EVENT_PAYLOAD_REQUIRED")
    require(repository == REPOSITORY, "OWNER_BOUNDARY")
    main_sha = sha(main_sha, "FEEDBACK_HEAD")
    identity(gate_run_id, "GATE_RUN_ID")
    identity(gate_attempt, "GATE_ATTEMPT")
    require(event_name in ALLOWED_EVENTS, "EVENT_NOT_SUBSCRIBED")
    require(
        type(observed_utc) is str and observed_utc.endswith("Z"), "UTC_SOURCE_TIMESTAMP"
    )
    try:
        t = dt.datetime.fromisoformat(observed_utc.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("UTC_SOURCE_TIMESTAMP") from exc
    require(t.utcoffset() == dt.timedelta(0), "UTC_SOURCE_TIMESTAMP")

    prs = parse_route_output(route_output)
    upstream = None
    if event_name == "workflow_run":
        run = event.get("workflow_run")
        require(type(run) is dict, "UPSTREAM_RUN_REQUIRED")
        require(
            run.get("status") == "completed" and run.get("conclusion") in TERMINAL,
            "UPSTREAM_TERMINAL_REQUIRED",
        )
        upstream = {
            "run_id": identity(run.get("id"), "UPSTREAM_RUN_ID"),
            "attempt": identity(run.get("run_attempt"), "UPSTREAM_ATTEMPT"),
            "name": run.get("name") if type(run.get("name")) is str else None,
            "head_sha": sha(run.get("head_sha"), "UPSTREAM_HEAD"),
            "conclusion": run["conclusion"],
        }
    else:
        # Direct review/issue/PR/schedule events must remain subscribed and
        # cannot be marked safely removable by this observer.
        require("workflow_run" not in event, "AMBIGUOUS_EVENT_CLASS")

    receipt = {
        "schema": SCHEMA,
        "observation_type": "TRUSTED_NATIVE_ROUTE_OUTPUT_NOT_GLOBAL_CAUSATION",
        "source_repository": REPOSITORY,
        "github_event_sha": main_sha,
        "main_head_verified": False,
        "observed_utc": observed_utc,
        "gate_run_id": gate_run_id,
        "gate_attempt": gate_attempt,
        "event": event_name,
        "upstream": upstream,
        "routed_pr_numbers": prs,
        "routed_unique_pr_count": len(prs),
        "route_stage": "ROUTE_OUTPUT_OBSERVED",
        "evaluated_pr_count": None,
        "published_check_count": None,
        "zero_route_observed": len(prs) == 0,
        "eligible_suppression": False,
        "rerun_reduction_verified": None,
        "source_coverage_delta": None,
        "formal_root_closures": None,
        "merge_admission": "HOLD",
        "security_waiver": False,
        "authority_transfer": False,
        "remote_dispatch": False,
    }
    receipt["receipt_sha256"] = hashlib.sha256(canonical(receipt)).hexdigest()
    return receipt


def verify(receipt: dict) -> None:
    require(type(receipt) is dict and receipt.get("schema") == SCHEMA, "RECEIPT_SCHEMA")
    expected = receipt.get("receipt_sha256")
    require(
        type(expected) is str and re.fullmatch(r"[0-9a-f]{64}", expected),
        "RECEIPT_HASH",
    )
    source = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    require(hashlib.sha256(canonical(source)).hexdigest() == expected, "RECEIPT_DRIFT")
    require(
        receipt.get("merge_admission") == "HOLD"
        and receipt.get("security_waiver") is False
        and receipt.get("eligible_suppression") is False
        and receipt.get("formal_root_closures") is None
        and receipt.get("authority_transfer") is False
        and receipt.get("remote_dispatch") is False,
        "AUTHORITY_PROMOTION",
    )
    require(
        receipt.get("source_repository") == REPOSITORY
        and type(receipt.get("github_event_sha")) is str
        and SHA.fullmatch(receipt["github_event_sha"])
        and receipt.get("main_head_verified") is False,
        "EVENT_SHA_NOT_MAIN_ATTESTATION",
    )
    require(
        receipt.get("route_stage") == "ROUTE_OUTPUT_OBSERVED"
        and receipt.get("evaluated_pr_count") is None
        and receipt.get("published_check_count") is None
        and receipt.get("rerun_reduction_verified") is None
        and receipt.get("source_coverage_delta") is None,
        "ROUTE_NOT_EVALUATION_PROOF",
    )
    identity(receipt.get("gate_run_id"), "GATE_RUN_ID")
    identity(receipt.get("gate_attempt"), "GATE_ATTEMPT")
    require(receipt.get("event") in ALLOWED_EVENTS, "RECEIPT_EVENT")
    prs = receipt.get("routed_pr_numbers")
    require(type(prs) is list and len(prs) <= 300, "RECEIPT_ROUTE_LIST")
    for pr in prs:
        identity(pr, "ROUTED_PR")
    require(
        len(prs) == len(set(prs)) and prs == sorted(prs),
        "RECEIPT_DUPLICATE_OR_UNORDERED",
    )
    upstream = receipt.get("upstream")
    if receipt["event"] == "workflow_run":
        require(
            type(upstream) is dict and upstream.get("conclusion") in TERMINAL,
            "RECEIPT_UPSTREAM_TERMINAL",
        )
        identity(upstream.get("run_id"), "UPSTREAM_RUN_ID")
        identity(upstream.get("attempt"), "UPSTREAM_ATTEMPT")
        sha(upstream.get("head_sha"), "UPSTREAM_HEAD")
    else:
        require(upstream is None, "UNEXPECTED_UPSTREAM")
    require(
        receipt["routed_unique_pr_count"] == len(receipt["routed_pr_numbers"]),
        "ROUTE_COUNT_DRIFT",
    )
    require(
        receipt["zero_route_observed"] == (receipt["routed_unique_pr_count"] == 0),
        "FALSE_NOOP",
    )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--event-path", type=Path, required=True)
    p.add_argument("--routed-prs", required=True)
    p.add_argument("--event-name", required=True)
    p.add_argument("--repository", required=True)
    p.add_argument("--event-sha", "--main-sha", dest="event_sha", required=True)
    p.add_argument("--gate-run-id", type=int, required=True)
    p.add_argument("--gate-attempt", type=int, required=True)
    args = p.parse_args()
    observed = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    result = build(
        json.loads(args.event_path.read_text(encoding="utf-8")),
        route_output=args.routed_prs,
        event_name=args.event_name,
        repository=args.repository,
        main_sha=args.event_sha,
        gate_run_id=args.gate_run_id,
        gate_attempt=args.gate_attempt,
        observed_utc=observed.replace("+00:00", "Z"),
    )
    verify(result)
    # GITHUB_SHA is event context, not a verified main branch head.
    # Deliberately prints only typed identifiers. No comments, PR payload
    # bodies, token or owner-private data enter the public Actions log.
    print("CBD_W38_ROUTE_YIELD " + canonical(result).decode().strip())


if __name__ == "__main__":
    main()
