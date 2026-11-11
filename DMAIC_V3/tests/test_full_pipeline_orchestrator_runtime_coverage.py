"""Behavioral C3 coverage for the operational full-pipeline runtime."""

import json
import re
import shlex
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

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
    stats = (
        tmp_path / "DMAIC_V3_OUTPUT" / "iteration_4" / "orchestration_statistics.json"
    )
    assert "Status:** SUCCESS" in summary.read_text(encoding="utf-8")
    payload = json.loads(stats.read_text(encoding="utf-8"))
    assert payload["orchestration"]["total_phases"] == 10


def test_core_phase_failure_stops_pipeline_but_detector_always_finalizes(
    tmp_path, monkeypatch
):
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

    ok, result = orch._execute_phase_with_tracking(
        Phase(result={"phase": "define"}), "Define", 1
    )
    assert ok is True
    assert result["phase"] == "define"

    ok, result = orch._execute_phase_with_tracking(
        Phase(result={"not_phase": True}), "Malformed", 1
    )
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


# --- ABACUS_EXECUTION_BACKLOG P1-3: ``--phase`` runs exactly one phase ---


def test_phase_plan_matches_cli_choices_in_order():
    orch = _orchestrator()
    plan = orch._phase_plan()

    assert [row[0] for row in plan] == list(orchestrator_module.PHASE_CHOICES)
    assert len({row[1] for row in plan}) == len(plan)
    assert [row[0] for row in plan if row[4]] == [0, 1, 2, 3, 4, 5]


