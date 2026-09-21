#!/usr/bin/env python3
"""Aggregate W83 semantic-basis probe receipts without fitting PCA."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

EXPECTED_W79 = {f"s{i:02d}" for i in range(1, 16)}
EXPECTED_RECENT = {
    "p1281-pass",
    "p1286-fail",
    "p1288-fail",
    "p1289-pass",
    "p1291-fail",
    "p1292-pass",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("receipts", nargs="+")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    rows = [json.loads(Path(path).read_text(encoding="utf-8")) for path in args.receipts]
    labels = {row["matrix_label"] for row in rows}
    expected = EXPECTED_W79 | EXPECTED_RECENT
    if labels != expected or len(rows) != len(expected):
        raise SystemExit("W83 requires exactly 21 unique predeclared states")

    feature_names = sorted(rows[0]["feature_vector"])
    if any(sorted(row["feature_vector"]) != feature_names for row in rows):
        raise SystemExit("W83 feature schema drift across exact-source states")

    groups = {
        "w79_historical": [row for row in rows if row["matrix_label"] in EXPECTED_W79],
        "recent_outcomes": [row for row in rows if row["matrix_label"] in EXPECTED_RECENT],
        "all_states": rows,
    }
    summary = {}
    for name, group in groups.items():
        summary[name] = {
            "state_count": len(group),
            "unique_feature_vectors": len({row["feature_vector_sha256"] for row in group}),
            "unique_semantic_composition": len(
                {row["block_sha256"]["semantic_composition"] for row in group}
            ),
            "unique_consumer_graph_distribution": len(
                {
                    row["block_sha256"]["consumer_graph_distribution"]
                    for row in group
                }
            ),
            "unique_workflow_governance_composition": len(
                {
                    row["block_sha256"]["workflow_governance_composition"]
                    for row in group
                }
            ),
        }

    ranges = {}
    for feature in feature_names:
        values = [int(row["feature_vector"][feature]) for row in rows]
        ranges[feature] = {
            "min": min(values),
            "max": max(values),
            "distinct": len(set(values)),
        }

    recent_variable = [
        feature
        for feature in feature_names
        if len({int(row["feature_vector"][feature]) for row in groups["recent_outcomes"]})
        > 1
    ]
    result = {
        "schema_version": "MC2-W83-SEMANTIC-BASIS-DIVERSITY-0.1.0",
        "status": (
            "DIVERSITY_SIGNAL_PRESENT"
            if summary["recent_outcomes"]["unique_feature_vectors"] > 1
            else "RECENT_BASIS_STILL_SATURATED"
        ),
        "groups": summary,
        "feature_ranges_all_states": ranges,
        "recent_variable_features": recent_variable,
        "recent_variable_feature_count": len(recent_variable),
        "pca_fit_performed": False,
        "pairwise_outcome_accumulation_permitted": False,
        "bt_status": "WITHHELD",
        "authority_transfer": False,
        "global_allocation_authority": False,
        "formal_credit_delta": 0,
    }
    Path(args.out).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
