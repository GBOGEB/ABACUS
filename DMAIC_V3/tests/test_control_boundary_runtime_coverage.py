"""Behavioral C5 coverage for Git and pipeline control boundaries."""

import json
from types import SimpleNamespace

import pytest

import DMAIC_V3.integrations.git_manager as git_module
import DMAIC_V3.pipeline_control as pipeline_module
from DMAIC_V3.integrations.git_manager import GitManager
from DMAIC_V3.pipeline_control import PipelineController


def manager_without_probe(tmp_path, available=True):
    manager = object.__new__(GitManager)
    manager.workspace_root = tmp_path
    manager.git_available = available
    return manager


def test_run_git_honors_nonzero_return_when_check_false(tmp_path, monkeypatch):
    manager = manager_without_probe(tmp_path)

    monkeypatch.setattr(
        git_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=7, stdout="", stderr="fatal: bad revision"
        ),
    )

    ok, output = manager._run_git(["diff", "bad"], check=False)

    assert ok is False
    assert "bad revision" in output


def test_run_git_unavailable_and_exception_fail_closed(tmp_path, monkeypatch):
    manager = manager_without_probe(tmp_path, available=False)
    assert manager._run_git(["status"], check=False) == (False, "Git not available")

    manager.git_available = True
    monkeypatch.setattr(
        git_module.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("git missing")),
    )
    ok, output = manager._run_git(["status"], check=False)
    assert ok is False
    assert "git missing" in output


def test_git_availability_uses_native_exit_code(monkeypatch):
    manager = object.__new__(GitManager)

    monkeypatch.setattr(
        git_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0),
    )
    assert manager._check_git_available() is True

    monkeypatch.setattr(
        git_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1),
    )
    assert manager._check_git_available() is False


def test_commit_iteration_stages_existing_files_and_propagates_commit_failure(
    tmp_path, monkeypatch
):
    (tmp_path / "DMAIC_V3_OUTPUT").mkdir()
    (tmp_path / "planning_matrix.json").write_text("{}", encoding="utf-8")
    manager = manager_without_probe(tmp_path)
    calls = []

    def fake_run(args, check=True):
        calls.append((args, check))
        if args[0] == "commit":
            return False, "hook rejected commit"
        return True, ""

    monkeypatch.setattr(manager, "_run_git", fake_run)

    assert manager.commit_iteration(3, phase="measure") is False
    assert ["add", "DMAIC_V3_OUTPUT/"] in [call[0] for call in calls]
    assert ["add", "planning_matrix.json"] in [call[0] for call in calls]
    commit = next(args for args, _ in calls if args[0] == "commit")
    assert "Iteration 3 - measure complete" in commit[2]


def test_commit_nothing_to_commit_is_idempotent_success(tmp_path, monkeypatch):
    manager = manager_without_probe(tmp_path)
    monkeypatch.setattr(
        manager,
        "_run_git",
        lambda args, check=True: (False, "nothing to commit, working tree clean"),
    )
    assert manager.commit_iteration(1) is True


def test_tag_diff_changes_and_log_obey_failed_git_result(tmp_path, monkeypatch):
    manager = manager_without_probe(tmp_path)
    monkeypatch.setattr(manager, "_run_git", lambda *args, **kwargs: (False, "bad ref"))

    assert manager.create_baseline_tag(2) is False
    assert manager.generate_diff_report(1, 2) == {"error": "Diff failed: bad ref"}
    assert manager.get_changes_since_iteration(1) == []
    assert manager.get_iteration_log(1) == {"error": "Log failed: bad ref"}
    assert manager.list_baselines() == []


