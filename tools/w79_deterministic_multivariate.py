#!/usr/bin/env python3
"""W79 diagnostic PCA/parallel-analysis over deterministic W78 work vectors.

This is derived operational analysis only.  It cannot grant engineering,
compliance, release, BT, or autonomous allocation authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable

import numpy as np

from w78_deterministic_work_probe import SEMANTIC_WORK_FEATURES, WORK_FEATURES

SCHEMA_VERSION = "MC2-W79-DETERMINISTIC-MULTIVARIATE-0.1.0"
MIN_TARGETS = 15
PA_REPLICATES = 2000
PA_QUANTILE = 0.95
RANDOM_SEED = 7901


def canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def load(paths: Iterable[str]) -> list[dict]:
    return [json.loads(Path(path).read_text(encoding="utf-8")) for path in paths]


def validate_rows(rows: list[dict]) -> list[dict]:
    if len(rows) != MIN_TARGETS:
        raise ValueError(f"W79 requires exactly {MIN_TARGETS} source-state receipts")
    shas = [str(row.get("source_sha", "")) for row in rows]
    labels = [str(row.get("matrix_label", "")) for row in rows]
    if len(set(shas)) != MIN_TARGETS or any(not sha for sha in shas):
        raise ValueError("W79 requires 15 unique non-empty source SHAs")
    if len(set(labels)) != MIN_TARGETS or any(not label for label in labels):
        raise ValueError("W79 requires 15 unique non-empty matrix labels")
    for row in rows:
        if row.get("execution_state") != "PASS":
            raise ValueError(f"non-PASS W78 source row: {row.get('source_sha')}")
        if row.get("semantic_parity_with_w72") is not True:
            raise ValueError(f"semantic parity failure: {row.get('source_sha')}")
        if not isinstance(row.get("work_vector"), dict):
            raise ValueError("work_vector missing")
        if not isinstance(row.get("semantic_work_vector"), dict):
            raise ValueError("semantic_work_vector missing")
    return sorted(rows, key=lambda row: str(row["matrix_label"]))


def standardized_log_matrix(
    rows: list[dict], features: tuple[str, ...], field: str
) -> tuple[np.ndarray, list[str], list[str]]:
    raw = np.asarray(
        [[float(row[field][feature]) for feature in features] for row in rows],
        dtype=float,
    )
    if np.any(raw < 0):
        raise ValueError("deterministic work counts must be non-negative")
    transformed = np.log1p(raw)
    scales = transformed.std(axis=0, ddof=1)
    keep = scales > 1.0e-12
    kept_features = [feature for feature, flag in zip(features, keep) if flag]
    dropped_features = [feature for feature, flag in zip(features, keep) if not flag]
    if len(kept_features) < 3:
        raise ValueError("fewer than three variable features remain after screening")
    x = transformed[:, keep]
    means = x.mean(axis=0)
    std = x.std(axis=0, ddof=1)
    z = (x - means) / std
    return z, kept_features, dropped_features


def ordered_eigendecomposition(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    values, vectors = np.linalg.eigh(matrix)
    order = np.argsort(values)[::-1]
    values = np.clip(values[order], 0.0, None)
    vectors = vectors[:, order]
    # Eigenvector sign is arbitrary. Fix it using the largest absolute loading so
    # receipts stay byte-stable for a pinned numerical stack.
    for idx in range(vectors.shape[1]):
        pivot = int(np.argmax(np.abs(vectors[:, idx])))
        if vectors[pivot, idx] < 0:
            vectors[:, idx] *= -1.0
    return values, vectors


def parallel_analysis_thresholds(
    n_rows: int, n_features: int, *, seed: int, replicates: int
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    simulated = np.empty((replicates, n_features), dtype=float)
    for idx in range(replicates):
        x = rng.normal(size=(n_rows, n_features))
        x = (x - x.mean(axis=0)) / x.std(axis=0, ddof=1)
        correlation = np.cov(x, rowvar=False, ddof=1)
        simulated[idx], _ = ordered_eigendecomposition(correlation)
    return np.quantile(simulated, PA_QUANTILE, axis=0)


def rounded_list(values: np.ndarray, digits: int = 8) -> list[float]:
    return [round(float(value), digits) for value in values]


def analyze_panel(
    rows: list[dict], features: tuple[str, ...], field: str, panel_name: str
) -> dict:
    z, kept_features, dropped_features = standardized_log_matrix(rows, features, field)
    correlation = np.cov(z, rowvar=False, ddof=1)
    eigenvalues, eigenvectors = ordered_eigendecomposition(correlation)
    thresholds = parallel_analysis_thresholds(
        z.shape[0], z.shape[1], seed=RANDOM_SEED, replicates=PA_REPLICATES
    )
    retained = 0
    for empirical, threshold in zip(eigenvalues, thresholds):
        if empirical > threshold:
            retained += 1
        else:
            break
    total = float(eigenvalues.sum()) or 1.0
    explained = eigenvalues / total
    loadings = eigenvectors * np.sqrt(eigenvalues)
    scores = z @ eigenvectors

    retained_components: list[dict] = []
    for component in range(retained):
        ranked = sorted(
            (
                (kept_features[row], float(loadings[row, component]))
                for row in range(len(kept_features))
            ),
            key=lambda pair: (-abs(pair[1]), pair[0]),
        )
        retained_components.append(
            {
                "component": component + 1,
                "eigenvalue": round(float(eigenvalues[component]), 8),
                "pa95_threshold": round(float(thresholds[component]), 8),
                "explained_variance_ratio": round(float(explained[component]), 8),
                "top_loadings": [
                    {"feature": name, "loading": round(value, 8)}
                    for name, value in ranked[: min(5, len(ranked))]
                ],
                "source_scores": [
                    {
                        "matrix_label": str(row["matrix_label"]),
                        "source_sha": str(row["source_sha"]),
                        "score": round(float(scores[index, component]), 8),
                    }
                    for index, row in enumerate(rows)
                ],
            }
        )

    return {
        "panel": panel_name,
        "input_field": field,
        "input_feature_count": len(features),
        "effective_feature_count": len(kept_features),
        "effective_features": kept_features,
        "dropped_constant_features": dropped_features,
        "target_count": len(rows),
        "sample_to_feature_ratio": round(len(rows) / len(kept_features), 6),
        "small_sample_warning": len(rows) < 5 * len(kept_features),
        "transform": "LOG1P_THEN_COLUMN_ZSCORE_DDOF1",
        "correlation_matrix_rank": int(np.linalg.matrix_rank(correlation)),
        "eigenvalues": rounded_list(eigenvalues),
        "explained_variance_ratio": rounded_list(explained),
        "parallel_analysis": {
            "method": "NORMAL_RANDOM_CORRELATION_PA95",
            "replicates": PA_REPLICATES,
            "quantile": PA_QUANTILE,
            "random_seed": RANDOM_SEED,
            "thresholds": rounded_list(thresholds),
            "retained_component_count": retained,
            "retention_rule": "CONTIGUOUS_PREFIX_EMPIRICAL_EIGENVALUE_GT_PA95",
        },
        "retained_components": retained_components,
        "interpretation_role": "EXPLORATORY_DIAGNOSTIC_ONLY",
    }


def evaluate(
    rows: list[dict], *, w78_run_id: str, w78_head_sha: str, w78_artifact_id: str,
    w78_artifact_digest: str
) -> dict:
    ordered = validate_rows(rows)
    bound_inputs = [
        {
            "matrix_label": row["matrix_label"],
            "source_sha": row["source_sha"],
            "work_vector": row["work_vector"],
            "semantic_work_vector": row["semantic_work_vector"],
        }
        for row in ordered
    ]
    result = {
        "schema_version": SCHEMA_VERSION,
        "status": "DIAGNOSTIC_PCA_PA_COMPLETE",
        "authority": "derived_operational_analysis",
        "source_panel": {
            "target_count": len(ordered),
            "matrix_labels": [str(row["matrix_label"]) for row in ordered],
            "source_shas": [str(row["source_sha"]) for row in ordered],
            "input_sha256": canonical_sha256(bound_inputs),
            "w78_proof": {
                "run_id": str(w78_run_id),
                "head_sha": str(w78_head_sha),
                "diversity_artifact_id": str(w78_artifact_id),
                "diversity_artifact_digest": str(w78_artifact_digest),
                "historical_gate": "DIVERSITY_GATE_PASS_FOR_W79_ANALYSIS",
            },
        },
        "primary_semantic_work_panel": analyze_panel(
            ordered,
            SEMANTIC_WORK_FEATURES,
            "semantic_work_vector",
            "SEMANTIC_WORK_PRIMARY",
        ),
        "all_work_sensitivity_panel": analyze_panel(
            ordered,
            WORK_FEATURES,
            "work_vector",
            "ALL_DETERMINISTIC_WORK_SENSITIVITY",
        ),
        "bt_status": "WITHHELD_NO_OBSERVED_PAIRWISE_OUTCOME_EVIDENCE",
        "reverse_bt_status": "WITHHELD_NO_PAIRWISE_OUTCOME_GRAPH",
        "allocation_status": "DESCRIPTIVE_PC_SCORES_ONLY_NO_AUTONOMOUS_ALLOCATION",
        "global_allocation_authority": False,
        "child_engineering_promotion_authority": False,
        "engineering_compliance_release_authority": False,
        "qps_credit_delta": 0,
        "non_compensating_blockers": ["cryoplant-project#923"],
    }
    result["receipt_sha256"] = canonical_sha256(result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("receipts", nargs="+")
    parser.add_argument("--out", required=True)
    parser.add_argument("--w78-run-id", required=True)
    parser.add_argument("--w78-head-sha", required=True)
    parser.add_argument("--w78-artifact-id", required=True)
    parser.add_argument("--w78-artifact-digest", required=True)
    args = parser.parse_args()
    result = evaluate(
        load(args.receipts),
        w78_run_id=args.w78_run_id,
        w78_head_sha=args.w78_head_sha,
        w78_artifact_id=args.w78_artifact_id,
        w78_artifact_digest=args.w78_artifact_digest,
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
