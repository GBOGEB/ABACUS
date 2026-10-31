"""Lane A wave 14: DMAIC_V3.dow_integration_executor fail-closed stages, mocked runs."""

import os
import sys
from types import SimpleNamespace

import pytest

from DMAIC_V3 import dow_integration_executor as die

AGENTS = (
    "dow_metadata_injector",
    "dow_recursive_hooks_injector",
    "dow_convergence_calculator",
    "dow_knowledge_extractor",
)
RANKING = "recursive_self_ranking_v2.3_OPTIMIZED.py"
SMOKE = "smoke_test_runner_ULTRA_OPTIMIZED.py"


class FakeRun:
    def __init__(self, rc=0, stdout="ok", stderr=""):
        self.rc, self.stdout, self.stderr = rc, stdout, stderr
        self.calls = []

    def __call__(self, cmd, **kw):
        self.calls.append((cmd, kw))
        return SimpleNamespace(
            returncode=self.rc, stdout=self.stdout, stderr=self.stderr
        )


@pytest.fixture
def ws(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "target").mkdir()
    return tmp_path


def _install(root, ranking="print('rank')\n", smoke_local=False, agents=AGENTS):
    adir = root / "DMAIC_V3" / "local_mcp" / "agents"
    adir.mkdir(parents=True, exist_ok=True)
    for name in agents:
        (adir / f"{name}.py").write_text("x = 1\n", encoding="utf-8")
    if ranking is not None:
        (adir / RANKING).write_text(ranking, encoding="utf-8")
    if smoke_local:
        sdir = root / "local_mcp" / "agents"
        sdir.mkdir(parents=True)
        (sdir / SMOKE).write_text("x = 1\n", encoding="utf-8")


def test_missing_target(ws):
    res = die.DOWIntegrationExecutor().execute_pipeline(1, "nope")
    assert res == {
        "status": "error",
        "error": "Target directory not found",
        "target": "nope",
    }


def test_missing_first_agent_blocks(ws):
    res = die.DOWIntegrationExecutor().execute_pipeline(1, "target")
    assert res["status"] == "error"
    assert res["stage"] == 1
    assert res["reason"].startswith("Required parent mechanic not found")
    assert "[BLOCKED] Missing parent mechanic: 1" in res["summary"]


def test_full_success_with_previous_iteration(ws, monkeypatch):
    _install(ws, smoke_local=True)
    (ws / "DMAIC_V3_OUTPUT" / "iteration_1").mkdir(parents=True)
    fake = FakeRun()
    monkeypatch.setattr("subprocess.run", fake)
    monkeypatch.setenv("PYTHONPATH", "EXISTING")
    res = die.DOWIntegrationExecutor().execute_pipeline(2, "target")
    assert res["status"] == "success"
    assert res["successful_stages"] == 6
    assert len(fake.calls) == 6
    conv_cmd = fake.calls[2][0]
    assert "--previous" in conv_cmd
    assert fake.calls[4][0][-2:] == ["--output", "ranking.json"]
    assert fake.calls[5][1]["timeout"] == 180
    assert fake.calls[0][1]["env"]["PYTHONPATH"].split(os.pathsep)[-1] == "EXISTING"
    assert "6. Validation: success" in res["summary"]


def test_convergence_without_previous(ws, monkeypatch, capsys):
    _install(ws)
    fake = FakeRun()
    monkeypatch.setattr("subprocess.run", fake)
    monkeypatch.delenv("PYTHONPATH", raising=False)
    ex = die.DOWIntegrationExecutor()
    assert ex._run_convergence(3, "target")["status"] == "success"
    assert "--previous" not in fake.calls[0][0]
    assert "running convergence without --previous" in capsys.readouterr().out
    ex._run_convergence(0, "target")
    assert "--previous" not in fake.calls[1][0]


def test_stage5_missing_and_stub(ws, monkeypatch):
    _install(ws, ranking=None)
    monkeypatch.setattr("subprocess.run", FakeRun())
    res = die.DOWIntegrationExecutor().execute_pipeline(0, "target")
    assert res["stage"] == 5
    assert res["results"][-1]["status"] == "blocked_missing_parent_mechanic"
    _install(ws, ranking="VERSION = '0.0.0-stub'\n")
    res = die.DOWIntegrationExecutor().execute_pipeline(0, "target")
    assert res["stage"] == 5
    assert res["results"][-1]["status"] == "blocked_stub_parent_mechanic"


def test_stage6_validation_missing(ws, monkeypatch):
    _install(ws)
    monkeypatch.setattr("subprocess.run", FakeRun())
    res = die.DOWIntegrationExecutor().execute_pipeline(0, "target")
    assert res["stage"] == 6
    assert len(res["results"][-1]["searched_paths"]) == 2


def test_run_script_failures(ws, monkeypatch):
    ex = die.DOWIntegrationExecutor()
    path = ws / "agent.py"
    monkeypatch.setattr("subprocess.run", FakeRun(rc=2, stdout="", stderr="bad"))
    res = ex._run_script("a", path, [], timeout=1)
    assert (res["status"], res["error"], res["return_code"]) == ("error", "bad", 2)
    monkeypatch.setattr("subprocess.run", FakeRun(rc=3, stdout="", stderr=""))
    assert ex._run_script("a", path, [], timeout=1)["error"] == "return code 3"

    def timeout(cmd, **kw):
        raise die.subprocess.TimeoutExpired(cmd, 1)

    monkeypatch.setattr("subprocess.run", timeout)
    assert ex._run_script("a", path, [], timeout=1)["error"] == "Timeout"

    def oserr(cmd, **kw):
        raise OSError("no exec")

    monkeypatch.setattr("subprocess.run", oserr)
    assert ex._run_script("a", path, [], timeout=1)["error"] == "no exec"


def test_stage_error_reason_from_error(ws, monkeypatch):
    _install(ws)
    monkeypatch.setattr("subprocess.run", FakeRun(rc=1, stdout="", stderr="crash"))
    res = die.DOWIntegrationExecutor().execute_pipeline(0, "target")
    assert res["stage"] == 1
    assert res["reason"] == "crash"
    assert "[X] Error: 1" in res["summary"]


@pytest.mark.parametrize("full,code", [(True, 0), (False, 1)])
def test_main(ws, monkeypatch, full, code):
    if full:
        _install(ws, smoke_local=True)
    monkeypatch.setattr("subprocess.run", FakeRun())
    monkeypatch.setattr(
        sys, "argv", ["dow.py", "--iteration", "0", "--target", "target", "--verbose"]
    )
    with pytest.raises(SystemExit) as exc:
        die.main()
    assert exc.value.code == code
    assert len(list(ws.glob("dow_integration_results_iteration_0*.json"))) == 1
