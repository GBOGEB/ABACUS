#!/usr/bin/env python3
"""Run diagnostic PCA over W73 exact-SHA semantic-topology rows."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from mc2_federated_telemetry import pca_block

FEATURES = [
    "consumer_penetration_rate",
    "consumer_edge_density",
    "consumer_degree_concentration",
]


def finite(value) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("rows")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    rows = json.loads(Path(args.rows).read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("rows root must be a list")
    for index, row in enumerate(rows):
        if row.get("observation_class") != "semantic_topology":
            raise ValueError(f"row {index}: wrong observation_class")
        for feature in FEATURES:
            value = row.get(feature)
            if not finite(value) or not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"row {index}: invalid {feature}")

    semantic = pca_block(rows, FEATURES)
    # PCA sign is arbitrary. Orient semantic PC1 so higher penetration is positive.
    if semantic.get("status") == "MEASURED_PCA_DIAGNOSTIC":
        pc1 = next(component for component in semantic["components"] if component["pc"] == 1)
        if pc1["loadings"].get("consumer_penetration_rate", 0.0) < 0:
            for component in semantic["components"]:
                component["loadings"] = {
                    key: round(-value, 6) for key, value in component["loadings"].items()
                }
    receipt = {
        "schema_version": "MC2-W73-SEMANTIC-TOPOLOGY-PCA-0.1.0",
        "authority": "derived_operational_analysis",
        "feature_definition": FEATURES,
        "rows_total": len(rows),
        "semantic_pca": semantic,
        "bt_status": "WITHHELD_NO_OBSERVED_PAIRWISE_EVIDENCE",
        "global_allocation_authority": False,
        "child_engineering_promotion_authority": False,
    }
    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()
    receipt["receipt_sha256"] = hashlib.sha256(canonical).hexdigest()
    Path(args.out).write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
