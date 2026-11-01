"""Behaviour tests for scripts/qps_w189_compute_pca_stability.py.

The module reads a feature matrix under ROOT and writes a receipt under ROOT,
so ROOT/MATRIX are redirected to tmp_path. Reference stability values are
computed independently with numpy.linalg.eigh on the correlation matrix.
"""

import json

import numpy as np
import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("scripts/qps_w189_compute_pca_stability.py", name="abn_w5_pca_stability")

COLS = ["a", "b", "c", "d"]
# Four features so the two 2-D PC subspaces do not have to share a line (in 3-D
# they always would, making the first principal angle ill-conditioned near 0).
VALUES = [
    [1.0, 2.0, 7.0, 3.0],
    [2.0, 5.0, 3.0, 8.0],
    [4.0, 4.0, 1.0, 2.0],
    [9.0, 1.0, 6.0, 5.0],
]


def _rows():
    rows = []
    for idx, vals in enumerate(VALUES):
        row = dict(zip(COLS, vals))
        row["sample_id"] = "S" + str(idx)
        row["accepted_sample"] = 1 if idx < 3 else 0
        rows.append(row)
    return rows


def _eig_desc(x):
    corr = np.corrcoef(np.asarray(x, dtype=float), rowvar=False)
    vals, vecs = np.linalg.eigh(corr)
    order = np.argsort(vals)[::-1]
    return vals[order], vecs[:, order]


def _reference():
    vals4, vecs4 = _eig_desc(VALUES)
    _, vecs3 = _eig_desc(VALUES[:3])
    evr4 = vals4 / vals4.sum()
    c1 = abs(float(vecs3[:, 0] @ vecs4[:, 0]))
    c2 = abs(float(vecs3[:, 1] @ vecs4[:, 1]))
    sv = np.linalg.svd(vecs3[:, :2].T @ vecs4[:, :2], compute_uv=False)
    angles = np.degrees(np.arccos(np.clip(sv, -1.0, 1.0)))
    return {
        "explained_variance_ratio": [float(v) for v in evr4[:3]],
        "pc1_loading_congruence_abs": c1,
        "pc2_loading_congruence_abs": c2,
        "pc12_subspace_principal_angles_deg": [float(v) for v in angles],
    }


@pytest.fixture
def root(tmp_path, monkeypatch):
    (tmp_path / "triage" / "w189").mkdir(parents=True)
    matrix = tmp_path / "triage" / "w189" / "matrix.json"
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(mod, "MATRIX", matrix)
    return tmp_path


def _write(root, data):
    path = root / "triage" / "w189" / "matrix.json"
    path.write_text(json.dumps(data), encoding="utf-8")


def _data():
    return {
        "pca_feature_columns": COLS,
        "rows": _rows(),
        "candidate_n4_stability": _reference(),
    }


def test_orient_flips_component_with_negative_pivot():
    loadings = np.array([[0.1, 0.3], [-0.9, 0.8]])
    scores = np.array([[1.0, 2.0], [3.0, 4.0]])
    out_l, out_s = mod.orient(loadings.copy(), scores.copy())
    np.testing.assert_allclose(out_l[:, 0], [-0.1, 0.9])
    np.testing.assert_allclose(out_s[:, 0], [-1.0, -3.0])
    # second component pivot (0.8) already positive -> untouched
    np.testing.assert_allclose(out_l[:, 1], [0.3, 0.8])
    np.testing.assert_allclose(out_s[:, 1], [2.0, 4.0])


def test_decompose_matches_correlation_eigen():
    evr, loadings, scores = mod.decompose(_rows(), COLS)
    vals, _ = _eig_desc(VALUES)
    np.testing.assert_allclose(evr, vals / vals.sum(), atol=1e-10)
    assert abs(evr.sum() - 1.0) < 1e-12
    for k in range(loadings.shape[1]):
        pivot = int(np.argmax(np.abs(loadings[:, k])))
        assert loadings[pivot, k] > 0
    assert scores.shape == (4, 4)


def test_decompose_rejects_zero_variance_feature():
    rows = [{"a": 1, "b": i} for i in range(3)]
    with pytest.raises(SystemExit, match="zero variance"):
        mod.decompose(rows, ["a", "b"])


def test_congruence_is_absolute_cosine():
    assert mod.congruence(np.array([1.0, 0.0]), np.array([-2.0, 0.0])) == 1.0
    assert abs(mod.congruence(np.array([1.0, 0.0]), np.array([0.0, 3.0]))) < 1e-12


def test_main_writes_receipt_and_prints_pass(root, capsys):
    _write(root, _data())
    mod.main()
    assert "W189 PCA PASS" in capsys.readouterr().out
    out = root / "triage" / "w189" / "QPS_W189_PCA_STABILITY_RUNTIME_RECEIPT.json"
    receipt = json.loads(out.read_text(encoding="utf-8"))
    ref = _reference()
    assert receipt["n_features"] == 4
    assert receipt["accepted_reference_n"] == 3
    assert receipt["candidate_n"] == 4
    assert receipt["state"] == "CANDIDATE_WITHHELD_PENDING_SAMPLE4_ACCEPTANCE"
    np.testing.assert_allclose(
        receipt["candidate_n4_explained_variance_ratio"],
        ref["explained_variance_ratio"],
        atol=1e-10,
    )
    assert len(receipt["accepted_n3_explained_variance_ratio"]) == 2
    assert len(receipt["sample4_scores_candidate"]) == 3
    assert (
        abs(receipt["pc1_loading_congruence_abs"] - ref["pc1_loading_congruence_abs"])
        < 1e-9
    )


def test_main_rejects_wrong_row_counts(root):
    data = _data()
    data["rows"][3]["accepted_sample"] = 1
    _write(root, data)
    with pytest.raises(SystemExit, match="expected accepted n3"):
        mod.main()


@pytest.mark.parametrize(
    "key, message",
    [
        ("explained_variance_ratio", "EVR mismatch"),
        ("pc1_loading_congruence_abs", "PC1 congruence mismatch"),
        ("pc2_loading_congruence_abs", "PC2 congruence mismatch"),
        ("pc12_subspace_principal_angles_deg", "principal-angle mismatch"),
    ],
)
def test_main_rejects_each_reference_mismatch(root, key, message):
    data = _data()
    ref = data["candidate_n4_stability"]
    if isinstance(ref[key], list):
        ref[key] = [v + 0.5 for v in ref[key]]
    else:
        ref[key] = ref[key] + 0.5
    _write(root, data)
    with pytest.raises(SystemExit, match=message):
        mod.main()
    out = root / "triage" / "w189" / "QPS_W189_PCA_STABILITY_RUNTIME_RECEIPT.json"
    assert not out.exists()
