#!/usr/bin/env python3
"""W79 deterministic complexity PCA/PA95 over the governed W78 work census."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

SCHEMA = "MC2-W79-DETERMINISTIC-WORK-PCA-0.1.0"
INPUT_SCHEMA = "MC2-W79-W78-INPUT-0.1.0"
DEFAULT_SIMULATIONS = 5000
DEFAULT_SEED = 20260914
DEFAULT_QUANTILE = 0.95
EXPECTED_W78 = {
    "workflow_run_id": 34777543492,
    "artifact_id": 10323323552,
    "artifact_digest": (
        "sha256:6e0a868916c1730fdc8eefc1f24ffea06185ca56ef1a8caffdaeb325eed445ae"
    ),
    "receipt_sha256": (
        "2717802c3e2bd80f4800e77149e12f47ad6595d3b2142b93b6748a4c0d4c72ed"
    ),
}


def canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _quantile_linear(values: list[float], q: float) -> float:
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    low = int(math.floor(pos))
    high = int(math.ceil(pos))
    if low == high:
        return ordered[low]
    return ordered[low] + (pos - low) * (ordered[high] - ordered[low])


def _standardize(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    means = matrix.mean(axis=0)
    sds = matrix.std(axis=0, ddof=1)
    if np.any(sds <= 0):
        raise ValueError("W79 requires every selected feature to vary")
    return (matrix - means) / sds, means, sds


def _parallel_analysis(
    n: int,
    p: int,
    *,
    simulations: int,
    seed: int,
    quantile: float,
) -> list[float]:
    if simulations < 500:
        raise ValueError("W79 requires at least 500 PA simulations")
    if not 0.5 < quantile < 1.0:
        raise ValueError("W79 PA quantile must be between 0.5 and 1.0")
    rng = np.random.default_rng(seed)
    buckets: list[list[float]] = [[] for _ in range(p)]
    for _ in range(simulations):
        sample = rng.normal(size=(n, p))
        z, _, _ = _standardize(sample)
        eigvals = np.linalg.eigvalsh(np.cov(z, rowvar=False, ddof=1))[::-1]
        for idx, value in enumerate(eigvals):
            buckets[idx].append(float(value))
    return [_quantile_linear(bucket, quantile) for bucket in buckets]


def _orient(loadings: np.ndarray, scores: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    loadings = loadings.copy()
    scores = scores.copy()
    for comp in range(loadings.shape[1]):
        pivot = int(np.argmax(np.abs(loadings[:, comp])))
        if loadings[pivot, comp] < 0:
            loadings[:, comp] *= -1
            scores[:, comp] *= -1
    return loadings, scores


def _fit_block(
    rows: list[dict],
    *,
    field: str,
    features: list[str],
    simulations: int,
    seed: int,
    quantile: float,
) -> dict:
    matrix = np.asarray(
        [[float(row[field][feature]) for feature in features] for row in rows],
        dtype=float,
    )
    z, means, sds = _standardize(matrix)
    eigenvalues, eigenvectors = np.linalg.eigh(np.cov(z, rowvar=False, ddof=1))
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]
    scores = z @ eigenvectors
    loadings, scores = _orient(eigenvectors, scores)
    thresholds = _parallel_analysis(
        len(rows),
        len(features),
        simulations=simulations,
        seed=seed,
        quantile=quantile,
    )
    retained = [
        idx + 1
        for idx, (observed, threshold) in enumerate(zip(eigenvalues, thresholds))
        if float(observed) > float(threshold)
    ]
    total = float(eigenvalues.sum())
    components = []
    for comp in range(len(features)):
        components.append(
            {
                "pc": comp + 1,
                "eigenvalue": round(float(eigenvalues[comp]), 6),
                "explained_variance_ratio": round(
                    float(eigenvalues[comp]) / total if total else 0.0, 6
                ),
                "pa95_threshold": round(float(thresholds[comp]), 6),
                "retained": (comp + 1) in retained,
                "loadings": {
                    feature: round(float(loadings[idx, comp]), 6)
                    for idx, feature in enumerate(features)
                },
            }
        )
    return {
        "feature_count": len(features),
        "features": features,
        "sample_size": len(rows),
        "centered_matrix_rank": int(np.linalg.matrix_rank(z)),
        "feature_means": {
            feature: round(float(means[idx]), 6)
            for idx, feature in enumerate(features)
        },
        "feature_sample_sds": {
            feature: round(float(sds[idx]), 6)
            for idx, feature in enumerate(features)
        },
        "components": components,
        "retained_pcs": retained,
        "retained_component_count": len(retained),
        "score_rows": [
            {
                "source_sha": row["source_sha"],
                "matrix_label": row["matrix_label"],
                "scores": {
                    f"pc{comp + 1}": round(float(scores[idx, comp]), 6)
                    for comp in range(len(features))
                },
            }
            for idx, row in enumerate(rows)
        ],
    }


def validate_input(source: dict) -> list[dict]:
    if source.get("schema_version") != INPUT_SCHEMA:
        raise ValueError("W79 input schema mismatch")
    w78 = source.get("source_w78") or {}
    for field, expected in EXPECTED_W78.items():
        if w78.get(field) != expected:
            raise ValueError(f"W78 governed lineage mismatch for {field}")
    if w78.get("status") != "DIVERSITY_GATE_PASS_FOR_W79_ANALYSIS":
        raise ValueError("W79 requires a W78 diversity gate PASS")
    if w78.get("w79_multivariate_analysis_permitted") is not True:
        raise ValueError("W78 did not permit W79 analysis")
    if w78.get("deterministic_replay_consistency") != "PASS_15_OF_15":
        raise ValueError("W79 requires W78 deterministic replay PASS_15_OF_15")
    if (
        int(w78.get("target_count", 0)) != 15
        or int(w78.get("observation_count", 0)) != 30
    ):
        raise ValueError("W79 requires the governed 15-target/30-observation W78 panel")

    work_features = list(source.get("work_features") or [])
    semantic_features = list(source.get("semantic_work_features") or [])
    if len(work_features) < 3 or len(semantic_features) < 3:
        raise ValueError("W79 requires multivariate deterministic work blocks")
    if not set(semantic_features).issubset(work_features):
        raise ValueError("semantic work features must be a subset of work features")

    rows = list(source.get("rows") or [])
    if len(rows) != 15 or len({row.get("sha") for row in rows}) != 15:
        raise ValueError("W79 requires 15 unique collapsed exact-SHA rows")
    if len({row.get("label") for row in rows}) != 15:
        raise ValueError("W79 requires 15 unique matrix labels")

    normalized = []
    for row in rows:
        values = list(row.get("values") or [])
        if len(values) != len(work_features):
            raise ValueError(f"work feature drift for {row.get('sha')}")
        work = dict(zip(work_features, values))
        if canonical_sha256(work) != row.get("work_sha256"):
            raise ValueError(f"work-vector hash mismatch for {row.get('sha')}")
        semantic = {feature: work[feature] for feature in semantic_features}
        if canonical_sha256(semantic) != row.get("semantic_sha256"):
            raise ValueError(f"semantic work-vector hash mismatch for {row.get('sha')}")
        normalized.append(
            {
                "source_sha": row["sha"],
                "matrix_label": row["label"],
                "work_vector": work,
                "semantic_work_vector": semantic,
            }
        )
    return sorted(normalized, key=lambda row: str(row["source_sha"]))


def evaluate(
    source: dict,
    *,
    source_input_sha256: str | None = None,
    simulations: int = DEFAULT_SIMULATIONS,
    seed: int = DEFAULT_SEED,
    quantile: float = DEFAULT_QUANTILE,
) -> dict:
    rows = validate_input(source)
    work_features = list(source["work_features"])
    semantic_features = list(source["semantic_work_features"])
    w78 = dict(source["source_w78"])

    full = _fit_block(
        rows,
        field="work_vector",
        features=work_features,
        simulations=simulations,
        seed=seed,
        quantile=quantile,
    )
    semantic = _fit_block(
        rows,
        field="semantic_work_vector",
        features=semantic_features,
        simulations=simulations,
        seed=seed + 1,
        quantile=quantile,
    )
    result = {
        "schema_version": SCHEMA,
        "status": "DETERMINISTIC_COMPLEXITY_PCA_DIAGNOSTIC",
        "authority": "derived_operational_analysis",
        "measurement_basis": "deterministic_work_complexity_not_elapsed_time",
        "source_input_sha256": source_input_sha256,
        "source_w78": w78,
        "parallel_analysis": {
            "simulations": simulations,
            "quantile": quantile,
            "full_seed": seed,
            "semantic_seed": seed + 1,
            "retention_rule": "retain observed eigenvalue strictly above PA95 threshold",
        },
        "full_work_pca": full,
        "semantic_work_pca": semantic,
        "small_sample_warning": True,
        "pca_fit_performed": True,
        "timing_pca_reopened": False,
        "next_step": (
            "validate retained deterministic components against independent observed "
            "outcomes before any allocation authority"
        ),
        "bt_status": "WITHHELD_NO_OBSERVED_PAIRWISE_OUTCOME_EVIDENCE",
        "global_allocation_authority": False,
        "child_engineering_promotion_authority": False,
        "engineering_compliance_release_authority": False,
    }
    result["receipt_sha256"] = canonical_sha256(result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--out", required=True)
    parser.add_argument("--simulations", type=int, default=DEFAULT_SIMULATIONS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--quantile", type=float, default=DEFAULT_QUANTILE)
    args = parser.parse_args()

    input_path = Path(args.input)
    source = json.loads(input_path.read_text(encoding="utf-8"))
    result = evaluate(
        source,
        source_input_sha256=file_sha256(input_path),
        simulations=args.simulations,
        seed=args.seed,
        quantile=args.quantile,
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
