#!/usr/bin/env python3
"""Execute generic 3P scouting over all items for one subtask or all subtasks."""
from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
from typing import Iterable

from generic_3pm_burndown import SUBTASKS, run_all_subtasks, run_subtask, stable_item_id


def load_items(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload.get("items", [])
    if not isinstance(items, list):
        raise TypeError("items must be a list")
    return [item for item in items if isinstance(item, dict)]


def aggregate(records: list[dict[str, object]], mode: str, subtask: str | None) -> dict[str, object]:
    durations: list[float] = []
    evidence_yield = 0.0
    edge_yield = 0.0
    for record in records:
        if mode == "all":
            for result in record.get("results", []) or []:
                if not isinstance(result, dict):
                    continue
                durations.append(float(result.get("duration_ms", 0) or 0))
                evidence = result.get("evidence", {})
                if isinstance(evidence, dict):
                    evidence_yield += float(evidence.get("evidence_yield", 0) or 0)
                    edge_yield += float(evidence.get("edge_yield", 0) or 0)
        else:
            durations.append(float(record.get("duration_ms", 0) or 0))
            evidence = record.get("evidence", {})
            if isinstance(evidence, dict):
                evidence_yield += float(evidence.get("evidence_yield", 0) or 0)
                edge_yield += float(evidence.get("edge_yield", 0) or 0)
    return {
        "mode": mode,
        "subtask": subtask,
        "record_count": len(records),
        "subtask_observations": len(durations),
        "median_subtask_ms": statistics.median(durations) if durations else 0.0,
        "p95_subtask_ms": max(durations) if durations else 0.0,
        "evidence_yield": evidence_yield,
        "edge_yield": edge_yield,
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--out", required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all-subtasks", action="store_true")
    group.add_argument("--subtask", choices=SUBTASKS)
    args = parser.parse_args(list(argv) if argv is not None else None)

    root = Path(args.root).resolve()
    items = load_items(Path(args.input))
    started = time.perf_counter_ns()
    records: list[dict[str, object]] = []
    for item in items:
        normalized = dict(item)
        normalized["item_id"] = stable_item_id(normalized)
        if args.all_subtasks:
            records.append(run_all_subtasks(root, normalized))
        else:
            records.append(run_subtask(root, normalized, str(args.subtask)))
    finished = time.perf_counter_ns()
    mode = "all" if args.all_subtasks else "single_subtask"
    summary = aggregate(records, mode, args.subtask)
    summary.update({
        "schema_version": "GENERIC-3P-BATCH-1.0.0",
        "item_count": len(items),
        "wall_time_ms": (finished - started) / 1_000_000,
        "records": records,
        "read_only": True,
    })
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"item_count": len(items), "out": str(out), "wall_time_ms": summary["wall_time_ms"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
