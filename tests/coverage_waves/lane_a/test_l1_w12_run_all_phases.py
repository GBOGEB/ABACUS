"""Lane A wave 12: run_all_phases CLI wrapper around a stubbed orchestrator."""

import importlib
import sys
import types

import pytest


class _FakeOrchestrator:
    instances = []
    outcome = True

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.iterations = []
        _FakeOrchestrator.instances.append(self)

    def execute_full_pipeline(self, iteration):
        self.iterations.append(iteration)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


@pytest.fixture
def runner(monkeypatch):
    fake = types.ModuleType("DMAIC_V3.full_pipeline_orchestrator")
    fake.FullPipelineOrchestrator = _FakeOrchestrator
    monkeypatch.setitem(sys.modules, "DMAIC_V3.full_pipeline_orchestrator", fake)
    monkeypatch.delitem(sys.modules, "DMAIC_V3.run_all_phases", raising=False)
    _FakeOrchestrator.instances = []
    _FakeOrchestrator.outcome = True
    module = importlib.import_module("DMAIC_V3.run_all_phases")
    yield module
    sys.modules.pop("DMAIC_V3.run_all_phases", None)


def test_defaults_run_iteration_one_with_git(runner, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["run_all_phases.py"])
    assert runner.main() == 0
    orch = _FakeOrchestrator.instances[-1]
    assert orch.kwargs == {
        "enable_idempotency_flag": True,
        "enable_git_commits": True,
        "verbose": False,
    }
    assert orch.iterations == [1]
    assert "ITERATION 1 COMPLETED SUCCESSFULLY" in capsys.readouterr().out


def test_flags_and_failure_return_one(runner, monkeypatch, capsys):
    argv = ["run_all_phases.py", "--iteration", "4", "--verbose", "--no-git"]
    monkeypatch.setattr(sys, "argv", argv)
    _FakeOrchestrator.outcome = False
    assert runner.main() == 1
    orch = _FakeOrchestrator.instances[-1]
    assert orch.kwargs["enable_git_commits"] is False
    assert orch.kwargs["verbose"] is True
    assert orch.iterations == [4]
    assert "ITERATION 4 FAILED" in capsys.readouterr().out


def test_exception_is_reported_and_returns_one(runner, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["run_all_phases.py", "--iteration", "2"])
    _FakeOrchestrator.outcome = RuntimeError("pipeline exploded")
    assert runner.main() == 1
    assert "ERROR: pipeline exploded" in capsys.readouterr().out
