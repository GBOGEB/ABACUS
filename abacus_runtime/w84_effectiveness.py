#!/usr/bin/env python3
"""W84 observed-effectiveness scorer for 3P3/3PR cycles.

No recommendation receives effectiveness credit without observed before/after
counters. Debug-spine fields are optional telemetry and carry no authority.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED = (
    "execution_effort",
    "accepted_atoms_before", "accepted_atoms_after",
    "dov_before", "dov_after",
    "recommendations_executed", "recommendations_successful",
    "retries", "successful_repaired_tasks",
    "residual_before", "residual_after",
)


def score(cycle: dict) -> dict:
    missing = [key for key in REQUIRED if key not in cycle]
    if missing:
        return {"status": "DEFER_MISSING_OBSERVED_METRICS", "missing": missing}
    effort = float(cycle["execution_effort"])
    if effort <= 0:
        return {"status": "DEFER_INVALID_EFFORT", "execution_effort": effort}
    recs = int(cycle["recommendations_executed"])
    retries = int(cycle["retries"])
    evidence_yield = (float(cycle["accepted_atoms_after"]) - float(cycle["accepted_atoms_before"])) / effort
    dov_yield = (float(cycle["dov_after"]) - float(cycle["dov_before"])) / effort
    hit_rate = int(cycle["recommendations_successful"]) / recs if recs else None
    retry_eff = int(cycle["successful_repaired_tasks"]) / retries if retries else None
    pressure_reduction = float(cycle["residual_before"]) - float(cycle["residual_after"])
    positive = evidence_yield > 0 and pressure_reduction > 0 and dov_yield >= 0
    return {
        "status": "PASS_POSITIVE_EFFECTIVENESS" if positive else "OBSERVED_NO_POSITIVE_EFFECTIVENESS",
        "evidence_yield": evidence_yield,
        "dov_yield": dov_yield,
        "recommendation_hit_rate": hit_rate,
        "retry_efficiency": retry_eff,
        "pressure_reduction": pressure_reduction,
        "debug_spine": cycle.get("debug_spine", {}),
        "adaptive_scheduler_credit": False,
        "engineering_credit_delta": 0,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("cycle", type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    receipt = score(json.loads(args.cycle.read_text(encoding="utf-8")))
    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0 if receipt.get("status") == "PASS_POSITIVE_EFFECTIVENESS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
