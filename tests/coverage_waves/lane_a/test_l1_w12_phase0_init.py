"""Wave 12 lane A behaviour tests for DMAIC_V3/phases/phase0_init.py."""

import json
from types import SimpleNamespace

import pytest

from DMAIC_V3.core import idempotency_wrapper
from DMAIC_V3.phases import phase0_init as p0

RAW_EXECUTE = p0.Phase0Init.execute.__wrapped__


class GitStub:
    """Replacement for subprocess.run that records calls."""

    def __init__(self, available=True, diff="", diff_error=None):
        self.available = available
        self.diff = diff
        self.diff_error = diff_error
        self.calls = []

    def __call__(self, cmd, **kwargs):
        self.calls.append((cmd, kwargs))
        if cmd[:2] == ["git", "--version"]:
            if not self.available:
                raise OSError("git missing")
            return SimpleNamespace(returncode=0, stdout="git version 2", stderr="")
        if self.diff_error is not None:
            raise self.diff_error
        return SimpleNamespace(returncode=0, stdout=self.diff, stderr="")


@pytest.fixture
def ws(tmp_path):
    return tmp_path


@pytest.fixture
def phase(ws, monkeypatch):
    paths = SimpleNamespace(
        workspace_root=ws, output_root=ws / "out", state_dir=ws / "state"
    )
    ph = p0.Phase0Init(SimpleNamespace(paths=paths), state_manager=object())
    monkeypatch.setattr(
        ph.agent_manager, "initialize_all_agents", lambda: {"analysis": {}}
    )
    calls = []

    def fake_enable(enabled=True, cache_dir=None):
        calls.append((enabled, cache_dir))

    monkeypatch.setattr(idempotency_wrapper, "enable_idempotency", fake_enable)
    ph.enable_calls = calls
    return ph


def test_check_git_true_and_false(phase, monkeypatch):
    monkeypatch.setattr(p0.subprocess, "run", GitStub(available=True))
    assert phase._check_git() is True
    monkeypatch.setattr(p0.subprocess, "run", GitStub(available=False))
    assert phase._check_git() is False


def test_check_dependencies_success_and_import_error(phase, monkeypatch):
    assert phase._check_dependencies() == {
        "pathlib": True,
        "json": True,
        "datetime": True,
        "typing": True,
    }
    real_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "typing":
            raise ImportError("gone")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    deps = phase._check_dependencies()
    assert deps["typing"] is False
    assert deps["json"] is True


def test_check_environment(phase, ws, monkeypatch, capsys):
    monkeypatch.setattr(p0.subprocess, "run", GitStub(available=False))
    env = phase._check_environment()
    assert env["workspace_exists"] is True
    assert env["output_dir_exists"] is False
    assert env["git_available"] is False
    assert env["workspace_root"] == str(ws)
    assert "Git: [FAIL]" in capsys.readouterr().out


def test_check_agent_present_and_absent(phase, ws):
    absent = phase._check_agent("analysis", "cryo_dm")
    assert absent["available"] is False
    assert absent["version"] == "unknown"
    assert absent["size"] == 0
    agents = ws / "local_mcp" / "agents"
    agents.mkdir(parents=True)
    (agents / "analysis_cryo_dm_v2.3_OPTIMIZED.py").write_bytes(b"x = 1\n")
    present = phase._check_agent("analysis", "cryo_dm")
    assert present == {
        "available": True,
        "path": present["path"],
        "version": "2.3.0",
        "size": 6,
    }


def test_initialize_agents_delegates(phase):
    assert phase._initialize_agents() == {"analysis": {}}


def test_setup_canonical_files(phase, ws):
    (ws / "README.md").write_bytes(b"hello")
    status = phase._setup_canonical_files()
    assert set(status) == set(phase.canonical_files)
    assert status["README"]["exists"] is True
    assert status["README"]["size"] == 5
    assert status["README"]["modified"]
    assert status["INDEX"] == {
        "path": "index.json",
        "exists": False,
        "size": 0,
        "modified": None,
    }


def test_detect_changes_without_git(phase, monkeypatch):
    monkeypatch.setattr(p0.subprocess, "run", GitStub(available=False))
    assert phase._detect_changes() == {
        "git_available": False,
        "modified_files": [],
        "modified_phases": [],
    }


def test_detect_changes_parses_diff(phase, ws, monkeypatch):
    diff = (
        "DMAIC_V3/phases/phase3_analyze.py\n"
        "  DMAIC_V3/phases/phase3_analyze.py  \n"
        "README.md\n"
        "\n"
        "DMAIC_V3/phases/phase0_init.py\n"
    )
    stub = GitStub(diff=diff)
    monkeypatch.setattr(p0.subprocess, "run", stub)
    res = phase._detect_changes()
    assert res["git_available"] is True
    assert res["change_count"] == 4
    assert res["modified_phases"] == ["phase3_analyze", "phase0_init"]
    assert stub.calls[-1][1]["cwd"] == ws