def test_git_report_and_history_parsing(tmp_path, monkeypatch):
    manager = manager_without_probe(tmp_path)
    responses = {
        "diff": (
            True,
            " a.py | 2 ++\n b.py | 3 ++-\n 2 files changed, 4 insertions(+), 1 deletion(-)\n",
        ),
        "log": (
            True,
            "abc|Alice|123|Iteration 4 | nested message\ndef|Bob|456|other\n",
        ),
        "tag": (True, "baseline-1\nbaseline-2\n"),
        "branch": (True, "feature/test\n"),
        "status": (True, ""),
    }

    def fake_run(args, check=True):
        if args[:2] == ["diff", "--stat"]:
            return responses["diff"]
        if args and args[0] == "log":
            return responses["log"]
        if args[:2] == ["tag", "-l"]:
            return responses["tag"]
        if args[:2] == ["rev-parse", "--abbrev-ref"]:
            return responses["branch"]
        if args[:2] == ["status", "--porcelain"]:
            return responses["status"]
        return True, ""

    monkeypatch.setattr(manager, "_run_git", fake_run)

    diff = manager.generate_diff_report(1, 2)
    assert [row["file"] for row in diff["files_changed"]] == ["a.py", "b.py"]
    assert "2 files changed" in diff["summary"]

    log = manager.get_iteration_log(4)
    assert log["commit_count"] == 2
    assert log["commits"][0]["message"] == "Iteration 4 | nested message"

    history = tmp_path / "history.json"
    manager.save_git_history(history)
    payload = json.loads(history.read_text(encoding="utf-8"))
    assert payload["total_commits"] == 2

    status = manager.get_status()
    assert status.branch == "feature/test"
    assert status.clean is True
    assert [row["tag"] for row in manager.list_baselines()] == [
        "baseline-1",
        "baseline-2",
    ]


def controller_without_real_signals(monkeypatch):
    registered = []
    monkeypatch.setattr(
        pipeline_module.signal,
        "signal",
        lambda sig, handler: registered.append((sig, handler)),
    )
    controller = PipelineController()
    return controller, registered


def test_pipeline_controller_registers_stop_signals_and_sets_stop(monkeypatch, capsys):
    controller, registered = controller_without_real_signals(monkeypatch)
    assert {sig for sig, _ in registered} == {
        pipeline_module.signal.SIGINT,
        pipeline_module.signal.SIGTERM,
    }

    controller._signal_handler(pipeline_module.signal.SIGINT, None)
    assert controller.stop_requested is True
    assert "stopping gracefully" in capsys.readouterr().out


def test_invalid_iteration_controls_fail_before_orchestration(monkeypatch):
    controller, _ = controller_without_real_signals(monkeypatch)

    with pytest.raises(ValueError, match="iteration"):
        controller.run_single_iteration(0)
    with pytest.raises(ValueError, match="start_iter"):
        controller.run_n_iterations_with_stops(0, 1)
    with pytest.raises(ValueError, match="n_iterations"):
        controller.run_n_iterations_with_stops(1, 0)


def test_single_iteration_returns_orchestrator_result(monkeypatch):
    controller, _ = controller_without_real_signals(monkeypatch)

    class FakeOrchestrator:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def execute_full_pipeline(self, iteration):
            return iteration == 2

    monkeypatch.setattr(pipeline_module, "FullPipelineOrchestrator", FakeOrchestrator)
    times = iter([10.0, 12.5])
    monkeypatch.setattr(pipeline_module.time, "time", lambda: next(times))

    assert controller.run_single_iteration(2) is True


def test_multi_iteration_stop_pause_and_crash_paths(monkeypatch, capsys):
    controller, _ = controller_without_real_signals(monkeypatch)
    sleeps = []

    class FakeOrchestrator:
        def __init__(self, **kwargs):
            pass

        def execute_full_pipeline(self, iteration):
            if iteration == 2:
                raise RuntimeError("boom")
            return iteration != 3

    monkeypatch.setattr(pipeline_module, "FullPipelineOrchestrator", FakeOrchestrator)
    monkeypatch.setattr(pipeline_module.time, "sleep", sleeps.append)
    monkeypatch.setattr(pipeline_module.time, "time", lambda: 100.0)

    results = controller.run_n_iterations_with_stops(1, 3, stop_after_each=False)
    assert [row["iteration"] for row in results] == [1, 2, 3]
    assert [row["success"] for row in results] == [True, False, False]
    assert results[1]["error"] == "boom"
    assert sleeps == [3, 3]
    assert "Iteration 2 crashed" in capsys.readouterr().out

    paused, _ = controller_without_real_signals(monkeypatch)
    results = paused.run_n_iterations_with_stops(5, 3, stop_after_each=True)
    assert len(results) == 1
    assert results[0]["iteration"] == 5

    stopped, _ = controller_without_real_signals(monkeypatch)
    stopped.stop_requested = True
    assert stopped.run_n_iterations_with_stops(4, 2) == []
