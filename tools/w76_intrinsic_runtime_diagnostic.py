#!/usr/bin/env python3
"""Evaluate W76 source-sensitive runtime candidates before any PCA fit."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

ICC_THRESHOLD = 0.75
RANK_THRESHOLD = 0.80
CANDIDATES = (
    "probe_execute_seconds",
    "seconds_per_consumer_edge",
    "seconds_per_consumer_file",
    "seconds_per_bound_entity",
    "log_probe_execute_seconds",
    "log_seconds_per_consumer_edge",
)


def load_panel(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def canonical_rows_sha256(rows: list[dict]) -> str:
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def validate_panel(panel: dict) -> list[dict]:
    rows = panel["rows"]
    if len(rows) != 15:
        raise ValueError("W76 requires exactly 15 observations")
    shas = {str(row["source_sha"]) for row in rows}
    repeats = {int(row["repeat"]) for row in rows}
    if len(shas) != 5 or repeats != {1, 2, 3}:
        raise ValueError("W76 requires five source SHAs and repeats 1..3")
    for sha in shas:
        subset = [row for row in rows if str(row["source_sha"]) == sha]
        if len(subset) != 3 or {int(row["repeat"]) for row in subset} != {1, 2, 3}:
            raise ValueError(f"unbalanced repeat panel for {sha}")
        feature_hashes = {str(row["feature_row_sha256"]) for row in subset}
        counters = {
            json.dumps(row["work_counters"], sort_keys=True) for row in subset
        }
        if len(feature_hashes) != 1 or len(counters) != 1:
            raise ValueError(f"source-state identity drift across repeats for {sha}")
    observed = canonical_rows_sha256(rows)
    if observed != panel.get("panel_sha256"):
        raise ValueError(
            f"panel SHA mismatch: declared={panel.get('panel_sha256')} observed={observed}"
        )
    return rows


def feature_value(row: dict, feature: str) -> float:
    seconds = float(row["probe_execute_seconds"])
    counters = row["work_counters"]
    if feature == "probe_execute_seconds":
        return seconds
    if feature == "seconds_per_consumer_edge":
        return seconds / float(counters["consumer_edges"])
    if feature == "seconds_per_consumer_file":
        return seconds / float(counters["consumer_files"])
    if feature == "seconds_per_bound_entity":
        return seconds / float(counters["bound_entities"])
    if feature == "log_probe_execute_seconds":
        return math.log(seconds)
    if feature == "log_seconds_per_consumer_edge":
        return math.log(seconds / float(counters["consumer_edges"]))
    raise KeyError(feature)


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
    left_delta = [value - left_mean for value in left]
    right_delta = [value - right_mean for value in right]
    denominator = math.sqrt(
        sum(value * value for value in left_delta)
        * sum(value * value for value in right_delta)
    )
    if denominator < 1e-15:
        return None
    return sum(a * b for a, b in zip(left_delta, right_delta)) / denominator


def icc_one_way(rows: list[dict], feature: str) -> float | None:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        grouped[str(row["source_sha"])].append(feature_value(row, feature))
    n = len(grouped)
    k = 3
    values = [value for group in grouped.values() for value in group]
    grand = mean(values)
    group_means = {sha: mean(group) for sha, group in grouped.items()}
    ss_between = k * sum((value - grand) ** 2 for value in group_means.values())
    ss_within = sum(
        sum((value - group_means[sha]) ** 2 for value in group)
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
    pairs = []
    for left_repeat, right_repeat in ((1, 2), (1, 3), (2, 3)):
        left = [
            feature_value(
                next(
                    row
                    for row in rows
                    if int(row["repeat"]) == left_repeat
                    and str(row["source_sha"]) == sha
                ),
                feature,
            )
            for sha in shas
        ]
        right = [
            feature_value(
                next(
                    row
                    for row in rows
                    if int(row["repeat"]) == right_repeat
                    and str(row["source_sha"]) == sha
                ),
                feature,
            )
            for sha in shas
        ]
        rho = pearson(ranks(left), ranks(right))
        pairs.append(
            {
                "repeats": [left_repeat, right_repeat],
                "spearman_rho": rho,
            }
        )
    observed = [item["spearman_rho"] for item in pairs if item["spearman_rho"] is not None]
    return {
        "pairs": pairs,
        "median_spearman_rho": statistics.median(observed) if observed else None,
    }


def rounded(value):
    if value is None:
        return None
    return round(float(value), 6)


def evaluate(panel: dict) -> dict:
    rows = validate_panel(panel)
    metrics = {}
    eligible = []
    for feature in CANDIDATES:
        icc = icc_one_way(rows, feature)
        stability = rank_stability(rows, feature)
        median_rho = stability["median_spearman_rho"]
        passed = (
            icc is not None
            and icc >= ICC_THRESHOLD
            and median_rho is not None
            and median_rho >= RANK_THRESHOLD
        )
        metrics[feature] = {
            "icc_one_way_single_measure": rounded(icc),
            "rank_stability": {
                "pairs": [
                    {
                        "repeats": item["repeats"],
                        "spearman_rho": rounded(item["spearman_rho"]),
                    }
                    for item in stability["pairs"]
                ],
                "median_spearman_rho": rounded(median_rho),
            },
            "stability_gate_pass": passed,
        }
        if passed:
            eligible.append(feature)

    ranked = sorted(
        CANDIDATES,
        key=lambda feature: (
            metrics[feature]["icc_one_way_single_measure"],
            metrics[feature]["rank_stability"]["median_spearman_rho"],
        ),
        reverse=True,
    )
    pca_ready = len(eligible) >= 2
    return {
        "candidate_metrics": metrics,
        "eligible_runtime_features": eligible,
        "best_candidate": ranked[0],
        "pca_fit_permitted": pca_ready,
        "pca_status": (
            "ELIGIBLE_FOR_SEPARATE_PCA_STEP"
            if pca_ready
            else "WITHHELD_NO_STABLE_RUNTIME_FEATURE_SET"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", required=True)
    parser.add_argument("--out")
    args = parser.parse_args()

    result = evaluate(load_panel(args.panel))
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
