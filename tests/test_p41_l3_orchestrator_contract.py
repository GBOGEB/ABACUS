"""P41-L3: source execution under sandbox-only and forbidden Git operations."""

from types import SimpleNamespace

import pytest

from cicd_github_orchestrator import CICDGitHubOrchestrator, RefactoringPlan


def test_analyze_refactoring_produces_proposal_without_mutating_files(tmp_path):
    source = tmp_path / "12_ORGANIZED_BY_CATEGORY" / "MISC_SCRIPTS"
    source.mkdir(parents=True)
    test_file = source / "test_legacy.py"
    test_file.write_text("value = 1\n", encoding="utf-8")
    orchestrator = CICDGitHubOrchestrator(tmp_path)
    proposal = orchestrator.analyze_refactoring_needs()
    assert any(m["from"].endswith("test_legacy.py") for m in proposal.moves)
    assert test_file.exists()


def test_dry_run_move_and_deletion_preserves_source(tmp_path):
    source = tmp_path / "original.py"
    source.write_text("important = True\n", encoding="utf-8")
    orchestrator = CICDGitHubOrchestrator(tmp_path)
    proposal = RefactoringPlan(
        moves=[{"from": "original.py", "to": "new/original.py"}],
        renames=[], consolidations=[], deletions=["original.py"],
    )
    result = orchestrator.execute_refactoring(proposal, dry_run=True)
    assert result["errors"] == []
    assert source.exists()
    assert not (tmp_path / "new" / "original.py").exists()


def test_git_status_scopes_read_only_to_sandbox(monkeypatch, tmp_path):
    orchestrator = CICDGitHubOrchestrator(tmp_path)
    calls = []
    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return SimpleNamespace(returncode=0, stdout=" M demo.py\n?? new.py\n", stderr="")
    monkeypatch.setattr("cicd_github_orchestrator.subprocess.run", fake_run)
    result = orchestrator.git_status()
    assert result["modified"] == ["demo.py"]
    assert result["untracked"] == ["new.py"]
    assert calls == [(["git", "status", "--porcelain"], {
        "cwd": tmp_path, "capture_output": True, "text": True, "timeout": 30,
    })]


@pytest.mark.parametrize(
    ("porcelain", "expected"),
    [
        (" M demo.py\n", {"modified": ["demo.py"]}),
        ("M  demo.py\n", {"modified": ["demo.py"]}),
        ("A  added.py\n", {"added": ["added.py"]}),
        (" D removed.py\n", {"deleted": ["removed.py"]}),
        ("D  removed.py\n", {"deleted": ["removed.py"]}),
        ("?? untracked.py\n", {"untracked": ["untracked.py"]}),
        ("", {"modified": [], "added": [], "deleted": [], "untracked": []}),
    ],
)
def test_git_status_preserves_porcelain_columns(monkeypatch, tmp_path, porcelain, expected):
    orchestrator = CICDGitHubOrchestrator(tmp_path)

    def fake_run(argv, **kwargs):
        assert argv == ["git", "status", "--porcelain"]
        assert kwargs["cwd"] == tmp_path
        return SimpleNamespace(returncode=0, stdout=porcelain, stderr="")

    monkeypatch.setattr("cicd_github_orchestrator.subprocess.run", fake_run)
    status = orchestrator.git_status()
    for field in ("modified", "added", "deleted", "untracked"):
        assert status[field] == expected.get(field, [])
    assert status["has_changes"] is bool(porcelain)
