"""Behaviour tests for run_comprehensive_deployment.py (subprocess is faked)."""

import json
import runpy
import types

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

mod = load("run_comprehensive_deployment.py", name="abn_run_comprehensive_deployment")

PHASE_SCRIPTS = [
    "run_cicd_integration.py",
    "run_full_dmaic_pipeline_v2_with_agents.py",
    "run_phase4_phase5.py",
    "run_direct_improvements.py",
]


class _Result:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _FakeRun:
    """Records shell commands and answers them from a prefix table."""

    def __init__(self, table=None, default=None):
        self.table = table or {}
        self.default = default or _Result(1, "", "unknown command")
        self.calls = []

    def __call__(self, cmd, **kwargs):
        self.calls.append((cmd, kwargs))
        for prefix, answer in self.table.items():
            if cmd.startswith(prefix):
                if isinstance(answer, BaseException):
                    raise answer
                if isinstance(answer, list):
                    return answer.pop(0)
                return answer
        return self.default


class _Sleeper:
    def __init__(self):
        self.calls = []

    def sleep(self, seconds):
        self.calls.append(seconds)


@pytest.fixture
def orch(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sleeper = _Sleeper()
    monkeypatch.setattr(mod, "time", types.SimpleNamespace(sleep=sleeper.sleep))
    o = mod.DeploymentOrchestrator()
    o.sleeper = sleeper
    return o


def _fake(monkeypatch, table=None, default=None):
    fake = _FakeRun(table, default)
    monkeypatch.setattr(mod.subprocess, "run", fake)
    return fake


def _abacus(tmp_path, scripts=()):
    folder = tmp_path / "ABACUS-v031"
    folder.mkdir(exist_ok=True)
    for name in scripts:
        (folder / name).write_bytes(b"print('x')\n")
    return folder


def _rankings(tmp_path, payload):
    folder = _abacus(tmp_path)
    (folder / "artifact_rankings.json").write_bytes(payload)


def _commands(fake):
    return [cmd for cmd, _ in fake.calls]


def test_init_has_empty_result_sections(orch):
    assert set(orch.results) == {
        "git_integration",
        "sprint_5",
        "dmaic_phases",
        "mcp_iteration",
        "cicd_pipeline",
        "self_improvement",
    }
    assert all(v == {} for v in orch.results.values())


def test_log_known_and_unknown_levels(orch, capsys):
    orch.log("hello")
    orch.log("done", "SUCCESS")
    orch.log("odd", "WEIRD")
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].endswith("hello")
    assert "✅ done" in lines[1]
    assert lines[2].endswith("]    odd")


def test_run_command_success_captures_output(orch, monkeypatch):
    fake = _fake(monkeypatch, {"echo": _Result(0, "out", "err")})
    res = orch.run_command("echo hi", cwd="here")
    assert res == {"success": True, "stdout": "out", "stderr": "err", "returncode": 0}
    cmd, kwargs = fake.calls[0]
    assert cmd == "echo hi"
    assert kwargs["cwd"] == "here"
    assert kwargs["timeout"] == 300
    assert kwargs["capture_output"] is True


def test_run_command_without_capture_blanks_output(orch, monkeypatch):
    _fake(monkeypatch, {}, _Result(3, "ignored", "ignored"))
    res = orch.run_command("x", capture=False)
    assert res == {"success": False, "stdout": "", "stderr": "", "returncode": 3}


def test_run_command_timeout(orch, monkeypatch):
    _fake(monkeypatch, {"slow": mod.subprocess.TimeoutExpired("slow", 300)})
    assert orch.run_command("slow") == {"success": False, "error": "Command timeout"}


def test_run_command_other_exception(orch, monkeypatch):
    _fake(monkeypatch, {"boom": OSError("no shell")})
    assert orch.run_command("boom") == {"success": False, "error": "no shell"}


def test_step_1_records_git_state_with_remote(orch, monkeypatch, capsys):
    _fake(
        monkeypatch,
        {
            "git status": _Result(0, " 7\n"),
            "git remote -v": _Result(0, "origin\thttps://x (fetch)\n"),
            "git branch": _Result(0, "main\n"),
        },
    )
    assert orch.step_1_git_integration() is True
    git = orch.results["git_integration"]
    assert git == {
        "modified_files": 7,
        "has_remote": True,
        "branch": "main",
        "status": "completed",
    }
    assert "Remote repository configured" in capsys.readouterr().out


def test_step_1_without_remote(orch, monkeypatch, capsys):
    _fake(
        monkeypatch,
        {"git remote -v": _Result(0, "")},
        _Result(1),
    )
    assert orch.step_1_git_integration() is True
    git = orch.results["git_integration"]
    assert git == {"has_remote": False, "status": "completed"}
    assert "No remote repository found" in capsys.readouterr().out


def test_step_1_non_numeric_count_raises(orch, monkeypatch):
    _fake(monkeypatch, {"git status": _Result(0, "many")})
    with pytest.raises(ValueError):
        orch.step_1_git_integration()


