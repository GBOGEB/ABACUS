#!/usr/bin/env python3
"""Evaluate repeatability of W77 phase-normalized runtime features."""
from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

ICC_THRESHOLD = 0.75
RANK_THRESHOLD = 0.80
MEDIAN_CV_THRESHOLD = 0.20
CANDIDATES = (
    "parse_cpu_seconds_per_entity",
    "scan_cpu_seconds_per_mib",
    "scan_cpu_seconds_per_candidate_check",
    "graph_cpu_seconds_per_edge",
    "emit_cpu_seconds_per_receipt",
    "scan_wall_seconds_per_mib",
    "graph_wall_seconds_per_edge",
)


def load_receipts(paths: list[str]) -> list[dict]:
    return [json.loads(Path(path).read_text(encoding="utf-8")) for path in paths]


def validate(receipts: list[dict]) -> list[dict]:
    if len(receipts) != 15:
        raise ValueError("W77 requires exactly 15 probe receipts")
    shas = {str(row["source_sha"]) for row in receipts}
    repeats = {int(row["repeat"]) for row in receipts}
    if len(shas) != 5 or repeats != {1, 2, 3}:
        raise ValueError("W77 requires five source SHAs and repeats 1..3")
    for row in receipts:
        if row.get("execution_state") != "PASS":
            raise ValueError("W77 only accepts PASS probe receipts")
        if row.get("semantic_parity_with_w72") is not True:
            raise ValueError("W77 requires semantic parity with W72")
        features = row.get("runtime_sensitive_features", {})
        if any(feature not in features for feature in CANDIDATES):
            raise ValueError("W77 probe receipt is missing runtime features")
    for sha in shas:
        subset = [row for row in receipts if str(row["source_sha"]) == sha]
        if len(subset) != 3 or {int(row["repeat"]) for row in subset} != {1, 2, 3}:
            raise ValueError(f"unbalanced W77 repeat panel for {sha}")
        feature_hashes = {str(row["feature_row_sha256"]) for row in subset}
        counters = {
            json.dumps(row["work_counters"], sort_keys=True) for row in subset
        }
        if len(feature_hashes) != 1 or len(counters) != 1:
            raise ValueError(f"source-state identity drift across repeats for {sha}")
    return receipts


def value(row: dict, feature: str) -> float:
    return float(row["runtime_sensitive_features"][feature])


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    out = [0.0] * len(values)
    index = 0
    while index < len(values):
        end = index
        while end + 1 < len(values) and values[order[end + 1]] == values[order[index]]:
            end += 1
        average_rank = (index + end + 2) / 2.0
        for position in range(index, end + 1):
            out[order[position]] = average_rank
        index = end + 1
    return out


def pearson(left: list[float], right: list[float]) -> float | None:
    left_mean = mean(left)
    right_mean = mean(right)
    left_delta = [item - left_mean for item in left]
    right_delta = [item - right_mean for item in right]
    denominator = math.sqrt(
        sum(item * item for item in left_delta)
        * sum(item * item for item in right_delta)
    )
    if denominator < 1e-15:
        return None
    return sum(a * b for a, b in zip(left_delta, right_delta)) / denominator


def icc_one_way(rows: list[dict], feature: str) -> float | None:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        grouped[str(row["source_sha"])].append(value(row, feature))
    n = len(grouped)
    k = 3
    flat = [item for group in grouped.values() for item in group]
    grand = mean(flat)
    group_means = {sha: mean(group) for sha, group in grouped.items()}
    ss_between = k * sum((item - grand) ** 2 for item in group_means.values())
    ss_within = sum(
        sum((item - group_means[sha]) ** 2 for item in group)
        for sha, group in grouped.items()
    )
    ms_between = ss_between / (n - 1)
    ms_within = ss_within / (n * (k - 1))
    denominator = ms_between + (k - 1) * ms_within
    if abs(denominator) < 1e-15:
        return None
    return (ms_between - ms_within) / denominator


def rank_stability(rows: list[dict], feature: str) -> dict:
    shas = sorted({str(row["source_sha"]) for row in rows})
    lookup = {
        (int(row["repeat"]), str(row["source_sha"])): value(row, feature)
        for row in rows
    }
    pairs = []
    for left, right in ((1, 2), (1, 3), (2, 3)):
        left_values = [lookup[(left, sha)] for sha in shas]
        right_values = [lookup[(right, sha)] for sha in shas]
        rho = pearson(ranks(left_values), ranks(right_values))
        pairs.append({"repeats": [left, right], "spearman_rho": rho})
    observed = [item["spearman_rho"] for item in pairs if item["spearman_rho"] is not None]
    return {
        "pairs": pairs,
        "median_spearman_rho": statistics.median(observed) if observed else None,
    }


def median_source_cv(rows: list[dict], feature: str) -> tuple[float | None, list[dict]]:
    result = []
    for sha in sorted({str(row["source_sha"]) for row in rows}):
        values = [value(row, feature) for row in rows if str(row["source_sha"]) == sha]
        avg = mean(values)
        cv = None if abs(avg) < 1e-15 else statistics.stdev(values) / abs(avg)
        result.append({"source_sha": sha, "cv": cv})
    observed = [item["cv"] for item in result if item["cv"] is not None]
    return (statistics.median(observed) if observed else None), result


def rounded(item):
    return None if item is None else round(float(item), 6)


def evaluate(receipts: list[dict]) -> dict:
    rows = validate(receipts)
    metrics = {}
    eligible = []
    for feature in CANDIDATES:
        icc = icc_one_way(rows, feature)
        rank = rank_stability(rows, feature)
        median_rho = rank["median_spearman_rho"]
        median_cv, source_cvs = median_source_cv(rows, feature)
        passed = (
            icc is not None
            and icc >= ICC_THRESHOLD
            and median_rho is not None
            and median_rho >= RANK_THRESHOLD
            and median_cv is not None
            and median_cv <= MEDIAN_CV_THRESHOLD
        )
        metrics[feature] = {
            "icc_one_way_single_measure": rounded(icc),
            "rank_stability": {
                "pairs": [
                    {
                        "repeats": item["repeats"],
                        "spearman_rho": rounded(item["spearman_rho"]),
                    }
                    for item in rank["pairs"]
                ],
                "median_spearman_rho": rounded(median_rho),
            },
            "median_source_cv": rounded(median_cv),
            "source_cvs": [
                {"source_sha": item["source_sha"], "cv": rounded(item["cv"])}
                for item in source_cvs
            ],
            "stability_gate_pass": passed,
        }
        if passed:
            eligible.append(feature)

    pca_permitted = len(eligible) >= 2
    return {
        "schema_version": "MC2-W77-PHASE-STABILITY-0.1.0",
        "status": (
            "PCA_ELIGIBLE_FEATURE_SET"
            if pca_permitted
            else "PCA_WITHHELD_NO_STABLE_PHASE_FEATURE_SET"
        ),
        "authority": "derived_operational_analysis",
        "observation_count": len(rows),
        "source_state_count": 5,
        "repeat_count_per_source": 3,
        "stability_design_decision": {
            "declared_before_measurement": True,
            "icc_min": ICC_THRESHOLD,
            "median_pairwise_rank_rho_min": RANK_THRESHOLD,
            "median_source_cv_max": MEDIAN_CV_THRESHOLD,
            "all_three_required": True,
            "statistical_truth_claim": False,
        },
        "candidate_metrics": metrics,
        "eligible_runtime_features": eligible,
        "pca_next_step_permitted": pca_permitted,
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
    result = evaluate(load_receipts(args.receipts))
    Path(args.out).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
