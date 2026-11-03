"""Gap tests for tools/w78_deterministic_work_probe.py (parity failure, main)."""

import json
import sys
import types

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

_W72 = types.ModuleType("w72_semantic_census")
_W77 = types.ModuleType("w77_instrumented_semantic_census")
_W72.measure = lambda root, sha: ([], {})
_W77.build_instrumented = lambda root, sha: ([], {}, {})

mod = load(
    "tools/w78_deterministic_work_probe.py",
    name="abn_w7_w78_deterministic_work_probe",
    deps={"w72_semantic_census": _W72, "w77_instrumented_semantic_census": _W77},
)


def _counters():
    return {name: index + 1 for index, name in enumerate(mod.WORK_FEATURES)}


def _wire(monkeypatch, receipts, row, base_receipts, base_row):
    telemetry = {"work_counters": _counters()}
    monkeypatch.setattr(
        mod.w77, "build_instrumented", lambda root, sha: (receipts, row, telemetry)
    )
    monkeypatch.setattr(mod.w72, "measure", lambda root, sha: (base_receipts, base_row))


def test_probe_raises_on_receipt_parity_failure(monkeypatch, tmp_path):
    _wire(monkeypatch, ["a"], {"x": 1}, ["b"], {"x": 1})
    with pytest.raises(RuntimeError, match="semantic parity failure"):
        mod.probe(tmp_path, "abc", 1, "lbl")


def test_probe_raises_on_feature_row_parity_failure(monkeypatch, tmp_path):
    _wire(monkeypatch, ["a"], {"x": 1}, ["a"], {"x": 2})
    with pytest.raises(RuntimeError, match="W72"):
        mod.probe(tmp_path, "abc", 1, "lbl")


def test_main_writes_receipt_and_prints(monkeypatch, tmp_path, capsys):
    _wire(monkeypatch, ["r"], {"f": 3}, ["r"], {"f": 3})
    out = tmp_path / "nested" / "dir" / "receipt.json"
    argv = [
        "w78",
        "--root",
        str(tmp_path),
        "--source-sha",
        "deadbeef",
        "--repeat",
        "2",
        "--matrix-label",
        "ubuntu-3.11",
        "--out",
        str(out),
    ]
    monkeypatch.setattr(sys, "argv", argv)
    assert mod.main() is None
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["source_sha"] == "deadbeef"
    assert written["repeat"] == 2
    assert written["matrix_label"] == "ubuntu-3.11"
    assert written["work_vector"] == _counters()
    assert written["feature_row_sha256"] == mod.canonical_sha256({"f": 3})
    assert set(written["semantic_work_vector"]) == set(mod.SEMANTIC_WORK_FEATURES)
    printed = json.loads(capsys.readouterr().out)
    assert printed == written
