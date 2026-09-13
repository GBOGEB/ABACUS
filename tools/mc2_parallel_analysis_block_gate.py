#!/usr/bin/env python3
"""Block-selectable deterministic PA95 gate for MC-2 PCA receipts.

Unlike the original runtime-only gate, this wrapper can evaluate runtime_pca or
semantic_pca. A withheld input PCA produces a withheld PA receipt with exit 0;
it never fabricates eigenvalues and never grants allocation authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from mc2_parallel_analysis_gate import parallel_analysis


BLOCKS = {"runtime_pca", "semantic_pca"}


def write_result(path: Path, result: dict) -> None:
    canonical = json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
    result["receipt_sha256"] = hashlib.sha256(canonical).hexdigest()
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("receipt")
    parser.add_argument("--block", choices=sorted(BLOCKS), required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--simulations", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260913)
    parser.add_argument("--quantile", type=float, default=0.95)
    args = parser.parse_args()

    if args.simulations < 500:
        raise ValueError("at least 500 simulations required")
    if not 0.5 < args.quantile < 1.0:
        raise ValueError("quantile must be between 0.5 and 1.0")

    source = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    block = source.get(args.block, {})
    base = {
        "schema_version": "MC2-PA95-BLOCK-RETENTION-0.1.0",
        "pca_block": args.block,
        "source_receipt_sha256": source.get("receipt_sha256"),
        "simulations": args.simulations,
        "seed": args.seed,
        "quantile": args.quantile,
        "retention_authority": "DIAGNOSTIC_ONLY",
        "allocation_authority": False,
        "child_engineering_promotion_authority": False,
        "bt_status": "WITHHELD_NO_OBSERVED_PAIRWISE_EVIDENCE",
    }

    if block.get("status") != "MEASURED_PCA_DIAGNOSTIC":
        result = {
            **base,
            "status": "WITHHELD_INPUT_PCA_NOT_MEASURED",
            "input_pca_status": block.get("status"),
            "input_pca_reason": block.get("reason"),
            "retained_pcs": [],
            "retained_component_count": 0,
        }
        write_result(Path(args.out), result)
        return

    components = block.get("components") or []
    n = int(block.get("numeric_comparable_rows", 0))
    p = len(components)
    if n < 5 or p < 2:
        result = {
            **base,
            "status": "WITHHELD_PA95_SAMPLE_OR_DIMENSION_GATE",
            "sample_size": n,
            "varying_feature_count": p,
            "retained_pcs": [],
            "retained_component_count": 0,
        }
        write_result(Path(args.out), result)
        return

    observed = [float(component["eigenvalue"]) for component in components]
    thresholds = parallel_analysis(
        n,
        p,
        simulations=args.simulations,
        seed=args.seed,
        quantile=args.quantile,
    )
    retained = [
        index + 1
        for index, (value, threshold) in enumerate(zip(observed, thresholds))
        if value > threshold
    ]
    result = {
        **base,
        "sample_size": n,
        "varying_feature_count": p,
        "observed_eigenvalues": [round(value, 6) for value in observed],
        "null_eigenvalue_thresholds": [round(value, 6) for value in thresholds],
        "retained_pcs": retained,
        "retained_component_count": len(retained),
        "pc2_diagnostic_not_retained": 2 not in retained and p >= 2,
        "status": "PA95_DIAGNOSTIC",
        "small_sample_warning": n < 10 * p,
    }
    write_result(Path(args.out), result)


if __name__ == "__main__":
    main()
