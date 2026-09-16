#!/usr/bin/env python3
"""Independent ABACUS/DOW challenge of the Grandmission I-B temporal-PCA KEB binding.

This module intentionally does not import gg_MATH kernels.  It independently
recomputes the frozen C01-C07 reference geometry, effect semantics and
multi-clock metrics, then emits a fail-closed DOW receipt bound to the exact
CODEX KEB revision.
"""
from __future__ import annotations

import hashlib
import importlib.util
import itertools
import json
import math
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "runtime" / "federation" / "input" / "codex_gg_math_temporal_pca_3b98e5ae.json"
OUT = ROOT / "runtime" / "federation" / "generated"
GOVERNANCE_CONSUMER = ROOT / "runtime" / "federation" / "gg_math_temporal_pca_dow_consumer.py"

CODEX_REPO = "GBOGEB/CODEX"
CODEX_COMMIT = "3b98e5ae1396bdec8e1950b33cb754a15aa84dc4"
CODEX_BINDING_PATH = "ssot/bridge_rows/gg_math_temporal_pca_w4_p31.json"
CODEX_BINDING_BLOB = "bd3a555514e7f1f7c59723313b9d5c7f98a932d2"

PROVIDER_HEAD = "a5f32ef2b65caa9b49270d7fe8134acd6f1e71d8"
PROVIDER_MERGE = "e9afd4131bde2071d184d0e3c5326b82f5756faa"
CORE_HEAD = "a99d7cacd03ed3a392c063a1b3f8dbffdba0d060"
CORE_MERGE = "513e4f7e06d1316512c820715b6eb41f3f9a066f"
I_B_ARTIFACT_DIGEST = "sha256:2c7cbcddffc6c3830ab02a212563ef390e7fe189ce24214f4313e6e5bccd2921"
CORE_ARTIFACT_DIGEST = "sha256:876c55c759de33392985f693f1735cdc0d38dda7d7b7a6c80ee80aee33fd8405"
CLOCK_FIELDS = ["k", "t", "a", "wave", "pulse", "pr", "run", "release"]

CHALLENGES = [
    "C01_SIGN_FLIP",
    "C02_COMPONENT_SWAP",
    "C03_SMALL_EIGENGAP_INTERNAL_ROTATION",
    "C04_TRUE_SUBSPACE_ROTATION",
    "C05_ATTENUATION_WITHOUT_REVERSAL",
    "C06_IRREGULAR_WALL_TIME",
    "C07_DISTINCT_AGE_CLOCK",
]


def _close(a: float, b: float, tol: float = 1e-8) -> bool:
    return abs(float(a) - float(b)) <= tol


def _orthonormal_columns(values: Iterable[Iterable[float]]) -> np.ndarray:
    matrix = np.asarray(list(values), dtype=float)
    if matrix.ndim != 2 or matrix.size == 0:
        raise ValueError("basis must be a non-empty matrix")
    q, _ = np.linalg.qr(matrix)
    return q[:, : matrix.shape[1]]


def signed_congruence(reference: Iterable[Iterable[float]], current: Iterable[Iterable[float]]) -> np.ndarray:
    ref = np.asarray(list(reference), dtype=float)
    cur = np.asarray(list(current), dtype=float)
    if ref.shape != cur.shape:
        raise ValueError("loading shapes must match")
    ref_norm = np.linalg.norm(ref, axis=0)
    cur_norm = np.linalg.norm(cur, axis=0)
    if np.any(ref_norm == 0.0) or np.any(cur_norm == 0.0):
        raise ValueError("zero-norm retained component")
    return (ref.T @ cur) / np.outer(ref_norm, cur_norm)


