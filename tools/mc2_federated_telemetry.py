#!/usr/bin/env python3
"""MC-2 typed semantic/runtime telemetry gate.

Builds one federated envelope with separate semantic and runtime blocks.
It never zero-imputes missing values and never mixes authority classes.
Runtime PCA is only emitted when >=5 comparable, distinct-SHA observations exist.
BT remains WITHHELD unless observed pairwise evidence is supplied elsewhere.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

SHA40 = re.compile(r"^[0-9a-f]{40}$")
RUNTIME_FEATURES = [
    "runner_allocated_fraction",
    "steps_executed_total",
    "queue_seconds_mean",
    "execute_seconds_total",
    "evidence_emit_count",
]
SEMANTIC_FEATURES = [
    "registry_gap_rate",
    "unresolved_reference_rate",
    "consumer_penetration_rate",
    "graph_drop_rate",
    "lineage_gap_rate",
]
ALLOWED_AUTHORITY = {
    "source_supported",
    "child_controlled",
    "derived_operational_analysis",
    "diagnostic_only",
}
ALLOWED_RUNTIME_STATES = {"PASS", "FAIL", "DEFER", "NOT_EXECUTED"}


def fail(msg: str) -> None:
    raise ValueError(msg)


def finite_number(value) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def load_rows(paths):
    rows = []
    for path in paths:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if isinstance(data, list):
            rows.extend(data)
        elif isinstance(data, dict):
            rows.append(data)
        else:
            fail(f"{path}: JSON root must be object or list")
    return rows


def validate_common(row, index):
    for key in (
        "row_id",
        "observation_class",
        "source_repo",
        "source_sha",
        "evidence_reference",
        "authority_class",
    ):
        if not row.get(key):
            fail(f"row {index}: missing {key}")
    if row["observation_class"] not in {"semantic", "runtime"}:
        fail(f"row {index}: unsupported observation_class")
    if not SHA40.fullmatch(str(row["source_sha"])):
        fail(f"row {index}: source_sha must be exact 40-char lowercase hex")
    if row["authority_class"] not in ALLOWED_AUTHORITY:
        fail(f"row {index}: unsupported authority_class")


def validate_runtime(row, index):
    state = row.get("execution_state")
    if state not in ALLOWED_RUNTIME_STATES:
        fail(f"row {index}: unsupported execution_state")
    runner_fraction = row.get("runner_allocated_fraction")
    steps = row.get("steps_executed_total")
    jobs = row.get("job_count")
    evidence = row.get("evidence_emit_count")
    for key, value in (
        ("runner_allocated_fraction", runner_fraction),
        ("steps_executed_total", steps),
        ("job_count", jobs),
        ("evidence_emit_count", evidence),
    ):
        if not finite_number(value) or float(value) < 0:
            fail(f"row {index}: invalid {key}")
    if not 0 <= float(runner_fraction) <= 1:
        fail(f"row {index}: runner_allocated_fraction outside [0,1]")
    if int(steps) != steps or int(jobs) != jobs or int(evidence) != evidence:
        fail(f"row {index}: steps/job/evidence counts must be integers")
    if state == "NOT_EXECUTED":
        if int(steps) != 0 or float(runner_fraction) != 0:
            fail(
                f"row {index}: NOT_EXECUTED requires zero steps and zero runner allocation"
            )
    else:
        if int(steps) <= 0 or float(runner_fraction) <= 0:
            fail(f"row {index}: executed state requires >0 steps and runner allocation")
    for key in ("queue_seconds_mean", "execute_seconds_total"):
        value = row.get(key)
        if value is not None and (not finite_number(value) or float(value) < 0):
            fail(f"row {index}: invalid {key}")


def validate_semantic(row, index):
    for key in SEMANTIC_FEATURES:
        value = row.get(key)
        if value is not None and (
            not finite_number(value) or not 0 <= float(value) <= 1
        ):
            fail(f"row {index}: invalid semantic feature {key}")


def comparable(row, features):
    return all(finite_number(row.get(key)) for key in features)


def standardize(rows, features):
    cols = [[float(row[key]) for row in rows] for key in features]
    means = [sum(col) / len(col) for col in cols]
    sds = []
    for col, mean in zip(cols, means):
        denom = max(len(col) - 1, 1)
        sds.append(math.sqrt(sum((x - mean) ** 2 for x in col) / denom))
    z = []
    for row in rows:
        z.append(
            [
                0.0
                if sds[j] == 0
                else (float(row[features[j]]) - means[j]) / sds[j]
                for j in range(len(features))
            ]
        )
    return z


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


def jacobi_eigen(matrix, max_iter=200, tol=1e-12):
    """Eigenpairs for a real symmetric matrix, stdlib only."""
    n = len(matrix)
    a = [row[:] for row in matrix]
    v = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
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
            theta = 0.5 * math.atan2(
                2 * a[p][q], a[q][q] - a[p][p]
            )
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
        for r in range(n):
            vrp, vrq = v[r][p], v[r][q]
            v[r][p] = c * vrp - s * vrq
            v[r][q] = s * vrp + c * vrq
    pairs = [(a[i][i], [v[r][i] for r in range(n)]) for i in range(n)]
    return sorted(pairs, key=lambda item: item[0], reverse=True)


def pca_block(rows, features, minimum_rows=5, minimum_distinct_shas=5):
    good = [row for row in rows if comparable(row, features)]
    shas = {row["source_sha"] for row in good}
    result = {
        "rows_seen": len(rows),
        "numeric_comparable_rows": len(good),
        "distinct_source_shas": len(shas),
        "required_rows": minimum_rows,
        "required_distinct_source_shas": minimum_distinct_shas,
        "status": "WITHHELD",
        "reason": None,
    }
    if len(good) < minimum_rows:
        result["reason"] = "INSUFFICIENT_COMPARABLE_ROWS"
        return result
    if len(shas) < minimum_distinct_shas:
        result["reason"] = "PSEUDOREPLICATION_DISTINCT_SHA_GATE"
        return result
    if len(good) != len(shas):
        result["reason"] = "ONE_OBSERVATION_PER_SHA_REQUIRED"
        return result

    varying = []
    for feature in features:
        values = [float(row[feature]) for row in good]
        if max(values) != min(values):
            varying.append(feature)
    result["constant_features_excluded"] = [
        feature for feature in features if feature not in varying
    ]
    if len(varying) < 2:
        result["reason"] = "INSUFFICIENT_VARYING_FEATURES"
        return result

    z = standardize(good, varying)
    cov = covariance(z)
    total = sum(cov[i][i] for i in range(len(varying)))
    eigens = jacobi_eigen(cov)
    components = []
    for idx, (eig, vector) in enumerate(eigens, start=1):
        ratio = eig / total if total else 0.0
        loadings = {
            name: round(vector[j] * math.sqrt(max(eig, 0.0)), 6)
            for j, name in enumerate(varying)
        }
        components.append(
            {
                "pc": idx,
                "eigenvalue": round(eig, 6),
                "explained_variance_ratio": round(ratio, 6),
                "loadings": loadings,
                "absolute_loading_rank": [
                    name
                    for name, _ in sorted(
                        loadings.items(), key=lambda kv: abs(kv[1]), reverse=True
                    )
                ],
            }
        )
    result.update(
        {
            "status": "MEASURED_PCA_DIAGNOSTIC",
            "reason": None,
            "components": components,
            "retention": "DIAGNOSTIC_ONLY_NO_PARALLEL_ANALYSIS_YET",
            "bt_status": "WITHHELD_NO_OBSERVED_PAIRWISE_EVIDENCE",
        }
    )
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("rows", nargs="+")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    rows = load_rows(args.rows)
    ids = set()
    semantic, runtime = [], []
    for index, row in enumerate(rows, start=1):
        validate_common(row, index)
        if row["row_id"] in ids:
            fail(f"row {index}: duplicate row_id")
        ids.add(row["row_id"])
        if row["observation_class"] == "runtime":
            validate_runtime(row, index)
            runtime.append(row)
        else:
            validate_semantic(row, index)
            semantic.append(row)

    receipt = {
        "schema_version": "MC2-FEDERATED-TELEMETRY-0.1.0",
        "parent_mission": "GBOGEB/cryoplant-project#1063",
        "worker_issue": "GBOGEB/ABACUS#1164",
        "authority": "derived_operational_analysis",
        "zero_imputation_performed": False,
        "authority_classes_collapsed": False,
        "rows_total": len(rows),
        "class_counts": dict(Counter(row["observation_class"] for row in rows)),
        "runtime_state_counts": dict(
            Counter(row.get("execution_state") for row in runtime)
        ),
        "runtime_pca": pca_block(runtime, RUNTIME_FEATURES),
        "semantic_pca": pca_block(semantic, SEMANTIC_FEATURES),
        "global_allocation_authority": False,
        "child_engineering_promotion_authority": False,
        "allocation_state": "WITHHELD_PARENT_TRANSITION_GATE",
    }
    canonical = json.dumps(
        receipt, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    receipt["receipt_sha256"] = hashlib.sha256(canonical).hexdigest()
    Path(args.out).write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
