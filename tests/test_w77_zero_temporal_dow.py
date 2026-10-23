"""W77 lane C: temporal/DOW execution controls, without real process dispatch.

All phase and subprocess interfaces are stubs; assertions target genuine
production decision logic and preserve blocked/failed states.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    source = ROOT / path
    spec = importlib.util.spec_from_file_location(name, source)
    if spec is None or spec.loader is None:
        raise AssertionError("source missing")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def temporal():
    return _load("w77_temporal", "DMAIC_V3/temporal_phase_runner.py")


@pytest.fixture
def dow():
    return _load("w77_dow", "DMAIC_V3/dow_integration_executor.py")


def _runner(module, root, *, temporal=True, devour=True):
    runner = object.__new__(module.TemporalPhaseRunner)
    runner.config = SimpleNamespace(paths=SimpleNamespace(output_root=root))
    runner.state_mgr = object()
    runner.enable_temporal = temporal
    runner.enable_dow = devour
    runner.execution_log = []
    runner.temporal_snapshots = []
    return runner


def test_temporal_invalid_phase_refused_before_any_snapshot(temporal, tmp_path):
    runner = _runner(temporal, tmp_path)
    with pytest.raises(ValueError, match="Invalid phase number"):
        runner.run_phase(99)
    assert runner.execution_log == []
    assert runner.temporal_snapshots == []


def test_temporal_tuple_success_emits_local_before_after_and_devour(temporal, tmp_path):
    class FakePhase:
        def __init__(self, config=None, state_manager=None):
            assert config is not None and state_manager is not None

        def execute(self, iteration):
            assert iteration == 3
            return True, {
                "metrics": {"a": 1, "b": 2},
                "improvements": ["I01"],
                "quality_gates": [1, 2],
            }

    runner = _runner(temporal, tmp_path)
    runner.PHASE_MAP = {0: ("Safe synthetic phase", FakePhase)}
    result = runner.run_phase(0, iteration=3, task_filter="3.1")
    assert result["success"] is True
    assert [v["stage"] for v in runner.temporal_snapshots] == ["BEFORE", "AFTER"]
    output = tmp_path / "iteration_3" / "devoured_phase0.json"
    payload = json.loads(output.read_text())
    assert payload["phase"] == 0 and len(payload["insights"]) == 3
    assert result["duration_seconds"] >= 0


def test_temporal_dict_without_phase_is_failed_not_green(temporal, tmp_path):
    class FakePhase:
        def __init__(self, **kwargs):
            pass

        def execute(self, iteration):
            return {"metrics": {"fake": "value"}}

    runner = _runner(temporal, tmp_path, temporal=False)
    runner.PHASE_MAP = {1: ("No phase evidence", FakePhase)}
    result = runner.run_phase(1)
    assert result["success"] is False
    assert runner.temporal_snapshots == []
    assert not list(tmp_path.glob("**/devoured*.json"))


def test_temporal_failure_is_logged_and_does_not_devour(temporal, tmp_path):
    class FakePhase:
        def __init__(self, config=None, state_manager=None):
            pass

        def execute(self, iteration):
            raise RuntimeError("synthetic phase failure")

    runner = _runner(temporal, tmp_path)
    runner.PHASE_MAP = {2: ("Failure", FakePhase)}
    result = runner.run_phase(2)
    assert result["success"] is False
    assert "synthetic phase failure" in result["error"]
    assert [v["stage"] for v in runner.temporal_snapshots] == ["BEFORE"]
    assert not list(tmp_path.glob("**/devoured*.json"))


def test_temporal_constructor_compatibility_fallback(temporal, tmp_path):
    class NeedsState:
        def __init__(self, config=None, state=None):
            if state is None:
                raise TypeError("state argument required")

        def execute(self, iteration):
            return {"phase": 1}

    runner = _runner(temporal, tmp_path, temporal=False, devour=False)
    runner.PHASE_MAP = {1: ("Fallback", NeedsState)}
    assert runner.run_phase(1)["success"] is True


def test_temporal_directory_count_and_missing_scope(temporal, tmp_path):
    runner = _runner(temporal, tmp_path)
    missing = tmp_path / "missing"
    assert runner._get_dir_size(missing) == 0
    assert runner._count_files(missing) == 0
    p = tmp_path / "sub"
    p.mkdir()
    (p / "a.json").write_bytes(b"abc")
    (p / "b.md").write_bytes(b"1234")
    assert runner._get_dir_size(tmp_path) == 7
    assert runner._count_files(tmp_path) == 2


def test_temporal_run_all_stops_at_first_red_and_saves_summary(
    temporal, tmp_path, monkeypatch
):
    runner = _runner(temporal, tmp_path)
    seen = []

    def fake_run(phase, iteration):
        seen.append(phase)
        return {
            "success": phase < 2,
            "phase": phase,
            "duration_seconds": float(phase + 1),
        }

    monkeypatch.setattr(runner, "run_phase", fake_run)
    summary = runner.run_all_phases(iteration=5)
    assert seen == [0, 1, 2]
    assert summary["total_phases"] == 3
    assert summary["failed_phases"] == 1
    assert summary["total_duration"] == 6.0
    saved = tmp_path / "temporal_execution_iteration_5.json"
    assert json.loads(saved.read_text())["failed_phases"] == 1


def test_temporal_cli_no_selection_refuses_implicit_work(temporal, monkeypatch, capsys):
    class FakeRunner:
        def __init__(self, **kwargs):
            pass

    monkeypatch.setattr(temporal, "TemporalPhaseRunner", FakeRunner)
    monkeypatch.setattr(sys, "argv", ["temporal_phase_runner.py"])
    assert temporal.main() == 1
    assert "usage:" in capsys.readouterr().out.lower()


def test_temporal_cli_phase_failure_is_nonzero(temporal, monkeypatch):
    class FakeRunner:
        def __init__(self, **kwargs):
            pass

        def run_phase(self, phase, iteration, task):
            return {"success": False}

    monkeypatch.setattr(temporal, "TemporalPhaseRunner", FakeRunner)
    monkeypatch.setattr(sys, "argv", ["runner", "--phase", "2", "--no-dow"])
    assert temporal.main() == 1


def test_dow_missing_target_is_error_without_dispatch(dow, tmp_path, monkeypatch):
    executor = dow.DOWIntegrationExecutor()
    monkeypatch.setattr(
        executor,
        "_run_agent",
        lambda *args: pytest.fail("forbidden dispatch"),
    )
    result = executor.execute_pipeline(1, str(tmp_path / "missing"))
    assert result["status"] == "error"
    assert result["error"] == "Target directory not found"
    assert executor.results == []


def test_dow_six_required_stages_success_only_when_each_succeeds(
    dow, tmp_path, monkeypatch
):
    executor = dow.DOWIntegrationExecutor()
    observed = []

    def mark(name, *args):
        observed.append(name)
        return {"status": "success", "agent": name}

    monkeypatch.setattr(executor, "_run_agent", mark)
    monkeypatch.setattr(
        executor,
        "_run_convergence",
        lambda *a: mark("convergence"),
    )
    monkeypatch.setattr(executor, "_run_ranking", lambda *a: mark("ranking"))
    monkeypatch.setattr(executor, "_run_validation", lambda *a: mark("validation"))
    result = executor.execute_pipeline(2, str(tmp_path))
    assert result["status"] == "success"
    assert result["required_stages"] == result["successful_stages"] == 6
    assert observed == [
        "dow_metadata_injector",
        "dow_recursive_hooks_injector",
        "convergence",
        "dow_knowledge_extractor",
        "ranking",
        "validation",
    ]


@pytest.mark.parametrize("fail_stage", [1, 2, 3, 4, 5, 6])
def test_dow_failure_stops_exactly_at_first_red(dow, tmp_path, monkeypatch, fail_stage):
    executor = dow.DOWIntegrationExecutor()
    index = 0

    def stage(*args, **kwargs):
        nonlocal index
        index += 1
        return {
            "status": (
                "blocked_missing_parent_mechanic" if index == fail_stage else "success"
            ),
            "reason": "missing parent",
        }

    for name in ("_run_agent", "_run_convergence", "_run_ranking", "_run_validation"):
        monkeypatch.setattr(executor, name, stage)
    result = executor.execute_pipeline(1, str(tmp_path))
    assert result["status"] == "error"
    assert result["stage"] == fail_stage
    assert len(result["results"]) == fail_stage
    assert "missing parent" in result["reason"]
    assert "BLOCKED" in result["summary"]


def test_dow_missing_mechanic_never_returns_success(dow, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    executor = dow.DOWIntegrationExecutor()
    result = executor._run_agent("absent_agent", ["--target", "."])
    assert result["status"] == "blocked_missing_parent_mechanic"
    assert "not found" in result["reason"]


def test_dow_convergence_previous_iteration_is_optional(dow, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    executor = dow.DOWIntegrationExecutor()
    calls = []
    monkeypatch.setattr(
        executor,
        "_run_agent",
        lambda name, args: (calls.append(args), {"status": "success"})[1],
    )
    executor._run_convergence(2, str(tmp_path))
    assert "--previous" not in calls[-1]
    previous = tmp_path / "DMAIC_V3_OUTPUT" / "iteration_1"
    previous.mkdir(parents=True)
    executor._run_convergence(2, str(tmp_path))
    assert "--previous" in calls[-1]


def test_dow_missing_and_stub_ranking_are_blocked(dow, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    executor = dow.DOWIntegrationExecutor()
    assert executor._run_ranking(str(tmp_path))["status"] == (
        "blocked_missing_parent_mechanic"
    )
    path = (
        tmp_path / "DMAIC_V3/local_mcp/agents/recursive_self_ranking_v2.3_OPTIMIZED.py"
    )
    path.parent.mkdir(parents=True)
    path.write_text("STUB - Needs implementation\n", encoding="utf-8")
    assert (
        executor._run_ranking(str(tmp_path))["status"] == "blocked_stub_parent_mechanic"
    )
    path.write_text("print('synthetic only')\n", encoding="utf-8")
    monkeypatch.setattr(
        executor,
        "_run_script",
        lambda *args, **kwargs: {"status": "success"},
    )
    assert executor._run_ranking(str(tmp_path))["status"] == "success"


def test_dow_missing_validation_and_local_fallback(dow, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    executor = dow.DOWIntegrationExecutor()
    missing = executor._run_validation(str(tmp_path))
    assert missing["status"] == "blocked_missing_parent_mechanic"
    target = tmp_path / "local_mcp/agents/smoke_test_runner_ULTRA_OPTIMIZED.py"
    target.parent.mkdir(parents=True)
    target.write_text("# synthetic fixture\n")
    monkeypatch.setattr(
        executor,
        "_run_script",
        lambda *args, **kwargs: {"status": "success", "agent": "smoke_test"},
    )
    assert executor._run_validation(str(tmp_path))["status"] == "success"


@pytest.mark.parametrize(
    ("result", "status"),
    [
        (SimpleNamespace(returncode=0, stdout="ok", stderr=""), "success"),
        (SimpleNamespace(returncode=9, stdout="", stderr="failure"), "error"),
    ],
)
def test_dow_subprocess_exit_contract_is_preserved(
    dow, tmp_path, monkeypatch, result, status
):
    executor = dow.DOWIntegrationExecutor()
    monkeypatch.setattr(dow.subprocess, "run", lambda *a, **kw: result)
    observed = executor._run_script("fake", tmp_path / "fake.py", [], 1)
    assert observed["status"] == status
    if status == "error":
        assert observed["return_code"] == 9


@pytest.mark.parametrize("fault_name", ["timeout", "offline"])
def test_dow_subprocess_exception_never_false_green(
    dow, tmp_path, monkeypatch, fault_name
):
    executor = dow.DOWIntegrationExecutor()
    fault = (
        dow.subprocess.TimeoutExpired("fake", 1)
        if fault_name == "timeout"
        else OSError("offline")
    )

    def deny(*args, **kwargs):
        raise fault

    monkeypatch.setattr(dow.subprocess, "run", deny)
    result = executor._run_script("fake", tmp_path / "fake.py", [], 1)
    assert result["status"] == "error"
    assert "Timeout" in result["error"] or "offline" in result["error"]


def test_dow_cli_failure_is_nonzero_and_local_only(dow, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    class Fake:
        def execute_pipeline(self, iteration, target_dir):
            return {"status": "error", "stage": 2, "reason": "blocked"}

    monkeypatch.setattr(dow, "DOWIntegrationExecutor", Fake)
    monkeypatch.setattr(sys, "argv", ["dow", "--iteration", "4"])
    with pytest.raises(SystemExit) as exc:
        dow.main()
    assert exc.value.code == 1
    receipt = tmp_path / "dow_integration_results_iteration_4.json"
    assert json.loads(receipt.read_text())["status"] == "error"