def max_abs_assignment(congruence: np.ndarray) -> tuple[list[int], list[int], float]:
    k = int(congruence.shape[0])
    if congruence.shape != (k, k):
        raise ValueError("assignment requires a square congruence matrix")
    best: tuple[float, tuple[int, ...]] | None = None
    for perm in itertools.permutations(range(k)):
        score = sum(abs(float(congruence[i, j])) for i, j in enumerate(perm))
        candidate = (score, tuple(perm))
        if best is None or score > best[0] + 1e-15 or (_close(score, best[0], 1e-15) and perm < best[1]):
            best = candidate
    assert best is not None
    assignment = list(best[1])
    signs = [-1 if float(congruence[i, j]) < 0.0 else 1 for i, j in enumerate(assignment)]
    return assignment, signs, best[0]


def local_relative_eigengap(values: list[float], index: int) -> float:
    if len(values) == 1:
        return math.inf
    gaps: list[float] = []
    if index > 0:
        gaps.append(abs(values[index - 1] - values[index]))
    if index + 1 < len(values):
        gaps.append(abs(values[index] - values[index + 1]))
    return min(gaps) / max(abs(values[index]), 1e-15)


def subspace_metrics(reference: Iterable[Iterable[float]], current: Iterable[Iterable[float]]) -> dict[str, Any]:
    qa = _orthonormal_columns(reference)
    qb = _orthonormal_columns(current)
    singular = np.linalg.svd(qa.T @ qb, compute_uv=False)
    singular = np.clip(singular, -1.0, 1.0)
    angles = np.arccos(singular)
    pa = qa @ qa.T
    pb = qb @ qb.T
    projection = float(np.linalg.norm(pa - pb, ord="fro") / math.sqrt(2.0))
    grassmann = float(np.linalg.norm(angles))
    u, _, vt = np.linalg.svd(qb.T @ qa)
    rotation = u @ vt
    procrustes = float(np.linalg.norm(qa - qb @ rotation, ord="fro"))
    return {
        "principal_angles": [float(x) for x in angles],
        "canonical_correlations": [float(x) for x in singular],
        "projection_distance": 0.0 if abs(projection) < 1e-12 else projection,
        "grassmann_geodesic_distance": 0.0 if abs(grassmann) < 1e-12 else grassmann,
        "orthogonal_procrustes_frobenius_residual": 0.0 if abs(procrustes) < 1e-12 else procrustes,
    }


def signed_effect_transition(previous: float, current: float, threshold_magnitude: float) -> dict[str, Any]:
    prev, cur, threshold = float(previous), float(current), float(threshold_magnitude)
    reversal = prev != 0.0 and cur != 0.0 and math.copysign(1.0, prev) != math.copysign(1.0, cur)
    if reversal:
        transition = "DIRECTION_REVERSAL"
    elif abs(cur) < abs(prev):
        transition = "ATTENUATING_TOWARD_PARITY"
    elif abs(cur) > abs(prev):
        transition = "STRENGTHENING_AWAY_FROM_PARITY"
    else:
        transition = "UNCHANGED_MAGNITUDE"
    prev_pass = abs(prev) >= threshold
    cur_pass = abs(cur) >= threshold
    crossing = "PASS_TO_FAIL" if prev_pass and not cur_pass else "FAIL_TO_PASS" if not prev_pass and cur_pass else "NONE"
    return {"transition": transition, "direction_reversal": reversal, "threshold_crossing": crossing}


def temporal_path_metrics(states: list[dict[str, Any]]) -> dict[str, Any]:
    adjacent: list[dict[str, float]] = []
    path = 0.0
    for left, right in zip(states, states[1:]):
        a = np.asarray(left["value"], dtype=float)
        b = np.asarray(right["value"], dtype=float)
        distance = float(np.linalg.norm(b - a))
        dk = float(right["k"] - left["k"])
        dt = float(right["t"] - left["t"])
        da = float(right["a"] - left["a"])
        if dk <= 0.0 or dt <= 0.0 or da <= 0.0:
            raise ValueError("k, t and a must strictly increase")
        adjacent.append({
            "distance": distance,
            "distance_per_event_index": distance / dk,
            "distance_per_wall_time": distance / dt,
            "distance_per_age": distance / da,
        })
        path += distance
    first = np.asarray(states[0]["value"], dtype=float)
    last = np.asarray(states[-1]["value"], dtype=float)
    displacement = float(np.linalg.norm(last - first))
    return {
        "adjacent": adjacent,
        "cumulative_path_length": path,
        "net_displacement_from_reference": displacement,
        "path_to_displacement_ratio": path / displacement if displacement else math.inf,
        "event_wall_age_clocks_separate": True,
    }


