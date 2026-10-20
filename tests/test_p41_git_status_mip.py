"""P41 MIP: parser and fail-closed no-mutation regressions."""

import subprocess
from types import SimpleNamespace

import pytest

from cicd_github_orchestrator import CICDGitHubOrchestrator


@pytest.mark.parametrize(
    ("record", "category", "path"),
    [
        (" M demo.py\n", "modified", "demo.py"),
        ("M  staged.py\n", "modified", "staged.py"),
        ("MM both.py\n", "modified", "both.py"),
        (" T type.py\n", "modified", "type.py"),
        ("A  added.py\n", "added", "added.py"),
        (" D gone.py\n", "deleted", "gone.py"),
        ("D  staged-gone.py\n", "deleted", "staged-gone.py"),
        ("R  old.py -> new.py\n", "renamed", "old.py -> new.py"),
        ("C  old.py -> copy.py\n", "copied", "old.py -> copy.py"),
        ("?? new file.py\n", "untracked", "new file.py"),
        (' M "space name.py"\n', "modified", '"space name.py"'),
        (" M demo.py\r\n", "modified", "demo.py"),
        (" M demo.py", "modified", "demo.py"),
        ("UU conflict.py\n", "unmerged", "conflict.py"),
        ("AA both-added.py\n", "unmerged", "both-added.py"),
        ("DD both-deleted.py\n", "unmerged", "both-deleted.py"),
    ],
)
def test_status_columns_and_raw_path_spellings(
    monkeypatch, tmp_path, record, category, path
):
    target = CICDGitHubOrchestrator(tmp_path)

    def fake_run(argv, **kwargs):
        assert argv == ["git", "status", "--porcelain"]
        assert kwargs == {
            "cwd": tmp_path,
            "capture_output": True,
            "text": True,
            "timeout": 30,
        }
        return SimpleNamespace(returncode=0, stdout=record, stderr="")

    monkeypatch.setattr("cicd_github_orchestrator.subprocess.run", fake_run)
    result = target.git_status()
    assert "error" not in result
    assert result["has_changes"] is True
    assert result[category] == [path]


def _fake_status(monkeypatch, stdout="", stderr="", returncode=0):
    def fake_run(*args, **kwargs):
        return SimpleNamespace(
            returncode=returncode, stdout=stdout, stderr=stderr
        )

    monkeypatch.setattr("cicd_github_orchestrator.subprocess.run", fake_run)


def test_clean_result_has_no_phantom_files(monkeypatch, tmp_path):
    _fake_status(monkeypatch)
    result = CICDGitHubOrchestrator(tmp_path).git_status()
    assert result["has_changes"] is False
    assert all(v == [] for k, v in result.items() if k != "has_changes")


@pytest.mark.parametrize(
    "record", ["\n", " M", "bad status\n", "ZZ invalid.py\n", "   absent.py\n"]
)
def test_malformed_or_unknown_status_is_not_clean(monkeypatch, tmp_path, record):
    _fake_status(monkeypatch, stdout=record)
    result = CICDGitHubOrchestrator(tmp_path).git_status()
    assert result["error"]
    assert result["has_changes"] is None


@pytest.mark.parametrize("stderr", ["fatal: not a repository", ""])
def test_nonzero_git_is_not_clean(monkeypatch, tmp_path, stderr):
    _fake_status(monkeypatch, stderr=stderr, returncode=128)
    result = CICDGitHubOrchestrator(tmp_path).git_status()
    assert result["error"] == (stderr or "git status exited 128")
    assert result["has_changes"] is None


@pytest.mark.parametrize(
    "error", [subprocess.TimeoutExpired("git", 30), OSError("git unavailable")]
)
def test_subprocess_exception_is_unknown(monkeypatch, tmp_path, error):
    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr("cicd_github_orchestrator.subprocess.run", fail)
    result = CICDGitHubOrchestrator(tmp_path).git_status()
    assert result["error"]
    assert result["has_changes"] is None


def test_bad_status_blocks_pipeline_before_any_refactoring(monkeypatch, tmp_path):
    target = CICDGitHubOrchestrator(tmp_path)
    monkeypatch.setattr(target, "verify_git_tools", lambda: {})
    sample = SimpleNamespace(
        total_files=0, python_files=0, total_lines=0,
        duplicate_files=0, import_issues=0,
    )
    monkeypatch.setattr(target, "collect_metrics", lambda _: sample)
    monkeypatch.setattr(target, "save_metrics", lambda *args: None)
    monkeypatch.setattr(
        target, "git_status", lambda: {"error": "denied", "has_changes": None}
    )

    def forbidden(*args, **kwargs):
        pytest.fail("Mutation or planning entered after failed status")

    for name in (
        "analyze_refactoring_needs", "execute_refactoring",
        "git_commit_push", "git_pull",
    ):
        monkeypatch.setattr(target, name, forbidden)
    result = target.execute_full_pipeline(dry_run=False)
    assert result["status"] == "BLOCKED_GIT_STATUS"
    assert result["stages"]["git_status_before"]["has_changes"] is None
