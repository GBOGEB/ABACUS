#!/usr/bin/env python3
"""Generic 3PM/3PR burndown discriminator, scout, and preservation gate.

The worker is read-only. It assigns stable IDs, scouts repository relationships,
measures five evidence subtasks, and evaluates whether a discriminated candidate
must be quarantined or is eligible for later single-writer removal.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from pathlib import Path
from typing import Iterable

SUBTASKS = [
    "identity_and_repo_location",
    "code_and_pipeline_relatives",
    "authority_and_provenance",
    "information_delta_and_preservation",
    "disposition_risk_and_tests",
]
TEXT_SUFFIXES = {".py", ".md", ".yaml", ".yml", ".json", ".toml", ".ini", ".txt", ".sh"}
AUTHORITY_WORDS = {"ssot", "authority", "contract", "schema", "registry", "manifest", "canonical"}
GENERATED_WORDS = {"generated", "dist", "build", "export", "rendered"}
VERSION_WORDS = {"legacy", "archive", "deprecated", "stale", "old", "v0", "v1", "v2", "v3"}


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


def iter_text_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def read_text_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def file_sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def identity_subtask(root: Path, members: list[str]) -> dict[str, object]:
    records = []
    for member in members:
        path = root / member
        records.append({
            "path": member,
            "exists": path.exists(),
            "is_file": path.is_file(),
            "suffix": path.suffix.lower(),
            "parent": path.parent.relative_to(root).as_posix() if path.parent.is_relative_to(root) else str(path.parent),
            "size": path.stat().st_size if path.is_file() else None,
        })
    return {"records": records, "evidence_yield": sum(1 for x in records if x["exists"])}


def relatives_subtask(root: Path, members: list[str]) -> dict[str, object]:
    needles = {Path(member).stem.lower() for member in members if Path(member).stem}
    relatives: list[dict[str, str]] = []
    member_set = set(members)
    for path in iter_text_files(root):
        rel = path.relative_to(root).as_posix()
        text = read_text_safe(path).lower()
        for needle in needles:
            if needle and needle in text and rel not in member_set:
                relatives.append({"path": rel, "edge": "references_or_documents", "needle": needle})
                break
    same_folder = []
    parents = {Path(member).parent.as_posix() for member in members}
    for parent in parents:
        base = root / parent
        if base.is_dir():
            for path in base.iterdir():
                rel = path.relative_to(root).as_posix()
                if path.is_file() and rel not in member_set:
                    same_folder.append({"path": rel, "edge": "same_folder"})
    combined = relatives[:250] + same_folder[:250]
    return {"edges": combined, "edge_yield": len(combined)}


def authority_subtask(root: Path, members: list[str]) -> dict[str, object]:
    records = []
    for member in members:
        path = root / member
        text = (member + " " + read_text_safe(path)[:20000]).lower() if path.is_file() else member.lower()
        authority_hits = sorted(word for word in AUTHORITY_WORDS if word in text)
        generated_hits = sorted(word for word in GENERATED_WORDS if word in text)
        version_hits = sorted(word for word in VERSION_WORDS if word in text)
        records.append({
            "path": member,
            "authority_hits": authority_hits,
            "generated_hits": generated_hits,
            "version_hits": version_hits,
        })
    return {"records": records, "evidence_yield": sum(bool(x["authority_hits"]) for x in records)}


def information_subtask(root: Path, members: list[str]) -> dict[str, object]:
    records = []
    hashes = []
    for member in members:
        path = root / member
        digest = file_sha256(path) if path.is_file() else None
        hashes.append(digest)
        records.append({"path": member, "sha256": digest, "size": path.stat().st_size if path.is_file() else None})
    valid_hashes = [h for h in hashes if h]
    return {
        "records": records,
        "all_byte_identical": bool(valid_hashes) and len(set(valid_hashes)) == 1,
        "distinct_content_count": len(set(valid_hashes)),
        "unique_information_requires_review": len(set(valid_hashes)) > 1,
    }


def risk_subtask(root: Path, members: list[str]) -> dict[str, object]:
    names = {Path(member).name.lower() for member in members}
    stems = {Path(member).stem.lower() for member in members}
    member_set = set(members)
    consumers = []
    for path in iter_text_files(root):
        rel = path.relative_to(root).as_posix()
        if rel in member_set:
            continue
        text = read_text_safe(path).lower()
        if any(name and name in text for name in names) or any(stem and stem in text for stem in stems):
            consumers.append(rel)
    return {
        "consumer_paths": sorted(set(consumers))[:500],
        "consumer_count": len(set(consumers)),
        "safe_to_remove_without_deeper_consumer_review": len(consumers) == 0,
    }


def run_subtask(root: Path, item: dict[str, object], subtask: str) -> dict[str, object]:
    if subtask not in SUBTASKS:
        raise ValueError(f"unknown subtask: {subtask}")
    members = [str(x) for x in item.get("members", []) or []]
    started = time.perf_counter_ns()
    if subtask == SUBTASKS[0]:
        evidence = identity_subtask(root, members)
    elif subtask == SUBTASKS[1]:
        evidence = relatives_subtask(root, members)
    elif subtask == SUBTASKS[2]:
        evidence = authority_subtask(root, members)
    elif subtask == SUBTASKS[3]:
        evidence = information_subtask(root, members)
    else:
        evidence = risk_subtask(root, members)
    finished = time.perf_counter_ns()
    return {
        "item_id": item.get("item_id") or stable_item_id(item),
        "subtask": subtask,
        "started_ns": started,
        "finished_ns": finished,
        "duration_ms": (finished - started) / 1_000_000,
        "evidence": evidence,
        "read_only": True,
    }


def run_all_subtasks(root: Path, item: dict[str, object]) -> dict[str, object]:
    results = [run_subtask(root, item, subtask) for subtask in SUBTASKS]
    durations = [float(x["duration_ms"]) for x in results]
    return {
        "item_id": item.get("item_id") or stable_item_id(item),
        "results": results,
        "median_subtask_ms": statistics.median(durations) if durations else 0.0,
        "p95_subtask_ms": max(durations) if durations else 0.0,
        "wall_time_ms": sum(durations),
    }


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
    parser.add_argument("--root", default=".")
    parser.add_argument("--evaluate", action="store_true")
    parser.add_argument("--subtask", choices=SUBTASKS)
    parser.add_argument("--item-index", type=int, default=0)
    args = parser.parse_args(list(argv) if argv is not None else None)
    source = json.loads(Path(args.input).read_text(encoding="utf-8"))
    if args.subtask:
        items = source.get("items", [])
        if not isinstance(items, list) or not items:
            raise ValueError("input must contain at least one item")
        item = items[args.item_index]
        if not isinstance(item, dict):
            raise TypeError("selected item must be an object")
        result = run_subtask(Path(args.root).resolve(), item, args.subtask)
    elif args.evaluate:
        result = evaluate_payload(source)
    else:
        result = build_plan(source)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(out)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