def _rotated_plane(theta: float) -> list[list[float]]:
    return [[1.0, 0.0], [0.0, math.cos(theta)], [0.0, math.sin(theta)]]


def run_independent_challenges() -> dict[str, Any]:
    results: dict[str, Any] = {}

    # C01 — sign is orientation only after assignment/alignment.
    ref = [[1.0, 0.0], [0.0, 1.0], [0.0, 0.0]]
    cur = [[-1.0, 0.0], [0.0, 1.0], [0.0, 0.0]]
    c = signed_congruence(ref, cur)
    assignment, signs, _ = max_abs_assignment(c)
    geometry = subspace_metrics(ref, cur)
    c01 = assignment == [0, 1] and signs == [-1, 1] and _close(geometry["projection_distance"], 0.0) and _close(geometry["grassmann_geodesic_distance"], 0.0)
    results[CHALLENGES[0]] = {"pass": c01, "assignment": assignment, "alignment_signs": signs, **geometry}

    # C02 — swapped near-degenerate components must be assigned before interpretation.
    ref = [[1.0, 0.0], [0.0, 1.0], [0.0, 0.0]]
    cur = [[0.0, 1.0], [1.0, 0.0], [0.0, 0.0]]
    c = signed_congruence(ref, cur)
    assignment, signs, _ = max_abs_assignment(c)
    ref_ev = [2.00, 1.99]
    cur_ev = [1.98, 2.01]
    min_gap = min(
        min(local_relative_eigengap(ref_ev, i), local_relative_eigengap(cur_ev, assignment[i]))
        for i in range(2)
    )
    c02 = assignment == [1, 0] and min_gap < 0.05
    results[CHALLENGES[1]] = {"pass": c02, "assignment": assignment, "alignment_signs": signs, "minimum_relative_local_eigengap": min_gap, "component_identity_ambiguous": min_gap < 0.05}

    # C03 — internal rotation may lower component congruence without moving the retained subspace.
    root2 = math.sqrt(2.0)
    cur = [[1.0 / root2, -1.0 / root2], [1.0 / root2, 1.0 / root2], [0.0, 0.0]]
    c = signed_congruence(ref, cur)
    assignment, _, _ = max_abs_assignment(c)
    matched = [abs(float(c[i, j])) for i, j in enumerate(assignment)]
    geometry = subspace_metrics(ref, cur)
    c03 = max(matched) < 0.95 and _close(geometry["projection_distance"], 0.0) and _close(geometry["grassmann_geodesic_distance"], 0.0) and _close(geometry["orthogonal_procrustes_frobenius_residual"], 0.0)
    results[CHALLENGES[2]] = {"pass": c03, "matched_absolute_congruence": matched, **geometry}

    # C04 — true retained-subspace rotation grows monotonically and geodesic equals theta.
    thetas = [0.10, 0.30, 0.60]
    geoms = [subspace_metrics(ref, _rotated_plane(theta)) for theta in thetas]
    projections = [g["projection_distance"] for g in geoms]
    geodesics = [g["grassmann_geodesic_distance"] for g in geoms]
    c04 = projections[0] < projections[1] < projections[2] and geodesics[0] < geodesics[1] < geodesics[2] and all(_close(g, t, 1e-7) for g, t in zip(geodesics, thetas))
    results[CHALLENGES[3]] = {"pass": c04, "theta": thetas, "projection_distance": projections, "grassmann_geodesic_distance": geodesics}

    # C05 — attenuation toward parity is not polarity reversal.
    attenuation = signed_effect_transition(-0.40, -0.20, 0.30)
    reversal = signed_effect_transition(-0.20, 0.10, 0.05)
    c05 = attenuation == {"transition": "ATTENUATING_TOWARD_PARITY", "direction_reversal": False, "threshold_crossing": "PASS_TO_FAIL"} and reversal["transition"] == "DIRECTION_REVERSAL" and reversal["direction_reversal"] is True
    results[CHALLENGES[4]] = {"pass": c05, "attenuation": attenuation, "reversal_control": reversal}

    # C06 — equal event motion can have unequal wall-time rate.
    temporal = temporal_path_metrics([
        {"k": 0, "t": 0.0, "a": 0.0, "value": [0.0]},
        {"k": 1, "t": 10.0, "a": 1.0, "value": [1.0]},
        {"k": 2, "t": 110.0, "a": 2.0, "value": [2.0]},
    ])
    first, second = temporal["adjacent"]
    c06 = _close(first["distance"], second["distance"]) and _close(first["distance_per_event_index"], second["distance_per_event_index"]) and first["distance_per_wall_time"] > second["distance_per_wall_time"] and temporal["event_wall_age_clocks_separate"] is True
    results[CHALLENGES[5]] = {"pass": c06, **temporal}

    # C07 — age/exposure clock is independent of wall time.
    temporal = temporal_path_metrics([
        {"k": 0, "t": 0.0, "a": 0.0, "value": [0.0]},
        {"k": 1, "t": 10.0, "a": 1.0, "value": [1.0]},
        {"k": 2, "t": 20.0, "a": 5.0, "value": [2.0]},
    ])
    first, second = temporal["adjacent"]
    c07 = _close(first["distance_per_wall_time"], second["distance_per_wall_time"]) and first["distance_per_age"] > second["distance_per_age"] and _close(temporal["cumulative_path_length"], 2.0) and _close(temporal["net_displacement_from_reference"], 2.0) and _close(temporal["path_to_displacement_ratio"], 1.0)
    results[CHALLENGES[6]] = {"pass": c07, **temporal}

    return results


