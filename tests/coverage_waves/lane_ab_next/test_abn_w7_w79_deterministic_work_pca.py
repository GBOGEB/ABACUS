"""Gap tests for tools/w79_deterministic_work_pca.py (guards, helpers, CLI)."""

import json
import sys

import numpy as np
import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

mod = load("tools/w79_deterministic_work_pca.py", name="abn_w7_w79_pca")

INPUT = REPO_ROOT / "architecture/w79/W79_W78_INPUT.json"


def _source():
    return json.loads(INPUT.read_text(encoding="utf-8"))


def test_quantile_linear_exact_index_and_interpolation():
    assert mod._quantile_linear([3.0, 1.0, 2.0], 0.5) == 2.0
    assert mod._quantile_linear([0.0, 10.0], 0.25) == 2.5


def test_standardize_rejects_constant_feature():
    matrix = np.array([[1.0, 2.0], [1.0, 3.0], [1.0, 4.0]])
    with pytest.raises(ValueError, match="every selected feature to vary"):
        mod._standardize(matrix)


def test_parallel_analysis_guards():
    with pytest.raises(ValueError, match="at least 500"):
        mod._parallel_analysis(5, 2, simulations=10, seed=1, quantile=0.95)
    with pytest.raises(ValueError, match="quantile must be between"):
        mod._parallel_analysis(5, 2, simulations=500, seed=1, quantile=0.4)


def _mutate_w78(source, field, value):
    source["source_w78"][field] = value
    return source


def _mutated(kind):
    source = _source()
    if kind == "schema":
        source["schema_version"] = "other"
    elif kind == "status":
        _mutate_w78(source, "status", "FAIL")
    elif kind == "panel":
        _mutate_w78(source, "observation_count", 29)
    elif kind == "blocks":
        source["semantic_work_features"] = source["semantic_work_features"][:2]
    elif kind == "subset":
        source["semantic_work_features"] = ["a", "b", "c"]
    elif kind == "rows":
        source["rows"] = source["rows"][:14]
    elif kind == "labels":
        source["rows"][1]["label"] = source["rows"][0]["label"]
    elif kind == "drift":
        source["rows"][0]["values"] = source["rows"][0]["values"][:-1]
    elif kind == "semantic":
        source["rows"][0]["semantic_sha256"] = "0" * 64
    return source


@pytest.mark.parametrize(
    "kind, message",
    [
        ("schema", "input schema mismatch"),
        ("status", "diversity gate PASS"),
        ("panel", "15-target/30-observation"),
        ("blocks", "multivariate deterministic work blocks"),
        ("subset", "must be a subset"),
        ("rows", "15 unique collapsed exact-SHA rows"),
        ("labels", "15 unique matrix labels"),
        ("drift", "work feature drift"),
        ("semantic", "semantic work-vector hash mismatch"),
    ],
)
def test_validate_input_fails_closed(kind, message):
    with pytest.raises(ValueError, match=message):
        mod.validate_input(_mutated(kind))


def test_main_writes_receipt(monkeypatch, tmp_path, capsys):
    out = tmp_path / "nested" / "w79.json"
    argv = ["w79", str(INPUT), "--out", str(out), "--simulations", "500"]
    monkeypatch.setattr(sys, "argv", argv)
    assert mod.main() is None
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["schema_version"] == mod.SCHEMA
    assert written["full_work_pca"]["components"][0]["retained"] is True
    assert (
        written["receipt_sha256"]
        == json.loads(capsys.readouterr().out)["receipt_sha256"]
    )
