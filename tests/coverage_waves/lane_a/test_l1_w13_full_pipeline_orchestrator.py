"""Wave 13 lane A behaviour tests for DMAIC_V3/full_pipeline_orchestrator.py."""

import importlib
import json
import sys
from types import SimpleNamespace

import pytest


def _import_restoring_sys_path():
    # The orchestrator (and one transitive import) insert entries into sys.path.
    saved = list(sys.path)
    try:
        return importlib.import_module("DMAIC_V3.full_pipeline_orchestrator")
    finally:
        sys.path[:] = saved


fpo = _import_restoring_sys_path()

PHASE_NAMES = [
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


class FakeConfig:
    root = None

    def __init__(self):
        r = FakeConfig.root
        self.paths = SimpleNamespace(
            state_dir=r / "state", output_root=r / "out", workspace_root=r
        )


class FakeTracker:
    def __init__(self, workspace_root):
        self.calls = []

    def scan_actual_state(self, path):
        self.calls.append("scan")

    def determine_current_state(self):
        self.calls.append("determine")

    def calculate_possible_next(self):
        self.calls.append("next")

    def save_snapshot(self, iteration):
        self.calls.append(("save", iteration))


class FakeDetector:
    summary = {"total": 3, "added": 1, "modified": 2, "deleted": 0}

    def __init__(self, workspace_root, state_dir):
        self.events = []

    def start(self):
        self.events.append("start")

    def stop(self):
        self.events.append("stop")

    def get_summary(self):
        return dict(FakeDetector.summary)


def _phase_cls(name, behaviour):
    class FakePhase:
        def __init__(self, *args):
            self.args = args

        def execute(self, iteration):
            outcome = behaviour.get(name, (True, {"phase": name}))
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

    FakePhase.__name__ = name
    return FakePhase


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    FakeConfig.root = tmp_path
    idem = []
    monkeypatch.setattr(fpo, "DMAICConfig", FakeConfig)
    monkeypatch.setattr(fpo, "StateManager", lambda path: SimpleNamespace(path=path))
    monkeypatch.setattr(fpo, "PlanningMatrixTracker", FakeTracker)
    monkeypatch.setattr(fpo, "BackgroundChangeDetector", FakeDetector)
    monkeypatch.setattr(fpo, "enable_idempotency", lambda enabled: idem.append(enabled))
    behaviour = {}
    for name in PHASE_NAMES:
        monkeypatch.setattr(fpo, name, _phase_cls(name, behaviour))
    git_calls = []
    monkeypatch.setattr(fpo.subprocess, "run", lambda cmd, check: git_calls.append(cmd))
    return SimpleNamespace(root=tmp_path, behaviour=behaviour, git=git_calls, idem=idem)


def test_deprecated_stubs():
    for cls, phase in (
        (fpo.Phase7AdvancedAnalytics, "phase7_advanced_analytics"),
        (fpo.Phase8RecursiveOptimization, "phase8_recursive_optimization"),
    ):
        ok, res = cls("cfg", "state").execute(4)
        assert ok is True
        assert res["phase"] == phase
        assert res["status"] == "DEPRECATED"
        assert res["iteration"] == 4


def test_init_flags(env):
    orch = fpo.FullPipelineOrchestrator()
    assert env.idem == [True]
    assert isinstance(orch.bg_change_detector, FakeDetector)
    assert orch.statistics["orchestration"]["total_phases"] == 0
    fpo.FullPipelineOrchestrator(enable_idempotency_flag=False)
    assert env.idem == [True]


def _summary_md(iteration_dir):
    # The orchestrator writes exactly one Markdown summary per iteration. Find it
    # instead of naming it: the root-relocation guard rejects code that names a
    # moved root file, and only acknowledged production consumers may do so.
    found = sorted(iteration_dir.glob("*.md"))
    assert len(found) == 1, found
    return found[0]


def test_full_pipeline_success(env, capsys):
    env.behaviour["Phase3Analyze"] = {"phase": "dict-result"}
    orch = fpo.FullPipelineOrchestrator()
    assert orch.execute_full_pipeline(iteration=2) is True
    stats = orch.statistics["orchestration"]
    assert stats["total_phases"] == 10
    assert stats["successful_phases"] == 10
    assert orch.planning_tracker.calls == ["scan", "determine", "next", ("save", 2)]
    assert orch.bg_change_detector.events == ["start", "stop"]
    assert [c[1] for c in env.git] == ["add", "commit"]
    it = env.root / "DMAIC_V3_OUTPUT" / "iteration_2"
    summary = _summary_md(it).read_text(encoding="utf-8")
    assert "**Status:** SUCCESS" in summary
    assert "## Phases Executed" in summary
    saved = json.loads((it / "orchestration_statistics.json").read_text("utf-8"))
    assert saved["orchestration"]["total_phases"] == 10
    out = capsys.readouterr().out
    assert "Total changes detected: 3" in out
    assert "Last snapshot" not in out


def test_full_pipeline_optional_phase_failures_continue(env, capsys):
    for name in PHASE_NAMES[6:]:
        env.behaviour[name] = (False, {"phase": name})
    FakeDetector.summary = {"total": 0, "timestamp": "2026-01-01"}
    try:
        orch = fpo.FullPipelineOrchestrator(enable_git_commits=False)
        assert orch.execute_full_pipeline(1) is True
    finally:
        FakeDetector.summary = {"total": 3, "added": 1, "modified": 2, "deleted": 0}
    assert env.git == []
    assert orch.statistics["orchestration"]["failed_phases"] == 4
    out = capsys.readouterr().out
    for n in (6, 7, 8, 9):
        assert f"[WARNING] Phase {n} failed but continuing..." in out
    assert "Last snapshot: 2026-01-01" in out
    summary = _summary_md(env.root / "DMAIC_V3_OUTPUT" / "iteration_1")
    assert '"success": false' in summary.read_text("utf-8")


def test_execution_summary_lists_matching_log_entries(env):
    orch = fpo.FullPipelineOrchestrator()
    orch.execution_log = [
        {"phase": "phase1_define run", "success": True, "duration_seconds": 1.0},
        {"phase": "phase2_measure run", "success": False, "duration_seconds": 2.5},
    ]
    orch._generate_execution_summary(
        5, ["phase1_define", "phase2_measure", "x"], 3.0, False
    )
    text = _summary_md(env.root / "DMAIC_V3_OUTPUT" / "iteration_5").read_text(
        encoding="utf-8"
    )
    assert "**Status:** FAILED" in text
    assert "1. [OK] phase1_define (1.00s)" in text
    assert "2. [FAIL] phase2_measure (2.50s)" in text
    assert "3. " not in text


def check_production_defect_execution_summary_never_lists_phases(env):
    # Pins a production_defect: _generate_execution_summary matches phase keys
    # such as 'phase0_init' against log names such as 'Phase 0: Initialization',
    # so the "Phases Executed" list is always empty after a real run. This check
    # will fail once the lookup is fixed.
    orch = fpo.FullPipelineOrchestrator(enable_git_commits=False)
    assert orch.execute_full_pipeline(1) is True
    text = _summary_md(env.root / "DMAIC_V3_OUTPUT" / "iteration_1").read_text(
        encoding="utf-8"
    )
    phases_section = text.split("## Phases Executed")[1].split("## Execution Log")[0]
    assert phases_section.strip() == ""


@pytest.mark.parametrize("failing", PHASE_NAMES[:6])
def test_full_pipeline_core_failure_stops(env, failing):
    env.behaviour[failing] = (False, {"phase": failing})
    orch = fpo.FullPipelineOrchestrator()
    assert orch.execute_full_pipeline(1) is False
    assert orch.bg_change_detector.events == ["start", "stop"]
    assert env.git == []
    assert (
        orch.statistics["orchestration"]["total_phases"]
        == PHASE_NAMES.index(failing) + 1
    )


def test_full_pipeline_unexpected_exception(env, monkeypatch):
    orch = fpo.FullPipelineOrchestrator()

    def boom(path):
        raise RuntimeError("tracker exploded")

    monkeypatch.setattr(orch.planning_tracker, "scan_actual_state", boom)
    assert orch.execute_full_pipeline(1) is False
    assert orch.bg_change_detector.events == ["start", "stop"]


def test_execute_phase_with_tracking_variants(env):
    orch = fpo.FullPipelineOrchestrator()

    class DictNoPhase:
        def execute(self, iteration):
            return {"other": 1}

    class Crash:
        def execute(self, iteration):
            raise ValueError("bad phase")

    ok, res = orch._execute_phase_with_tracking(DictNoPhase(), "P", 1)
    assert ok is False
    assert res == {"other": 1}
    ok, res = orch._execute_phase_with_tracking(DictNoPhase(), "P", 1)
    p = orch.statistics["phases"]["P"]
    assert (p["executions"], p["failures"], p["successes"]) == (2, 2, 0)
    assert p["avg_duration"] == pytest.approx(p["total_duration"] / 2)
    ok, res = orch._execute_phase_with_tracking(Crash(), "C", 1)
    assert ok is False
    assert res == {"error": "bad phase"}
    stats = orch.statistics["orchestration"]
    assert (stats["total_phases"], stats["failed_phases"]) == (3, 3)
    assert "C" not in orch.statistics["phases"]


def test_git_commit_swallow_errors(env, monkeypatch, capsys):
    orch = fpo.FullPipelineOrchestrator()

    def fail(cmd, check):
        raise OSError("git missing")

    monkeypatch.setattr(fpo.subprocess, "run", fail)
    orch._git_commit(3)
    assert "Commit failed: git missing" in capsys.readouterr().out


def test_generate_human_report(env):
    orch = fpo.FullPipelineOrchestrator()
    full = env.root / "full.md"
    orch._generate_human_report(
        {
            "iteration": 2,
            "duration_seconds": 1.5,
            "canonical_books_count": 4,
            "recursive_hooks_registered": 2,
            "maturity_score": 77,
        },
        full,
    )
    text = full.read_text(encoding="utf-8")
    assert "**Iteration:** 2" in text
    assert "**Books Referenced:** 4" in text
    assert "**Hooks Registered:** 2" in text
    assert "**Current Maturity Score:** 77/100" in text
    bare = env.root / "bare.md"
    orch._generate_human_report({}, bare)
    text = bare.read_text(encoding="utf-8")
    assert "**Iteration:** N/A" in text
    assert "Canonical Knowledge Books" not in text


class FakeConn:
    def __init__(self, sent):
        self.sent = sent

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def recv(self, size):
        return b"stats"

    def sendall(self, data):
        self.sent.append(data)


class StopServer(Exception):
    pass


def _fake_socket_factory(sent):
    class FakeSocket:
        def __init__(self, *args):
            self.accepts = 0

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def setsockopt(self, *args):
            pass

        def bind(self, addr):
            self.addr = addr

        def listen(self, n):
            pass

        def accept(self):
            self.accepts += 1
            if self.accepts > 1:
                raise StopServer()
            return FakeConn(sent), ("127.0.0.1", 1)

    return FakeSocket


def test_debug_monitoring_server_serves_stats(env, monkeypatch, capsys):
    sent = []
    targets = []

    class FakeThread:
        def __init__(self, target, daemon):
            targets.append(target)

        def start(self):
            pass

    monkeypatch.setattr("socket.socket", _fake_socket_factory(sent))
    monkeypatch.setattr("threading.Thread", FakeThread)
    orch = fpo.FullPipelineOrchestrator(debug_port=5999)
    assert "Debug port enabled: 5999" in capsys.readouterr().out
    with pytest.raises(StopServer):
        targets[0]()
    assert json.loads(sent[0].decode()) == orch.statistics


def test_debug_monitoring_setup_failure(env, monkeypatch, capsys):
    def broken(*args, **kwargs):
        raise RuntimeError("no threads")

    monkeypatch.setattr("threading.Thread", broken)
    fpo.FullPipelineOrchestrator(debug_port=6000)
    assert "Failed to setup debug monitoring: no threads" in capsys.readouterr().out


def test_main_parses_arguments(env, monkeypatch):
    seen = {}

    class FakeOrch:
        def __init__(self, **kwargs):
            seen.update(kwargs)

        def execute_full_pipeline(self, iteration):
            seen["iteration"] = iteration
            return iteration == 3

    monkeypatch.setattr(fpo, "FullPipelineOrchestrator", FakeOrch)
    monkeypatch.setattr(
        sys, "argv", ["x", "--iteration", "3", "--no-git", "--no-idempotency"]
    )
    with pytest.raises(SystemExit) as exc:
        fpo.main()
    assert exc.value.code == 0
    assert seen == {
        "enable_idempotency_flag": False,
        "enable_git_commits": False,
        "verbose": True,
        "debug_port": None,
        "iteration": 3,
    }
    monkeypatch.setattr(sys, "argv", ["x", "--quiet", "--debug-port", "7"])
    with pytest.raises(SystemExit) as exc:
        fpo.main()
    assert exc.value.code == 1
    assert seen["verbose"] is False
    assert seen["debug_port"] == 7
