#!/usr/bin/env python3
"""G3A source-bound gg_MATH adapter. Advisory only; zero authority transfer."""
from __future__ import annotations

import argparse
import importlib
import json
import re
import subprocess
import sys
from pathlib import Path

GG_MATH_SHA = "961eadf43f19b6bc0ef11fdd640c30ab59f74f41"
EXPECTED_SNAPSHOT = "code-purple.mip.g3a.statistical-control.v1"
SCOPE = "ABACUS_G3A_FOUR_MODULE_FROZEN_446_BRANCHES_coverage7.16.2"
SOURCE_MODULES = {
    "DMAIC_V3/debug_pipeline.py": 116,
    "DMAIC_V3/phases/phase4_improve.py": 134,
    "DMAIC_V3/phases/phase8_todo_management.py": 118,
    "cicd_github_orchestrator.py": 78,
}


def transform(snapshot: dict) -> dict:
    if snapshot.get("schema") != EXPECTED_SNAPSHOT:
        raise ValueError("HOLD: unexpected native snapshot schema")
    ln = snapshot["lineage"]
    agg = snapshot["aggregate"]
    if (agg["eligible"], agg["n13_covered"], agg["n14_covered"]) != (446, 115, 200):
        raise ValueError("HOLD: frozen numerator/denominator drift")
    if (ln.get("coverage_version") != "7.16.2" or
            ln.get("source_bytes_frozen") is not True or
            ln.get("exact_arcs_rejoined") is not True):
        raise ValueError("HOLD: exact-source or arc evidence missing")
    modules = snapshot["modules"]
    if len(modules) != 4 or {m["path"]: m["eligible"] for m in modules} != SOURCE_MODULES:
        raise ValueError("HOLD: module scope drift")
    if (sum(m["n13"] for m in modules), sum(m["n14"] for m in modules)) != (115, 200):
        raise ValueError("HOLD: module numerator mismatch")
    if any(m["n14"] - m["n13"] != m["gained"] - m["lost"] for m in modules):
        raise ValueError("HOLD: arc gain/loss mismatch")
    if agg.get("six_sigma") != "NOT_ASSESSED_FROM_BRANCH_COVERAGE":
        raise ValueError("HOLD: no Six Sigma from coverage")
    if snapshot.get("controls", {}).get("merge_admission") != "HOLD":
        raise ValueError("HOLD: admission control is not HOLD")

    rows = []
    for n in (13, 14):
        sha = ln[f"n{n}_sha"]
        run = ln[f"n{n}_run"]
        if not isinstance(sha, str) or not re.fullmatch("[a-f0-9]{40}", sha):
            raise ValueError("HOLD: non-exact SHA")
        if type(run) is not int or run < 1:
            raise ValueError("HOLD: invalid native run ID")
        rows.append({"n": n, "k": 115 if n == 13 else 200, "d": 446,
                     "scope_id": SCOPE, "sha": sha, "run_id": run, "attempt": 1})
    return {"schema": "gg_math.convergence_input.v1",
            "evidence_class": "SOURCE_BOUND_UNVERIFIED_RECEIPTS",
            "authority_transfer": False, "tolerance_pp": 0.5,
            "cap_tolerance_pp": 1.0, "equivalence_alpha": 0.05,
            "observations": rows,
            "blocking_dependencies": ["CI_GOVERNANCE_EXACT_HEAD_PROOF_PENDING",
                                      "INDEPENDENT_REVIEW_PENDING"],
            "defect_opportunities": {"defects": None, "opportunities": None,
                                     "independent": False, "ctq": None},
            "federation": {"math_provider": "GBOGEB/gg_MATH",
                           "math_provider_sha": GG_MATH_SHA,
                           "semantic_owner": "CODEX/KEB", "consumer": "ABACUS/MIP",
                           "native_ci_authenticated_by_provider": False,
                           "hard_gate_compensation_allowed": False,
                           "merge_admission": "HOLD"}}


def run_pinned_provider(payload: dict, repo_root: Path) -> dict:
    if not (repo_root / "kernels/convergence_control.py").is_file():
        raise ValueError("HOLD: gg_MATH provider checkout missing")
    exact = subprocess.check_output(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"], text=True).strip()
    if exact != GG_MATH_SHA:
        raise ValueError("HOLD: gg_MATH provider SHA drift")
    sys.path.insert(0, str(repo_root.resolve()))
    try:
        from kernels.convergence_control import assess_convergence
        report = assess_convergence(payload)
    finally:
        sys.path.pop(0)
    if (report.get("schema") != "gg_math.convergence_receipt.v1" or
        report.get("merge_admission") != "HOLD" or
        report.get("authority_transfer") is not False):
        raise ValueError("HOLD: invalid provider authority guards")
    return {"status": "PINNED_LOCAL_PROVIDER_EXECUTED",
            "provider_sha": exact, "native_ci_authentication": False,
            "result": report}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--provider-root", type=Path)
    args = parser.parse_args(argv)
    bound = transform(json.loads(args.snapshot.read_text(encoding="utf-8")))
    provider = (run_pinned_provider(bound, args.provider_root) if args.provider_root else
                {"status": "PROVIDER_NOT_EXECUTED_SOURCE_ONLY",
                 "provider_sha": GG_MATH_SHA, "native_ci_authentication": False})
    receipt = {"schema": "abacus.mip.gg_math_bridge.v1",
               "provider_input": bound, "provider": provider,
               "authority_transfer": False, "merge_admission": "HOLD"}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(json.dumps({"bridge": receipt["schema"], "provider": provider["status"],
                      "merge_admission": "HOLD"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
