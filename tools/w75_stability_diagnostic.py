#!/usr/bin/env python3
"""W75 deconfounded repeatability diagnostic over frozen W74/W73 PC1 axes."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

from w74_paired_pressure import (
    RUNTIME_FEATURES,
    SEMANTIC_FEATURES,
    mean_sd,
    pc1,
    pearson,
    ranks,
)

ICC_THRESHOLD = 0.75
RANK_THRESHOLD = 0.80


def load(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def vector_from_pc1(block: dict, features: list[str]) -> dict[str, float]:
    component = pc1(block)
    eig = float(component["eigenvalue"])
    if eig <= 0:
        raise ValueError("PC1 eigenvalue must be positive")
    return {
        feature: float(component["loadings"][feature]) / math.sqrt(eig)
        for feature in features
    }


def project_rows(
    rows: list[dict],
    baseline: list[dict],
    block: dict,
    features: list[str],
) -> list[dict]:
    means, sds = mean_sd(baseline, features)
    vector = vector_from_pc1(block, features)
    projected = []
    for row in rows:
        score = sum(
            ((float(row[feature]) - means[feature]) / sds[feature])
            * vector[feature]
            for feature in features
        )
        item = dict(row)
        item["runtime_pc1_frozen_score"] = score
        projected.append(item)
    return projected


def solve_linear(matrix: list[list[float]], vector: list[float]) -> list[float]:
    n = len(vector)
    a = [row[:] + [vector[i]] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[pivot][col]) < 1e-12:
            raise ValueError("singular deconfounding design matrix")
        a[col], a[pivot] = a[pivot], a[col]
        scale = a[col][col]
        a[col] = [value / scale for value in a[col]]
        for row in range(n):
            if row == col:
                continue
            factor = a[row][col]
            if factor == 0:
                continue
            a[row] = [
                a[row][j] - factor * a[col][j]
                for j in range(n + 1)
            ]
    return [a[i][-1] for i in range(n)]


def residualize(rows: list[dict]) -> tuple[list[dict], dict]:
    # Environment-only terms. Intrinsic probe time is deliberately NOT regressed out.
    x = [
        [
            1.0,
            float(row["queue_seconds_mean"]),
            float(row["orchestration_overhead_seconds"]),
        ]
        for row in rows
    ]
    y = [float(row["runtime_pc1_frozen_score"]) for row in rows]
    p = len(x[0])
    xtx = [[sum(r[i] * r[j] for r in x) for j in range(p)] for i in range(p)]
    xty = [sum(r[i] * yy for r, yy in zip(x, y)) for i in range(p)]
    beta = solve_linear(xtx, xty)
    out = []
    for row, design, observed in zip(rows, x, y):
        fitted = sum(b * d for b, d in zip(beta, design))
        item = dict(row)
        item["runtime_pc1_environment_fitted"] = fitted
        item["runtime_pc1_environment_residual"] = observed - fitted
        out.append(item)
    return out, {
        "model": "runtime_pc1_frozen_score ~ 1 + queue_seconds_mean + orchestration_overhead_seconds",
        "coefficients": {
            "intercept": beta[0],
            "queue_seconds_mean": beta[1],
            "orchestration_overhead_seconds": beta[2],
        },
        "intrinsic_probe_time_regressed_out": False,
        "causal_inference_authority": False,
    }


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def sample_sd(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    return statistics.stdev(values)


def cv(values: list[float]) -> float | None:
    m = mean(values)
    if abs(m) < 1e-12:
        return None
    return sample_sd(values) / abs(m)


def icc_one_way(rows: list[dict], field: str) -> float | None:
    by_sha: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        by_sha[str(row["source_sha"])].append(float(row[field]))
    if len(by_sha) != 5 or {len(v) for v in by_sha.values()} != {3}:
        raise ValueError("ICC requires five source SHAs with three repeats each")
    n = len(by_sha)
    k = 3
    grand = mean([value for values in by_sha.values() for value in values])
    group_means = {sha: mean(values) for sha, values in by_sha.items()}
    ss_between = k * sum((m - grand) ** 2 for m in group_means.values())
    ss_within = sum(
        sum((value - group_means[sha]) ** 2 for value in values)
        for sha, values in by_sha.items()
    )
    ms_between = ss_between / (n - 1)
    ms_within = ss_within / (n * (k - 1))
    den = ms_between + (k - 1) * ms_within
    if abs(den) < 1e-12:
        return None
    return (ms_between - ms_within) / den


def repeat_vectors(rows: list[dict], field: str) -> dict[int, list[float]]:
    shas = sorted({str(row["source_sha"]) for row in rows})
    lookup = {
        (int(row["repeat"]), str(row["source_sha"])): float(row[field])
        for row in rows
    }
    return {repeat: [lookup[(repeat, sha)] for sha in shas] for repeat in (1, 2, 3)}


def pairwise_rank_stability(rows: list[dict], field: str) -> dict:
    vectors = repeat_vectors(rows, field)
    pairs = []
    for left, right in ((1, 2), (1, 3), (2, 3)):
        rho = pearson(ranks(vectors[left]), ranks(vectors[right]))
        pairs.append({"repeats": [left, right], "spearman_rho": rho})
    values = [p["spearman_rho"] for p in pairs if p["spearman_rho"] is not None]
    return {
        "pairs": pairs,
        "median_spearman_rho": None if not values else statistics.median(values),
    }


def per_sha_stats(rows: list[dict]) -> list[dict]:
    result = []
    for sha in sorted({str(row["source_sha"]) for row in rows}):
        subset = [row for row in rows if str(row["source_sha"]) == sha]
        entry = {"source_sha": sha, "repeat_count": len(subset)}
        for field in (
            "queue_seconds_mean",
            "execute_seconds_total",
            "probe_execute_seconds",
            "orchestration_overhead_seconds",
            "runtime_pc1_frozen_score",
            "runtime_pc1_environment_residual",
        ):
            values = [float(row[field]) for row in subset]
            entry[field] = {
                "mean": mean(values),
                "sd": sample_sd(values),
                "cv": cv(values),
                "min": min(values),
                "max": max(values),
            }
        result.append(entry)
    return result


def semantic_scores(rows: list[dict], block: dict) -> dict[str, float]:
    means, sds = mean_sd(rows, SEMANTIC_FEATURES)
    vector = vector_from_pc1(block, SEMANTIC_FEATURES)
    out = {}
    for row in rows:
        out[str(row["source_sha"])] = sum(
            ((float(row[f]) - means[f]) / sds[f]) * vector[f]
            for f in SEMANTIC_FEATURES
        )
    return out


def association_by_repeat(
    rows: list[dict], semantic: dict[str, float], field: str
) -> list[dict]:
    result = []
    for repeat in (1, 2, 3):
        subset = sorted(
            (row for row in rows if int(row["repeat"]) == repeat),
            key=lambda row: str(row["source_sha"]),
        )
        runtime = [float(row[field]) for row in subset]
        sem = [semantic[str(row["source_sha"])] for row in subset]
        r = pearson(runtime, sem)
        rho = pearson(ranks(runtime), ranks(sem))
        result.append(
            {
                "repeat": repeat,
                "pearson_r": r,
                "spearman_rho": rho,
            }
        )
    return result


def rounded(value):
    return None if value is None else round(float(value), 6)


def round_tree(value):
    if isinstance(value, float):
        return rounded(value)
    if isinstance(value, list):
        return [round_tree(item) for item in value]
    if isinstance(value, dict):
        return {key: round_tree(item) for key, item in value.items()}
    return value


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
    if len(runtime_rows) != 15:
        raise ValueError("W75 requires exactly 15 measured runtime rows")
    seed = load(args.runtime_baseline_rows)
    runtime_baseline = [
        row
        for row in seed
        if row.get("observation_class") == "runtime"
        and row.get("execution_state") == "PASS"
        and all(row.get(feature) is not None for feature in RUNTIME_FEATURES)
    ]
    runtime_block = load(args.runtime_telemetry)["runtime_pca"]
    semantic_rows = load(args.semantic_rows)
    semantic_block = load(args.semantic_telemetry)["semantic_pca"]

    projected = project_rows(
        runtime_rows, runtime_baseline, runtime_block, RUNTIME_FEATURES
    )
    residualized, model = residualize(projected)
    semantic = semantic_scores(semantic_rows, semantic_block)
    runtime_shas = {str(row["source_sha"]) for row in residualized}
    if runtime_shas != set(semantic) or len(runtime_shas) != 5:
        raise ValueError("W75 runtime and semantic states must exact-pair on five SHAs")

    raw_icc = icc_one_way(residualized, "runtime_pc1_frozen_score")
    residual_icc = icc_one_way(
        residualized, "runtime_pc1_environment_residual"
    )
    raw_rank = pairwise_rank_stability(residualized, "runtime_pc1_frozen_score")
    residual_rank = pairwise_rank_stability(
        residualized, "runtime_pc1_environment_residual"
    )
    median_residual_rank = residual_rank["median_spearman_rho"]
    stable = (
        residual_icc is not None
        and residual_icc >= ICC_THRESHOLD
        and median_residual_rank is not None
        and median_residual_rank >= RANK_THRESHOLD
    )

    receipt = {
        "schema_version": "MC2-W75-DECONFOUNDED-STABILITY-0.1.0",
        "status": (
            "STABILITY_DIAGNOSTIC_PASS"
            if stable
            else "STABILITY_DIAGNOSTIC_WITHHELD"
        ),
        "authority": "derived_operational_analysis",
        "observation_count": len(residualized),
        "source_state_count": len(runtime_shas),
        "repeat_count_per_source": 3,
        "pair_key": "exact_source_sha",
        "runtime_axis_frozen": True,
        "semantic_axis_frozen": True,
        "loading_refit_performed": False,
        "joint_pca_performed": False,
        "timing_decomposition": {
            "queue_admission": "queue_seconds_mean",
            "orchestration_wall": "execute_seconds_total",
            "intrinsic_probe": "probe_execute_seconds",
            "orchestration_overhead": "execute_seconds_total - probe_execute_seconds",
        },
        "environment_deconfounding": model,
        "stability_design_decision": {
            "declared_before_measurement": True,
            "residual_icc_min": ICC_THRESHOLD,
            "median_pairwise_rank_rho_min": RANK_THRESHOLD,
            "both_required": True,
            "statistical_truth_claim": False,
        },
        "raw_frozen_pc1": {
            "icc_one_way_single_measure": raw_icc,
            "rank_stability": raw_rank,
            "semantic_association_by_repeat": association_by_repeat(
                residualized, semantic, "runtime_pc1_frozen_score"
            ),
        },
        "environment_residualized_pc1": {
            "icc_one_way_single_measure": residual_icc,
            "rank_stability": residual_rank,
            "semantic_association_by_repeat": association_by_repeat(
                residualized,
                semantic,
                "runtime_pc1_environment_residual",
            ),
        },
        "per_source_repeatability": per_sha_stats(residualized),
        "rows": residualized,
        "limitations": [
            "only five distinct source states are observed",
            "three repeats quantify short-horizon repeatability, not long-horizon stationarity",
            "environment residualization is observational and has no causal authority",
            "semantic PC1 contains only two observed topology states across the five SHAs",
            "stability PASS cannot compensate any external non-compensating gate",
        ],
        "bt_status": "WITHHELD_NO_OBSERVED_PAIRWISE_OUTCOME_EVIDENCE",
        "global_allocation_authority": False,
        "child_engineering_promotion_authority": False,
        "engineering_compliance_release_authority": False,
    }
    receipt = round_tree(receipt)
    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()
    receipt["receipt_sha256"] = hashlib.sha256(canonical).hexdigest()
    Path(args.out).write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
