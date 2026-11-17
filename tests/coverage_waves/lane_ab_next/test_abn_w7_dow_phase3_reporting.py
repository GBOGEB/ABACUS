"""Gap tests for dow_phase3_reporting.py (fail-closed contract and main)."""

import json
from pathlib import Path

import pytest

import dow_phase3_reporting as mod
from dow_phase2_statistics import METHOD, SCHEMA, SEMANTICS, digest


def _group(mean):
    return {"n": 3, "mean": mean, "sample_std": 0.5, "bootstrap_ci": [1.0, 2.0]}


def _payload(**overrides):
    payload = {
        "schema": SCHEMA,
        "method": METHOD,
        "semantics_status": SEMANTICS,
        "source_sha256": "f" * 64,
        "alpha": 0.05,
        "groups": {"a": _group(1.5), "b": _group(2.5)},
        "comparisons": [{"estimate_right_minus_left": 1.0, "bootstrap_ci": [0.5, 1.5]}],
    }
    payload.update(overrides)
    return payload


def _write(tmp_path, payload, sign=True):
    data = dict(payload)
    if sign:
        data["receipt_sha256"] = digest(payload)
    path = tmp_path / "meta.json"
    path.write_bytes(json.dumps(data).encode("utf-8"))
    return path


def test_empty_metadata_rejected(tmp_path):
    path = tmp_path / "meta.json"
    path.write_bytes(b"")
    with pytest.raises(ValueError, match="missing or oversized"):
        mod.report(path, tmp_path / "out")


def test_non_object_metadata_rejected(tmp_path):
    path = tmp_path / "meta.json"
    path.write_bytes(b"[1, 2]")
    with pytest.raises(ValueError, match="not an object"):
        mod.report(path, tmp_path / "out")


def test_unrecognized_method_rejected(tmp_path):
    path = _write(tmp_path, _payload(method="other"))
    with pytest.raises(ValueError, match="unrecognized Phase 2"):
        mod.report(path, tmp_path / "out")


def test_single_group_rejected(tmp_path):
    path = _write(tmp_path, _payload(groups={"a": _group(1.0)}))
    with pytest.raises(ValueError, match="lacks validated groups"):
        mod.report(path, tmp_path / "out")


def test_invalid_alpha_rejected(tmp_path):
    path = _write(tmp_path, _payload(alpha=1.5))
    with pytest.raises(ValueError, match="invalid alpha"):
        mod.report(path, tmp_path / "out")


def test_small_group_row_rejected(tmp_path):
    bad = dict(_group(1.0), n=1)
    path = _write(tmp_path, _payload(groups={"a": bad, "b": _group(2.0)}))
    with pytest.raises(ValueError, match="invalid group row"):
        mod.report(path, tmp_path / "out")


def test_non_finite_group_statistics_rejected(tmp_path):
    bad = dict(_group(1.0), bootstrap_ci=[1.0])
    path = _write(tmp_path, _payload(groups={"a": bad, "b": _group(2.0)}))
    with pytest.raises(ValueError, match="invalid group statistics"):
        mod.report(path, tmp_path / "out")


def test_main_prints_report_paths(tmp_path, capsys):
    path = _write(tmp_path, _payload())
    root = tmp_path / "reports"
    assert mod.main(["--phase2-metadata", str(path), "--reports-root", str(root)]) == 0
    printed = capsys.readouterr().out.splitlines()
    assert len(printed) == 2
    assert printed[0].endswith(".json")
    assert printed[1].endswith(".md")
    report = json.loads(Path(printed[0]).read_text(encoding="utf-8"))
    assert report["merge_admission"] == "HOLD"


def test_main_contract_failure_exits_2(tmp_path, capsys):
    path = _write(tmp_path, _payload(), sign=False)
    with pytest.raises(SystemExit) as excinfo:
        mod.main(["--phase2-metadata", str(path), "--reports-root", str(tmp_path)])
    assert excinfo.value.code == 2
    assert "digest mismatch" in capsys.readouterr().err
