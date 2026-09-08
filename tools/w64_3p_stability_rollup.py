#!/usr/bin/env python3
"""Compute comparable-run speedups and conservative stability status for 3P execution."""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path


def ratio(base: float, current: float) -> float | None:
    if base <= 0 or current <= 0:
        return None
    return base / current


def gain(current: float, base: float) -> float | None:
    if base <= 0:
        return None
    return current / base - 1.0


def run_metric(run: dict[str, object], key: str) -> float:
    try:
        return float(run.get(key, 0.0))
    except (TypeError, ValueError):
        return 0.0


def comparable(a: dict[str, object], b: dict[str, object]) -> bool:
    return (
        a.get("stratum") == b.get("stratum")
        and a.get("measurement_contract") == b.get("measurement_contract")
    )


def speed_view(base: dict[str, object], current: dict[str, object]) -> dict[str, object]:
    return {
        "wall_speedup_x": ratio(run_metric(base, "wall_ms_per_root_item"), run_metric(current, "wall_ms_per_root_item")),
        "AHT_speedup_x": ratio(run_metric(base, "AHT_ms_per_root_item"), run_metric(current, "AHT_ms_per_root_item")),
        "throughput_gain_fraction": gain(run_metric(current, "terminal_items_per_worker_hour"), run_metric(base, "terminal_items_per_worker_hour")),
        "evidence_yield_change_fraction": gain(run_metric(current, "evidence_yield_per_worker_minute"), run_metric(base, "evidence_yield_per_worker_minute")),
        "rework_change_absolute": run_metric(current, "rework_rate") - run_metric(base, "rework_rate"),
    }


def classify(comparable_runs: list[dict[str, object]], current: dict[str, object]) -> tuple[str, list[str]]:
    if len(comparable_runs) < 3:
        return "INSUFFICIENT_EVIDENCE", ["fewer_than_3_comparable_valid_runs"]
    baseline = comparable_runs[0]
    base_view = speed_view(baseline, current)
    wall = base_view.get("wall_speedup_x")
    quality_ok = (
        run_metric(current, "rework_rate") <= run_metric(baseline, "rework_rate") + 0.05
        and run_metric(current, "information_loss_failures") == 0
        and run_metric(current, "evidence_yield_per_worker_minute") >= 0.9 * run_metric(baseline, "evidence_yield_per_worker_minute")
    )
    recent = comparable_runs[-5:]
    positive = 0
    speedups = []
    for run in recent:
        x = ratio(run_metric(baseline, "wall_ms_per_root_item"), run_metric(run, "wall_ms_per_root_item"))
        if x is not None:
            speedups.append(x)
            positive += int(x > 1.0)
    rolling = statistics.median(speedups) if speedups else None
    if rolling is not None and rolling < 0.90:
        return "REGRESSION", ["rolling_median_speedup_below_0_90"]
    if len(comparable_runs) >= 5 and positive >= 4 and rolling is not None and rolling >= 1.10 and quality_ok:
        if run_metric(current, "DoV_gap_after") <= run_metric(baseline, "DoV_gap_after"):
            return "STABLE_IMPROVEMENT", ["4_of_last_5_positive", "rolling_median_speedup_at_least_1_10", "quality_guards_pass"]
    if positive >= 3 and rolling is not None and rolling >= 1.05 and quality_ok:
        return "PROVISIONALLY_STABLE", ["3_of_last_5_positive", "rolling_median_speedup_at_least_1_05", "quality_guards_pass"]
    if wall is not None and wall > 1.0 and quality_ok:
        return "DIRECTIONAL_IMPROVEMENT", ["faster_than_fixed_baseline", "quality_guards_pass"]
    return "NO_STABLE_GAIN_YET", ["speed_or_quality_gate_not_met"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    rows = []
    for line in Path(args.history).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            row = json.loads(line)
            if isinstance(row, dict) and row.get("valid", True):
                rows.append(row)
    if not rows:
        raise ValueError("history contains no valid runs")
    current = rows[-1]
    comp = [r for r in rows if comparable(r, current)]
    if not comp:
        comp = [current]
    baseline = comp[0]
    previous = comp[-2] if len(comp) > 1 else baseline
    prior = comp[:-1][-5:]
    if prior:
        rolling_reference = {
            "wall_ms_per_root_item": statistics.median(run_metric(r, "wall_ms_per_root_item") for r in prior),
            "AHT_ms_per_root_item": statistics.median(run_metric(r, "AHT_ms_per_root_item") for r in prior),
            "terminal_items_per_worker_hour": statistics.median(run_metric(r, "terminal_items_per_worker_hour") for r in prior),
            "evidence_yield_per_worker_minute": statistics.median(run_metric(r, "evidence_yield_per_worker_minute") for r in prior),
            "rework_rate": statistics.median(run_metric(r, "rework_rate") for r in prior),
        }
    else:
        rolling_reference = baseline
    stability, reasons = classify(comp, current)
    result = {
        "schema_version": "TRIAGE-3P-STABILITY-ROLLUP-1.0.0",
        "current_run_id": current.get("run_id"),
        "comparable_valid_run_count": len(comp),
        "speed_vs_fixed_baseline": speed_view(baseline, current),
        "speed_vs_previous_valid": speed_view(previous, current),
        "speed_vs_rolling_5_reference": speed_view(rolling_reference, current),
        "stability_class": stability,
        "stability_reasons": reasons,
        "claim_guard": "Do not call a speed increase stable unless stability_class is STABLE_IMPROVEMENT.",
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
