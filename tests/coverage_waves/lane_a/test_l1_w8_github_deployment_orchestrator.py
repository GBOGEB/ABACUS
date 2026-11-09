"""Behaviour tests for ABACUS_V21_DEPLOYMENT_PACKAGE/github_deployment_orchestrator.py.

Every git subprocess call is faked; cwd is pinned to tmp_path.
"""

import json
import types

import pytest

from tests.coverage_waves.lane_a._load import load

gdo = load("ABACUS_V21_DEPLOYMENT_PACKAGE/github_deployment_orchestrator.py")


@pytest.fixture
def orch(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ABACUS_V21_DEPLOYMENT_PACKAGE").mkdir()
    return gdo.GitHubDeploymentOrchestrator()


def _fake(behaviour, calls):
    """behaviour maps command[0:2] tuples to a returncode int or an exception."""

    def fake(cmd, **kwargs):
        calls.append(list(cmd))
        outcome = behaviour.get(tuple(cmd[:2]), 0)
        if isinstance(outcome, BaseException):
            raise outcome
        if kwargs.get("check") and outcome != 0:
            raise gdo.subprocess.CalledProcessError(outcome, cmd)
        return types.SimpleNamespace(returncode=outcome, stdout="", stderr="")

    return fake


def _steps(o):
    return [(s["step"], s["status"]) for s in o.results["steps"]]


def test_init(orch, tmp_path):
    assert orch.project_root == tmp_path
    assert orch.results["status"] == "in_progress"
    assert orch.results["steps"] == []


def test_log_step_with_and_without_details(orch, capsys):
    orch.log_step("A", "success", "detail")
    orch.log_step("B", "warning")
    out = capsys.readouterr().out
    assert "[SUCCESS] A" in out
    assert "detail" in out
    assert "[WARNING] B" in out
    assert orch.results["steps"][1]["details"] == ""


def test_check_git_status_ok(orch, monkeypatch):
    calls = []
    monkeypatch.setattr("subprocess.run", _fake({}, calls))
    assert orch.check_git_status() is True
    assert calls == [["git", "status"]]
    assert _steps(orch) == [("Git Status Check", "success")]


def test_check_git_status_not_repo(orch, monkeypatch):
    monkeypatch.setattr("subprocess.run", _fake({("git", "status"): 128}, []))
    assert orch.check_git_status() is False
    assert _steps(orch) == [("Git Status Check", "warning")]


def test_initialize_existing_repo(orch, monkeypatch):
    calls = []
    monkeypatch.setattr("subprocess.run", _fake({}, calls))
    orch.initialize_git_repo()
    assert ["git", "init"] not in calls
    assert ["git", "config", "user.name", "ABACUS Team"] in calls
    assert ["git", "config", "user.email", "abacus@example.com"] in calls


def test_initialize_new_repo(orch, monkeypatch):
    calls = []
    monkeypatch.setattr("subprocess.run", _fake({("git", "status"): 128}, calls))
    orch.initialize_git_repo()
    assert ["git", "init"] in calls
    assert ("Git Initialization", "success") in _steps(orch)


def test_initialize_git_missing_logs_error(orch, monkeypatch):
    exc = FileNotFoundError("git")
    monkeypatch.setattr("subprocess.run", _fake({("git", "status"): exc}, []))
    orch.initialize_git_repo()
    assert _steps(orch) == [("Git Initialization", "error")]


def test_create_structure_present(orch):
    orch.create_deployment_structure()
    assert orch.results["steps"][-1]["details"] == "Created 1 deployment files"


def test_create_structure_absent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    o = gdo.GitHubDeploymentOrchestrator()
    o.create_deployment_structure()
    assert o.results["steps"][-1]["details"] == "Created 0 deployment files"


def test_create_structure_error(orch, monkeypatch):
    class Boom:
        def exists(self):
            raise RuntimeError("disk")

    orch.deployment_package = Boom()
    orch.create_deployment_structure()
    assert orch.results["steps"][-1]["status"] == "error"
    assert orch.results["steps"][-1]["details"] == "disk"


def test_stage_files_success(orch, monkeypatch):
    calls = []
    monkeypatch.setattr("subprocess.run", _fake({}, calls))
    orch.stage_files_for_commit()
    assert [c[2] for c in calls] == [
        "abacus_v21_*.py",
        "ABACUS_V21_*.md",
        "ABACUS_V21_DEPLOYMENT_PACKAGE/",
        ".gitignore",
    ]
    assert _steps(orch) == [("Stage Files", "success")]


def test_stage_files_oserror_per_pattern(orch, monkeypatch):
    monkeypatch.setattr("subprocess.run", _fake({("git", "add"): OSError("x")}, []))
    orch.stage_files_for_commit()
    steps = _steps(orch)
    assert steps.count(("Stage Files", "warning")) == 4
    assert steps[-1] == ("Stage Files", "success")


def test_stage_files_unexpected_error(orch, monkeypatch):
    monkeypatch.setattr(
        "subprocess.run", _fake({("git", "add"): ValueError("bad")}, [])
    )
    orch.stage_files_for_commit()
    assert _steps(orch) == [("Stage Files", "error")]


def test_commit_success(orch, monkeypatch):
    calls = []
    monkeypatch.setattr("subprocess.run", _fake({}, calls))
    orch.create_commit()
    assert calls[0][:3] == ["git", "commit", "-m"]
    assert calls[0][3].startswith("ABACUS v2.1 Deployment Package - ")
    step = orch.results["steps"][-1]
    assert step["status"] == "success"
    assert step["details"] == calls[0][3]


def test_commit_nothing_to_commit(orch, monkeypatch):
    monkeypatch.setattr("subprocess.run", _fake({("git", "commit"): 1}, []))
    orch.create_commit()
    assert _steps(orch) == [("Git Commit", "info")]


def test_commit_error(orch, monkeypatch):
    exc = FileNotFoundError("git")
    monkeypatch.setattr("subprocess.run", _fake({("git", "commit"): exc}, []))
    orch.create_commit()
    assert _steps(orch) == [("Git Commit", "error")]


def test_instructions_written(orch, tmp_path):
    orch.prepare_github_push_instructions()
    text = (tmp_path / "GITHUB_DEPLOYMENT_INSTRUCTIONS.txt").read_text(encoding="utf-8")
    assert "GITHUB DEPLOYMENT INSTRUCTIONS" in text
    assert "git push -u origin main" in text
    assert _steps(orch) == [("GitHub Instructions", "success")]


def test_report_summary_counts(orch):
    orch.log_step("a", "success")
    orch.log_step("b", "warning")
    orch.log_step("c", "error")
    orch.log_step("d", "info")
    orch.generate_deployment_report()
    path = orch.deployment_package / "DEPLOYMENT_REPORT.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["status"] == "completed"
    assert data["summary"] == {
        "total_steps": 4,
        "successful": 1,
        "warnings": 1,
        "errors": 1,
    }


def test_run_end_to_end(orch, monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr("subprocess.run", _fake({}, calls))
    orch.run()
    assert (tmp_path / "GITHUB_DEPLOYMENT_INSTRUCTIONS.txt").exists()
    report = json.loads(
        (orch.deployment_package / "DEPLOYMENT_REPORT.json").read_text(encoding="utf-8")
    )
    assert report["status"] == "completed"
    assert report["summary"]["errors"] == 0
    names = [s["step"] for s in report["steps"]]
    assert names == [
        "Git Status Check",
        "Deployment Structure",
        "Stage Files",
        "Git Commit",
        "GitHub Instructions",
    ]
    assert ["git", "status"] in calls
