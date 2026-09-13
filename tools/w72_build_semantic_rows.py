#!/usr/bin/env python3
"""Build MC-2 semantic telemetry rows from same-schema W72 FEATURE_ROW files."""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

EXPECTED_SCHEMA = "W72-SEMANTIC-CENSUS-2.0.0"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
FEATURES = [
    "registry_gap_rate",
    "unresolved_reference_rate",
    "consumer_penetration_rate",
    "graph_drop_rate",
    "lineage_gap_rate",
]


def finite(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("feature_rows", nargs="+")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    rows = []
    seen = set()
    for raw_path in args.feature_rows:
        path = Path(raw_path)
        feature = json.loads(path.read_text(encoding="utf-8"))
        if feature.get("measurement_schema") != EXPECTED_SCHEMA:
            raise ValueError(f"{path}: incompatible measurement schema")
        sha = str(feature.get("source_sha", ""))
        if not SHA40.fullmatch(sha):
            raise ValueError(f"{path}: source_sha must be exact 40-char lowercase hex")
        if sha in seen:
            raise ValueError(f"{path}: duplicate source_sha {sha}")
        seen.add(sha)
        for key in FEATURES:
            value = feature.get(key)
            if not finite(value) or not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"{path}: invalid {key}")
        row = {
            "authority_class": "derived_operational_analysis",
            "evidence_reference": path.as_posix(),
            "observation_class": "semantic",
            "row_id": f"SEM-W72-{sha[:12]}",
            "source_repo": "GBOGEB/ABACUS",
            "source_sha": sha,
        }
        row.update({key: float(feature[key]) for key in FEATURES})
        rows.append(row)

    rows.sort(key=lambda item: item["source_sha"])
    Path(args.out).write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"rows": len(rows), "distinct_source_shas": len(seen)}, sort_keys=True))


if __name__ == "__main__":
    main()
