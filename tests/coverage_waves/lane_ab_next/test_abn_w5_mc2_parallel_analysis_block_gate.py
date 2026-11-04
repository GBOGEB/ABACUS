"""Behaviour tests for tools/mc2_parallel_analysis_block_gate.py.

The sibling ``mc2_parallel_analysis_gate`` is loaded by path and injected via
``deps`` so the bare import resolves without touching sys.path.
"""

import hashlib
import json

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

gate = load("tools/mc2_parallel_analysis_gate.py", name="abn_w5_pa_gate_dep")
mod = load(
    "tools/mc2_parallel_analysis_block_gate.py",
    name="abn_w5_pa_block_gate",
    deps={"mc2_parallel_analysis_gate": gate},
)


def _source(tmp_path, **blocks):
    path = tmp_path / "telemetry.json"
    doc = dict(receipt_sha256="src-sha", **blocks)
    path.write_text(json.dumps(doc), encoding="utf-8")
    return str(path)


def _measured(n=6, eigen=(1.995, 0.005)):
    return {
        "status": "MEASURED_PCA_DIAGNOSTIC",
        "numeric_comparable_rows": n,
        "components": [{"eigenvalue": e} for e in eigen],
    }


def _run(monkeypatch, tmp_path, src, block, *extra):
    out = tmp_path / "pa.json"
    argv = ["prog", src, "--block", block, "--out", str(out)] + list(extra)
    monkeypatch.setattr("sys.argv", argv)
    mod.main()
    return json.loads(out.read_text(encoding="utf-8"))


def test_imports_sibling_parallel_analysis():
    assert mod.parallel_analysis is gate.parallel_analysis
    assert mod.BLOCKS == {"runtime_pca", "semantic_pca"}


def test_write_result_adds_sha_and_prints(tmp_path, capsys):
    out = tmp_path / "r.json"
    result = {"b": 2, "a": 1}
    mod.write_result(out, result)
    expected = hashlib.sha256(b'{"a":1,"b":2}').hexdigest()
    assert result["receipt_sha256"] == expected
    assert json.loads(out.read_text(encoding="utf-8")) == result
    assert json.loads(capsys.readouterr().out) == result


def test_main_semantic_block_measured(tmp_path, monkeypatch):
    src = _source(
        tmp_path, semantic_pca=_measured(), runtime_pca={"status": "WITHHELD"}
    )
    result = _run(monkeypatch, tmp_path, src, "semantic_pca", "--simulations", "500")
    thresholds = gate.parallel_analysis(
        6, 2, simulations=500, seed=20260913, quantile=0.95
    )
    assert result["status"] == "PA95_DIAGNOSTIC"
    assert result["pca_block"] == "semantic_pca"
    assert result["schema_version"] == "MC2-PA95-BLOCK-RETENTION-0.1.0"
    assert result["null_eigenvalue_thresholds"] == [round(t, 6) for t in thresholds]
    assert result["retained_pcs"] == [1]
    assert result["pc2_diagnostic_not_retained"] is True
    assert result["small_sample_warning"] is True
    assert result["source_receipt_sha256"] == "src-sha"
    assert result["allocation_authority"] is False


def test_main_retains_both_with_patched_thresholds(tmp_path, monkeypatch):
    calls = []

    def fake_pa(n, p, *, simulations, seed, quantile):
        calls.append((n, p, simulations, seed, quantile))
        return [0.5] * p

    monkeypatch.setattr(mod, "parallel_analysis", fake_pa)
    src = _source(tmp_path, runtime_pca=_measured(n=40, eigen=(1.4, 0.6)))
    result = _run(
        monkeypatch, tmp_path, src, "runtime_pca", "--seed", "3", "--quantile", "0.9"
    )
    assert calls == [(40, 2, 2000, 3, 0.9)]
    assert result["retained_pcs"] == [1, 2]
    assert result["pc2_diagnostic_not_retained"] is False
    assert result["small_sample_warning"] is False


def test_main_withheld_input_pca(tmp_path, monkeypatch):
    block = {"status": "WITHHELD", "reason": "INSUFFICIENT_COMPARABLE_ROWS"}
    src = _source(tmp_path, runtime_pca=block)
    result = _run(monkeypatch, tmp_path, src, "runtime_pca")
    assert result["status"] == "WITHHELD_INPUT_PCA_NOT_MEASURED"
    assert result["input_pca_status"] == "WITHHELD"
    assert result["input_pca_reason"] == "INSUFFICIENT_COMPARABLE_ROWS"
    assert result["retained_pcs"] == []
    assert result["retained_component_count"] == 0


def test_main_missing_block_is_withheld(tmp_path, monkeypatch):
    src = _source(tmp_path)
    result = _run(monkeypatch, tmp_path, src, "semantic_pca")
    assert result["status"] == "WITHHELD_INPUT_PCA_NOT_MEASURED"
    assert result["input_pca_status"] is None


@pytest.mark.parametrize("n, eigen", [(4, (1.5, 0.5)), (8, (2.0,))])
def test_main_sample_or_dimension_gate(tmp_path, monkeypatch, n, eigen):
    src = _source(tmp_path, runtime_pca=_measured(n=n, eigen=eigen))
    result = _run(monkeypatch, tmp_path, src, "runtime_pca")
    assert result["status"] == "WITHHELD_PA95_SAMPLE_OR_DIMENSION_GATE"
    assert result["sample_size"] == n
    assert result["varying_feature_count"] == len(eigen)
    assert result["retained_pcs"] == []


@pytest.mark.parametrize(
    "extra, message",
    [
        (["--simulations", "100"], "at least 500 simulations"),
        (["--quantile", "0.4"], "quantile must be between"),
    ],
)
def test_main_rejects_bad_parameters(tmp_path, monkeypatch, extra, message):
    src = _source(tmp_path, runtime_pca=_measured())
    out = tmp_path / "pa.json"
    argv = ["prog", src, "--block", "runtime_pca", "--out", str(out)] + extra
    monkeypatch.setattr("sys.argv", argv)
    with pytest.raises(ValueError, match=message):
        mod.main()
    assert not out.exists()


def test_main_rejects_unknown_block(tmp_path, monkeypatch, capsys):
    src = _source(tmp_path)
    monkeypatch.setattr(
        "sys.argv", ["prog", src, "--block", "other", "--out", str(tmp_path / "o")]
    )
    with pytest.raises(SystemExit):
        mod.main()
    assert "invalid choice" in capsys.readouterr().err