def test_step_2_skips_without_sprint_file(orch, monkeypatch):
    fake = _fake(monkeypatch)
    assert orch.step_2_sprint_5_execution() is False
    assert orch.results["sprint_5"] == {"status": "skipped"}
    assert fake.calls == []


def _sprint_file(tmp_path):
    (tmp_path / "DOW").mkdir()
    (tmp_path / "DOW" / "sprints.yaml").write_bytes(b"sprints: []\n")


def test_step_2_success(orch, tmp_path, monkeypatch):
    _sprint_file(tmp_path)
    fake = _fake(monkeypatch, {"python dmaic": _Result(0)})
    assert orch.step_2_sprint_5_execution() is True
    assert orch.results["sprint_5"] == {"status": "completed", "tasks_executed": 5}
    cmd, kwargs = fake.calls[0]
    assert "--sprint 5" in cmd
    assert kwargs["capture_output"] is False


def test_step_2_failure(orch, tmp_path, monkeypatch):
    _sprint_file(tmp_path)
    _fake(monkeypatch, {}, _Result(1))
    assert orch.step_2_sprint_5_execution() is False
    assert orch.results["sprint_5"] == {"status": "failed"}


def test_step_3_no_scripts_is_failed(orch, monkeypatch, capsys):
    fake = _fake(monkeypatch)
    assert orch.step_3_dmaic_phase_0_to_9() is False
    assert orch.results["dmaic_phases"] == {
        "completed": 0,
        "total": 4,
        "status": "failed",
    }
    assert fake.calls == []
    assert capsys.readouterr().out.count("Script not found") == 4


def test_step_3_mixed_results(orch, tmp_path, monkeypatch):
    _abacus(tmp_path, PHASE_SCRIPTS[:3])
    fake = _fake(
        monkeypatch,
        {
            "python run_cicd": _Result(0),
            "python run_full": _Result(1),
            "python run_phase4": _Result(0),
        },
    )
    assert orch.step_3_dmaic_phase_0_to_9() is True
    assert orch.results["dmaic_phases"] == {
        "completed": 2,
        "total": 4,
        "status": "completed",
    }
    assert len(fake.calls) == 3
    assert all(kw["cwd"] == "ABACUS-v031" for _, kw in fake.calls)


def test_step_4_all_iterations_commit_and_sleep(orch, monkeypatch):
    fake = _fake(monkeypatch, {"python run_direct": _Result(0)}, _Result(0))
    assert orch.step_4_mcp_orchestration() is True
    assert orch.results["mcp_iteration"] == {
        "completed": 3,
        "total": 3,
        "status": "completed",
    }
    commits = [c for c in _commands(fake) if c.startswith("git add -A")]
    assert len(commits) == 3
    assert "Iteration 3" in commits[-1]
    assert orch.sleeper.calls == [2, 2]


def test_step_4_stops_after_first_failure(orch, monkeypatch):
    fake = _fake(
        monkeypatch,
        {"python run_direct": [_Result(0), _Result(1)]},
        _Result(0),
    )
    assert orch.step_4_mcp_orchestration() is True
    assert orch.results["mcp_iteration"]["completed"] == 1
    runs = [c for c in _commands(fake) if c.startswith("python")]
    assert len(runs) == 2
    assert orch.sleeper.calls == [2]


def test_step_4_immediate_failure_is_failed(orch, monkeypatch):
    _fake(monkeypatch, {}, _Result(1))
    assert orch.step_4_mcp_orchestration() is False
    assert orch.results["mcp_iteration"]["status"] == "failed"
    assert orch.sleeper.calls == []


def test_step_5_missing_file_is_skipped(orch):
    assert orch.step_5_self_improvement() is False
    assert orch.results["self_improvement"] == {"status": "skipped"}


def test_step_5_low_score_triggers_improvement(orch, tmp_path, monkeypatch, capsys):
    payload = [
        {"metrics": {"overall_score": 0.2}},
        {"metrics": {"overall_score": 0.4}},
        {"other": 1},
    ]
    _rankings(tmp_path, json.dumps(payload).encode())
    fake = _fake(monkeypatch, {"python run_direct": _Result(0)})
    assert orch.step_5_self_improvement() is True
    si = orch.results["self_improvement"]
    assert si["avg_score"] == pytest.approx(0.2)
    assert si["total_artifacts"] == 3
    assert si["status"] == "completed"
    assert len(fake.calls) == 1
    assert "Additional improvement completed" in capsys.readouterr().out


def test_step_5_low_score_improvement_failure(orch, tmp_path, monkeypatch, capsys):
    _rankings(tmp_path, b'[{"metrics": {"overall_score": 0.1}}]')
    _fake(monkeypatch, {}, _Result(1))
    assert orch.step_5_self_improvement() is True
    assert "Additional improvement completed" not in capsys.readouterr().out


