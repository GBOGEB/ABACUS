"""Gap tests for sync_pytest_config.py, run only against tmp_path copies."""

import importlib
import json

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("sync_pytest_config.py", name="abn_w7_sync_pytest_config")

INI = "[pytest]\nmarkers =\n    slow: slow tests\n    integration: needs services\n"


def _root(tmp_path, ini=INI, pyproject=None):
    (tmp_path / "pytest.ini").write_bytes(ini.encode("utf-8"))
    if pyproject is not None:
        (tmp_path / "pyproject.toml").write_bytes(pyproject.encode("utf-8"))
    return tmp_path


def test_tomli_fallback_used_when_tomllib_missing():
    real = importlib.import_module("tomllib")
    fallback = load(
        "sync_pytest_config.py",
        name="abn_w7_sync_pytest_config_tomli",
        deps={"tomllib": None, "tomli": real},
    )
    assert fallback.tomllib is real


def test_markers_reject_non_list_entries():
    with pytest.raises(ValueError, match="must be a string or list"):
        mod._markers(42, owner="x")


def test_markers_reject_non_string_item():
    with pytest.raises(ValueError, match="non-string marker declaration"):
        mod._markers(["slow: s", 3], owner="x")


def test_markers_reject_invalid_name():
    with pytest.raises(ValueError, match="invalid marker name"):
        mod._markers(["9bad: nope"], owner="x")


def test_ini_without_markers_rejected(tmp_path):
    root = _root(tmp_path, ini="[pytest]\naddopts = -q\n")
    with pytest.raises(ValueError, match="no \\[pytest\\] markers"):
        mod.validate(root)


def test_malformed_ini_options_rejected(tmp_path):
    root = _root(tmp_path, pyproject='[tool.pytest]\nini_options = "bad"\n')
    with pytest.raises(ValueError, match="Malformed pyproject pytest ini_options"):
        mod.validate(root)


def test_pyproject_without_markers_is_single_source(tmp_path):
    root = _root(tmp_path, pyproject='[tool.pytest.ini_options]\naddopts = "-q"\n')
    result = mod.validate(root)
    assert result["status"] == "SINGLE_CANONICAL_SOURCE_VALIDATED"
    assert result["secondary_config"] == "NOT_DECLARED"
    assert result["marker_count"] == 2


def test_main_success_prints_json(monkeypatch, tmp_path, capsys):
    root = _root(tmp_path)
    monkeypatch.setattr(mod.validate, "__defaults__", (root,))
    assert mod.main(["--dry-run"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["source_mutation"] is False
    assert payload["marker_count"] == 2


def test_main_failure_reports_to_stderr(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(mod.validate, "__defaults__", (tmp_path,))
    assert mod.main([]) == 1
    assert "PYTEST_MARKER_SYNC_FAIL: Missing canonical pytest.ini" in (
        capsys.readouterr().err
    )
