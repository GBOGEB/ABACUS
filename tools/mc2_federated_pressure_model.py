#!/usr/bin/env python3
"""Build the first bounded runtime x semantic MC-2 pressure model.

This is deliberately a two-axis diagnostic model, not a joint PCA: runtime and
semantic observations are not paired samples. Each axis must independently have
PC1 retained by PA95. No joint score, allocation authority or BT evidence is
created.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def pc1(block: dict) -> dict | None:
    for component in block.get("components") or []:
        if component.get("pc") == 1:
            return component
    return None


def retained(pa: dict) -> bool:
    return pa.get("status") == "PA95_DIAGNOSTIC" and 1 in (pa.get("retained_pcs") or [])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-telemetry", required=True)
    parser.add_argument("--runtime-pa95", required=True)
    parser.add_argument("--semantic-telemetry", required=True)
    parser.add_argument("--semantic-pa95", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    runtime_t = load(args.runtime_telemetry)
    runtime_pa = load(args.runtime_pa95)
    semantic_t = load(args.semantic_telemetry)
    semantic_pa = load(args.semantic_pa95)

    runtime_block = runtime_t.get("runtime_pca") or {}
    semantic_block = semantic_t.get("semantic_pca") or {}
    runtime_pc1 = pc1(runtime_block)
    semantic_pc1 = pc1(semantic_block)

    gates = {
        "runtime_pca_measured": runtime_block.get("status") == "MEASURED_PCA_DIAGNOSTIC",
        "runtime_pc1_pa95_retained": retained(runtime_pa),
        "semantic_pca_measured": semantic_block.get("status") == "MEASURED_PCA_DIAGNOSTIC",
        "semantic_pc1_pa95_retained": retained(semantic_pa),
    }
    ready = all(gates.values()) and runtime_pc1 is not None and semantic_pc1 is not None

    receipt = {
        "schema_version": "MC2-FEDERATED-PRESSURE-MODEL-0.1.0",
        "status": (
            "MEASURED_TWO_AXIS_DIAGNOSTIC"
            if ready
            else "WITHHELD_AXIS_RETENTION_GATE"
        ),
        "gates": gates,
        "model_class": "TWO_AXIS_UNPAIRED_DIAGNOSTIC",
        "runtime_axis": None,
        "semantic_axis": None,
        "coupling": {
            "paired_observations": False,
            "joint_score_authority": False,
            "reason": "runtime and semantic source SHAs are not paired observations; compare retained pressure axes, do not pool row scores",
        },
        "bt_status": "WITHHELD_NO_OBSERVED_PAIRWISE_EVIDENCE",
        "global_allocation_authority": False,
        "child_engineering_promotion_authority": False,
        "engineering_compliance_release_authority": False,
    }
    if runtime_pc1 is not None:
        receipt["runtime_axis"] = {
            "name": "runtime_execution_evidence_pressure_pc1",
            "sample_size": runtime_block.get("numeric_comparable_rows"),
            "eigenvalue": runtime_pc1.get("eigenvalue"),
            "explained_variance_ratio": runtime_pc1.get("explained_variance_ratio"),
            "loadings": runtime_pc1.get("loadings"),
            "pa95_retained": retained(runtime_pa),
        }
    if semantic_pc1 is not None:
        receipt["semantic_axis"] = {
            "name": "semantic_topology_integration_pressure_pc1",
            "sample_size": semantic_block.get("numeric_comparable_rows"),
            "eigenvalue": semantic_pc1.get("eigenvalue"),
            "explained_variance_ratio": semantic_pc1.get("explained_variance_ratio"),
            "loadings": semantic_pc1.get("loadings"),
            "pa95_retained": retained(semantic_pa),
        }

    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()
    receipt["receipt_sha256"] = hashlib.sha256(canonical).hexdigest()
    Path(args.out).write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