def test_detect_changes_no_phase_changes(phase, monkeypatch, capsys):
    monkeypatch.setattr(p0.subprocess, "run", GitStub(diff=""))
    res = phase._detect_changes()
    assert res["change_count"] == 0
    assert "Modified phases: None" in capsys.readouterr().out


def test_detect_changes_diff_failure(phase, monkeypatch):
    monkeypatch.setattr(
        p0.subprocess, "run", GitStub(diff_error=RuntimeError("bad revision"))
    )
    res = phase._detect_changes()
    assert res["git_available"] is True
    assert res["error"] == "bad revision"
    assert res["modified_files"] == []


@pytest.mark.parametrize("enable", [True, False])
def test_configure_idempotency(phase, ws, enable):
    res = phase._configure_idempotency(enable)
    assert res["enabled"] is enable
    assert res["algorithm"] == "sha256"
    assert phase.enable_calls == [(enable, ws / "state" / "cache")]


def test_integrate_time_engine(phase, ws):
    assert phase._integrate_time_engine()["v2_3_engine_exists"] is False
    engine = ws / "tools_v2.3"
    engine.mkdir()
    (engine / "time_tracking_engine_v2.3.py").write_text("x = 1\n")
    state = phase._integrate_time_engine()
    assert state["v2_3_engine_exists"] is True
    assert state["iteration_timer_initialized"] is True


def test_load_todo_matrix_variants(phase, ws):
    assert phase._load_todo_matrix()["todo_file_exists"] is False
    todo = ws / phase.canonical_files["TODO"]
    todo.write_text("phase1: []\nphase2: []\n", encoding="utf-8")
    m = phase._load_todo_matrix()
    assert m["loaded"] is True
    assert m["categories"] == ["phase1", "phase2"]
    todo.write_text("", encoding="utf-8")
    assert phase._load_todo_matrix()["categories"] == []
    todo.write_text("key: [unclosed\n", encoding="utf-8")
    bad = phase._load_todo_matrix()
    assert "error" in bad
    assert "loaded" not in bad


def test_bootstrap_ranking_system(phase, ws):
    state = phase._bootstrap_ranking_system()
    assert state["ready_for_phase1"] is False
    (ws / "ranking_engine.py").write_text("")
    (ws / phase.canonical_files["GLOBAL_RANKING"]).write_text("")
    rec = ws / "CRYO_LINAC_HANDOVER_v2.1.0_20251103_020746"
    rec.mkdir()
    (rec / "recursive_self_ranking_system.py").write_text("")
    state = phase._bootstrap_ranking_system()
    assert state["ready_for_phase1"] is True
    assert state["recursive_ranking_exists"] is True


def test_validate_output_structure(phase, ws):
    res = phase._validate_output_structure(iteration=2)
    it = ws / "out" / "iteration_2"
    names = sorted(p.name for p in it.iterdir())
    assert names == [
        "phase0_init",
        "phase1_define",
        "phase2_measure",
        "phase3_analyze",
        "phase4_improve",
        "phase5_control",
    ]
    assert res["phase_count"] == 6
    assert res["iteration_dir"] == str(it)


def test_execute_success_writes_results(phase, ws, monkeypatch, capsys):
    monkeypatch.setattr(
        p0.subprocess, "run", GitStub(diff="DMAIC_V3/phases/phase1_define.py\n")
    )
    (ws / "README.md").write_text("x")
    ok, res = RAW_EXECUTE(phase, iteration=3, enable_idempotency=False)
    assert ok is True
    assert res["phase"] == "INIT"
    assert res["iteration"] == 3
    assert res["changes"]["modified_phases"] == ["phase1_define"]
    assert res["idempotency"]["enabled"] is False
    out = ws / "out" / "iteration_3" / "phase0_init" / "phase0_init.json"
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["version"] == "3.3.0"
    text = capsys.readouterr().out
    assert "Canonical files checked: 1/10" in text
    assert "Changes detected: 1" in text
    assert "Idempotency: DISABLED" in text
    assert "Ranking system: NOT READY" in text
    assert "PHASE 0 PASSED" in text


def test_execute_success_ready_ranking_no_git(phase, ws, monkeypatch, capsys):
    monkeypatch.setattr(p0.subprocess, "run", GitStub(available=False))
    (ws / "ranking_engine.py").write_text("")
    (ws / phase.canonical_files["GLOBAL_RANKING"]).write_text("")
    ok, res = RAW_EXECUTE(phase)
    assert ok is True
    assert "change_count" not in res["changes"]
    text = capsys.readouterr().out
    assert "Changes detected: 0" in text
    assert "Idempotency: ENABLED" in text
    assert "Ranking system: READY" in text


def test_execute_failure_returns_error(phase, monkeypatch, capsys):
    def boom():
        raise RuntimeError("env exploded")

    monkeypatch.setattr(phase, "_check_environment", boom)
    ok, res = RAW_EXECUTE(phase, iteration=1)
    assert ok is False
    assert res == {"error": "env exploded"}
    assert "Phase 0 failed: env exploded" in capsys.readouterr().out
