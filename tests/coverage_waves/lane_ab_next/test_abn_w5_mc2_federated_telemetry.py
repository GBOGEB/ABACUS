"""Behaviour tests for tools/mc2_federated_telemetry.py.

Covers row validation guards, the stdlib Jacobi eigen solver (checked against
numpy), every PCA withholding reason and the CLI receipt.
"""

import hashlib
import json

import numpy as np
import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("tools/mc2_federated_telemetry.py", name="abn_w5_federated_telemetry")


def _sha(i):
    return "".join([format(i, "x")] * 40)[:40]


def _runtime(i, **over):
    row = {
        "row_id": "rt-" + str(i),
        "observation_class": "runtime",
        "source_repo": "GBOGEB/ABACUS",
        "source_sha": _sha(i),
        "evidence_reference": "run/" + str(i),
        "authority_class": "source_supported",
        "execution_state": "PASS",
        "runner_allocated_fraction": [0.2, 0.5, 0.9, 0.4, 1.0, 0.7][i % 6],
        "steps_executed_total": [3, 8, 12, 5, 20, 9][i % 6],
        "job_count": 2,
        "evidence_emit_count": [1, 4, 2, 6, 3, 5][i % 6],
        "queue_seconds_mean": [10.0, 4.0, 30.0, 12.0, 2.0, 7.0][i % 6],
        "execute_seconds_total": [100.0, 250.0, 80.0, 400.0, 60.0, 90.0][i % 6],
    }
    row.update(over)
    return row


def _semantic(i, **over):
    row = {
        "row_id": "se-" + str(i),
        "observation_class": "semantic",
        "source_repo": "GBOGEB/CODEX",
        "source_sha": _sha(i),
        "evidence_reference": "doc/" + str(i),
        "authority_class": "diagnostic_only",
        "registry_gap_rate": [0.1, 0.4, 0.2, 0.9, 0.5][i % 5],
        "unresolved_reference_rate": [0.3, 0.1, 0.6, 0.2, 0.8][i % 5],
        "consumer_penetration_rate": [0.5, 0.7, 0.2, 0.9, 0.4][i % 5],
        "graph_drop_rate": [0.0, 0.2, 0.1, 0.3, 0.6][i % 5],
        "lineage_gap_rate": [0.05, 0.15, 0.5, 0.25, 0.35][i % 5],
    }
    row.update(over)
    return row


def test_fail_raises_value_error():
    with pytest.raises(ValueError, match="bad"):
        mod.fail("bad")


def test_finite_number():
    assert mod.finite_number(3) is True
    assert mod.finite_number(2.5) is True
    assert mod.finite_number(True) is False
    assert mod.finite_number(float("nan")) is False
    assert mod.finite_number(float("inf")) is False
    assert mod.finite_number("1") is False
    assert mod.finite_number(None) is False


def test_load_rows_accepts_list_and_object(tmp_path):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text(json.dumps([{"x": 1}, {"x": 2}]), encoding="utf-8")
    b.write_text(json.dumps({"x": 3}), encoding="utf-8")
    assert mod.load_rows([a, b]) == [{"x": 1}, {"x": 2}, {"x": 3}]


