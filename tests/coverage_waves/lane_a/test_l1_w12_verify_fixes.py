"""Lane A wave 12: DMAIC V3.3 fix verification script with stubbed phases."""

import sys
import types

import pytest

from DMAIC_V3 import verify_fixes as vf


class _Cfg:
    def __init__(self, workspace_root):
        self.workspace_root = workspace_root
        self.paths = types.SimpleNamespace(state_dir="state")


def _phase_class(**attrs):
    def init(self, cfg, state_mgr):
        self.cfg = cfg
        self.state_mgr = state_mgr

    namespace = dict(attrs)
    namespace["__init__"] = init
    return type("Phase", (), namespace)


def _install(monkeypatch, workspace_root="/data/Master_Input/x", good=True):
    config = types.ModuleType("config")
    config.DMAICConfig = lambda: _Cfg(workspace_root)
    monkeypatch.setitem(sys.modules, "config", config)

    core = types.ModuleType("core")
    state = types.ModuleType("core.state")
    state.StateManager = lambda state_dir: ("state", state_dir)
    core.state = state
    monkeypatch.setitem(sys.modules, "core", core)
    monkeypatch.setitem(sys.modules, "core.state", state)

    phases = types.ModuleType("phases")
    specs = {
        "phase2_measure": ("Phase2Measure", {"max_files_per_chunk": 5000}),
        "phase4_improve": ("Phase4Improve", {"max_files": 100}),
        "phase5_control": ("Phase5Control", {"_check_quality_gates": None}),
        "phase6_knowledge": (
            "Phase6Knowledge",
            {"_extract_improvement_knowledge": None},
        ),
        "phase7_action_tracking": (
            "Phase7ActionTracking",
            {"_collect_phase_actions": None},
        ),
        "phase8_todo_management": (
            "Phase8TODOManagement",
            {"_collect_phase_todos": None},
        ),
    }
    for mod_name, (cls_name, attrs) in specs.items():
        sub = types.ModuleType("phases." + mod_name)
        if good:
            cls = _phase_class(**attrs)
        elif "max_files_per_chunk" in attrs:
            cls = _phase_class(max_files_per_chunk=10)
        elif "max_files" in attrs:
            cls = _phase_class(max_files=5)
        else:
            cls = _phase_class()
        setattr(sub, cls_name, cls)
        setattr(phases, mod_name, sub)
        monkeypatch.setitem(sys.modules, "phases." + mod_name, sub)
    monkeypatch.setitem(sys.modules, "phases", phases)


CHECKS = [
    vf.test_fix_1_workspace_scope,
    vf.test_fix_2_chunking,
    vf.test_fix_3_improvements,
    vf.test_fix_4_quality_gates,
    vf.test_fix_5_knowledge_extraction,
    vf.test_fix_6_action_collection,
    vf.test_fix_7_todo_scanning,
]


@pytest.mark.parametrize("check", CHECKS, ids=[c.__name__ for c in CHECKS])
def test_each_check_passes_with_conforming_stubs(monkeypatch, capsys, check):
    _install(monkeypatch)
    assert check() is True
    assert "PASS" in capsys.readouterr().out


@pytest.mark.parametrize("check", CHECKS, ids=[c.__name__ for c in CHECKS])
def test_each_check_fails_with_nonconforming_stubs(monkeypatch, capsys, check):
    _install(monkeypatch, workspace_root="/data/DMAIC_V3", good=False)
    assert check() is False
    assert "FAIL" in capsys.readouterr().out


def test_main_returns_zero_when_all_pass(monkeypatch, capsys):
    _install(monkeypatch)
    assert vf.main() == 0
    out = capsys.readouterr().out
    assert "Tests passed: 7/7" in out
    assert "ALL FIXES VERIFIED" in out


def test_main_returns_one_and_counts_failures(monkeypatch, capsys):
    _install(monkeypatch, workspace_root="/data/DMAIC_V3", good=False)
    assert vf.main() == 1
    assert "7 FIXES FAILED" in capsys.readouterr().out


def test_main_treats_exceptions_as_failures(monkeypatch, capsys):
    _install(monkeypatch)

    def boom():
        raise RuntimeError("config broken")

    monkeypatch.setattr(sys.modules["config"], "DMAICConfig", boom)
    assert vf.main() == 1
    captured = capsys.readouterr()
    assert "ERROR: config broken" in captured.out
    assert "Tests passed: 0/7" in captured.out
