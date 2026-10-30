"""Behaviour tests for ABACUS_V21_DEPLOYMENT_PACKAGE/local_deployment_runner.py.

Every docker / python subprocess call is faked; cwd is pinned to tmp_path.
"""

import json
import os
import types

import pytest

from tests.coverage_waves.lane_a._load import load

ldr = load("ABACUS_V21_DEPLOYMENT_PACKAGE/local_deployment_runner.py")


@pytest.fixture
def runner(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ABACUS_V21_DEPLOYMENT_PACKAGE").mkdir()
    return ldr.LocalDeploymentRunner()


def _fake(behaviour, calls):
    """behaviour maps command[0:2] tuples to a returncode int or an exception."""

    def fake(cmd, **kwargs):
        calls.append((list(cmd), kwargs))
        outcome = behaviour.get(tuple(cmd[:2]), 0)
        if isinstance(outcome, BaseException):
            raise outcome
        if kwargs.get("check") and outcome != 0:
            raise ldr.subprocess.CalledProcessError(outcome, cmd, stderr="err-text")
        return types.SimpleNamespace(returncode=outcome, stdout=" v1.2 \n", stderr="")

    return fake


def _statuses(r):
    return [(e["status"], e["message"]) for e in r.results]


def test_init_paths(runner, tmp_path):
    assert runner.project_root == tmp_path
    assert runner.deployment_package == tmp_path / "ABACUS_V21_DEPLOYMENT_PACKAGE"
    assert runner.results == []


def test_log_appends_entry(runner, capsys):
    runner.log("hello", "WARN")
    entry = runner.results[-1]
    assert entry["status"] == "WARN"
    assert entry["message"] == "hello"
    assert len(entry["timestamp"]) == 8
    assert "[WARN] hello" in capsys.readouterr().out
    runner.log("default")
    assert runner.results[-1]["status"] == "INFO"


def test_check_docker_found(runner, monkeypatch):
    calls = []
    monkeypatch.setattr("subprocess.run", _fake({}, calls))
    assert runner.check_docker() is True
    assert calls[0][0] == ["docker", "--version"]
    assert ("SUCCESS", "Docker found: v1.2") in _statuses(runner)


@pytest.mark.parametrize(
    "outcome", [1, FileNotFoundError("docker")], ids=["calledprocess", "missing"]
)
def test_check_docker_missing(runner, monkeypatch, outcome):
    monkeypatch.setattr("subprocess.run", _fake({("docker", "--version"): outcome}, []))
    assert runner.check_docker() is False
    assert runner.results[-1]["status"] == "WARNING"


def test_check_compose_found(runner, monkeypatch):
    monkeypatch.setattr("subprocess.run", _fake({}, []))
    assert runner.check_docker_compose() is True
    assert ("SUCCESS", "Docker Compose found: v1.2") in _statuses(runner)


@pytest.mark.parametrize(
    "outcome", [3, FileNotFoundError("dc")], ids=["calledprocess", "missing"]
)
def test_check_compose_missing(runner, monkeypatch, outcome):
    monkeypatch.setattr(
        "subprocess.run", _fake({("docker-compose", "--version"): outcome}, [])
    )
    assert runner.check_docker_compose() is False
    assert ("WARNING", "Docker Compose not found") in _statuses(runner)


def test_build_image_success_restores_cwd(runner, monkeypatch, tmp_path):
    seen = []

    def fake(cmd, **kwargs):
        seen.append(os.getcwd())
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake)
    runner.build_docker_image()
    assert seen and seen[0].endswith("ABACUS_V21_DEPLOYMENT_PACKAGE")
    assert ("SUCCESS", "Docker image built successfully") in _statuses(runner)
    assert os.getcwd() == str(tmp_path)


def test_build_image_failure(runner, monkeypatch, tmp_path):
    monkeypatch.setattr("subprocess.run", _fake({("docker", "build"): 1}, []))
    runner.build_docker_image()
    assert ("ERROR", "Docker build failed: err-text") in _statuses(runner)
    assert os.getcwd() == str(tmp_path)


def test_start_compose_success(runner, monkeypatch):
    calls = []
    monkeypatch.setattr("subprocess.run", _fake({}, calls))
    runner.start_docker_compose()
    assert calls[0][0] == ["docker-compose", "up", "-d"]
    msgs = [m for _, m in _statuses(runner)]
    assert "Docker Compose services started" in msgs
    assert any("9090" in m for m in msgs)


def test_start_compose_failure(runner, monkeypatch):
    monkeypatch.setattr("subprocess.run", _fake({("docker-compose", "up"): 2}, []))
    runner.start_docker_compose()
    assert ("ERROR", "Docker Compose failed: err-text") in _statuses(runner)


def test_run_local_success(runner, monkeypatch):
    calls = []
    monkeypatch.setattr("subprocess.run", _fake({}, calls))
    runner.run_local_deployment()
    assert calls[0][0][1] == "abacus_v21_session_tuple_analyzer.py"
    assert calls[0][1]["timeout"] == 30
    assert runner.results[-1]["status"] == "SUCCESS"


def test_run_local_nonzero(runner, monkeypatch):
    monkeypatch.setattr(
        "subprocess.run",
        _fake({("python", "abacus_v21_session_tuple_analyzer.py"): 1}, []),
    )
    runner.run_local_deployment()
    assert runner.results[-1]["status"] == "WARNING"


def test_run_local_timeout(runner, monkeypatch):
    exc = ldr.subprocess.TimeoutExpired(cmd="python", timeout=30)
    monkeypatch.setattr(
        "subprocess.run",
        _fake({("python", "abacus_v21_session_tuple_analyzer.py"): exc}, []),
    )
    runner.run_local_deployment()
    assert runner.results[-1]["status"] == "INFO"
    assert "timeout" in runner.results[-1]["message"]


def test_run_local_other_error(runner, monkeypatch):
    exc = OSError("nope")
    monkeypatch.setattr(
        "subprocess.run",
        _fake({("python", "abacus_v21_session_tuple_analyzer.py"): exc}, []),
    )
    runner.run_local_deployment()
    assert ("ERROR", "Error running ABACUS: nope") in _statuses(runner)


def test_generate_report_writes_json(runner):
    runner.log("x")
    runner.generate_report()
    path = runner.deployment_package / "LOCAL_DEPLOYMENT_REPORT.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["deployment_type"] == "local"
    assert data["results"][0]["message"] == "x"
    assert runner.results[-1]["status"] == "SUCCESS"


def test_run_with_docker(runner, monkeypatch):
    calls = []
    monkeypatch.setattr("subprocess.run", _fake({}, calls))
    runner.run()
    cmds = [c[0] for c in calls]
    assert ["docker", "build", "-t", "abacus-v21:latest", "."] in cmds
    assert ["docker-compose", "up", "-d"] in cmds
    assert not any(c[0] == "python" for c in cmds)
    assert (runner.deployment_package / "LOCAL_DEPLOYMENT_REPORT.json").exists()


def test_run_without_docker(runner, monkeypatch):
    calls = []
    behaviour = {("docker", "--version"): FileNotFoundError("docker")}
    monkeypatch.setattr("subprocess.run", _fake(behaviour, calls))
    runner.run()
    cmds = [c[0] for c in calls]
    assert ["python", "abacus_v21_session_tuple_analyzer.py"] in cmds
    assert not any(c[:2] == ["docker", "build"] for c in cmds)
    assert ("INFO", "Docker not available - running Python directly") in _statuses(
        runner
    )