def test_load_rows_rejects_scalar_root(tmp_path):
    c = tmp_path / "c.json"
    c.write_text("5", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON root must be object or list"):
        mod.load_rows([c])


def test_validate_common_accepts_valid_row():
    assert mod.validate_common(_runtime(1), 1) is None


@pytest.mark.parametrize(
    "over, message",
    [
        ({"row_id": ""}, "missing row_id"),
        ({"evidence_reference": None}, "missing evidence_reference"),
        ({"observation_class": "other"}, "unsupported observation_class"),
        ({"source_sha": "ABC"}, "source_sha must be exact"),
        ({"source_sha": "A" * 40}, "source_sha must be exact"),
        ({"authority_class": "promoted"}, "unsupported authority_class"),
    ],
)
def test_validate_common_rejects(over, message):
    with pytest.raises(ValueError, match=message):
        mod.validate_common(_runtime(1, **over), 4)


def test_validate_runtime_accepts_executed_and_not_executed():
    assert mod.validate_runtime(_runtime(1), 1) is None
    row = _runtime(
        2,
        execution_state="NOT_EXECUTED",
        steps_executed_total=0,
        runner_allocated_fraction=0,
        queue_seconds_mean=None,
        execute_seconds_total=None,
    )
    assert mod.validate_runtime(row, 2) is None


@pytest.mark.parametrize(
    "over, message",
    [
        ({"execution_state": "RUNNING"}, "unsupported execution_state"),
        ({"job_count": None}, "invalid job_count"),
        ({"evidence_emit_count": -1}, "invalid evidence_emit_count"),
        ({"runner_allocated_fraction": 1.5}, "outside"),
        ({"steps_executed_total": 2.5}, "must be integers"),
        (
            {"execution_state": "NOT_EXECUTED", "steps_executed_total": 1},
            "NOT_EXECUTED requires zero steps",
        ),
        ({"steps_executed_total": 0}, "executed state requires >0 steps"),
        ({"runner_allocated_fraction": 0}, "executed state requires"),
        ({"queue_seconds_mean": -2.0}, "invalid queue_seconds_mean"),
        ({"execute_seconds_total": "x"}, "invalid execute_seconds_total"),
    ],
)
def test_validate_runtime_rejects(over, message):
    with pytest.raises(ValueError, match=message):
        mod.validate_runtime(_runtime(1, **over), 3)


def test_validate_semantic_accepts_and_allows_missing():
    assert mod.validate_semantic(_semantic(1), 1) is None
    assert mod.validate_semantic(_semantic(1, graph_drop_rate=None), 1) is None


@pytest.mark.parametrize("value", [1.2, -0.1, "0.5", float("nan")])
def test_validate_semantic_rejects(value):
    with pytest.raises(ValueError, match="invalid semantic feature lineage_gap_rate"):
        mod.validate_semantic(_semantic(1, lineage_gap_rate=value), 7)


def test_comparable():
    assert mod.comparable({"a": 1, "b": 2.0}, ["a", "b"]) is True
    assert mod.comparable({"a": 1, "b": None}, ["a", "b"]) is False


def test_standardize_zero_sd_column_becomes_zero():
    rows = [{"a": 1.0, "b": 5.0}, {"a": 3.0, "b": 5.0}]
    z = mod.standardize(rows, ["a", "b"])
    assert z[0][1] == 0.0 and z[1][1] == 0.0
    assert z[0][0] == pytest.approx(-1 / np.sqrt(2))
    assert z[1][0] == pytest.approx(1 / np.sqrt(2))


def test_covariance_matches_numpy():
    z = [[1.0, 2.0], [2.0, 1.0], [0.0, 0.5], [3.0, 4.0]]
    expected = np.asarray(z).T @ np.asarray(z) / 3
    np.testing.assert_allclose(mod.covariance(z), expected)


@pytest.mark.parametrize(
    "matrix",
    [
        [[1.0, 0.6], [0.6, 1.0]],
        [[2.0, 1.0], [1.0, 3.0]],
        [[4.0, 1.0, 0.5], [1.0, 3.0, 0.2], [0.5, 0.2, 1.0]],
        [[1.0, 0.0], [0.0, 2.0]],
    ],
)
def test_jacobi_eigen_matches_numpy(matrix):
    pairs = mod.jacobi_eigen(matrix)
    values = [p[0] for p in pairs]
    np.testing.assert_allclose(values, sorted(np.linalg.eigvalsh(matrix))[::-1])
    arr = np.asarray(matrix)
    for value, vector in pairs:
        np.testing.assert_allclose(
            arr @ np.asarray(vector), value * np.asarray(vector), atol=1e-9
        )


def test_jacobi_eigen_stops_at_max_iter():
    matrix = [[4.0, 1.0, 0.5], [1.0, 3.0, 0.2], [0.5, 0.2, 1.0]]
    pairs = mod.jacobi_eigen(matrix, max_iter=1)
    assert len(pairs) == 3
    exact = sorted(np.linalg.eigvalsh(matrix))[::-1]
    assert not np.allclose([p[0] for p in pairs], exact, atol=1e-9)


def test_pca_block_insufficient_rows():
    res = mod.pca_block([_runtime(i) for i in range(4)], mod.RUNTIME_FEATURES)
    assert res["status"] == "WITHHELD"
    assert res["reason"] == "INSUFFICIENT_COMPARABLE_ROWS"
    assert res["numeric_comparable_rows"] == 4


def test_pca_block_excludes_non_comparable_rows():
    rows = [_runtime(i) for i in range(5)]
    rows[0]["queue_seconds_mean"] = None
    res = mod.pca_block(rows, mod.RUNTIME_FEATURES)
    assert res["rows_seen"] == 5
    assert res["numeric_comparable_rows"] == 4
    assert res["reason"] == "INSUFFICIENT_COMPARABLE_ROWS"


def test_pca_block_pseudoreplication_gate():
    rows = [_runtime(i, source_sha=_sha(i % 3)) for i in range(6)]
    res = mod.pca_block(rows, mod.RUNTIME_FEATURES)
    assert res["reason"] == "PSEUDOREPLICATION_DISTINCT_SHA_GATE"
    assert res["distinct_source_shas"] == 3


def test_pca_block_one_observation_per_sha():
    rows = [_runtime(i) for i in range(5)] + [_runtime(9, source_sha=_sha(1))]
    res = mod.pca_block(rows, mod.RUNTIME_FEATURES)
    assert res["reason"] == "ONE_OBSERVATION_PER_SHA_REQUIRED"


def test_pca_block_insufficient_varying_features():
    rows = [_semantic(i) for i in range(5)]
    for row in rows:
        for key in mod.SEMANTIC_FEATURES[1:]:
            row[key] = 0.5
    res = mod.pca_block(rows, mod.SEMANTIC_FEATURES)
    assert res["reason"] == "INSUFFICIENT_VARYING_FEATURES"
    assert res["constant_features_excluded"] == mod.SEMANTIC_FEATURES[1:]


def test_pca_block_measured_components():
    rows = [_runtime(i) for i in range(5)]
    rows_const = [dict(r, evidence_emit_count=3) for r in rows]
    res = mod.pca_block(rows_const, mod.RUNTIME_FEATURES)
    assert res["status"] == "MEASURED_PCA_DIAGNOSTIC"
    assert res["constant_features_excluded"] == ["evidence_emit_count"]
    comps = res["components"]
    assert [c["pc"] for c in comps] == [1, 2, 3, 4]
    eig = [c["eigenvalue"] for c in comps]
    assert eig == sorted(eig, reverse=True)
    assert sum(c["explained_variance_ratio"] for c in comps) == pytest.approx(
        1.0, abs=1e-5
    )
    assert set(comps[0]["loadings"]) == set(mod.RUNTIME_FEATURES) - {
        "evidence_emit_count"
    }
    rank = comps[0]["absolute_loading_rank"]
    mags = [abs(comps[0]["loadings"][k]) for k in rank]
    assert mags == sorted(mags, reverse=True)
    # eigenvalues equal those of the correlation matrix of the varying features
    varying = [f for f in mod.RUNTIME_FEATURES if f != "evidence_emit_count"]
    x = np.array([[r[f] for f in varying] for r in rows_const], dtype=float)
    expected = sorted(np.linalg.eigvalsh(np.corrcoef(x, rowvar=False)))[::-1]
    np.testing.assert_allclose(eig, np.round(expected, 6), atol=2e-6)


def _write_rows(tmp_path, name, rows):
    path = tmp_path / name
    path.write_text(json.dumps(rows), encoding="utf-8")
    return str(path)


def test_main_writes_receipt(tmp_path, monkeypatch, capsys):
    runtime = [_runtime(i) for i in range(5)]
    semantic = [_semantic(i) for i in range(5)]
    single = _semantic(7, row_id="se-solo", source_sha=_sha(2))
    p1 = _write_rows(tmp_path, "rt.json", runtime)
    p2 = _write_rows(tmp_path, "se.json", semantic)
    p3 = _write_rows(tmp_path, "one.json", single)
    out = tmp_path / "receipt.json"
    monkeypatch.setattr("sys.argv", ["prog", p1, p2, p3, "--out", str(out)])
    mod.main()
    receipt = json.loads(out.read_text(encoding="utf-8"))
    assert receipt["rows_total"] == 11
    assert receipt["class_counts"] == {"runtime": 5, "semantic": 6}
    assert receipt["runtime_state_counts"] == {"PASS": 5}
    assert receipt["runtime_pca"]["status"] == "MEASURED_PCA_DIAGNOSTIC"
    # semantic has 6 rows over only 5 distinct SHAs (se-solo reuses _sha(2))
    assert receipt["semantic_pca"]["reason"] == "ONE_OBSERVATION_PER_SHA_REQUIRED"
    assert receipt["zero_imputation_performed"] is False
    body = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    assert receipt["receipt_sha256"] == hashlib.sha256(canonical).hexdigest()
    assert json.loads(capsys.readouterr().out) == receipt


def test_main_rejects_duplicate_row_id(tmp_path, monkeypatch):
    rows = [_runtime(1), _runtime(2, row_id="rt-1")]
    p1 = _write_rows(tmp_path, "rt.json", rows)
    monkeypatch.setattr("sys.argv", ["prog", p1, "--out", str(tmp_path / "o.json")])
    with pytest.raises(ValueError, match="row 2: duplicate row_id"):
        mod.main()
    assert not (tmp_path / "o.json").exists()
