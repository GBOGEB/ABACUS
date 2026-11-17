#!/usr/bin/env python3
"""Read-only, capacity-bounded CODE PURPLE DAG proposal; never dispatch or admit.

The YAML catalog declares ownership and dependency edges. A staged proposal is
NOT a GitHub run, reviewer action, accepted root closure, or CI admission.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

import yaml

HEAD = re.compile(r"^[a-f0-9]{40}$")
SCHEMA = "abacus.governed_recovery.stage.v1"
SCHEDULER = Path("runtime/execution/federated-execution-scheduler.yaml")


def _canonical(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _overlap(first: str, second: str) -> bool:
    a, b = first.rstrip("/"), second.rstrip("/")
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def plan(head_sha: str, config: dict) -> dict:
    """Choose disjoint candidate lanes without treating proposals as execution."""
    if not isinstance(head_sha, str) or not HEAD.fullmatch(head_sha):
        raise ValueError("INVALID_EXACT_HEAD")
    scheduler = config.get("federated_execution_scheduler", {})
    if scheduler.get("moniker") != "DELTA_1":
        raise ValueError("CANONICAL_SCHEDULER_DRIFT")
    wave = scheduler.get("governed_recovery_wave", {})
    if (
        wave.get("action_class") != "STAGE_ONLY"
        or wave.get("merge_admission") != "HOLD"
        or wave.get("auto_merge") is not False
        or wave.get("worker_dispatch_authorized") is not False
    ):
        raise ValueError("UNAUTHORIZED_SCHEDULER_ESCALATION")

    resources = wave.get("resources", {})
    slots = resources.get("proposal_worker_slots")
    if type(slots) is not int or not 1 <= slots <= 8:
        raise ValueError("INVALID_WORKER_CAPACITY")
    for key in (
        "human_approval_slots",
        "secret_configuration_slots",
        "admission_slots",
    ):
        if resources.get(key) != 0:
            raise ValueError("UNVERIFIED_EXTERNAL_AUTHORITY")

    lanes = wave.get("lanes", [])
    if not isinstance(lanes, list) or not lanes:
        raise ValueError("NO_LANES")
    by_id = {}
    for lane in lanes:
        if not isinstance(lane, dict):
            raise ValueError("MALFORMED_LANE")
        key = lane.get("id")
        if not isinstance(key, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]+", key):
            raise ValueError("INVALID_LANE_ID")
        if key in by_id:
            raise ValueError("DUPLICATE_LANE")
        if (
            lane.get("resource") not in ("technical", "owner", "proof", "admission")
            or type(lane.get("priority")) is not int
            or lane["priority"] not in (0, 1, 2)
            or not isinstance(lane.get("source_owner"), str)
            or not isinstance(lane.get("needs"), list)
        ):
            raise ValueError("INVALID_LANE_CONTRACT")
        by_id[key] = lane

    ordered = []
    visiting = set()
    visited = set()

    def visit(key: str) -> None:
        if key not in by_id:
            raise ValueError("UNKNOWN_DEPENDENCY")
        if key in visiting:
            raise ValueError("DAG_CYCLE")
        if key in visited:
            return
        visiting.add(key)
        for dependency in by_id[key]["needs"]:
            visit(dependency)
        visiting.remove(key)
        visited.add(key)
        ordered.append(key)

    for key in sorted(by_id, key=lambda k: (by_id[k]["priority"], k)):
        visit(key)

    chosen = []
    owners = []
    rows = []
    for key in ordered:
        lane = by_id[key]
        resource = lane["resource"]
        if resource == "owner":
            state = "OWNER_ACTION_REQUIRED"
        elif resource == "admission":
            state = "ADMISSION_HOLD"
        elif resource == "proof" or lane["needs"]:
            state = "AWAIT_AUTHENTICATED_DEPENDENCY_RECEIPTS"
        elif len(chosen) >= slots:
            state = "STAGED_CAPACITY_WAIT"
        else:
            owner = lane["source_owner"]
            if owner.startswith(("UNALLOCATED", "AUTHORIZED", "READ_ONLY")):
                raise ValueError("INVALID_TECHNICAL_SOURCE_OWNER")
            if any(_overlap(owner, other) for other in owners):
                raise ValueError("OVERLAPPING_SOURCE_OWNERS")
            chosen.append(key)
            owners.append(owner)
            state = "DISJOINT_PROPOSAL_ONLY"
        rows.append(
            {
                "id": key,
                "priority": lane["priority"],
                "resource": resource,
                "source_owner": lane["source_owner"],
                "needs": list(lane["needs"]),
                "evidence_needed": lane["evidence"],
                "state": state,
            }
        )

    result = {
        "schema": SCHEMA,
        "repo": "GBOGEB/ABACUS",
        "source_head_sha": head_sha,
        "canonical_scheduler": SCHEDULER.as_posix(),
        "action_class": "STAGE_ONLY",
        "planned_worker_slots": slots,
        "selected_disjoint_proposals": chosen,
        "lane_count": len(rows),
        "edge_count": sum(len(x["needs"]) for x in rows),
        "lanes": rows,
        "observed_dispatches": 0,
        "successful_worker_returns": None,
        "verified_distinct_roots_closed": 0,
        "native_admission_receipts": None,
        "human_approval_receipt": None,
        "engineering_credit_delta": 0,
        "formal_credit_delta": 0,
        "merge_admission": "HOLD",
        "mutation_enabled": False,
        "worker_dispatch_authorized": False,
        "authority_transfer": False,
    }
    result["proposal_sha256"] = hashlib.sha256(_canonical(result)).hexdigest()
    return result


def verify(payload: dict) -> None:
    claimed = payload.get("proposal_sha256")
    raw = {k: v for k, v in payload.items() if k != "proposal_sha256"}
    if claimed != hashlib.sha256(_canonical(raw)).hexdigest():
        raise ValueError("PROPOSAL_DIGEST_MISMATCH")
    if (
        payload.get("schema") != SCHEMA
        or payload.get("action_class") != "STAGE_ONLY"
        or payload.get("merge_admission") != "HOLD"
        or payload.get("observed_dispatches") != 0
        or payload.get("verified_distinct_roots_closed") != 0
        or payload.get("formal_credit_delta") != 0
        or payload.get("engineering_credit_delta") != 0
        or payload.get("mutation_enabled") is not False
        or payload.get("worker_dispatch_authorized") is not False
        or payload.get("authority_transfer") is not False
    ):
        raise ValueError("FALSE_DISPATCH_OR_ADMISSION")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    actual = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=args.root,
        capture_output=True,
        text=True,
        check=False,
    )
    if actual.returncode or actual.stdout.strip() != args.expected_head:
        raise SystemExit("OWNER_EXACT_HEAD_MISMATCH")
    config = yaml.safe_load((args.root / SCHEDULER).read_text(encoding="utf-8"))
    result = plan(args.expected_head, config)
    verify(result)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(_canonical(result))
    print(
        json.dumps(
            {
                "planned_workers": len(result["selected_disjoint_proposals"]),
                "lanes": result["lane_count"],
                "edges": result["edge_count"],
                "observed_dispatches": 0,
                "merge_admission": "HOLD",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
