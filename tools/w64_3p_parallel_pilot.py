#!/usr/bin/env python3
"""Execute bounded parallel 3P variant arms over frozen W64 duplicate families.

Read-only pilot. It converts current P2 duplicate findings to stable root items,
runs discovery and discrimination variant arms, and emits timing/yield comparison.
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from generic_3pm_burndown import build_plan, run_all_subtasks

ARM_CHAINS = {
    "ARM_DISCOVERY": ["3PE", "3PL"],
    "ARM_DISCRIMINATION": ["3PC", "3PV"],
}


def p2_to_payload(p2: dict[str, object]) -> dict[str, object]:
    items = []
    for finding in p2.get("findings", []) or []:
        if not isinstance(finding, dict):
            continue
        if finding.get("type") != "duplicate_or_competing_authority":
            continue
        paths = finding.get("paths", []) or []
        items.append({
            "scope": "GBOGEB/ABACUS",
            "type": "duplicate_or_competing_authority",
            "cluster": finding.get("family"),
            "members": sorted(str(x) for x in paths),
        })
    return {"items": items}


def evidence_yield(run: dict[str, object]) -> int:
    total = 0
    for result in run.get("results", []) or []:
        if not isinstance(result, dict):
            continue
        evidence = result.get("evidence", {})
        if not isinstance(evidence, dict):
            continue
        total += int(evidence.get("evidence_yield", 0) or 0)
        total += int(evidence.get("edge_yield", 0) or 0)
    return total


def execute_variant(root: Path, item: dict[str, object], variant: str) -> dict[str, object]:
    started = time.perf_counter_ns()
    run = run_all_subtasks(root, item, variant=variant)
    finished = time.perf_counter_ns()
    return {
        "root_item_id": run["root_item_id"],
        "variant": variant,
        "wall_time_ms": (finished - started) / 1_000_000,
        "subtask_wall_time_ms": run["wall_time_ms"],
        "median_subtask_ms": run["median_subtask_ms"],
        "p95_subtask_ms": run["p95_subtask_ms"],
        "yield": evidence_yield(run),
        "run": run,
    }


def execute_arm(root: Path, items: list[dict[str, object]], arm: str, workers: int) -> dict[str, object]:
    chain = ARM_CHAINS[arm]
    jobs = [(item, variant) for item in items for variant in chain]
    started = time.perf_counter_ns()
    results = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = [pool.submit(execute_variant, root, item, variant) for item, variant in jobs]
        for future in as_completed(futures):
            results.append(future.result())
    finished = time.perf_counter_ns()
    durations = [float(x["wall_time_ms"]) for x in results]
    return {
        "arm": arm,
        "chain": chain,
        "workers": workers,
        "root_item_count": len(items),
        "variant_job_count": len(jobs),
        "wall_time_ms": (finished - started) / 1_000_000,
        "AHT_variant_job_ms": statistics.fmean(durations) if durations else 0.0,
        "median_variant_job_ms": statistics.median(durations) if durations else 0.0,
        "p95_variant_job_ms": max(durations) if durations else 0.0,
        "total_yield": sum(int(x["yield"]) for x in results),
        "results": sorted(results, key=lambda x: (str(x["root_item_id"]), str(x["variant"]))),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--p2", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--out", required=True)
    parser.add_argument("--sample", type=int, default=5)
    parser.add_argument("--discovery-workers", type=int, default=5)
    parser.add_argument("--discrimination-workers", type=int, default=5)
    args = parser.parse_args()

    p2 = json.loads(Path(args.p2).read_text(encoding="utf-8"))
    payload = p2_to_payload(p2)
    plan = build_plan(payload, variant="3PM")
    items = [x for x in plan.get("items", []) if isinstance(x, dict)]
    items = items[: max(1, args.sample)]
    root = Path(args.root).resolve()

    discovery = execute_arm(root, items, "ARM_DISCOVERY", args.discovery_workers)
    discrimination = execute_arm(root, items, "ARM_DISCRIMINATION", args.discrimination_workers)
    result = {
        "schema_version": "W64-3P-PARALLEL-PILOT-1.0.0",
        "mutation_allowed": False,
        "sample_root_items": len(items),
        "stable_root_ids": [str(x.get("item_id")) for x in items],
        "arms": [discovery, discrimination],
        "comparison": {
            "discovery_wall_time_ms": discovery["wall_time_ms"],
            "discrimination_wall_time_ms": discrimination["wall_time_ms"],
            "discovery_total_yield": discovery["total_yield"],
            "discrimination_total_yield": discrimination["total_yield"],
        },
        "DoD": {
            "same_frozen_root_ids": True,
            "all_workers_read_only": True,
            "single_writer_not_invoked": True,
            "no_release_or_engineering_credit": True,
        },
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result["comparison"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
