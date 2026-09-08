#!/usr/bin/env python3
"""Generic 3PM/3PR burndown discriminator and preservation gate.

Consumes an item-list JSON and emits stable IDs, five read-only subtask plans,
relationship-scout hints, preservation gates, and timing/result roll-up slots.
It does not delete, rename, merge, or mutate repository truth.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable

SUBTASKS = [
    "identity_and_repo_location",
    "code_and_pipeline_relatives",
    "authority_and_provenance",
    "information_delta_and_preservation",
    "disposition_risk_and_tests",
]


def stable_item_id(item: dict[str, object]) -> str:
    scope = str(item.get("scope", ""))
    kind = str(item.get("type", ""))
    members = sorted(str(x) for x in item.get("members", []) or [])
    raw = json.dumps({"scope": scope, "type": kind, "members": members}, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def relation_hints(path: str) -> list[dict[str, str]]:
    p = Path(path)
    stem = p.stem
    parent = p.parent.as_posix()
    hints = [
        {"edge": "same_folder", "query": parent or "."},
        {"edge": "same_stem", "query": stem},
    ]
    suffix = p.suffix.lower()
    if suffix == ".py":
        hints += [
            {"edge": "documents", "query": stem + " markdown yaml json"},
            {"edge": "workflow_invokes", "query": stem + " workflow"},
        ]
    elif suffix in {".md", ".yaml", ".yml", ".json"}:
        hints += [
            {"edge": "implemented_by", "query": stem + " python"},
            {"edge": "workflow_invokes", "query": stem + " workflow"},
        ]
    return hints


def preservation_disposition(result: dict[str, object]) -> dict[str, object]:
    atoms = result.get("unique_information_atoms", []) or []
    targets = result.get("reintroduction_targets", []) or []
    proof = str(result.get("reintroduction_proof", "NOT_EXECUTED"))
    consumer = str(result.get("consumer_dependency_check", "NOT_EXECUTED"))
    duplicate_proven = bool(result.get("duplicate_or_obsolete_role_proven", False))
    canonical_target = bool(result.get("canonical_target_lineaged", False))
    post_tests = bool(result.get("post_reintroduction_tests_passed", False))
    all_atoms_reintroduced = len(atoms) == len(targets) and proof == "PASS"
    no_live_consumer = consumer == "PASS_NO_REQUIRED_CONSUMER"
    remove_eligible = all(
        [duplicate_proven, canonical_target, post_tests, all_atoms_reintroduced, no_live_consumer]
    )
    return {
        "remove_eligible": remove_eligible,
        "quarantine_required": not remove_eligible,
        "disposition": "REMOVE_ELIGIBLE" if remove_eligible else "QUARANTINE",
        "checks": {
            "duplicate_or_obsolete_role_proven": duplicate_proven,
            "all_unique_information_atoms_reintroduced": all_atoms_reintroduced,
            "canonical_target_lineaged": canonical_target,
            "post_reintroduction_tests_passed": post_tests,
            "no_required_consumer_dependency": no_live_consumer,
        },
    }


def build_plan(payload: dict[str, object]) -> dict[str, object]:
    raw_items = payload.get("items", [])
    if not isinstance(raw_items, list):
        raise TypeError("items must be a list")
    items: list[dict[str, object]] = []
    seen: set[str] = set()
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        item_id = stable_item_id(raw)
        if item_id in seen:
            continue
        seen.add(item_id)
        members = [str(x) for x in raw.get("members", []) or []]
        tasks = []
        for i, subtask in enumerate(SUBTASKS, start=1):
            tasks.append({
                "subtask_id": f"{item_id[:12]}-S{i}",
                "item_id": item_id,
                "subtask": subtask,
                "read_only": True,
                "runner_may_parallelize": True,
                "timing": {"started_ns": None, "finished_ns": None, "duration_ms": None},
            })
        hints = []
        for member in members:
            hints.extend(relation_hints(member))
        items.append({
            "item_id": item_id,
            "scope": raw.get("scope"),
            "type": raw.get("type"),
            "members": sorted(members),
            "cluster": raw.get("cluster"),
            "subtasks": tasks,
            "relationship_hints": hints,
            "disposition": "UNRESOLVED",
            "preservation": {
                "unique_information_atoms": [],
                "reintroduction_targets": [],
                "reintroduction_proof": "NOT_EXECUTED",
                "consumer_dependency_check": "NOT_EXECUTED",
                "duplicate_or_obsolete_role_proven": False,
                "canonical_target_lineaged": False,
                "post_reintroduction_tests_passed": False,
                "remove_eligible": False,
                "quarantine_required": True,
            },
        })
    return {
        "schema_version": "GENERIC-3PM-BURNDOWN-1.0.0",
        "item_count": len(items),
        "items": items,
        "runner_experiment": {
            "arm_A": "1_runner_x_5_sequential_subtasks",
            "arm_B": "5_runners_x_1_subtask_each",
            "metrics": [
                "wall_time_ms", "median_subtask_ms", "p95_subtask_ms",
                "evidence_yield", "edge_yield", "disagreement_rate",
                "rework_rate", "information_loss_failures",
            ],
        },
        "single_writer": True,
        "mutation_allowed": False,
    }


def evaluate_payload(payload: dict[str, object]) -> dict[str, object]:
    items = payload.get("items", [])
    if not isinstance(items, list):
        raise TypeError("items must be a list")
    evaluated = []
    for item in items:
        if not isinstance(item, dict):
            continue
        preservation = item.get("preservation", {})
        if not isinstance(preservation, dict):
            preservation = {}
        decision = preservation_disposition(preservation)
        evaluated.append({
            "item_id": item.get("item_id") or stable_item_id(item),
            "disposition": decision["disposition"],
            "remove_eligible": decision["remove_eligible"],
            "quarantine_required": decision["quarantine_required"],
            "checks": decision["checks"],
        })
    return {
        "schema_version": "GENERIC-3PM-BURNDOWN-EVAL-1.0.0",
        "item_count": len(evaluated),
        "items": evaluated,
        "remove_eligible_count": sum(1 for x in evaluated if x["remove_eligible"]),
        "quarantine_count": sum(1 for x in evaluated if x["quarantine_required"]),
        "mutation_allowed": False,
        "single_writer_required_for_any_later_mutation": True,
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--evaluate", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    source = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = evaluate_payload(source) if args.evaluate else build_plan(source)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"item_count": result["item_count"], "out": str(out)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
