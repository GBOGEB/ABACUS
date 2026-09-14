#!/usr/bin/env python3
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "triage/w189/QPS_W189_CROSS_SURFACE_FEATURE_MATRIX_v0.1.json"


def orient(loadings, scores):
    for k in range(loadings.shape[1]):
        pivot = int(np.argmax(np.abs(loadings[:, k])))
        if loadings[pivot, k] < 0:
            loadings[:, k] *= -1
            scores[:, k] *= -1
    return loadings, scores


def decompose(rows, cols):
    X = np.array([[float(r[c]) for c in cols] for r in rows], dtype=float)
    std = X.std(axis=0, ddof=1)
    if np.any(std == 0):
        raise SystemExit("W189 PCA REJECT: zero variance feature")
    Z = (X - X.mean(axis=0)) / std
    U, S, Vt = np.linalg.svd(Z, full_matrices=False)
    scores = U * S
    loadings, scores = orient(Vt.T, scores)
    eig = (S ** 2) / (len(rows) - 1)
    return eig / eig.sum(), loadings, scores


def congruence(a, b):
    return abs(float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))))


def main():
    data = json.loads(MATRIX.read_text(encoding="utf-8"))
    cols = data["pca_feature_columns"]
    rows4 = data["rows"]
    rows3 = [r for r in rows4 if int(r["accepted_sample"]) == 1]
    if len(rows3) != 3 or len(rows4) != 4:
        raise SystemExit("W189 PCA REJECT: expected accepted n3 plus one candidate")
    r3, l3, _ = decompose(rows3, cols)
    r4, l4, s4 = decompose(rows4, cols)
    c1, c2 = congruence(l3[:, 0], l4[:, 0]), congruence(l3[:, 1], l4[:, 1])
    Q3 = np.linalg.qr(l3[:, :2])[0]
    Q4 = np.linalg.qr(l4[:, :2])[0]
    sv = np.linalg.svd(Q3.T @ Q4, compute_uv=False)
    angles = np.degrees(np.arccos(np.clip(sv, -1.0, 1.0)))
    ref = data["candidate_n4_stability"]
    if not np.allclose(r4[:3], np.array(ref["explained_variance_ratio"]), atol=1e-8):
        raise SystemExit(f"W189 PCA REJECT: n4 EVR mismatch {r4[:3]}")
    if not np.isclose(c1, ref["pc1_loading_congruence_abs"], atol=1e-8):
        raise SystemExit(f"W189 PCA REJECT: PC1 congruence mismatch {c1}")
    if not np.isclose(c2, ref["pc2_loading_congruence_abs"], atol=1e-8):
        raise SystemExit(f"W189 PCA REJECT: PC2 congruence mismatch {c2}")
    if not np.allclose(angles, np.array(ref["pc12_subspace_principal_angles_deg"]), atol=1e-6):
        raise SystemExit(f"W189 PCA REJECT: principal-angle mismatch {angles}")
    receipt = {
        "schema": "qps-w189-federation-pca-stability-runtime/v1",
        "state": "CANDIDATE_WITHHELD_PENDING_SAMPLE4_ACCEPTANCE",
        "accepted_reference_n": 3,
        "candidate_n": 4,
        "n_features": len(cols),
        "accepted_n3_explained_variance_ratio": [float(x) for x in r3[:2]],
        "candidate_n4_explained_variance_ratio": [float(x) for x in r4[:3]],
        "pc1_loading_congruence_abs": c1,
        "pc2_loading_congruence_abs": c2,
        "pc12_subspace_principal_angles_deg": [float(x) for x in angles],
        "sample4_scores_candidate": [float(x) for x in s4[3, :3]],
        "disposition": "PC1_STABLE_PC2_ROTATES_MATERIALLY_CANDIDATE_ONLY",
        "guard": "NO_MEASURED_N4_STABILITY_PROMOTION_BEFORE_SAMPLE4_ACCEPTANCE"
    }
    out = ROOT / "triage/w189/QPS_W189_PCA_STABILITY_RUNTIME_RECEIPT.json"
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("W189 PCA PASS: n4 candidate reproduced; PC1 stable, PC2 materially rotating; promotion withheld")


if __name__ == "__main__":
    main()
