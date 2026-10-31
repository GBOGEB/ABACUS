"""Lane A wave 14: DMAIC_V3.temporal_phase_runner with stub phases and config."""

import importlib
import json
import sys
from types import SimpleNamespace

import pytest


def _import_restoring_sys_path():
    saved = list(sys.path)
    try:
        return importlib.import_module("DMAIC_V3.temporal_phase_runner")
    finally:
        sys.path[:] = saved


tpr = _import_restoring_sys_path()


class TupleStateManager:
    def __init__(self, config, state_manager):
        self.config = config

    def execute(self, iteration):
        return True, {
            "metrics": [1],
            "improvements": [1, 2],
            "quality_gates": {"a": 1},
        }


class DictState:
    def __init__(self, config, state):
        self.config = config

    def execute(self, iteration):
        return {"phase": iteration}


class DictStateMgr:
    def __init__(self, config, state_mgr):
        self.config = config

    def execute(self, iteration):
        return {"other": 1}


class Boom:
    def __init__(self, config, state_manager):
        self.config = config

    def execute(self, iteration):
        raise RuntimeError("phase exploded")


class PlainList(TupleStateManager):
    def execute(self, iteration):
        return True, ["not", "a", "dict"]


@pytest.fixture
def runner(tmp_path, monkeypatch):
    out = tmp_path / "out"
    out.mkdir()
    cfg = SimpleNamespace(
        paths=SimpleNamespace(state_dir=tmp_path / "st", output_root=out)
    )
    calls = []
    monkeypatch.setattr(tpr, "DMAICConfig", lambda: cfg)
    monkeypatch.setattr(tpr, "StateManager", lambda d: ("state", d))
    monkeypatch.setattr(
        tpr, "enable_idempotency", lambda enabled: calls.append(enabled)
    )
    r = tpr.TemporalPhaseRunner()
    assert calls == [True]
    return r


def _set_map(monkeypatch, classes):
    mapping = {i: (f"P{i}", c) for i, c in enumerate(classes)}
    monkeypatch.setattr(tpr.TemporalPhaseRunner, "PHASE_MAP", mapping)


def test_invalid_phase_number(runner):
    with pytest.raises(ValueError, match="Invalid phase number: 42"):
        runner.run_phase(42)


def test_tuple_result_with_dow_and_temporal(runner, monkeypatch, capsys):
    _set_map(monkeypatch, [TupleStateManager])
    (runner.config.paths.output_root / "seed.txt").write_bytes(b"abcd")
    rec = runner.run_phase(0, iteration=3, task_filter="1.1")
    assert rec["success"] is True
    assert rec["result"]["improvements"] == [1, 2]
    stages = [s["stage"] for s in runner.temporal_snapshots]
    assert stages == ["BEFORE", "AFTER"]
    assert runner.temporal_snapshots[0]["output_dir_size"] == 4
    assert runner.temporal_snapshots[0]["file_count"] == 1
    devoured = runner.config.paths.output_root / "iteration_3" / "devoured_phase0.json"
    data = json.loads(devoured.read_text(encoding="utf-8"))
    assert len(data["insights"]) == 3
    assert "Task Filter: 1.1" in capsys.readouterr().out


def test_constructor_fallbacks_and_dict_results(runner, monkeypatch):
    _set_map(monkeypatch, [DictState, DictStateMgr])
    assert runner.run_phase(0)["success"] is True
    rec = runner.run_phase(1)
    assert rec["success"] is False
    assert rec["result"] == {"other": 1}
    assert not (
        runner.config.paths.output_root / "iteration_1" / "devoured_phase1.json"
    ).exists()


def test_non_dict_result_devours_nothing(runner, monkeypatch):
    _set_map(monkeypatch, [PlainList])
    runner.enable_temporal = False
    rec = runner.run_phase(0, iteration=2)
    assert rec["success"] is True
    assert runner.temporal_snapshots == []
    path = runner.config.paths.output_root / "iteration_2" / "devoured_phase0.json"
    assert json.loads(path.read_text(encoding="utf-8"))["insights"] == []


def test_phase_exception_is_recorded(runner, monkeypatch):
    _set_map(monkeypatch, [Boom])
    rec = runner.run_phase(0)
    assert rec["success"] is False
    assert rec["error"] == "phase exploded"
    assert runner.execution_log == [rec]


def test_dir_helpers_on_missing_path(runner, tmp_path):
    assert runner._get_dir_size(tmp_path / "missing") == 0
    assert runner._count_files(tmp_path / "missing") == 0


def test_run_all_phases_success_and_stop(runner, monkeypatch):
    _set_map(monkeypatch, [DictState] * 9)
    summary = runner.run_all_phases(iteration=5)
    assert summary["total_phases"] == 9
    assert summary["failed_phases"] == 0
    saved = list(
        runner.config.paths.output_root.glob("temporal_execution_iteration_5*.json")
    )
    assert len(saved) == 1
    assert json.loads(saved[0].read_text(encoding="utf-8"))["successful_phases"] == 9

    _set_map(monkeypatch, [DictState, Boom] + [DictState] * 7)
    summary = runner.run_all_phases(iteration=6)
    assert summary["total_phases"] == 2
    assert summary["failed_phases"] == 1


@pytest.mark.parametrize(
    "argv,classes,code",
    [
        (["--all"], [DictState] * 9, 0),
        (["--all", "--no-dow", "--no-temporal"], [Boom] + [DictState] * 8, 1),
        (["--phase", "0", "--task", "2.3"], [DictState] * 9, 0),
        (["--phase", "1"], [DictState, DictStateMgr] + [DictState] * 7, 1),
        ([], [DictState] * 9, 1),
    ],
)
def test_main(runner, monkeypatch, argv, classes, code):
    _set_map(monkeypatch, classes)
    monkeypatch.setattr(sys, "argv", ["temporal_phase_runner.py", *argv])
    assert tpr.main() == code