def load_governance_consumer():
    spec = importlib.util.spec_from_file_location("gg_math_temporal_pca_dow_consumer", GOVERNANCE_CONSUMER)
    if not spec or not spec.loader:
        raise RuntimeError("cannot load ABACUS DOW governance consumer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_binding(binding: dict[str, Any]) -> dict[str, bool]:
    expected = {
        "schema": binding.get("schema") == "codex.keb.gg_math_temporal_pca_binding.v2",
        "semantic_owner": binding.get("semantic_owner") == "CODEX/KEB",
        "status": binding.get("status") == "ACCEPT",
        "object_type": binding.get("object_type") == "KEB_SOURCE_RECEIPT",
        "provider_head": binding.get("source_sha") == PROVIDER_HEAD,
        "provider_merge": binding.get("source_merge_sha") == PROVIDER_MERGE,
        "core_head": binding.get("source_core_exact_head") == CORE_HEAD,
        "core_merge": binding.get("source_core_merge_sha") == CORE_MERGE,
        "artifact_digest": binding.get("source_artifact_digest") == I_B_ARTIFACT_DIGEST,
        "runtime_pass": binding.get("provider_runtime_result") == "PASS",
        "challenges_complete": set(binding.get("provider_challenges", [])) == set(CHALLENGES),
        "clock_fields": binding.get("multi_clock_fields") == CLOCK_FIELDS,
        "authority_transfer_false": binding.get("authority_transfer") is False,
        "hard_gate_compensation_false": binding.get("hard_gate_compensation_allowed") is False,
        "formal_credit_zero": binding.get("cycle2_3p_ral", {}).get("formal_credit_delta") == 0,
        "downstream_consumer": binding.get("downstream_consumer") == "GBOGEB/ABACUS/DOW",
    }
    return expected


def build_receipt() -> dict[str, Any]:
    binding_bytes = INPUT.read_bytes()
    binding = json.loads(binding_bytes)
    binding_checks = validate_binding(binding)

    governance = load_governance_consumer().consume(binding)
    challenges = run_independent_challenges()
    challenge_pass = all(item["pass"] for item in challenges.values())
    governance_pass = governance.get("status") == "ACCEPT" and governance.get("emit_for_qps_bounded_consumption") is True
    all_pass = all(binding_checks.values()) and challenge_pass and governance_pass

    receipt: dict[str, Any] = {
        "schema": "abacus.dow.gg_math_temporal_pca_independent_challenge.v2",
        "receipt_id": "DOW-GG-MATH-TEMPORAL-PCA-I-B-CYCLE2-001",
        "created_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "status": "ACCEPT" if all_pass else "DEFER",
        "cycle": 2,
        "moniker": "INDEPENDENT_CONSUMPTION",
        "consumer": "GBOGEB/ABACUS/DOW",
        "consumer_exact_head": os.getenv("SOURCE_SHA", "LOCAL_UNBOUND"),
        "source": {
            "repo": CODEX_REPO,
            "commit": CODEX_COMMIT,
            "path": CODEX_BINDING_PATH,
            "git_blob_sha1": CODEX_BINDING_BLOB,
            "snapshot_sha256": hashlib.sha256(binding_bytes).hexdigest(),
        },
        "provider": {
            "grandmission": "GRANDMISSION-I-B-TEMPORAL-PCA-FEDERATION",
            "exact_head": PROVIDER_HEAD,
            "merge_sha": PROVIDER_MERGE,
            "artifact_digest": I_B_ARTIFACT_DIGEST,
            "core_exact_head": CORE_HEAD,
            "core_merge_sha": CORE_MERGE,
            "core_artifact_digest_expected_next_keb_atom": CORE_ARTIFACT_DIGEST,
        },
        "binding_checks": binding_checks,
        "governance_consumer": governance,
        "independent_math": {
            "imports_gg_math_kernels": False,
            "challenge_pass_ratio": sum(1 for x in challenges.values() if x["pass"]) / len(challenges),
            "challenges": challenges,
        },
        "kpis": {
            "independent_consumer_count": 1,
            "independent_reproduction_pass_ratio": 1.0 if challenge_pass else 0.0,
            "schema_parity": 1.0 if all(binding_checks.values()) else 0.0,
            "receipt_concordance": 1.0 if governance_pass else 0.0,
            "authority_inversion_count": 0 if binding.get("authority_transfer") is False and governance["authority_guards"]["qps_engineering_authority_transfer"] is False else 1,
            "formal_credit_delta": 0,
        },
        "interpretation": {
            "pca_loading_sign_is_physical_reversal": False,
            "attenuation_toward_parity_is_direction_reversal": False,
            "component_identity_requires_assignment": True,
            "event_wall_age_clocks_are_distinct": True,
        },
        "next_action": "PROMOTE_CODEX_KEB_SOURCE_RECEIPT_TO_KNOWLEDGE_ATOM_BINDING_CORE_876C55C_AND_I_B_2C7C_DIGESTS" if all_pass else "DEFER_AND_REPAIR_FIRST_RED",
        "authority_transfer": False,
        "formal_credit_delta": 0,
        "hard_gate_compensation_allowed": False,
    }
    receipt["receipt_sha256"] = hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest()
    return receipt


def main() -> int:
    receipt = build_receipt()
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "gg_math_temporal_pca_independent_dow_receipt.json"
    target.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    if receipt["status"] != "ACCEPT":
        return 1
    print("PASS_GG_MATH_TEMPORAL_PCA_INDEPENDENT_DOW_CYCLE2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
