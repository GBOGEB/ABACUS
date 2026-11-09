#!/usr/bin/env python3
"""Verify numerical parity between the gg_MATH canonical kernels and the QPS
slide-reviewer consumer, and (re)generate mission/QPS/parity/qps_parity_vector.json.

Run from anywhere:  python3 mission/QPS/parity/verify_qps_parity.py
Exit 0 and prints "PARITY OK ..." on success; non-zero on any parity breach.

Synthetic data only. Non-authoritative: no engineering/compliance/release authority
is implied, consistent with mission/QPS/QPS_TRIAGE_PCA_MATH_APPLICATION.md.
"""
from __future__ import annotations
import os
import sys

# make the repo root importable regardless of CWD (kernels/ lives at repo root)
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
for _p in (_ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import json
import math
import random

from kernels.pca_reference import pca_reference, parallel_analysis
from kernels.bradley_terry import rank_pairs
from slide_reviewer_port import sr_pca, sr_bradley_terry

SEED = 20260925
rng = random.Random(SEED)

# ---- synthetic slide x feature matrix (8 slides, 4 feature blocks) ----
FEATURES = ["evidence", "reliability", "delivery", "visual"]
N_SLIDES = 8
# latent quality drives correlated features + noise -> non-trivial PCA
matrix = []
ids = list(range(1, N_SLIDES + 1))
for _ in ids:
    q = rng.gauss(0, 1)
    row = [
        q + rng.gauss(0, 0.4),            # evidence ~ quality
        0.8 * q + rng.gauss(0, 0.5),      # reliability ~ quality
        rng.gauss(0, 1),                  # delivery ~ independent
        0.5 * q + rng.gauss(0, 0.7),      # visual ~ weak quality
    ]
    matrix.append(row)

# ---- canonical PCA (scale=True == standardize, matches slide-reviewer) ----
canon = pca_reference(matrix, scale=True, components=3)
pa = parallel_analysis(matrix, simulations=200, percentile=0.95, seed=SEED, scale=True)
sr = sr_pca(ids, FEATURES, matrix, n_components=3)

# compare eigenvalues (canonical reports all p; slide-reviewer top-3)
canon_eig = canon["eigenvalues"][:3]
sr_eig = sr["eigenvalues"]
eig_absdiff = [abs(a - b) for a, b in zip(canon_eig, sr_eig)]
canon_evr = canon["explained_variance_ratio"][:3]
sr_evr = sr["explained_variance"]
evr_absdiff = [abs(a - b) for a, b in zip(canon_evr, sr_evr)]

# ---- synthetic pairwise comparisons from the latent quality ----
def build_comps(repeats, upset_rate):
    out = []
    for _r in range(repeats):
        for i in range(N_SLIDES):
            for j in range(i + 1, N_SLIDES):
                si = matrix[i][0] + matrix[i][1]
                sj = matrix[j][0] + matrix[j][1]
                upset = rng.random() < upset_rate
                a_wins = (si > sj) != upset
                out.append({
                    "slideAId": ids[i], "slideBId": ids[j],
                    "winnerId": ids[i] if a_wins else ids[j], "isTie": False,
                })
    return out

def canon_pairs_of(cmps):
    return [(c["winnerId"], c["slideBId"] if c["winnerId"] == c["slideAId"] else c["slideAId"]) for c in cmps]

# Case A: single round-robin, 15% upsets -> may not be strongly connected (fail-closed)
comps_sparse = build_comps(1, 0.15)
canon_bt_sparse = rank_pairs(canon_pairs_of(comps_sparse))
sr_bt_sparse = sr_bradley_terry(ids, comps_sparse)

# Case B: 4x round-robin, 25% upsets -> strongly connected, canonical PASSES
comps = build_comps(4, 0.25)
canon_bt = rank_pairs(canon_pairs_of(comps))
sr_bt = sr_bradley_terry(ids, comps)

canon_order = list(canon_bt["scores"].keys()) if canon_bt["status"] == "PASS_TESTABLE_ENGINE" else []
sr_order = [k for k, _ in sorted(sr_bt.items(), key=lambda kv: kv[1], reverse=True)]

out = {
    "schema": "gg-math-qps-parity/v1",
    "seed": SEED,
    "note": "Synthetic reference vector. Non-authoritative; verifies numerical parity "
            "between gg_MATH canonical kernels and the QPS slide-reviewer consumer.",
    "features": FEATURES,
    "slide_ids": ids,
    "matrix": matrix,
    "pca": {
        "canonical_eigenvalues_top3": canon_eig,
        "slide_reviewer_eigenvalues_top3": sr_eig,
        "eigenvalue_abs_diff": eig_absdiff,
        "canonical_explained_variance_top3": canon_evr,
        "slide_reviewer_explained_variance_top3": sr_evr,
        "explained_variance_abs_diff": evr_absdiff,
        "parallel_analysis_PA95_retained_candidate": pa["retained_candidate"],
        "parallel_analysis_null_thresholds": pa["null_eigenvalue_thresholds"],
    },
    "bradley_terry_fail_closed_case": {
        "comparisons": len(comps_sparse),
        "canonical_status": canon_bt_sparse["status"],
        "note": "Canonical fails closed when the directed win-graph is not strongly "
                "connected (Ford condition); the slide-reviewer's prior=0.1 masks this.",
        "slide_reviewer_still_returns_ranking": [
            k for k, _ in sorted(sr_bt_sparse.items(), key=lambda kv: kv[1], reverse=True)
        ],
    },
    "bradley_terry_convergent_case": {
        "comparisons": len(comps),
        "canonical_status": canon_bt["status"],
        "canonical_order": canon_order,
        "canonical_scores": canon_bt.get("scores", {}),
        "slide_reviewer_order": sr_order,
        "slide_reviewer_scores": sr_bt,
        "order_matches": canon_order == sr_order,
    },
}

print(json.dumps(out, indent=2))

# ---- assertions: parity must hold ----
max_eig = max(eig_absdiff)
max_evr = max(evr_absdiff)
assert max_eig < 1e-6, f"PCA eigenvalue parity failed: {eig_absdiff}"
assert max_evr < 1e-6, f"PCA explained-variance parity failed: {evr_absdiff}"
assert canon_bt["status"] == "PASS_TESTABLE_ENGINE", f"convergent BT should pass: {canon_bt['status']}"
assert canon_order == sr_order, f"BT order mismatch: {canon_order} vs {sr_order}"
import sys
print(f"\nPARITY OK  max|dEig|={max_eig:.2e}  max|dEVR|={max_evr:.2e}  "
      f"fail_closed={canon_bt_sparse['status']}  convergent_BT_order_match={canon_order==sr_order}", file=sys.stderr)
