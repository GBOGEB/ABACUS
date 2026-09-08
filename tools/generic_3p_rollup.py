#!/usr/bin/env python3
"""Roll up generic 3P history into DMAIC, AHT, progress, DoV and statistical gates."""
from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Iterable


def load_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if isinstance(row, dict):
            rows.append(row)
    return rows


def safe_rate(num: float, den: float) -> float:
    return num / den if den else 0.0


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return xs[lo]
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def statistical_eligibility(terminal_n: int, paired_n: int, arm_n: int, complete_n: int, p: int, positives: int) -> dict[str, object]:
    covariance_gate = max(30, 10 * p)
    pca_gate = max(50, 10 * p)
    model_gate = max(50, 10 * p)
    return {
        "descriptive": True,
        "robust_distribution": terminal_n >= 10,
        "paired_pre_post": paired_n >= 20,
        "paired_pre_post_preferred": paired_n >= 30,
        "runner_arm_comparison": arm_n >= 20,
        "runner_arm_preferred": arm_n >= 30,
        "covariance": complete_n >= covariance_gate,
        "covariance_required_n": covariance_gate,
        "empirical_PCA": complete_n >= pca_gate,
        "pca_required_n": pca_gate,
        "empirical_BT": terminal_n >= 30 and positives >= 5,
        "empirical_BT_preferred": terminal_n >= 50 and positives >= 5,
        "multivariable_model": complete_n >= model_gate,
        "multivariable_required_n": model_gate,
    }


def build_rollup(rows: list[dict[str, object]], variables: int = 5) -> dict[str, object]:
    pulses = [r for r in rows if str(r.get("event", "")).upper() != "BASELINE"]
    terminal_ids: set[str] = set()
    durations: list[float] = []
    walls: list[float] = []
    queue_deltas: list[float] = []
    blocker_deltas: list[float] = []
    rework_rates: list[float] = []
    false_positive_rates: list[float] = []
    evidence_yields: list[float] = []
    edge_yields: list[float] = []
    positives = 0
    paired_n = 0
    arm_n = 0
    complete_n = 0

    for row in pulses:
        for item in row.get("root_item_ids", []) or []:
            terminal_ids.add(str(item))
        for key, target in (("median_item_ms", durations), ("wall_time_ms", walls), ("rework_rate", rework_rates), ("false_positive_rate", false_positive_rates), ("evidence_yield", evidence_yields), ("edge_yield", edge_yields)):
            value = row.get(key)
            if isinstance(value, (int, float)):
                target.append(float(value))
        qb, qa = row.get("queue_before"), row.get("queue_after")
        if isinstance(qb, (int, float)) and isinstance(qa, (int, float)):
            queue_deltas.append(float(qb) - float(qa))
        bb, ba = row.get("blockers_before"), row.get("blockers_after")
        if isinstance(bb, (int, float)) and isinstance(ba, (int, float)):
            blocker_deltas.append(float(bb) - float(ba))
        if row.get("positive_outcome") is True:
            positives += 1
        if row.get("paired_pre_post") is True:
            paired_n += 1
        if row.get("runner_arm_comparison") is True:
            arm_n += 1
        required = [row.get(k) for k in ("wall_time_ms", "evidence_yield", "edge_yield", "rework_rate", "false_positive_rate")]
        if all(isinstance(v, (int, float)) for v in required):
            complete_n += 1

    baseline = rows[0] if rows else {}
    initial_queue = float(baseline.get("queue_before", 0) or 0)
    current_queue = float(pulses[-1].get("queue_after", initial_queue) if pulses else initial_queue)
    terminal_n = len(terminal_ids)
    active_hours = safe_rate(sum(walls), 3_600_000.0)
    velocity = safe_rate(terminal_n, active_hours)
    prior_velocity = 0.0
    if len(pulses) > 1:
        prior_walls = [float(r.get("wall_time_ms", 0) or 0) for r in pulses[:-1]]
        prior_ids = {str(i) for r in pulses[:-1] for i in (r.get("root_item_ids", []) or [])}
        prior_velocity = safe_rate(len(prior_ids), safe_rate(sum(prior_walls), 3_600_000.0))

    progress = {
        "initial_queue": initial_queue,
        "current_queue": current_queue,
        "queue_burndown_fraction": safe_rate(initial_queue - current_queue, initial_queue),
        "terminal_sample_n": terminal_n,
        "convergence_velocity_items_per_hour": velocity,
        "convergence_acceleration_items_per_hour2": velocity - prior_velocity,
        "mean_queue_delta_per_pulse": statistics.mean(queue_deltas) if queue_deltas else 0.0,
        "mean_blocker_delta_per_pulse": statistics.mean(blocker_deltas) if blocker_deltas else 0.0,
    }
    aht = {
        "AHT_item_ms": statistics.mean(durations) if durations else None,
        "median_item_ms": statistics.median(durations) if durations else None,
        "p95_item_ms": percentile(durations, 0.95),
        "median_wall_time_ms": statistics.median(walls) if walls else None,
        "p95_wall_time_ms": percentile(walls, 0.95),
    }
    quality = {
        "mean_rework_rate": statistics.mean(rework_rates) if rework_rates else None,
        "mean_false_positive_rate": statistics.mean(false_positive_rates) if false_positive_rates else None,
        "mean_evidence_yield": statistics.mean(evidence_yields) if evidence_yields else None,
        "mean_edge_yield": statistics.mean(edge_yields) if edge_yields else None,
    }
    eligibility = statistical_eligibility(terminal_n, paired_n, arm_n, complete_n, variables, positives)
    dov = {
        "progress_is_not_DoV": True,
        "queue_DoV_candidate": current_queue == 0 and terminal_n > 0,
        "release_DoV": "NOT_EVALUATED_BY_ROLLUP",
        "reason": "Local authority, preservation/reentry receipts, exact-head CI and downstream acceptance remain AND-gated.",
    }
    return {
        "schema_version": "GENERIC-3P-ROLLUP-1.0.0",
        "history_records": len(rows),
        "pulse_records": len(pulses),
        "DMAIC": {
            "D": {"initial_queue": initial_queue, "root_scope_frozen": bool(rows)},
            "M": {"sample_n": terminal_n, **aht},
            "A": {"statistical_eligibility": eligibility, **quality},
            "I": {"mean_blocker_delta_per_pulse": progress["mean_blocker_delta_per_pulse"]},
            "C": {"current_queue": current_queue, "velocity_items_per_hour": velocity, "acceleration_items_per_hour2": progress["convergence_acceleration_items_per_hour2"]},
        },
        "progress": progress,
        "AHT": aht,
        "quality": quality,
        "statistical_eligibility": eligibility,
        "DoV": dov,
        "convergence_signal": "IMPROVING" if progress["convergence_acceleration_items_per_hour2"] > 0 else "NOT_YET_ACCELERATING",
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--variables", type=int, default=5)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = build_rollup(load_jsonl(Path(args.history)), variables=args.variables)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(out), "sample_n": result["progress"]["terminal_sample_n"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
