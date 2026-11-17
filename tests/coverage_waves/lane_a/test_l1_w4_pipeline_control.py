"""Lane A wave 4: DMAIC_V3.pipeline_control (orchestrator, signals, time faked)."""

import signal
import types

import pytest

from DMAIC_V3 import pipeline_control as pc


class FakeOrchestrator:
    """Stands in for FullPipelineOrchestrator; outcome keyed by iteration."""

    outcomes = {}
    calls = []
    init_kwargs = []

    def __init__(self, **kwargs):
        FakeOrchestrator.init_kwargs.append(kwargs)

    def execute_full_pipeline(self, iteration):
        FakeOrchestrator.calls.append(iteration)
        outcome = FakeOrchestrator.outcomes.get(iteration, True)
        if isinstance(outcome, Exception):
            raise outcome
        if callable(outcome):
            return outcome()
        return outcome


@pytest.fixture
def env(monkeypatch):
    installed = []
    sleeps = []
    clock = iter(range(0, 1000, 2))
    monkeypatch.setattr(
        signal, "signal", lambda sig, handler: installed.append((sig, handler))
    )
    monkeypatch.setattr(pc, "FullPipelineOrchestrator", FakeOrchestrator)
    fake_time = types.SimpleNamespace(
        time=lambda: float(next(clock)), sleep=sleeps.append
    )
    monkeypatch.setattr(pc, "time", fake_time)
    FakeOrchestrator.outcomes = {}
    FakeOrchestrator.calls = []
    FakeOrchestrator.init_kwargs = []
    return types.SimpleNamespace(installed=installed, sleeps=sleeps)


def test_init_registers_sigint_and_sigterm(env):
    ctl = pc.PipelineController()
    assert ctl.orchestrator is None and ctl.stop_requested is False
    assert ctl.current_iteration == 0
    assert [s for s, _ in env.installed] == [signal.SIGINT, signal.SIGTERM]
    assert all(h == ctl._signal_handler for _, h in env.installed)


def test_signal_handler_requests_stop(env, capsys):
    ctl = pc.PipelineController()
    ctl._signal_handler(2, None)
    assert ctl.stop_requested is True
    assert "Received signal 2" in capsys.readouterr().out


@pytest.mark.parametrize("outcome,label", [(True, "SUCCESS"), (False, "FAILED")])
def test_run_single_iteration(env, capsys, outcome, label):
    FakeOrchestrator.outcomes = {4: outcome}
    ctl = pc.PipelineController()
    assert ctl.run_single_iteration(4) is outcome
    assert FakeOrchestrator.calls == [4]
    assert FakeOrchestrator.init_kwargs[0] == {
        "enable_idempotency_flag": True,
        "enable_git_commits": True,
        "verbose": True,
    }
    out = capsys.readouterr().out
    assert label in out and "Iteration 4 completed in 2.00s" in out


def test_run_single_iteration_rejects_zero(env):
    with pytest.raises(ValueError, match="iteration must be >= 1"):
        pc.PipelineController().run_single_iteration(0)


@pytest.mark.parametrize(
    "start,count,msg",
    [(0, 1, "start_iter must be >= 1"), (1, 0, "n_iterations must be >= 1")],
)
def test_run_n_validates_arguments(env, start, count, msg):
    with pytest.raises(ValueError, match=msg):
        pc.PipelineController().run_n_iterations_with_stops(start, count)


def test_run_n_continuous_with_pauses(env, capsys):
    FakeOrchestrator.outcomes = {6: False}
    ctl = pc.PipelineController()
    results = ctl.run_n_iterations_with_stops(5, 3)
    assert [r["iteration"] for r in results] == [5, 6, 7]
    assert [r["success"] for r in results] == [True, False, True]
    assert all(r["duration"] == 2.0 for r in results)
    assert env.sleeps == [3, 3]
    assert ctl.current_iteration == 7
    out = capsys.readouterr().out
    assert "CONTINUOUS" in out and "ITERATION 5 OF 7" in out
    assert "Successful: 2/3" in out and "Failed: 1/3" in out
    assert "Iteration 6: " in out


def test_run_n_stop_after_each_pauses_after_first(env, capsys):
    results = pc.PipelineController().run_n_iterations_with_stops(
        2, 3, stop_after_each=True
    )
    assert [r["iteration"] for r in results] == [2]
    assert env.sleeps == []
    out = capsys.readouterr().out
    assert "STOP AFTER EACH ITERATION" in out and "--resume 3" in out


