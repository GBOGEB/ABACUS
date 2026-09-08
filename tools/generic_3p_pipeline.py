#!/usr/bin/env python3
"""Execute the W64 generic 3P pipeline start-to-finish and optionally repeat.

The pipeline is read-only with respect to source truth. It regenerates the W64
census/P2 queue, freezes stable root IDs, benchmarks sequential vs five-worker
scouting, emits proposed history, and computes DMAIC/AHT/DoV roll-up. Any later
source mutation remains a separate single-writer action.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable

from generic_3p_batch import aggregate, load_items
from generic_3p_rollup import build_rollup, load_jsonl
from generic_3pm_burndown import SUBTASKS, build_plan, run_all_subtasks, run_subtask, stable_item_id
from w64_duplicate_queue_to_3p import convert


def run_python(script: Path, args: list[str], cwd: Path) -> None:
    subprocess.run([sys.executable, str(script), *args], cwd=cwd, check=True)


def arm_a(root: Path, items: list[dict[str, object]]) -> dict[str, object]:
    started = time.perf_counter_ns()
    records = []
    for item in items:
        normalized = dict(item)
        normalized["item_id"] = stable_item_id(normalized)
        records.append(run_all_subtasks(root, normalized))
    finished = time.perf_counter_ns()
    summary = aggregate(records, "all", None)
    summary.update({
        "arm": "A",
        "runner_model": "1_runner_x_5_sequential_subtasks",
        "item_count": len(items),
        "wall_time_ms": (finished - started) / 1_000_000,
        "records": records,
    })
    return summary


def _run_subtask_batch(root_text: str, items: list[dict[str, object]], subtask: str) -> dict[str, object]:
    root = Path(root_text)
    started = time.perf_counter_ns()
    records = []
    for item in items:
        normalized = dict(item)
        normalized["item_id"] = stable_item_id(normalized)
        records.append(run_subtask(root, normalized, subtask))
    finished = time.perf_counter_ns()
    summary = aggregate(records, "single_subtask", subtask)
    summary.update({
        "subtask": subtask,
        "wall_time_ms": (finished - started) / 1_000_000,
        "records": records,
    })
    return summary


def arm_b(root: Path, items: list[dict[str, object]]) -> dict[str, object]:
    started = time.perf_counter_ns()
    with concurrent.futures.ProcessPoolExecutor(max_workers=len(SUBTASKS)) as pool:
        futures = [pool.submit(_run_subtask_batch, str(root), items, subtask) for subtask in SUBTASKS]
        batches = [future.result() for future in futures]
    finished = time.perf_counter_ns()
    durations = [float(batch.get("median_subtask_ms", 0) or 0) for batch in batches]
    return {
        "arm": "B",
        "runner_model": "5_read_only_runners_x_1_subtask",
        "item_count": len(items),
        "wall_time_ms": (finished - started) / 1_000_000,
        "median_subtask_ms": sorted(durations)[len(durations) // 2] if durations else 0.0,
        "p95_subtask_ms": max(float(batch.get("p95_subtask_ms", 0) or 0) for batch in batches) if batches else 0.0,
        "evidence_yield": sum(float(batch.get("evidence_yield", 0) or 0) for batch in batches),
        "edge_yield": sum(float(batch.get("edge_yield", 0) or 0) for batch in batches),
        "batches": batches,
    }


def compare_arms(a: dict[str, object], b: dict[str, object]) -> dict[str, object]:
    a_wall = float(a.get("wall_time_ms", 0) or 0)
    b_wall = float(b.get("wall_time_ms", 0) or 0)
    speedup = a_wall / b_wall if b_wall else 0.0
    same_evidence = float(a.get("evidence_yield", 0) or 0) == float(b.get("evidence_yield", 0) or 0)
    same_edges = float(a.get("edge_yield", 0) or 0) == float(b.get("edge_yield", 0) or 0)
    choose_b = speedup >= 1.10 and same_evidence and same_edges
    return {
        "speedup_A_over_B": speedup,
        "evidence_yield_equal": same_evidence,
        "edge_yield_equal": same_edges,
        "quality_regression_detected": not (same_evidence and same_edges),
        "recommended_pool": 5 if choose_b else 1,
        "recommendation": "ARM_B" if choose_b else "ARM_A_OR_HOLD",
        "rule": "choose smallest pool; require >=10% wall-time gain and no measured yield regression",
    }


def pulse_history_record(pulse: int, source_sha: str, item_count: int, a: dict[str, object], b: dict[str, object], comparison: dict[str, object]) -> dict[str, object]:
    chosen = b if comparison.get("recommended_pool") == 5 else a
    return {
        "event": "PULSE",
        "pulse": pulse,
        "repo": "GBOGEB/ABACUS",
        "variant": "3PE>3PC>3PV>3PR",
        "pulse_stage": "POST",
        "runner_pool_requested": comparison.get("recommended_pool"),
        "runner_pool_active": comparison.get("recommended_pool"),
        "sample_size_items": item_count,
        "sample_size_subtasks": item_count * len(SUBTASKS),
        "queue_before": item_count,
        "queue_after": item_count,
        "blockers_before": item_count,
        "blockers_after": item_count,
        "wall_time_ms": chosen.get("wall_time_ms"),
        "median_item_ms": chosen.get("median_subtask_ms"),
        "p95_item_ms": chosen.get("p95_subtask_ms"),
        "evidence_yield": chosen.get("evidence_yield", 0),
        "edge_yield": chosen.get("edge_yield", 0),
        "true_duplicate_rate": None,
        "quarantine_rate": None,
        "removal_eligible_rate": None,
        "information_atoms_extracted": 0,
        "information_atoms_reintroduced": 0,
        "false_positive_rate": 0.0,
        "rework_rate": 0.0,
        "method_version": "W64-GENERIC-3P-FAMILY-1.1.0",
        "source_sha": source_sha,
        "paired_pre_post": False,
        "runner_arm_comparison": True,
        "positive_outcome": bool(float(comparison.get("speedup_A_over_B", 0) or 0) >= 1.10),
        "note": "Read-only discrimination pulse; queue burns only after P3 preservation/reentry disposition.",
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", default="architecture/w64/pulses/latest")
    parser.add_argument("--history", default="architecture/w64/GENERIC_3P_BURNDOWN_HISTORY.jsonl")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--source-sha", default="WORKTREE")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.repeat < 1:
        raise ValueError("--repeat must be >= 1")

    root = Path(args.root).resolve()
    out_dir = (root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    tools = root / "tools"
    p1_path = out_dir / "W64_TOTAL_REPO_CENSUS_P1.json"
    p2_path = out_dir / "W64_TOTAL_REPO_CENSUS_P2_REVERSE_PRESSURE.json"

    run_python(tools / "w64_total_repo_census.py", ["--root", ".", "--out", str(p1_path)], root)
    run_python(tools / "w64_census_reverse_pressure.py", ["--census", str(p1_path), "--out", str(p2_path)], root)
    p2 = json.loads(p2_path.read_text(encoding="utf-8"))
    normalized = convert(p2)
    input_path = out_dir / "duplicate_items.json"
    input_path.write_text(json.dumps(normalized, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    plan = build_plan(normalized)
    (out_dir / "plan.json").write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    items = load_items(input_path)

    proposed_history = load_jsonl(root / args.history)
    pulse_results = []
    for pulse in range(1, args.repeat + 1):
        a = arm_a(root, items)
        b = arm_b(root, items)
        comparison = compare_arms(a, b)
        record = pulse_history_record(pulse, args.source_sha, len(items), a, b, comparison)
        proposed_history.append(record)
        pulse_result = {"pulse": pulse, "arm_A": a, "arm_B": b, "comparison": comparison, "history_record": record}
        pulse_results.append(pulse_result)
        (out_dir / f"pulse_{pulse:03d}.json").write_text(json.dumps(pulse_result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    proposed_history_path = out_dir / "PROPOSED_HISTORY.jsonl"
    proposed_history_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in proposed_history), encoding="utf-8")
    rollup = build_rollup(proposed_history)
    (out_dir / "ROLLUP.json").write_text(json.dumps(rollup, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    receipt = {
        "schema_version": "GENERIC-3P-PIPELINE-RECEIPT-1.0.0",
        "source_sha": args.source_sha,
        "repeat_count": args.repeat,
        "root_item_count": len(items),
        "mutation_performed": False,
        "single_writer_required_for_later_mutation": True,
        "pulse_results": [{"pulse": p["pulse"], "comparison": p["comparison"]} for p in pulse_results],
        "rollup": rollup,
        "next_gate": "P3 unique-information extraction/reintroduction and local-authority disposition before queue burn",
    }
    (out_dir / "PIPELINE_RECEIPT.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"out_dir": str(out_dir), "root_item_count": len(items), "repeat_count": args.repeat}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
