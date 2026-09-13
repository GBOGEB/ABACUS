#!/usr/bin/env python3
"""Project exact-SHA W74 pairs onto frozen retained runtime/semantic PC1 axes."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

RUNTIME_FEATURES = [
    "steps_executed_total",
    "queue_seconds_mean",
    "execute_seconds_total",
    "evidence_emit_count",
]
SEMANTIC_FEATURES = [
    "consumer_penetration_rate",
    "consumer_edge_density",
    "consumer_degree_concentration",
]


def load(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def pc1(block: dict) -> dict:
    for component in block.get("components") or []:
        if component.get("pc") == 1:
            return component
    raise ValueError("PC1 missing from frozen telemetry")


def mean_sd(rows: list[dict], features: list[str]) -> tuple[dict, dict]:
    means = {}
    sds = {}
    for feature in features:
        values = [float(row[feature]) for row in rows]
        mean = sum(values) / len(values)
        denom = max(len(values) - 1, 1)
        sd = math.sqrt(sum((value - mean) ** 2 for value in values) / denom)
        if sd == 0:
            raise ValueError(f"baseline feature is constant: {feature}")
        means[feature] = mean
        sds[feature] = sd
    return means, sds


def frozen_scores(
    rows: list[dict], baseline: list[dict], block: dict, features: list[str]
) -> dict[str, float]:
    component = pc1(block)
    eig = float(component["eigenvalue"])
    if eig <= 0:
        raise ValueError("PC1 eigenvalue must be positive")
    vector = {
        feature: float(component["loadings"][feature]) / math.sqrt(eig)
        for feature in features
    }
    means, sds = mean_sd(baseline, features)
    scores = {}
    for row in rows:
        score = sum(
            ((float(row[feature]) - means[feature]) / sds[feature])
            * vector[feature]
            for feature in features
        )
        scores[str(row["source_sha"])] = round(score, 6)
    return scores


def pearson(xs: list[float], ys: list[float]) -> float | None:
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]
    den = math.sqrt(sum(x * x for x in dx) * sum(y * y for y in dy))
    if den == 0:
        return None
    return sum(x * y for x, y in zip(dx, dy)) / den


def ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        rank = ((i + 1) + j) / 2.0
        for k in range(i, j):
            out[order[k]] = rank
        i = j
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-rows", required=True)
    parser.add_argument("--runtime-baseline-rows", required=True)
    parser.add_argument("--runtime-telemetry", required=True)
    parser.add_argument("--semantic-rows", required=True)
    parser.add_argument("--semantic-telemetry", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    runtime_rows = load(args.runtime_rows)
    semantic_rows = load(args.semantic_rows)
    seed = load(args.runtime_baseline_rows)
    runtime_baseline = [
        row
        for row in seed
        if row.get("observation_class") == "runtime"
        and row.get("execution_state") == "PASS"
        and all(row.get(feature) is not None for feature in RUNTIME_FEATURES)
    ]
    runtime_block = load(args.runtime_telemetry)["runtime_pca"]
    semantic_block = load(args.semantic_telemetry)["semantic_pca"]

    runtime_scores = frozen_scores(
        runtime_rows, runtime_baseline, runtime_block, RUNTIME_FEATURES
    )
    semantic_scores = frozen_scores(
        semantic_rows, semantic_rows, semantic_block, SEMANTIC_FEATURES
    )
    runtime_shas = set(runtime_scores)
    semantic_shas = set(semantic_scores)
    if runtime_shas != semantic_shas or len(runtime_shas) < 5:
        raise ValueError("runtime and semantic rows must exact-pair on >=5 source SHAs")

    paired = []
    for sha in sorted(runtime_shas):
        paired.append(
            {
                "source_sha": sha,
                "runtime_pc1_frozen_score": runtime_scores[sha],
                "semantic_pc1_frozen_score": semantic_scores[sha],
            }
        )
    runtime_values = [row["runtime_pc1_frozen_score"] for row in paired]
    semantic_values = [row["semantic_pc1_frozen_score"] for row in paired]
    r = pearson(runtime_values, semantic_values)
    rho = pearson(ranks(runtime_values), ranks(semantic_values))
    variable = len(set(runtime_values)) > 1 and len(set(semantic_values)) > 1

    receipt = {
        "schema_version": "MC2-W74-PAIRED-PRESSURE-0.1.0",
        "status": (
            "PAIRED_COORDINATE_DIAGNOSTIC"
            if variable and r is not None and rho is not None
            else "WITHHELD_INSUFFICIENT_PAIRED_VARIATION"
        ),
        "authority": "derived_operational_analysis",
        "pair_count": len(paired),
        "paired_observations": True,
        "pair_key": "exact_source_sha",
        "runtime_axis_frozen": True,
        "semantic_axis_frozen": True,
        "loading_refit_performed": False,
        "joint_pca_performed": False,
        "pairs": paired,
        "association": {
            "pearson_r": None if r is None else round(r, 6),
            "spearman_rho": None if rho is None else round(rho, 6),
            "inference_authority": False,
            "small_sample_warning": True,
        },
        "limitations": [
            "runtime PC1 is projected from fresh homogeneous probe jobs onto the frozen mixed-workflow runtime axis",
            "semantic PC1 has only two observed topology states across the five historical SHAs",
            "paired association is diagnostic and does not establish causality or allocation authority",
        ],
        "bt_status": "WITHHELD_NO_OBSERVED_PAIRWISE_OUTCOME_EVIDENCE",
        "global_allocation_authority": False,
        "child_engineering_promotion_authority": False,
        "engineering_compliance_release_authority": False,
    }
    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()
    receipt["receipt_sha256"] = hashlib.sha256(canonical).hexdigest()
    Path(args.out).write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
