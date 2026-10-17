"""Behavioral C3 coverage for the operational full-pipeline runtime."""

import json
from types import SimpleNamespace

import DMAIC_V3.full_pipeline_orchestrator as orchestrator_module
from DMAIC_V3.full_pipeline_orchestrator import FullPipelineOrchestrator


class DummyDetector:
    def __init__(self):
        self.started = 0
        self.stopped = 0

    def start(self):
        self.started += 1

    def stop(self):
        self.stopped += 1

    def get_summary(self):
        return {
            "total": 3,
            "added": 1,
            "modified": 1,
            "deleted": 1,
            "timestamp": "2026-10-16T08:30:00",
        }


class DummyPlanner:
    def __init__(self):
        self.calls = []

    def scan_actual_state(self, path):
        self.calls.append(("scan", str(path)))

    def determine_current_state(self):
        self.calls.append(("state", None))

    def calculate_possible_next(self):
        self.calls.append(("next", None))

    def save_snapshot(self, iteration):
        self.calls.append(("save", iteration))


class Phase:
    def __init__(self, *args, result=None, **kwargs):
        self.result = result if result is not None else {"phase": "ok"}

    def execute(self, iteration):
        result = self.result
        if callable(result):
            return result(iteration)
        return result


def _orchestrator():
    obj = object.__new__(FullPipelineOrchestrator)
    obj.config = SimpleNamespace()
    obj.state_mgr = SimpleNamespace()
    obj.planning_tracker = DummyPlanner()
    obj.bg_change_detector = DummyDetector()
    obj.enable_idempotency_flag = False
    obj.enable_git_commits = False
    obj.verbose = False
    obj.debug_port = None
    obj.execution_log = []
    obj.statistics = {
        "phases": {},
        "agents": {},
        "orchestration": {
            "total_phases": 0,
            "successful_phases": 0,
            "failed_phases": 0,
            "total_duration_seconds": 0,
        },
    }
    return obj


def _patch_phases(monkeypatch, failing=None):
    names = [
        "Phase0Init",
        "Phase1Define",
        "Phase2Measure",
        "Phase3Analyze",
        "Phase4Improve",
        "Phase5Control",
        "Phase6Knowledge",
        "Phase7ActionTracking",
        "Phase8TODOManagement",
        "Phase9DocumentationGeneration",
    ]
    for name in names:
        if name == failing:
            monkeypatch.setattr(
                orchestrator_module,
                name,
                lambda *args, **kwargs: Phase(result=(False, {"phase": "failed"})),
            )
        else:
            monkeypatch.setattr(orchestrator_module, name, Phase)


def test_full_pipeline_success_runs_all_phases_and_finalizes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _patch_phases(monkeypatch)
    orch = _orchestrator()

    assert orch.execute_full_pipeline(iteration=4) is True
    assert orch.bg_change_detector.started == 1
    assert orch.bg_change_detector.stopped == 1
    assert orch.statistics["orchestration"]["total_phases"] == 10
    assert orch.statistics["orchestration"]["successful_phases"] == 10
    assert orch.statistics["orchestration"]["failed_phases"] == 0
    assert orch.planning_tracker.calls == [
        ("scan", "DMAIC_V3_OUTPUT"),
        ("state", None),
        ("next", None),
        ("save", 4),
    ]

    summary = tmp_path / "DMAIC_V3_OUTPUT" / "iteration_4" / "EXECUTION_SUMMARY.md"
    stats = tmp_path / "DMAIC_V3_OUTPUT" / "iteration_4" / "orchestration_statistics.json"
    assert "Status:** SUCCESS" in summary.read_text(encoding="utf-8")
    payload = json.loads(stats.read_text(encoding="utf-8"))
    assert payload["orchestration"]["total_phases"] == 10


def test_core_phase_failure_stops_pipeline_but_detector_always_finalizes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _patch_phases(monkeypatch, failing="Phase2Measure")
    orch = _orchestrator()

    assert orch.execute_full_pipeline(iteration=2) is False
    assert orch.bg_change_detector.started == 1
    assert orch.bg_change_detector.stopped == 1
    assert orch.statistics["orchestration"]["total_phases"] == 3
    assert orch.statistics["orchestration"]["successful_phases"] == 2
    assert orch.statistics["orchestration"]["failed_phases"] == 1
    assert orch.planning_tracker.calls == []


def test_phase_tracking_handles_dict_false_and_crash_without_false_green():
    orch = _orchestrator()

    ok, result = orch._execute_phase_with_tracking(Phase(result={"phase": "define"}), "Define", 1)
    assert ok is True
    assert result["phase"] == "define"

    ok, result = orch._execute_phase_with_tracking(Phase(result={"not_phase": True}), "Malformed", 1)
    assert ok is False
    assert result == {"not_phase": True}

    class Crash:
        def execute(self, iteration):
            raise RuntimeError("phase crash")

    ok, result = orch._execute_phase_with_tracking(Crash(), "Crash", 1)
    assert ok is False
    assert result == {"error": "phase crash"}
    assert orch.statistics["orchestration"]["failed_phases"] == 2


def test_reports_statistics_and_git_commit_paths(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    orch = _orchestrator()
    orch.execution_log = [
        {
            "phase": "phase6_knowledge",
            "iteration": 7,
            "success": True,
            "duration_seconds": 1.25,
            "timestamp": "2026-10-16T08:30:00",
        }
    ]
    orch.statistics["orchestration"].update(
        {
            "total_phases": 1,
            "successful_phases": 1,
            "failed_phases": 0,
            "total_duration_seconds": 1.25,
        }
    )

    orch._generate_execution_summary(7, ["phase6_knowledge", "missing"], 1.25, True)
    orch._save_statistics(7)

    report = tmp_path / "knowledge.md"
    orch._generate_human_report(
        {
            "iteration": 7,
            "duration_seconds": 1.25,
            "canonical_books_count": 3,
            "recursive_hooks_registered": 2,
            "maturity_score": 88,
        },
        report,
    )
    text = report.read_text(encoding="utf-8")
    assert "Books Referenced:** 3" in text
    assert "Hooks Registered:** 2" in text
    assert "88/100" in text

    calls = []
    monkeypatch.setattr(
        orchestrator_module.subprocess,
        "run",
        lambda args, check=False: calls.append((args, check)),
    )
    orch._git_commit(7)
    assert [call[0][1] for call in calls] == ["add", "commit"]

    monkeypatch.setattr(
        orchestrator_module.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("git unavailable")),
    )
    orch._git_commit(8)
    assert "Commit failed: git unavailable" in capsys.readouterr().out
