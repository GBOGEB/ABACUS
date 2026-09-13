#!/usr/bin/env python3
"""Deduplicate W78 work states and gate any later multivariate analysis."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from w78_deterministic_work_probe import SEMANTIC_WORK_FEATURES, WORK_FEATURES

MIN_TARGETS = 15
MIN_DISTINCT_WORK_STATES = 8
MIN_DISTINCT_SEMANTIC_WORK_STATES = 5
MIN_CENTERED_WORK_RANK = 3


def load(paths: list[str]) -> list[dict]:
    return [json.loads(Path(path).read_text(encoding="utf-8")) for path in paths]


def validate(rows: list[dict]) -> dict[str, dict]:
    if len(rows) != MIN_TARGETS * 2:
        raise ValueError("W78 requires exactly 30 receipts: 15 SHAs x 2 replays")
    shas = {str(row["source_sha"]) for row in rows}
    if len(shas) != MIN_TARGETS:
        raise ValueError("W78 requires 15 distinct source SHAs")
    collapsed: dict[str, dict] = {}
    labels: dict[str, str] = {}
    for sha in sorted(shas):
        subset = [row for row in rows if str(row["source_sha"]) == sha]
        if len(subset) != 2 or {int(row["repeat"]) for row in subset} != {1, 2}:
            raise ValueError(f"unbalanced W78 replay panel for {sha}")
        for row in subset:
            if row.get("execution_state") != "PASS":
                raise ValueError(f"non-PASS W78 receipt for {sha}")
            if row.get("semantic_parity_with_w72") is not True:
                raise ValueError(f"semantic parity failure for {sha}")
        work_hashes = {str(row["work_vector_sha256"]) for row in subset}
        semantic_hashes = {
            str(row["semantic_work_vector_sha256"]) for row in subset
        }
        feature_hashes = {str(row["feature_row_sha256"]) for row in subset}
        work_vectors = {
            json.dumps(row["work_vector"], sort_keys=True) for row in subset
        }
        semantic_vectors = {
            json.dumps(row["semantic_work_vector"], sort_keys=True)
            for row in subset
        }
        if not (
            len(work_hashes)
            == len(semantic_hashes)
            == len(feature_hashes)
            == len(work_vectors)
            == len(semantic_vectors)
            == 1
        ):
            raise ValueError(f"deterministic replay mismatch for {sha}")
        labels_for_sha = {str(row["matrix_label"]) for row in subset}
        if len(labels_for_sha) != 1:
            raise ValueError(f"matrix label drift for {sha}")
        label = next(iter(labels_for_sha))
        if label in labels and labels[label] != sha:
            raise ValueError(f"matrix label collision: {label}")
        labels[label] = sha
        collapsed[sha] = subset[0]
    return collapsed


def centered_scaled_rank(rows: list[dict], features: tuple[str, ...], field: str) -> int:
    matrix = [
        [float(row[field][feature]) for feature in features]
        for row in rows
    ]
    if not matrix:
        return 0
    cols = len(features)
    means = [sum(row[col] for row in matrix) / len(matrix) for col in range(cols)]
    centered = [
        [row[col] - means[col] for col in range(cols)]
        for row in matrix
    ]
    scales = [
        max(abs(row[col]) for row in centered) or 1.0
        for col in range(cols)
    ]
    a = [
        [row[col] / scales[col] for col in range(cols)]
        for row in centered
    ]
    rank = 0
    row_count = len(a)
    for col in range(cols):
        pivot = max(range(rank, row_count), key=lambda idx: abs(a[idx][col]), default=rank)
        if rank >= row_count or abs(a[pivot][col]) <= 1e-10:
            continue
        a[rank], a[pivot] = a[pivot], a[rank]
        pivot_value = a[rank][col]
        a[rank] = [value / pivot_value for value in a[rank]]
        for idx in range(row_count):
            if idx == rank:
                continue
            factor = a[idx][col]
            if abs(factor) <= 1e-12:
                continue
            a[idx] = [
                a[idx][j] - factor * a[rank][j]
                for j in range(cols)
            ]
        rank += 1
        if rank == row_count:
            break
    return rank


def grouped_states(rows: list[dict], hash_field: str) -> list[dict]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        grouped[str(row[hash_field])].append(str(row["source_sha"]))
    return [
        {
            "state_sha256": state_hash,
            "source_count": len(shas),
            "source_shas": sorted(shas),
        }
        for state_hash, shas in sorted(grouped.items())
    ]


def evaluate(receipts: list[dict]) -> dict:
    collapsed_map = validate(receipts)
    collapsed = [collapsed_map[sha] for sha in sorted(collapsed_map)]
    work_counts = Counter(str(row["work_vector_sha256"]) for row in collapsed)
    semantic_counts = Counter(
        str(row["semantic_work_vector_sha256"]) for row in collapsed
    )
    work_rank = centered_scaled_rank(collapsed, WORK_FEATURES, "work_vector")
    semantic_rank = centered_scaled_rank(
        collapsed,
        SEMANTIC_WORK_FEATURES,
        "semantic_work_vector",
    )
    distinct_work = len(work_counts)
    distinct_semantic = len(semantic_counts)
    ready = (
        len(collapsed) >= MIN_TARGETS
        and distinct_work >= MIN_DISTINCT_WORK_STATES
        and distinct_semantic >= MIN_DISTINCT_SEMANTIC_WORK_STATES
        and work_rank >= MIN_CENTERED_WORK_RANK
    )
    return {
        "schema_version": "MC2-W78-DETERMINISTIC-WORK-DIVERSITY-0.1.0",
        "status": (
            "DIVERSITY_GATE_PASS_FOR_W79_ANALYSIS"
            if ready
            else "DIVERSITY_GATE_WITHHELD"
        ),
        "authority": "derived_operational_analysis",
        "target_count": len(collapsed),
        "observation_count": len(receipts),
        "replay_count_per_target": 2,
        "deterministic_replay_consistency": "PASS_15_OF_15",
        "distinct_work_state_count": distinct_work,
        "distinct_semantic_work_state_count": distinct_semantic,
        "centered_work_matrix_rank": work_rank,
        "centered_semantic_work_matrix_rank": semantic_rank,
        "largest_work_state_multiplicity": max(work_counts.values()),
        "largest_semantic_work_state_multiplicity": max(semantic_counts.values()),
        "diversity_design_decision": {
            "declared_before_measurement": True,
            "minimum_exact_sha_targets": MIN_TARGETS,
            "minimum_distinct_work_states": MIN_DISTINCT_WORK_STATES,
            "minimum_distinct_semantic_work_states": MIN_DISTINCT_SEMANTIC_WORK_STATES,
            "minimum_centered_work_matrix_rank": MIN_CENTERED_WORK_RANK,
            "all_required": True,
            "statistical_truth_claim": False,
        },
        "work_features": list(WORK_FEATURES),
        "semantic_work_features": list(SEMANTIC_WORK_FEATURES),
        "work_states": grouped_states(collapsed, "work_vector_sha256"),
        "semantic_work_states": grouped_states(
            collapsed, "semantic_work_vector_sha256"
        ),
        "rows": [
            {
                "source_sha": row["source_sha"],
                "matrix_label": row["matrix_label"],
                "feature_row": row["feature_row"],
                "work_vector": row["work_vector"],
                "work_vector_sha256": row["work_vector_sha256"],
                "semantic_work_vector": row["semantic_work_vector"],
                "semantic_work_vector_sha256": row[
                    "semantic_work_vector_sha256"
                ],
            }
            for row in collapsed
        ],
        "w79_multivariate_analysis_permitted": ready,
        "pca_fit_performed": False,
        "bt_status": "WITHHELD_NO_OBSERVED_PAIRWISE_OUTCOME_EVIDENCE",
        "global_allocation_authority": False,
        "child_engineering_promotion_authority": False,
        "engineering_compliance_release_authority": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("receipts", nargs="+")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    result = evaluate(load(args.receipts))
    Path(args.out).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
