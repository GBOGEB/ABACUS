"""Lane A wave 14: DMAIC_V3.dmaic_v3_engine CLI branches with phase 6 stubbed."""

import json
import sys
from types import SimpleNamespace

import pytest


def _import_engine():
    # The engine's import chain inserts repo paths into sys.path; undo that.
    saved_path = list(sys.path)
    try:
        from DMAIC_V3 import dmaic_v3_engine

        return dmaic_v3_engine
    finally:
        sys.path[:] = saved_path


eng = _import_engine()


class _Cfg:
    def __init__(self, tmp, enabled=True):
        self.paths = SimpleNamespace(state_dir=tmp / "state", reports_dir=tmp / "rep")
        self.knowledge = SimpleNamespace(enabled=enabled)


class _State:
    def __init__(self, state_dir):
        self.state_dir = state_dir


def _install(monkeypatch, tmp_path, result, enabled=True, record=None):
    record = record if record is not None else []

    class _Phase6:
        def __init__(self, cfg, state):
            self.cfg = cfg
            self.state = state

        def execute(self, iteration):
            record.append(iteration)
            if isinstance(result, Exception):
                raise result
            return result

    monkeypatch.setattr(eng, "DMAICConfig", lambda: _Cfg(tmp_path, enabled))
    monkeypatch.setattr(eng, "StateManager", _State)
    monkeypatch.setattr(eng, "Phase6Knowledge", _Phase6)
    return record


def _argv(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["dmaic_v3_engine", *args])


def _reports(tmp_path):
    return sorted((tmp_path / "rep").glob("*.json"))


def test_version_flag(monkeypatch, capsys):
    _argv(monkeypatch, "--version")
    assert eng.main() == 0
    assert capsys.readouterr().out.strip() == "DMAIC V3 Engine " + eng.ENGINE_VERSION


@pytest.mark.parametrize(
    "result,code",
    [
        ((True, {"a": 1}), 0),
        ((False, {"a": 1}), 2),
        ({"ok": 1}, 0),
        ({"error": "x"}, 2),
        ({"skipped": True}, 2),
    ],
)
def test_single_phase6_return_shapes(monkeypatch, tmp_path, result, code):
    _install(monkeypatch, tmp_path, result)
    _argv(monkeypatch, "--mode", "single", "--phase", "phase6_knowledge")
    assert eng.main() == code
    files = _reports(tmp_path)
    assert len(files) == 1
    payload = result[1] if isinstance(result, tuple) else result
    assert json.loads(files[0].read_text(encoding="utf-8")) == payload


def test_single_other_phase_does_nothing(monkeypatch, tmp_path):
    record = _install(monkeypatch, tmp_path, {"ok": 1})
    _argv(monkeypatch, "--mode", "single", "--phase", "phase2_measure")
    assert eng.main() is None
    assert record == []
    assert not (tmp_path / "rep").exists()


def test_full_mode_runs_phase6_when_enabled(monkeypatch, tmp_path):
    record = _install(monkeypatch, tmp_path, {"ok": 1})
    _argv(monkeypatch)
    assert eng.main() is None
    assert record == [1]


def test_full_mode_skips_when_disabled(monkeypatch, tmp_path):
    record = _install(monkeypatch, tmp_path, {"ok": 1}, enabled=False)
    _argv(monkeypatch, "--mode", "single")  # single without --phase -> full path
    assert eng.main() is None
    assert record == []


def test_full_mode_swallows_phase6_failure(monkeypatch, tmp_path, capsys):
    _install(monkeypatch, tmp_path, RuntimeError("phase6 down"))
    _argv(monkeypatch, "--mode", "dry-run")
    assert eng.main() is None
    assert (
        "[WARN] Phase 6 execution skipped/failed: phase6 down"
        in capsys.readouterr().out
    )
