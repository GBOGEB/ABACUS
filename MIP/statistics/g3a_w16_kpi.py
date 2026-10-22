#!/usr/bin/env python3
"""Small, fail-closed DMAIC/MIP G3A native KPI contract (not an admission gate).

Five decision KPIs. Missing clocks, unmatched source epochs, unsupported PCA,
BT, capability and unverified root closures are explicitly null/unqualified.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

EPOCH = "G3A_W16_V2_PHASE4_REPAIRED"
FOUR_BRANCHES = {
    "DMAIC_V3/debug_pipeline.py": 116,
    "DMAIC_V3/phases/phase4_improve.py": 132,
    "DMAIC_V3/phases/phase8_todo_management.py": 118,
    "cicd_github_orchestrator.py": 78,
}
METRIC_NAMES = (
    "matched_coverage",
    "proof_yield",
    "root_burndown",
    "time_to_evidence",
    "statistical_control",
)


def _valid_int(value: object, lower: int = 0) -> bool:
    return type(value) is int and value >= lower


def evaluate(
    receipt: dict | None,
    *,
    start_s: float | None = None,
    end_s: float | None = None,
    independently_verified_roots: int = 0,
    comparable_independent_pulses: int = 1,
) -> dict:
    if independently_verified_roots != 0:
        raise ValueError("no authenticated causal-root closure receipt supplied")
    if not _valid_int(comparable_independent_pulses, 1):
        raise ValueError("independent pulse count must be a positive int")
    elapsed = None
    if start_s is not None and end_s is not None:
        if (
            type(start_s) not in (float, int)
            or type(end_s) not in (float, int)
            or not math.isfinite(start_s)
            or not math.isfinite(end_s)
            or end_s < start_s
        ):
            raise ValueError("invalid monotone clock sample")
        elapsed = round(float(end_s - start_s), 3)

    status = "NATIVE_NOT_MEASURED"
    covered = eligible = None
    proof = None
    if receipt is not None:
        if receipt.get("schema") != "code-purple.g3a.w16.native.v1":
            raise ValueError("wrong native receipt schema")
        if receipt.get("source_epoch") != EPOCH:
            raise ValueError("source epoch mismatch")
        if receipt.get("merge_admission") != "HOLD":
            raise ValueError("cannot accept a promoted merge claim")
        if not isinstance(receipt.get("checkout_sha"), str) or not re.fullmatch(
            r"[a-f0-9]{40}", receipt["checkout_sha"]
        ):
            raise ValueError("missing exact-head identity")
        if (
            receipt.get("phase4_source_blob")
            != "18bec722fef537aa74b85295954cf66a002695d0"
        ):
            raise ValueError("Phase4 source blob drift")
        if not _valid_int(receipt.get("run_id"), 1) or not _valid_int(
            receipt.get("run_attempt"), 1
        ):
            raise ValueError("run/attempt identity missing")
        files = receipt.get("files")
        if not isinstance(files, dict) or set(files) != set(FOUR_BRANCHES):
            raise ValueError("coverage population mismatch")
        for name, den in FOUR_BRANCHES.items():
            f = files[name]
            if (
                not _valid_int(f.get("eligible"), 1)
                or f["eligible"] != den
                or not _valid_int(f.get("covered"))
                or f["covered"] > f["eligible"]
            ):
                raise ValueError("coverage branch denominator/numerator drift")
        covered = sum(v["covered"] for v in files.values())
        eligible = sum(FOUR_BRANCHES.values())
        if (
            covered != receipt.get("covered")
            or eligible != receipt.get("eligible")
            or not _valid_int(receipt.get("tests"), 121)
        ):
            raise ValueError("receipt arithmetic or test identity drift")
        status = "NATIVE_FOCUSED_PROOF_PASS"
        proof = 1.0

    return {
        "schema": "code-purple.mip.g3a.w16.decision_kpi.v1",
        "source_epoch": EPOCH,
        "native_state": status,
        "metric_count": len(METRIC_NAMES),
        "metrics": {
            "matched_coverage": {
                "k": covered,
                "d": eligible,
                "ratio": None if covered is None else covered / eligible,
                "uncovered": None if covered is None else eligible - covered,
                "cross_epoch_delta": None,
            },
            "proof_yield": {
                "single_exact_head_focused_proof": proof,
                "global_native_job_yield": None,
            },
            "root_burndown": {
                "verified_closed_roots": independently_verified_roots,
                "denominator_unique_roots": None,
                "candidate_first_reds_are_closed": False,
            },
            "time_to_evidence": {
                "measured_test_execution_seconds": elapsed,
                "native_run_wall_seconds": None,
                "queue_seconds": None,
                "queue_p95_seconds": None,
                "unverified_speedup_claim": None,
            },
            "statistical_control": {
                "state": (
                    "NOT_ESTIMABLE"
                    if comparable_independent_pulses < 6
                    else "REQUIRES_SLOPE_EQUIVALENCE_AND_REVIEW"
                ),
                "comparable_independent_pulses": comparable_independent_pulses,
                "pca": "NOT_QUALIFIED",
                "bt": "NO_PAIRWISE_OUTCOMES",
                "six_sigma": "NOT_ASSESSED",
            },
        },
        "formal_root_closure_credit": 0,
        "security_waiver": False,
        "merge_admission": "HOLD",
        "authority_transfer": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt", type=Path, required=True)
    ap.add_argument("--start-s", type=Path)
    ap.add_argument("--end-s", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    receipt = (
        json.loads(a.receipt.read_text(encoding="utf-8"))
        if a.receipt.is_file()
        else None
    )

    def clock(path):
        return float(path.read_text().strip()) if path and path.is_file() else None

    output = evaluate(receipt, start_s=clock(a.start_s), end_s=clock(a.end_s))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(
        json.dumps(output, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(
        "G3A_W16_KPIS="
        + output["native_state"]
        + " count="
        + str(output["metric_count"])
        + " coverage="
        + str(output["metrics"]["matched_coverage"]["ratio"])
    )
    return 0 if output["native_state"] == "NATIVE_FOCUSED_PROOF_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