def test_noncritical_phase_failure_still_completes_full_pipeline(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _patch_phases(monkeypatch, failing="Phase7ActionTracking")
    orch = _orchestrator()

    assert orch.execute_full_pipeline(iteration=1) is True
    assert orch.statistics["orchestration"]["total_phases"] == 10
    assert orch.statistics["orchestration"]["failed_phases"] == 1


def test_single_phase_runs_only_the_requested_phase(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _patch_phases(monkeypatch)
    built = []

    class Analyze(Phase):
        def __init__(self, *args, **kwargs):
            built.append("Phase3Analyze")
            super().__init__(result={"phase": "analyze"})

    monkeypatch.setattr(orchestrator_module, "Phase3Analyze", Analyze)
    orch = _orchestrator()

    assert orch.execute_single_phase(3, iteration=5) is True
    assert built == ["Phase3Analyze"]
    assert orch.statistics["orchestration"]["total_phases"] == 1
    assert [entry["phase"] for entry in orch.execution_log] == ["Phase 3: Analyze"]
    assert orch.bg_change_detector.started == 0
    assert orch.planning_tracker.calls == []

    iteration_dir = tmp_path / "DMAIC_V3_OUTPUT" / "iteration_5"
    receipt = json.loads(
        (iteration_dir / "single_phase" / "phase3_analyze.json").read_text(
            encoding="utf-8"
        )
    )
    assert receipt["mode"] == "single_phase"
    assert (receipt["phase_number"], receipt["success"]) == (3, True)
    assert receipt["error"] is None
    assert not (iteration_dir / "EXECUTION_SUMMARY.md").exists()
    assert not (iteration_dir / "orchestration_statistics.json").exists()


def test_single_phase_failure_fails_even_for_noncritical_phase(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _patch_phases(monkeypatch, failing="Phase7ActionTracking")
    orch = _orchestrator()

    assert orch.execute_single_phase(7, iteration=1) is False
    receipt = json.loads(
        (
            tmp_path
            / "DMAIC_V3_OUTPUT"
            / "iteration_1"
            / "single_phase"
            / "phase7_action_tracking.json"
        ).read_text(encoding="utf-8")
    )
    assert receipt["success"] is False


def test_single_phase_construction_error_is_a_recorded_failure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _patch_phases(monkeypatch)

    def broken(*args, **kwargs):
        raise RuntimeError("cannot build phase 9")

    monkeypatch.setattr(orchestrator_module, "Phase9DocumentationGeneration", broken)
    orch = _orchestrator()

    assert orch.execute_single_phase(9, iteration=2) is False
    receipt = json.loads(
        (
            tmp_path
            / "DMAIC_V3_OUTPUT"
            / "iteration_2"
            / "single_phase"
            / "phase9_documentation_generation.json"
        ).read_text(encoding="utf-8")
    )
    assert receipt["success"] is False
    assert receipt["error"] == "cannot build phase 9"


def test_single_phase_rejects_unknown_phase_number():
    orch = _orchestrator()
    with pytest.raises(ValueError, match="Unknown phase 10"):
        orch.execute_single_phase(10)


class _RecordingOrchestrator:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.calls = []
        _RecordingOrchestrator.instances.append(self)

    def execute_single_phase(self, phase, iteration=1):
        self.calls.append(("single", phase, iteration))
        return True

    def execute_full_pipeline(self, iteration=1):
        self.calls.append(("full", iteration))
        return False


def test_cli_phase_flag_dispatches_single_phase(monkeypatch):
    _RecordingOrchestrator.instances = []
    monkeypatch.setattr(
        orchestrator_module, "FullPipelineOrchestrator", _RecordingOrchestrator
    )

    with pytest.raises(SystemExit) as exit_info:
        orchestrator_module.main(["--phase", "4", "--iteration", "3", "--no-git"])
    assert exit_info.value.code == 0
    (single,) = _RecordingOrchestrator.instances
    assert single.calls == [("single", 4, 3)]
    assert single.kwargs["enable_git_commits"] is False

    with pytest.raises(SystemExit) as exit_info:
        orchestrator_module.main(["--iteration", "2"])
    assert exit_info.value.code == 1
    assert _RecordingOrchestrator.instances[-1].calls == [("full", 2)]


def test_cli_rejects_out_of_range_phase(capsys):
    with pytest.raises(SystemExit) as exit_info:
        orchestrator_module.build_parser().parse_args(["--phase", "10"])
    assert exit_info.value.code == 2
    assert "invalid choice" in capsys.readouterr().err


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = "DMAIC_V3/full_pipeline_orchestrator.py"
# A python command line that runs the script (not, e.g., a Markdown link to it).
_INVOCATION = re.compile(
    r"\bpython[\d.]*\s+(?:-\S+\s+)*" + re.escape(_SCRIPT) + r"(?P<rest>.*)$"
)
_SHELL_STOP = {"|", "||", "&&", ";", ">", ">>", "2>&1", "&"}


def _workflow_invocations():
    """Yield (workflow, step, argv) for every workflow step that runs the script."""
    for path in sorted((_REPO_ROOT / ".github" / "workflows").glob("*.y*ml")):
        text = path.read_text(encoding="utf-8")
        if _SCRIPT not in text:
            continue
        doc = yaml.safe_load(text)
        for job in (doc.get("jobs") or {}).values():
            for step in job.get("steps") or []:
                run = step.get("run") or ""
                for line in run.replace("\\\n", " ").splitlines():
                    match = _INVOCATION.search(line)
                    if not match:
                        continue
                    tokens = shlex.split(match.group("rest"))
                    argv = []
                    for token in tokens:
                        if token in _SHELL_STOP:
                            break
                        argv.append(token)
                    yield path.name, step, argv


def test_every_workflow_invocation_is_accepted_by_the_parser():
    invocations = list(_workflow_invocations())
    assert any(name == "dmaic-phase-execution.yml" for name, _, _ in invocations)

    for name, _step, argv in invocations:
        resolved = [token.replace("$PHASE", "0") for token in argv]
        assert not any("${{" in token for token in resolved), name
        orchestrator_module.build_parser().parse_args(resolved)


def test_phase_workflow_offers_exactly_the_cli_phases_through_env():
    path = _REPO_ROOT / ".github" / "workflows" / "dmaic-phase-execution.yml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    phase_input = doc["on"]["workflow_dispatch"]["inputs"]["phase"]
    assert phase_input["type"] == "choice"
    assert phase_input["options"] == [str(n) for n in orchestrator_module.PHASE_CHOICES]

    (step,) = [
        step
        for name, step, _ in _workflow_invocations()
        if name == "dmaic-phase-execution.yml"
    ]
    assert step["env"]["PHASE"] == "${{ github.event.inputs.phase }}"
    for option in phase_input["options"]:
        args = orchestrator_module.build_parser().parse_args(
            ["--phase", option, "--no-git"]
        )
        assert args.phase == int(option)
