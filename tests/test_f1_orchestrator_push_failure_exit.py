"""F1 regression: a failed live commit/push or pull must not exit 0.

Before the fix, ``execute_full_pipeline`` recorded a rejected ``git push`` only
as stage evidence and set no pipeline ``status``, so ``main`` printed success
and returned 0. Fail-closed covered the git-status scan alone.

Hermetic: the workspace is ``tmp_path``; ``subprocess.run`` is a scripted fake
at the module import site (no real git); the ranking-engine import probe is
faked; ``sys.path`` (mutated by the orchestrator) is restored per test.
"""

from __future__ import annotations

import json
import runpy
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import cicd_github_orchestrator as cgo

MODULE_PATH = Path(cgo.__file__).resolve()
SUCCESS_LINE = "[OK] CI/CD pipeline executed successfully"
BLOCKED_LINE = "[BLOCKED] CI/CD pipeline cannot claim success"


class FakeGit:
    """Scripted ``subprocess.run`` restricted to git verbs."""

    def __init__(self, *, status=" M a.py\n", raises=None, rc=None):
        self.status = status
        self.raises = raises or {}
        self.rc = rc or {}
        self.verbs: list[str] = []

    def __call__(self, cmd, **kwargs):
        assert cmd[0] == "git", f"non-git subprocess call: {cmd}"
        verb = cmd[1]
        self.verbs.append(verb)
        if verb in self.raises:
            raise self.raises[verb]
        rc = self.rc.get(verb, 0)
        if verb == "status":
            return subprocess.CompletedProcess(cmd, rc, self.status, "")
        stderr = f"{verb} refused" if rc else ""
        return subprocess.CompletedProcess(cmd, rc, "" if rc else "ok", stderr)


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setenv("PYTHONIOENCODING", "utf-8")
    monkeypatch.setattr(
        cgo, "import_module", lambda name: SimpleNamespace(RankingEngine=object)
    )


def _git(monkeypatch, **kw) -> FakeGit:
    fake = FakeGit(**kw)
    monkeypatch.setattr(cgo.subprocess, "run", fake)
    return fake


def _argv(monkeypatch, ws: Path, *extra):
    monkeypatch.setattr(
        sys, "argv", ["cicd_github_orchestrator.py", "--workspace", str(ws), *extra]
    )


def _report(ws: Path) -> dict:
    reports = sorted(ws.rglob("cicd_pipeline_*.json"))
    assert len(reports) == 1, reports
    return json.loads(reports[0].read_text(encoding="utf-8"))


def test_rejected_push_exits_2_and_records_failed_status(tmp_path, monkeypatch, capsys):
    git = _git(monkeypatch, rc={"push": 1})
    _argv(monkeypatch, tmp_path)

    assert cgo.main() == 2

    out = capsys.readouterr().out
    assert "Push failed: push refused" in out
    assert BLOCKED_LINE in out
    assert SUCCESS_LINE not in out
    # No pull after a failed push.
    assert git.verbs == ["status", "add", "commit", "push"]
    report = _report(tmp_path)
    assert report["status"] == "FAILED_GIT_PUSH"
    assert report["stages"]["git_push"]["success"] is False
    assert "git_pull" not in report["stages"]


@pytest.mark.parametrize(
    "raises",
    [
        {"add": subprocess.CalledProcessError(1, ["git", "add", "."])},
        {"commit": subprocess.CalledProcessError(1, ["git", "commit"])},
        {"push": subprocess.TimeoutExpired(["git", "push"], 120)},
        {"push": OSError("git unavailable")},
    ],
    ids=["add-fails", "commit-fails", "push-timeout", "push-oserror"],
)
def test_commit_or_push_exception_exits_2(tmp_path, monkeypatch, capsys, raises):
    git = _git(monkeypatch, raises=raises)
    _argv(monkeypatch, tmp_path)

    assert cgo.main() == 2

    out = capsys.readouterr().out
    assert SUCCESS_LINE not in out
    assert "pull" not in git.verbs
    assert _report(tmp_path)["status"] == "FAILED_GIT_PUSH"


def test_pull_failure_after_successful_push_exits_2(tmp_path, monkeypatch, capsys):
    git = _git(monkeypatch, rc={"pull": 1})
    _argv(monkeypatch, tmp_path)

    assert cgo.main() == 2

    assert SUCCESS_LINE not in capsys.readouterr().out
    assert git.verbs == ["status", "add", "commit", "push", "pull"]
    report = _report(tmp_path)
    assert report["status"] == "FAILED_GIT_PULL"
    assert report["stages"]["git_push"]["success"] is True
    assert report["stages"]["git_pull"]["success"] is False


def test_successful_roundtrip_still_exits_0_without_status(
    tmp_path, monkeypatch, capsys
):
    git = _git(monkeypatch)
    _argv(monkeypatch, tmp_path)

    assert cgo.main() == 0

    assert SUCCESS_LINE in capsys.readouterr().out
    assert git.verbs == ["status", "add", "commit", "push", "pull"]
    assert "status" not in _report(tmp_path)


def test_dry_run_never_pushes_and_exits_0(tmp_path, monkeypatch, capsys):
    git = _git(monkeypatch, rc={"push": 1})
    _argv(monkeypatch, tmp_path, "--dry-run")

    assert cgo.main() == 0

    assert "DRY RUN complete" in capsys.readouterr().out
    assert git.verbs == ["status"]


def test_script_entrypoint_propagates_push_failure_to_shell(
    tmp_path, monkeypatch, capsys
):
    _git(monkeypatch, rc={"push": 128})
    _argv(monkeypatch, tmp_path)

    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(MODULE_PATH), run_name="__main__")

    assert exc.value.code == 2
    assert SUCCESS_LINE not in capsys.readouterr().out