def test_run_n_stop_after_each_single_iteration_runs_to_end(env):
    results = pc.PipelineController().run_n_iterations_with_stops(
        1, 1, stop_after_each=True
    )
    assert len(results) == 1 and env.sleeps == []


def test_run_n_stop_requested_before_first(env, capsys):
    ctl = pc.PipelineController()
    ctl.stop_requested = True
    assert ctl.run_n_iterations_with_stops(1, 2) == []
    assert FakeOrchestrator.calls == []
    assert "Stopping before iteration 1" in capsys.readouterr().out


def test_run_n_stop_requested_mid_run_skips_pause(env):
    ctl = pc.PipelineController()

    def succeed_then_stop():
        ctl.stop_requested = True
        return True

    FakeOrchestrator.outcomes = {1: succeed_then_stop}
    results = ctl.run_n_iterations_with_stops(1, 3)
    assert len(results) == 1 and env.sleeps == []


def test_run_n_crash_is_recorded_and_backs_off(env, capsys):
    FakeOrchestrator.outcomes = {1: RuntimeError("boom")}
    results = pc.PipelineController().run_n_iterations_with_stops(1, 2)
    assert results[0]["success"] is False and results[0]["error"] == "boom"
    assert "duration" not in results[0]
    assert results[1]["success"] is True
    assert env.sleeps == [3]
    captured = capsys.readouterr()
    assert "Iteration 1 crashed: boom" in captured.out
    assert "RuntimeError" in captured.err
    assert "Iteration 1: " in captured.out and "(0.00s)" in captured.out


def test_run_n_crash_on_last_iteration_no_pause(env):
    FakeOrchestrator.outcomes = {2: RuntimeError("late")}
    results = pc.PipelineController().run_n_iterations_with_stops(1, 2)
    assert results[-1]["error"] == "late"
    assert env.sleeps == [3]


def test_run_n_crash_with_stop_after_each_breaks(env, capsys):
    FakeOrchestrator.outcomes = {1: ValueError("x")}
    results = pc.PipelineController().run_n_iterations_with_stops(
        1, 3, stop_after_each=True
    )
    assert len(results) == 1 and FakeOrchestrator.calls == [1]
    capsys.readouterr()


def _run_main(monkeypatch, argv):
    monkeypatch.setattr(pc.sys, "argv", ["pipeline_control.py", *argv])
    with pytest.raises(SystemExit) as exc:
        pc.main()
    return exc.value.code


@pytest.mark.parametrize("outcome,code", [(True, 0), (False, 1)])
def test_main_single(env, monkeypatch, capsys, outcome, code):
    FakeOrchestrator.outcomes = {3: outcome}
    assert _run_main(monkeypatch, ["--single", "3"]) == code
    assert FakeOrchestrator.calls == [3]
    capsys.readouterr()


def test_main_run_all_success(env, monkeypatch, capsys):
    assert _run_main(monkeypatch, ["--run", "2"]) == 0
    assert FakeOrchestrator.calls == [1, 2]
    capsys.readouterr()


def test_main_run_with_stop_after_each_fails_exit(env, monkeypatch, capsys):
    assert _run_main(monkeypatch, ["--run", "2", "--stop-after-each"]) == 1
    assert FakeOrchestrator.calls == [1]
    capsys.readouterr()


def test_main_resume_uses_count(env, monkeypatch, capsys):
    assert _run_main(monkeypatch, ["--resume", "4", "--count", "2"]) == 0
    assert FakeOrchestrator.calls == [4, 5]
    FakeOrchestrator.calls = []
    FakeOrchestrator.outcomes = {5: False}
    assert _run_main(monkeypatch, ["--resume", "4", "--count", "2"]) == 1
    capsys.readouterr()


@pytest.mark.parametrize("outcome,code", [(True, 0), (False, 1)])
def test_main_default_runs_three(env, monkeypatch, capsys, outcome, code):
    FakeOrchestrator.outcomes = {2: outcome}
    assert _run_main(monkeypatch, []) == code
    assert FakeOrchestrator.calls == [1, 2, 3]
    assert "Running 3 iterations by default" in capsys.readouterr().out
