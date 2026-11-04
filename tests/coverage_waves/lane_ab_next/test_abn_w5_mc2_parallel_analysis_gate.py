"""Behaviour tests for tools/mc2_parallel_analysis_gate.py.

The null distribution uses ``random.Random(seed)``, so results are
deterministic for a fixed seed; the minimum 500 simulations on a 5x2 problem
keep the run fast.
"""

import hashlib
import json

import numpy as np
import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("tools/mc2_parallel_analysis_gate.py", name="abn_w5_pa_gate")


def test_fail_raises_value_error():
    with pytest.raises(ValueError, match="nope"):
        mod.fail("nope")


def test_standardize_matrix_zero_mean_unit_sd_and_constant_column():
    matrix = [[1.0, 4.0], [2.0, 4.0], [6.0, 4.0]]
    z = np.asarray(mod.standardize_matrix(matrix))
    np.testing.assert_allclose(z[:, 0].mean(), 0.0, atol=1e-12)
    np.testing.assert_allclose(z[:, 0].std(ddof=1), 1.0)
    assert list(z[:, 1]) == [0.0, 0.0, 0.0]


def test_covariance_matches_numpy():
    z = [[1.0, 0.0], [0.0, 1.0], [-1.0, -1.0]]
    np.testing.assert_allclose(mod.covariance(z), np.cov(np.asarray(z), rowvar=False))


@pytest.mark.parametrize(
    "matrix",
    [
        [[1.0, 0.3], [0.3, 1.0]],
        [[5.0, 2.0, 0.1], [2.0, 2.0, 0.4], [0.1, 0.4, 1.0]],
        [[3.0, 0.0], [0.0, 1.0]],
    ],
)
def test_jacobi_eigenvalues_matches_numpy(matrix):
    values = mod.jacobi_eigenvalues(matrix)
    np.testing.assert_allclose(values, sorted(np.linalg.eigvalsh(matrix))[::-1])


def test_jacobi_eigenvalues_max_iter_one_is_approximate():
    matrix = [[5.0, 2.0, 0.1], [2.0, 2.0, 0.4], [0.1, 0.4, 1.0]]
    values = mod.jacobi_eigenvalues(matrix, max_iter=1)
    assert not np.allclose(values, sorted(np.linalg.eigvalsh(matrix))[::-1], atol=1e-9)
    assert sum(values) == pytest.approx(8.0)


def test_quantile_linear():
    assert mod.quantile_linear([3, 1, 2], 0.5) == 2
    assert mod.quantile_linear([0.0, 10.0], 0.25) == 2.5
    assert mod.quantile_linear([4.0, 1.0, 9.0, 2.0, 7.0], 0.9) == pytest.approx(
        float(np.quantile([4.0, 1.0, 9.0, 2.0, 7.0], 0.9))
    )


def test_parallel_analysis_deterministic_and_ordered():
    a = mod.parallel_analysis(5, 2, simulations=50, seed=11, quantile=0.95)
    b = mod.parallel_analysis(5, 2, simulations=50, seed=11, quantile=0.95)
    c = mod.parallel_analysis(5, 2, simulations=50, seed=12, quantile=0.95)
    assert a == b
    assert a != c
    assert len(a) == 2
    # 2x2 correlation eigenvalues sum to 2, the largest lies in [1, 2]
    assert 1.0 <= a[0] <= 2.0
    assert 0.0 <= a[1] <= 1.0


def _receipt(tmp_path, runtime):
    path = tmp_path / "telemetry.json"
    path.write_text(
        json.dumps({"receipt_sha256": "abc", "runtime_pca": runtime}), encoding="utf-8"
    )
    return str(path)


def _measured(n=5, eigen=(1.99, 0.01)):
    return {
        "status": "MEASURED_PCA_DIAGNOSTIC",
        "numeric_comparable_rows": n,
        "components": [{"eigenvalue": e} for e in eigen],
    }


def test_main_writes_pa95_receipt(tmp_path, monkeypatch, capsys):
    src = _receipt(tmp_path, _measured())
    out = tmp_path / "pa.json"
    argv = ["prog", src, "--out", str(out), "--simulations", "500", "--seed", "7"]
    monkeypatch.setattr("sys.argv", argv)
    mod.main()
    result = json.loads(out.read_text(encoding="utf-8"))
    thresholds = mod.parallel_analysis(5, 2, simulations=500, seed=7, quantile=0.95)
    assert result["null_eigenvalue_thresholds"] == [round(t, 6) for t in thresholds]
    assert result["observed_eigenvalues"] == [1.99, 0.01]
    assert result["retained_pcs"] == [1]
    assert result["retained_component_count"] == 1
    assert result["pc2_diagnostic_not_retained"] is True
    assert result["small_sample_warning"] is True
    assert result["source_receipt_sha256"] == "abc"
    assert result["allocation_authority"] is False
    body = {k: v for k, v in result.items() if k != "receipt_sha256"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    assert result["receipt_sha256"] == hashlib.sha256(canonical).hexdigest()
    assert json.loads(capsys.readouterr().out) == result


def test_main_retains_nothing_when_eigenvalues_below_null(tmp_path, monkeypatch):
    src = _receipt(tmp_path, _measured(eigen=(1.0, 0.0)))
    out = tmp_path / "pa.json"
    monkeypatch.setattr(
        "sys.argv", ["prog", src, "--out", str(out), "--simulations", "500"]
    )
    mod.main()
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["retained_pcs"] == []
    assert result["seed"] == 20260913
    assert result["quantile"] == 0.95


@pytest.mark.parametrize(
    "runtime, extra, message",
    [
        ({"status": "WITHHELD"}, [], "runtime PCA must be MEASURED"),
        (_measured(n=4), [], "at least five observations"),
        (_measured(eigen=(2.0,)), [], "two varying features"),
        (_measured(), ["--simulations", "499"], "at least 500 simulations"),
        (_measured(), ["--quantile", "0.5"], "quantile must be between"),
        (_measured(), ["--quantile", "1.0"], "quantile must be between"),
    ],
)
def test_main_rejects(tmp_path, monkeypatch, runtime, extra, message):
    src = _receipt(tmp_path, runtime)
    out = tmp_path / "pa.json"
    monkeypatch.setattr("sys.argv", ["prog", src, "--out", str(out)] + extra)
    with pytest.raises(ValueError, match=message):
        mod.main()
    assert not out.exists()
