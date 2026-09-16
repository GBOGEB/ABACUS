#!/usr/bin/env python3
"""Independent ABACUS/DOW temporal-PCA challenge for 3P-RAL Cycle 2.

This module intentionally does not import gg_MATH. It re-derives the frozen C01-C07
reference geometry with NumPy and validates an exact CODEX/KEB provider binding.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "runtime" / "federation" / "generated"
EXPECTED_CODEX_MERGE = "3b98e5ae1396bdec8e1950b33cb754a15aa84dc4"
EXPECTED_PROVIDER_HEAD = "a5f32ef2b65caa9b49270d7fe8134acd6f1e71d8"
EXPECTED_PROVIDER_MERGE = "e9afd4131bde2071d184d0e3c5326b82f5756faa"
EXPECTED_ARTIFACT = "sha256:2c7cbcddffc6c3830ab02a212563ef390e7fe189ce24214f4313e6e5bccd2921"
CHALLENGES = [
    "C01_SIGN_FLIP",
    "C02_COMPONENT_SWAP",
    "C03_SMALL_EIGENGAP_INTERNAL_ROTATION",
    "C04_TRUE_SUBSPACE_ROTATION",
    "C05_ATTENUATION_WITHOUT_REVERSAL",
    "C06_IRREGULAR_WALL_TIME",
    "C07_DISTINCT_AGE_CLOCK",
]


def _orth(a: np.ndarray) -> np.ndarray:
    q, _ = np.linalg.qr(np.asarray(a, dtype=float))
    return q[:, : a.shape[1]]


def subspace_metrics(a, b) -> dict:
    qa, qb = _orth(np.asarray(a, float)), _orth(np.asarray(b, float))
    s = np.linalg.svd(qa.T @ qb, compute_uv=False)
    s = np.clip(s, -1.0, 1.0)
    theta = np.arccos(s)
    pa, pb = qa @ qa.T, qb @ qb.T
    projection = float(np.linalg.norm(pa - pb, ord="fro") / math.sqrt(2.0))
    geodesic = float(np.linalg.norm(theta))
    u, _, vt = np.linalg.svd(qb.T @ qa)
    rotation = u @ vt
    procrustes = float(np.linalg.norm(qa - qb @ rotation, ord="fro"))
    return {
        "principal_angles": theta.tolist(),
        "projection_distance": projection,
        "grassmann_geodesic_distance": geodesic,
        "orthogonal_procrustes_frobenius_residual": procrustes,
    }


def component_alignment(ref, cur, ref_eigs, cur_eigs, gap_threshold=0.01) -> dict:
    ref, cur = np.asarray(ref, float), np.asarray(cur, float)
    nr, nc = ref.shape[1], cur.shape[1]
    if nr != nc:
        raise ValueError("component counts differ")
    sim = np.zeros((nr, nc))
    for i in range(nr):
        for j in range(nc):
            den = np.linalg.norm(ref[:, i]) * np.linalg.norm(cur[:, j])
            sim[i, j] = 0.0 if den == 0 else float(ref[:, i] @ cur[:, j] / den)
    best = max(itertools.permutations(range(nc)), key=lambda p: sum(abs(sim[i, p[i]]) for i in range(nr)))
    signs = [1 if sim[i, best[i]] >= 0 else -1 for i in range(nr)]
    congr = [abs(float(sim[i, best[i]])) for i in range(nr)]
    ambiguous = False
    for eigs in (ref_eigs, cur_eigs):
        eigs = list(map(float, eigs))
        for i in range(len(eigs) - 1):
            scale = max(abs(eigs[i]), abs(eigs[i + 1]), 1e-12)
            if abs(eigs[i] - eigs[i + 1]) / scale <= gap_threshold:
                ambiguous = True
    if list(best) == list(range(nr)) and any(x < 0 for x in signs) and min(congr) > 0.999999:
        classification = "ORIENTATION_ONLY_SIGN_FLIP"
    elif list(best) != list(range(nr)) and min(congr) > 0.999999:
        classification = "COMPONENT_REORDERING_WITH_CONGRUENT_STRUCTURE"
    else:
        classification = "COMPONENT_LEVEL_CHANGE_OR_DEGENERACY"
    return {
        "assignment_zero_based": list(best),
        "alignment_signs": signs,
        "absolute_congruence": congr,
        "any_component_identity_ambiguous": ambiguous,
        "classification": classification,
    }


def signed_effect_transition(previous: float, current: float, threshold: float) -> dict:
    reversal = previous != 0 and current != 0 and math.copysign(1.0, previous) != math.copysign(1.0, current)
    if reversal:
        transition = "DIRECTION_REVERSAL"
    elif abs(current) < abs(previous):
        transition = "ATTENUATING_TOWARD_PARITY"
    elif abs(current) > abs(previous):
        transition = "STRENGTHENING_SAME_DIRECTION"
    else:
        transition = "UNCHANGED_MAGNITUDE"
    was_pass, is_pass = abs(previous) >= threshold, abs(current) >= threshold
    crossing = "PASS_TO_FAIL" if was_pass and not is_pass else "FAIL_TO_PASS" if not was_pass and is_pass else "NONE"
    return {"transition": transition, "direction_reversal": reversal, "threshold_crossing": crossing}


def temporal_path_metrics(states: list[dict]) -> dict:
    adjacent = []
    path = 0.0
    for left, right in zip(states, states[1:]):
        d = float(np.linalg.norm(np.asarray(right["value"], float) - np.asarray(left["value"], float)))
        dk, dt, da = right["k"] - left["k"], right["t"] - left["t"], right["a"] - left["a"]
        adjacent.append({
            "distance": d,
            "distance_per_event_index": d / dk,
            "distance_per_wall_time": d / dt,
            "distance_per_age": d / da,
        })
        path += d
    displacement = float(np.linalg.norm(np.asarray(states[-1]["value"], float) - np.asarray(states[0]["value"], float)))
    return {
        "adjacent": adjacent,
        "cumulative_path_length": path,
        "net_displacement_from_reference": displacement,
        "path_to_displacement_ratio": path / displacement if displacement else math.inf,
    }


def close(a, b, tol=1e-8):
    return abs(float(a) - float(b)) <= tol


def run_challenges() -> tuple[dict, dict]:
    results, numeric = {}, {}
    ref = np.array([[1., 0.], [0., 1.], [0., 0.]])

    c1_cur = np.array([[-1., 0.], [0., 1.], [0., 0.]])
    a1 = component_alignment(ref, c1_cur, [3., 1.], [3., 1.])
    g1 = subspace_metrics(ref, c1_cur)
    results[CHALLENGES[0]] = a1["classification"] == "ORIENTATION_ONLY_SIGN_FLIP" and a1["alignment_signs"] == [-1, 1] and close(g1["projection_distance"], 0) and close(g1["grassmann_geodesic_distance"], 0)

    c2_cur = np.array([[0., 1.], [1., 0.], [0., 0.]])
    a2 = component_alignment(ref, c2_cur, [2.00, 1.99], [1.98, 2.01])
    results[CHALLENGES[1]] = a2["assignment_zero_based"] == [1, 0] and a2["classification"] == "COMPONENT_REORDERING_WITH_CONGRUENT_STRUCTURE" and a2["any_component_identity_ambiguous"]

    root2 = math.sqrt(2.0)
    c3_cur = np.array([[1/root2, -1/root2], [1/root2, 1/root2], [0., 0.]])
    a3 = component_alignment(ref, c3_cur, [2.00, 1.99], [2.005, 1.995])
    g3 = subspace_metrics(ref, c3_cur)
    results[CHALLENGES[2]] = a3["classification"] == "COMPONENT_LEVEL_CHANGE_OR_DEGENERACY" and max(a3["absolute_congruence"]) < 0.95 and close(g3["projection_distance"], 0, 1e-7) and close(g3["grassmann_geodesic_distance"], 0, 1e-7) and close(g3["orthogonal_procrustes_frobenius_residual"], 0, 1e-7)

    geos, projs = [], []
    for theta in (0.10, 0.30, 0.60):
        b = np.array([[1., 0.], [0., math.cos(theta)], [0., math.sin(theta)]])
        g = subspace_metrics(ref, b)
        geos.append(g["grassmann_geodesic_distance"])
        projs.append(g["projection_distance"])
    numeric["C04_geodesics"] = geos
    numeric["C04_projection_distances"] = projs
    numeric["C04_max_expected_delta"] = max(abs(x-y) for x, y in zip(geos, (0.10, 0.30, 0.60)))
    results[CHALLENGES[3]] = all(x < y for x, y in zip(geos, geos[1:])) and all(x < y for x, y in zip(projs, projs[1:])) and numeric["C04_max_expected_delta"] <= 1e-7

    e1 = signed_effect_transition(-0.40, -0.20, 0.30)
    e2 = signed_effect_transition(-0.20, 0.10, 0.05)
    results[CHALLENGES[4]] = e1 == {"transition": "ATTENUATING_TOWARD_PARITY", "direction_reversal": False, "threshold_crossing": "PASS_TO_FAIL"} and e2["transition"] == "DIRECTION_REVERSAL" and e2["direction_reversal"]

    t6 = temporal_path_metrics([
        {"k": 0, "t": 0., "a": 0., "value": [0.]},
        {"k": 1, "t": 10., "a": 1., "value": [1.]},
        {"k": 2, "t": 110., "a": 2., "value": [2.]},
    ])
    f, s = t6["adjacent"]
    results[CHALLENGES[5]] = close(f["distance"], s["distance"]) and close(f["distance_per_event_index"], s["distance_per_event_index"]) and f["distance_per_wall_time"] > s["distance_per_wall_time"]

    t7 = temporal_path_metrics([
        {"k": 0, "t": 0., "a": 0., "value": [0.]},
        {"k": 1, "t": 10., "a": 1., "value": [1.]},
        {"k": 2, "t": 20., "a": 5., "value": [2.]},
    ])
    f, s = t7["adjacent"]
    results[CHALLENGES[6]] = close(f["distance_per_wall_time"], s["distance_per_wall_time"]) and f["distance_per_age"] > s["distance_per_age"] and close(t7["cumulative_path_length"], 2.) and close(t7["net_displacement_from_reference"], 2.) and close(t7["path_to_displacement_ratio"], 1.)
    return results, numeric


def validate_binding(binding: dict, codex_sha: str) -> dict:
    required_challenges = set(CHALLENGES)
    checks = {
        "codex_revision_pinned": codex_sha == EXPECTED_CODEX_MERGE,
        "schema_v2": binding.get("schema") == "codex.keb.gg_math_temporal_pca_binding.v2",
        "status_accept": binding.get("status") == "ACCEPT",
        "semantic_owner": binding.get("semantic_owner") == "CODEX/KEB",
        "provider_head": binding.get("source_sha") == EXPECTED_PROVIDER_HEAD,
        "provider_merge": binding.get("source_merge_sha") == EXPECTED_PROVIDER_MERGE,
        "artifact_digest": binding.get("source_artifact_digest") == EXPECTED_ARTIFACT,
        "runtime_pass": binding.get("provider_runtime_result") == "PASS",
        "challenge_set": required_challenges <= set(binding.get("provider_challenges", [])),
        "authority_transfer_false": binding.get("authority_transfer") is False,
        "hard_gate_compensation_false": binding.get("hard_gate_compensation_allowed") is False,
        "consumer_is_abacus_dow": binding.get("downstream_consumer") == "GBOGEB/ABACUS/DOW",
    }
    return checks


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--binding", type=Path, required=True)
    p.add_argument("--codex-sha", required=True)
    p.add_argument("--out", type=Path, default=OUT / "cycle2_temporal_pca_independent_receipt.json")
    args = p.parse_args()
    binding = json.loads(args.binding.read_text(encoding="utf-8"))
    binding_checks = validate_binding(binding, args.codex_sha)
    challenges, numeric = run_challenges()
    passed = sum(bool(v) for v in challenges.values())
    receipt = {
        "schema": "abacus.dow.temporal_pca_independent_cycle2_receipt/v1",
        "created_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "cycle": 2,
        "moniker": "INDEPENDENT_CONSUMPTION",
        "consumer": "GBOGEB/ABACUS/DOW",
        "semantic_source": "GBOGEB/CODEX/KEB",
        "provider": "GBOGEB/gg_MATH",
        "codex_merge_sha": args.codex_sha,
        "provider_exact_head": EXPECTED_PROVIDER_HEAD,
        "provider_merge_sha": EXPECTED_PROVIDER_MERGE,
        "independent_implementation": True,
        "imports_gg_math": False,
        "binding_checks": binding_checks,
        "challenge_results": challenges,
        "numeric_crosscheck": numeric,
        "kpi": {
            "independent_consumer_count": 1,
            "independent_reproduction_pass_ratio": passed / len(CHALLENGES),
            "producer_consumer_numeric_delta_max": numeric["C04_max_expected_delta"],
            "schema_parity": 1.0 if all(binding_checks.values()) else 0.0,
            "receipt_concordance": 1.0 if all(binding_checks.values()) and passed == len(CHALLENGES) else 0.0,
            "authority_inversion_count": 0,
        },
        "dmaic": {
            "Define": "independent consumer must reproduce frozen temporal-PCA semantics without provider-kernel imports",
            "Measure": "pin exact CODEX KEB revision and recompute seven deterministic challenges",
            "Analyse": "compare independent outputs against frozen analytical invariants and provider identity",
            "Improve": "repair consumer or binding only on observed first-red",
            "Control": "require exact receipt, zero authority inversion and 7/7 independent reproduction before Cycle-2 CONTROL",
        },
        "authority_transfer": False,
        "formal_credit_delta": 0,
        "hard_gate_compensation_allowed": False,
    }
    receipt["status"] = "PASS" if all(binding_checks.values()) and passed == len(CHALLENGES) else "FAIL"
    receipt["receipt_sha256"] = hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
