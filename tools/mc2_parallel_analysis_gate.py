#!/usr/bin/env python3
"""Deterministic MC-2 PA95 retention gate for a measured PCA receipt.

This gate does not recompute PCA and does not grant allocation authority.
It tests observed eigenvalues against a null distribution generated for the
same sample size and feature count. Small-N output remains diagnostic only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from pathlib import Path


def fail(message: str) -> None:
    raise ValueError(message)


def standardize_matrix(matrix):
    n = len(matrix)
    p = len(matrix[0])
    means = [sum(row[j] for row in matrix) / n for j in range(p)]
    sds = []
    for j, mean in enumerate(means):
        sds.append(
            math.sqrt(
                sum((row[j] - mean) ** 2 for row in matrix) / max(n - 1, 1)
            )
        )
    return [
        [
            0.0 if sds[j] == 0 else (row[j] - means[j]) / sds[j]
            for j in range(p)
        ]
        for row in matrix
    ]


def covariance(z):
    n = len(z)
    p = len(z[0])
    return [
        [
            sum(z[i][a] * z[i][b] for i in range(n)) / max(n - 1, 1)
            for b in range(p)
        ]
        for a in range(p)
    ]


def jacobi_eigenvalues(matrix, max_iter=200, tol=1e-12):
    n = len(matrix)
    a = [row[:] for row in matrix]
    for _ in range(max_iter):
        p = q = 0
        largest = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                if abs(a[i][j]) > largest:
                    largest = abs(a[i][j])
                    p, q = i, j
        if largest < tol:
            break
        if a[p][p] == a[q][q]:
            theta = math.pi / 4
        else:
            theta = 0.5 * math.atan2(2 * a[p][q], a[q][q] - a[p][p])
        c, s = math.cos(theta), math.sin(theta)
        app, aqq, apq = a[p][p], a[q][q], a[p][q]
        a[p][p] = c * c * app - 2 * s * c * apq + s * s * aqq
        a[q][q] = s * s * app + 2 * s * c * apq + c * c * aqq
        a[p][q] = a[q][p] = 0.0
        for r in range(n):
            if r in (p, q):
                continue
            arp, arq = a[r][p], a[r][q]
            a[r][p] = a[p][r] = c * arp - s * arq
            a[r][q] = a[q][r] = s * arp + c * arq
    return sorted((a[i][i] for i in range(n)), reverse=True)


def quantile_linear(values, q):
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    low = int(math.floor(pos))
    high = int(math.ceil(pos))
    if low == high:
        return ordered[low]
    return ordered[low] + (pos - low) * (ordered[high] - ordered[low])


def parallel_analysis(n, p, *, simulations, seed, quantile):
    rng = random.Random(seed)
    simulated = [[] for _ in range(p)]
    for _ in range(simulations):
        matrix = [[rng.gauss(0.0, 1.0) for _ in range(p)] for _ in range(n)]
        eigenvalues = jacobi_eigenvalues(covariance(standardize_matrix(matrix)))
        for index, value in enumerate(eigenvalues):
            simulated[index].append(value)
    return [quantile_linear(values, quantile) for values in simulated]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("receipt")
    parser.add_argument("--out", required=True)
    parser.add_argument("--simulations", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260913)
    parser.add_argument("--quantile", type=float, default=0.95)
    args = parser.parse_args()

    source = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    runtime = source.get("runtime_pca", {})
    if runtime.get("status") != "MEASURED_PCA_DIAGNOSTIC":
        fail("runtime PCA must be MEASURED_PCA_DIAGNOSTIC")
    components = runtime.get("components") or []
    n = int(runtime.get("numeric_comparable_rows", 0))
    p = len(components)
    if n < 5 or p < 2:
        fail("PA95 requires at least five observations and two varying features")
    if args.simulations < 500:
        fail("at least 500 simulations required")
    if not 0.5 < args.quantile < 1.0:
        fail("quantile must be between 0.5 and 1.0")

    observed = [float(component["eigenvalue"]) for component in components]
    thresholds = parallel_analysis(
        n,
        p,
        simulations=args.simulations,
        seed=args.seed,
        quantile=args.quantile,
    )
    retained = [
        index + 1
        for index, (value, threshold) in enumerate(zip(observed, thresholds))
        if value > threshold
    ]
    result = {
        "schema_version": "MC2-PA95-RETENTION-0.1.0",
        "source_receipt_sha256": source.get("receipt_sha256"),
        "sample_size": n,
        "varying_feature_count": p,
        "simulations": args.simulations,
        "seed": args.seed,
        "quantile": args.quantile,
        "observed_eigenvalues": [round(value, 6) for value in observed],
        "null_eigenvalue_thresholds": [round(value, 6) for value in thresholds],
        "retained_pcs": retained,
        "retained_component_count": len(retained),
        "pc2_diagnostic_not_retained": 2 not in retained and p >= 2,
        "status": "PA95_DIAGNOSTIC",
        "small_sample_warning": n < 10 * p,
        "retention_authority": "DIAGNOSTIC_ONLY",
        "allocation_authority": False,
        "child_engineering_promotion_authority": False,
        "bt_status": "WITHHELD_NO_OBSERVED_PAIRWISE_EVIDENCE",
    }
    canonical = json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
    result["receipt_sha256"] = hashlib.sha256(canonical).hexdigest()
    Path(args.out).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
