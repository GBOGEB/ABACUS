"""Lane A wave 13: DOW recursive hooks injection agent."""

import json
import sys

import pytest

from tests.coverage_waves.lane_a._load import load

_REL = "DMAIC_V3/local_mcp/agents/dow_recursive_hooks_injector.py"
_NAME = "l1_w13_dow_recursive_hooks_injector"


def _load_restoring():
    # The module inserts the repo root and src/ at sys.path[0] on import.
    saved = list(sys.path)
    try:
        return load(_REL, name=_NAME)
    finally:
        sys.path[:] = saved
        sys.modules.pop(_NAME, None)


mod = _load_restoring()


def _write(path, data):
    path.write_bytes(json.dumps(data).encode("utf-8"))
    return path


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def injector():
    return mod.DOWRecursiveHooksInjector()


def test_dependency_map_covers_all_phases(injector):
    assert injector.config_path == "orchestrator_config.yaml"
    assert len(injector.dependency_map) == 7
    assert injector.dependency_map["phase6_knowledge.json"]["feeds_into"] == [
        "next_iteration"
    ]


def test_inject_known_file_adds_hooks(tmp_path, injector):
    path = _write(
        tmp_path / "phase3_analyze.json",
        {"metadata": {"phase": "phase3", "version": "9.9"}, "v": 1},
    )
    result = injector.inject_recursive_hooks(path, 2)
    assert result == {"status": "success", "file": str(path)}
    data = _read(path)
    hooks = data["recursive_hooks"]
    assert hooks["consumed_from"] == ["phase2_measure.json", "phase2_metrics.json"]
    assert hooks["feeds_into"] == ["phase4_improve.json"]
    assert hooks["iteration_lineage"] == [0, 1, 2]
    assert "9.9" in hooks["version_history"]
    assert data["lineage"]["parent_artifacts"] == hooks["consumed_from"]
    assert len(data["idempotency"]["input_hash"]) == 64
    assert data["idempotency"]["input_hash"] != data["idempotency"]["output_hash"]
    assert data["v"] == 1


def test_inject_unknown_file_has_empty_dependencies(tmp_path, injector):
    path = _write(tmp_path / "other.json", {"x": 1})
    assert injector.inject_recursive_hooks(path, 0)["status"] == "success"
    hooks = _read(path)["recursive_hooks"]
    assert hooks["consumed_from"] == []
    assert hooks["feeds_into"] == []
    assert hooks["iteration_lineage"] == [0]


def test_inject_invalid_json_reports_error(tmp_path, injector):
    path = tmp_path / "bad.json"
    path.write_bytes(b"{not json")
    result = injector.inject_recursive_hooks(path, 1)
    assert result["status"] == "error"
    assert result["error"]


def test_inject_batch_counts(tmp_path, injector):
    good = _write(tmp_path / "phase1_define.json", {"a": 1})
    bad = tmp_path / "bad.json"
    bad.write_bytes(b"[")
    result = injector.inject_batch([good, bad, tmp_path / "missing.json"], 1)
    assert result["total"] == 3
    assert result["success"] == 1
    assert result["failed"] == 2
    assert len(result["results"]) == 3


def test_version_history_variants(tmp_path, monkeypatch, injector):
    monkeypatch.setattr(mod, "ROOT_DIR", tmp_path)
    assert injector._get_version_history({}) == ["3.3.0"]
    assert injector._get_version_history({"metadata": "x"}) == ["3.3.0"]
    assert injector._get_version_history({"metadata": {"version": 4}}) == ["4"]

    version_file = tmp_path / "DMAIC_V3" / "VERSION"
    version_file.parent.mkdir()
    version_file.write_bytes(b"  \n")
    assert injector._get_version_history({}) == ["3.3.0"]
    version_file.write_bytes(b"5.0\n")
    assert injector._get_version_history({"metadata": {"version": "5.0"}}) == ["5.0"]
    assert injector._get_version_history({"metadata": {"version": "1"}}) == [
        "1",
        "5.0",
    ]


def _run_main(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["dow_recursive_hooks_injector.py", *args])
    return mod.main()


def test_main_missing_target_exits_one(tmp_path, monkeypatch, capsys):
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, "--target", str(tmp_path / "none"))
    assert exc.value.code == 1
    assert "Target directory not found" in capsys.readouterr().out


def test_main_no_json_exits_zero(tmp_path, monkeypatch, capsys):
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, "--target", str(tmp_path), "--verbose")
    assert exc.value.code == 0
    assert "No JSON files found" in capsys.readouterr().out


def test_main_success_then_failure(tmp_path, monkeypatch, capsys):
    _write(tmp_path / "phase2_measure.json", {"a": 1})
    assert _run_main(monkeypatch, "--target", str(tmp_path), "--iteration", "3") is None
    out = capsys.readouterr().out
    assert "Total: 1" in out
    assert "Success: 1" in out
    assert _read(tmp_path / "phase2_measure.json")["recursive_hooks"][
        "iteration_lineage"
    ] == [0, 1, 2, 3]

    (tmp_path / "broken.json").write_bytes(b"{")
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, "--target", str(tmp_path))
    assert exc.value.code == 1
    assert "Some files failed" in capsys.readouterr().out