def test_step_5_high_score_achieves_target(orch, tmp_path, monkeypatch, capsys):
    _rankings(tmp_path, b'[{"metrics": {"overall_score": 0.9}}]')
    fake = _fake(monkeypatch)
    assert orch.step_5_self_improvement() is True
    assert orch.results["self_improvement"]["avg_score"] == pytest.approx(0.9)
    assert fake.calls == []
    assert "Quality target achieved" in capsys.readouterr().out


def test_step_5_empty_list_is_skipped(orch, tmp_path):
    _rankings(tmp_path, b"[]")
    assert orch.step_5_self_improvement() is False
    assert orch.results["self_improvement"] == {"status": "skipped"}


def test_step_5_invalid_json_is_logged(orch, tmp_path, capsys):
    _rankings(tmp_path, b"{bad")
    assert orch.step_5_self_improvement() is False
    assert "Error analyzing rankings" in capsys.readouterr().out
    assert orch.results["self_improvement"] == {"status": "skipped"}


def test_step_6_configs_and_remote(orch, tmp_path, monkeypatch):
    (tmp_path / ".pre-commit-config.yaml").write_bytes(b"repos: []\n")
    _abacus(tmp_path)
    (tmp_path / "ABACUS-v031" / ".pre-commit-config.yaml").write_bytes(b"x\n")
    _fake(monkeypatch, {"git remote get-url": _Result(0, "https://example/r.git\n")})
    assert orch.step_6_cicd_validation() is True
    ci = orch.results["cicd_pipeline"]
    assert ci["configs_found"] == 2
    assert ci["configs"] == [
        ".pre-commit-config.yaml",
        "ABACUS-v031/.pre-commit-config.yaml",
    ]
    assert ci["status"] == "validated"
    assert ci["remote_url"] == "https://example/r.git"
    assert ci["ready_to_push"] is True


def test_step_6_nothing_configured(orch, monkeypatch):
    _fake(monkeypatch, {}, _Result(2))
    assert orch.step_6_cicd_validation() is True
    ci = orch.results["cicd_pipeline"]
    assert ci == {
        "configs_found": 0,
        "configs": [],
        "status": "not_configured",
        "ready_to_push": False,
    }


def test_generate_report_minimal(orch, tmp_path, capsys):
    orch.generate_report()
    out = capsys.readouterr().out
    assert "COMPREHENSIVE DEPLOYMENT REPORT" in out
    assert "Git Integration:      N/A" in out
    assert "DMAIC Phases:         0/0" in out
    assert "QUALITY METRICS" not in out
    assert "GIT STATUS" not in out
    assert "READY FOR DEPLOYMENT" not in out
    data = json.loads((tmp_path / "deployment_report.json").read_bytes())
    assert data["results"] == orch.results
    assert data["duration_seconds"] >= 0


def test_generate_report_full(orch, tmp_path, capsys):
    orch.results["self_improvement"].update(avg_score=0.75, total_artifacts=4)
    orch.results["git_integration"].update(branch="dev", has_remote=True)
    orch.results["cicd_pipeline"].update(
        ready_to_push=True, remote_url="https://r", configs_found=3
    )
    orch.generate_report()
    out = capsys.readouterr().out
    assert "Average Score:     0.750" in out
    assert "Total Artifacts:   4" in out
    assert "Branch:            dev" in out
    assert "Modified Files:    0" in out
    assert "Remote:            Yes" in out
    assert "Remote URL:        https://r" in out
    assert "CI/CD Configs:     3 found" in out


def test_generate_report_branch_without_remote(orch, capsys):
    orch.results["git_integration"]["branch"] = "dev"
    orch.generate_report()
    assert "Remote:            No" in capsys.readouterr().out


def test_run_happy_path_returns_zero(orch, tmp_path, monkeypatch, capsys):
    _fake(
        monkeypatch,
        {
            "git status": _Result(0, "0\n"),
            "git remote -v": _Result(0, "origin x\n"),
            "git branch": _Result(0, "main\n"),
        },
        _Result(1),
    )
    assert orch.run() == 0
    assert "DEPLOYMENT ORCHESTRATION COMPLETE" in capsys.readouterr().out
    assert (tmp_path / "deployment_report.json").is_file()


def test_run_exception_returns_one(orch, tmp_path, monkeypatch, capsys):
    _fake(monkeypatch, {"git status": _Result(0, "lots")})
    assert orch.run() == 1
    assert "Deployment failed" in capsys.readouterr().out
    assert not (tmp_path / "deployment_report.json").exists()


def test_run_keyboard_interrupt_returns_one(orch, monkeypatch, capsys):
    def interrupt():
        raise KeyboardInterrupt

    monkeypatch.setattr(orch, "step_1_git_integration", interrupt)
    assert orch.run() == 1
    assert "interrupted by user" in capsys.readouterr().out


def test_main_block_exits_with_run_code(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("subprocess.run", _FakeRun({}, _Result(1)))

    with pytest.raises(SystemExit) as exc:
        runpy.run_path(
            str(REPO_ROOT / "run_comprehensive_deployment.py"), run_name="__main__"
        )

    assert exc.value.code == 0
    assert (tmp_path / "deployment_report.json").is_file()
