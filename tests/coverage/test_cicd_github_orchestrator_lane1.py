"""Lane L1: fail-closed tracking and CLI exit propagation for ``cicd_github_orchestrator``.

Hermetic: every workspace lives under ``tmp_path``; ``subprocess.run`` is
replaced by a scripted fake (no real git is ever launched); the dynamic
``import_module`` probe is replaced at the module's import site; ``sys.path``
(which the orchestrator mutates in ``__init__``) is restored after each test.
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

# Bound via the module (not a from-import): a 3-name from-import here is 89-120
# chars, where black (88) and isort (.editorconfig 120) disagree on wrapping.
CICDGitHubOrchestrator = cgo.CICDGitHubOrchestrator
MetricsSnapshot = cgo.MetricsSnapshot
RefactoringPlan = cgo.RefactoringPlan

MODULE_PATH = Path(cgo.__file__).resolve()


# --------------------------------------------------------------------------
# Helpers / fixtures
# --------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _isolate_process_state(monkeypatch):
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setenv("PYTHONIOENCODING", "utf-8")


class FakeGit:
    """Scripted stand-in for ``subprocess.run`` restricted to git commands."""

    def __init__(
        self,
        *,
        status="",
        status_rc=0,
        status_exc=None,
        add_exc=None,
        commit_exc=None,
        push_rc=0,
        push_exc=None,
        pull_rc=0,
        pull_exc=None,
    ):
        self.status, self.status_rc, self.status_exc = status, status_rc, status_exc
        self.add_exc, self.commit_exc = add_exc, commit_exc
        self.push_rc, self.push_exc = push_rc, push_exc
        self.pull_rc, self.pull_exc = pull_rc, pull_exc
        self.calls: list[tuple[list[str], dict]] = []

    @property
    def verbs(self):
        return [cmd[1] for cmd, _ in self.calls]

    def __call__(self, cmd, **kwargs):
        self.calls.append((list(cmd), kwargs))
        assert cmd[0] == "git", f"non-git subprocess call: {cmd}"
        verb = cmd[1]
        if verb == "status":
            if self.status_exc:
                raise self.status_exc
            return subprocess.CompletedProcess(
                cmd,
                self.status_rc,
                self.status,
                "fatal: not a git repository" if self.status_rc else "",
            )
        if verb in ("add", "commit"):
            exc = self.add_exc if verb == "add" else self.commit_exc
            if exc:
                raise exc
            return subprocess.CompletedProcess(cmd, 0)
        if verb == "push":
            if self.push_exc:
                raise self.push_exc
            return subprocess.CompletedProcess(
                cmd,
                self.push_rc,
                "pushed" if not self.push_rc else "",
                "rejected: non-fast-forward" if self.push_rc else "",
            )
        if verb == "pull":
            if self.pull_exc:
                raise self.pull_exc
            return subprocess.CompletedProcess(
                cmd,
                self.pull_rc,
                "Already up to date." if not self.pull_rc else "",
                "merge conflict" if self.pull_rc else "",
            )
        raise AssertionError(f"unexpected git verb {verb}")


def install_git(monkeypatch, **kw) -> FakeGit:
    fake = FakeGit(**kw)
    monkeypatch.setattr(cgo.subprocess, "run", fake)
    return fake


def ranking_probe(monkeypatch, *, has_engine=True, error=None):
    seen = []

    def fake_import(name):
        seen.append(name)
        if error is not None:
            raise error
        return (
            SimpleNamespace(RankingEngine=object) if has_engine else SimpleNamespace()
        )

    monkeypatch.setattr(cgo, "import_module", fake_import)
    return seen


def snapshot(**overrides):
    base = dict(
        timestamp="t",
        total_files=10,
        total_lines=100,
        python_files=5,
        duplicate_files=2,
        import_issues=3,
        version_headers=1,
        file_hashes={"a.py": "abc"},
        directory_structure={".": 5},
    )
    base.update(overrides)
    return MetricsSnapshot(**base)


def write(path: Path, text: str = "x = 1\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def build_refactor_workspace(root: Path) -> None:
    misc = root / "12_ORGANIZED_BY_CATEGORY" / "MISC_SCRIPTS"
    for name in ("test_widget.py", "validate_schema.py", "helper.py"):
        write(misc / name, f"NAME = {name!r}\n")  # distinct content: no duplicates
    write(
        root / "13_CORE_SYSTEMS" / "DMAIC" / "DMAIC_V3" / "core" / "ranking_engine.py",
        "class RankingEngine: pass\n",
    )
    (root / "13_CORE_SYSTEMS" / "CENTRAL_LIBRARY").mkdir(parents=True)
    write(root / "legacy" / "ranking_engine.py", "class RankingEngine: pass  # dup\n")


def report_files(ws: Path, pattern: str):
    return sorted((ws / "DMAIC_INTEGRATION_OUTPUT" / "cicd_github").glob(pattern))


# --------------------------------------------------------------------------
# Config loading (missing artifact)
# --------------------------------------------------------------------------
def test_absent_tool_configs_default_to_disabled(tmp_path, capsys):
    orch = CICDGitHubOrchestrator(tmp_path)
    assert orch.gitlens_config == {"enabled": False}
    assert orch.gitkraken_config == {"enabled": False}
    assert (tmp_path / "DMAIC_INTEGRATION_OUTPUT" / "cicd_github").is_dir()
    assert sys.path[0] == str(tmp_path)
    verification = orch.verify_git_tools()
    assert verification["gitlens"] == {
        "configured": False,
        "graph_enabled": False,
        "ai_enabled": False,
    }
    assert verification["gitkraken"] == {"configured": False, "pro_token_set": False}
    assert verification["vscode_extensions"]["extensions_json_exists"] is False


def test_partial_and_malformed_tool_configs(tmp_path, capsys):
    write(
        tmp_path / ".vscode" / "settings.json",
        json.dumps({"gitlens.graph.layout": "panel"}),
    )
    write(
        tmp_path / ".gitkraken" / "config.json", "[1, 2"
    )  # adversarial: truncated JSON
    orch = CICDGitHubOrchestrator(tmp_path)
    assert orch.gitlens_config == {
        "enabled": False,
        "graph_enabled": False,
        "ai_enabled": False,
    }
    assert orch.gitkraken_config == {"enabled": False}
    assert "Failed to load GitKraken config" in capsys.readouterr().out

    write(tmp_path / ".vscode" / "settings.json", "{")
    write(
        tmp_path / ".gitkraken" / "config.json",
        json.dumps({"authentication": {"gitlens": {"enabled": True, "pro_token": ""}}}),
    )
    orch = CICDGitHubOrchestrator(tmp_path)
    assert orch.gitlens_config == {"enabled": False}
    assert "Failed to load GitLens config" in capsys.readouterr().out
    assert orch.verify_git_tools()["gitkraken"] == {
        "configured": True,
        "pro_token_set": False,
    }


def test_git_status_routes_conflicts_to_unmerged(tmp_path, monkeypatch):
    install_git(monkeypatch, status="UU both.py\nAA added_twice.py\nR  old -> new\n")
    status = CICDGitHubOrchestrator(tmp_path).git_status()
    assert status["has_changes"] is True
    assert status["unmerged"] == ["both.py", "added_twice.py"]
    assert status["renamed"] == ["old -> new"]
    assert status["modified"] == []


# --------------------------------------------------------------------------
# Metrics collection, persistence round-trip, comparison
# --------------------------------------------------------------------------
def test_collect_metrics_skips_unreadable_py_entries(tmp_path):
    write(tmp_path / "ok.py", "from ranking_engine import X\n__version__ = '1'\n")
    (tmp_path / "trap.py").mkdir()  # a *directory* that matches *.py: read fails
    orch = CICDGitHubOrchestrator(tmp_path)
    metrics = orch.collect_metrics("PRE")
    assert metrics.python_files == 2
    assert list(metrics.file_hashes) == ["ok.py"]
    assert metrics.import_issues == 1
    assert metrics.total_lines == 2
    assert metrics.version_headers == 1
    assert metrics.directory_structure == {".": 2}


def test_collect_metrics_large_tree_reports_progress_and_extrapolates(tmp_path, capsys):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    for i in range(501):
        (pkg / f"m{i:03d}.py").write_text(
            f"from ranking_engine import X\nv = {i}\n", encoding="utf-8"
        )
    metrics = CICDGitHubOrchestrator(tmp_path).collect_metrics("PRE")
    out = capsys.readouterr().out
    assert "Progress: 500/501 files..." in out
    assert metrics.python_files == 501
    assert metrics.duplicate_files == 0
    # every sampled file has the legacy import -> 300 hits scaled to 501 files
    assert metrics.import_issues == 501
    assert metrics.directory_structure == {"pkg": 501}


def test_save_metrics_round_trips_to_snapshot(tmp_path):
    orch = CICDGitHubOrchestrator(tmp_path)
    original = snapshot()
    orch.save_metrics(original, "pre")
    saved = (
        tmp_path
        / "DMAIC_INTEGRATION_OUTPUT"
        / "cicd_github"
        / f"metrics_pre_{orch.execution_id}.json"
    )
    loaded = MetricsSnapshot(**json.loads(saved.read_text(encoding="utf-8")))
    assert loaded == original


def test_save_metrics_truncates_oversized_hash_map(tmp_path):
    orch = CICDGitHubOrchestrator(tmp_path)
    big = snapshot(
        file_hashes={f"dir/file_{i:05d}.py": "0123456789ab" for i in range(5000)}
    )
    orch.save_metrics(big, "post")
    saved = json.loads(
        report_files(tmp_path, "metrics_post_*.json")[0].read_text(encoding="utf-8")
    )
    assert saved["file_hashes"] == "<5000 files>"
    assert saved["python_files"] == big.python_files
    assert len(big.file_hashes) == 5000  # in-memory snapshot is not mutated


def test_compare_metrics_requires_both_snapshots(tmp_path):
    orch = CICDGitHubOrchestrator(tmp_path)
    assert orch.compare_metrics() == {"error": "Missing metrics"}
    orch.pre_metrics = snapshot()
    assert orch.compare_metrics() == {"error": "Missing metrics"}


def test_compare_metrics_reports_improvements(tmp_path):
    orch = CICDGitHubOrchestrator(tmp_path)
    orch.pre_metrics = snapshot(duplicate_files=4, import_issues=5, version_headers=1)
    orch.post_metrics = snapshot(
        total_files=8,
        total_lines=90,
        duplicate_files=1,
        import_issues=2,
        version_headers=3,
    )
    cmp = orch.compare_metrics()
    assert (cmp["files_changed"], cmp["lines_changed"]) == (-2, -10)
    assert cmp["improvements"] == [
        "Removed 3 duplicate files",
        "Fixed 3 import issues",
        "Added 2 version headers",
    ]


def test_compare_metrics_regressions_are_not_improvements(tmp_path):
    orch = CICDGitHubOrchestrator(tmp_path)
    orch.pre_metrics = snapshot(duplicate_files=0, import_issues=0, version_headers=3)
    orch.post_metrics = snapshot(duplicate_files=2, import_issues=1, version_headers=3)
    cmp = orch.compare_metrics()
    assert cmp["duplicates_removed"] == -2
    assert cmp["import_issues_fixed"] == -1
    assert cmp["version_headers_added"] == 0
    assert cmp["improvements"] == []


# --------------------------------------------------------------------------
# Refactoring analysis and execution
# --------------------------------------------------------------------------
def test_analyze_refactoring_classifies_misc_scripts_and_duplicates(tmp_path):
    build_refactor_workspace(tmp_path)
    plan = CICDGitHubOrchestrator(tmp_path).analyze_refactoring_needs()
    moves = {Path(m["from"]).name: m for m in plan.moves}
    assert set(moves) == {"test_widget.py", "validate_schema.py"}  # helper.py stays
    assert (
        moves["test_widget.py"]["to"]
        == "12_ORGANIZED_BY_CATEGORY/TEST_SUITES/test_widget.py"
    )
    assert (
        moves["validate_schema.py"]["to"]
        == "12_ORGANIZED_BY_CATEGORY/VALIDATION/validate_schema.py"
    )
    assert [Path(d).parts for d in plan.deletions] == [("legacy", "ranking_engine.py")]


def test_analyze_refactoring_keeps_duplicates_when_primary_missing(tmp_path):
    write(tmp_path / "legacy" / "ranking_engine.py")
    plan = CICDGitHubOrchestrator(tmp_path).analyze_refactoring_needs()
    assert plan == RefactoringPlan(
        moves=[], renames=[], consolidations=[], deletions=[]
    )
    assert (tmp_path / "legacy" / "ranking_engine.py").exists()


def test_live_refactoring_moves_and_deletes_then_is_idempotent(tmp_path):
    build_refactor_workspace(tmp_path)
    orch = CICDGitHubOrchestrator(tmp_path)
    plan = orch.analyze_refactoring_needs()

    first = orch.execute_refactoring(plan, dry_run=False)
    assert len(first["moves_executed"]) == 2 and first["errors"] == []
    assert len(first["deletions_executed"]) == 1
    assert (
        tmp_path / "12_ORGANIZED_BY_CATEGORY" / "TEST_SUITES" / "test_widget.py"
    ).exists()
    assert (
        tmp_path / "12_ORGANIZED_BY_CATEGORY" / "VALIDATION" / "validate_schema.py"
    ).exists()
    assert not (
        tmp_path / "12_ORGANIZED_BY_CATEGORY" / "MISC_SCRIPTS" / "test_widget.py"
    ).exists()
    assert not (tmp_path / "legacy" / "ranking_engine.py").exists()

    # Duplicate attempt with the same (now stale) plan: sources are gone, so
    # nothing is executed and nothing errors.
    second = orch.execute_refactoring(plan, dry_run=False)
    assert second == {
        "moves_executed": [],
        "renames_executed": [],
        "consolidations_executed": [],
        "deletions_executed": [],
        "errors": [],
    }


def test_refactoring_errors_are_collected_not_raised(tmp_path):
    write(tmp_path / "src.py")
    write(tmp_path / "blocker")  # a regular file where a directory is needed
    (tmp_path / "a_dir").mkdir()
    plan = RefactoringPlan(
        moves=[{"from": "src.py", "to": "blocker/src.py"}],
        renames=[],
        consolidations=[],
        deletions=["a_dir"],
    )
    results = CICDGitHubOrchestrator(tmp_path).execute_refactoring(plan, dry_run=False)
    assert results["moves_executed"] == [] and results["deletions_executed"] == []
    assert len(results["errors"]) == 2
    assert results["errors"][0].startswith("Move failed: src.py - ")
    assert results["errors"][1].startswith("Deletion failed: a_dir - ")
    assert (tmp_path / "src.py").exists() and (tmp_path / "a_dir").is_dir()


# --------------------------------------------------------------------------
# git_commit_push / git_pull (mocked subprocess)
# --------------------------------------------------------------------------
def test_commit_push_success_runs_add_commit_push_in_workspace(tmp_path, monkeypatch):
    git = install_git(monkeypatch)
    result = CICDGitHubOrchestrator(tmp_path).git_commit_push("msg")
    assert result == {"success": True, "output": "pushed"}
    assert [c for c, _ in git.calls] == [
        ["git", "add", "."],
        ["git", "commit", "-m", "msg"],
        ["git", "push"],
    ]
    assert all(kw["cwd"] == tmp_path for _, kw in git.calls)
    assert git.calls[0][1]["check"] is True and git.calls[1][1]["check"] is True


def test_commit_push_rejected_push_reports_failure(tmp_path, monkeypatch):
    install_git(monkeypatch, push_rc=1)
    result = CICDGitHubOrchestrator(tmp_path).git_commit_push("msg")
    assert result == {"success": False, "error": "rejected: non-fast-forward"}


def test_commit_push_nonzero_add_stops_before_commit(tmp_path, monkeypatch):
    git = install_git(
        monkeypatch, add_exc=subprocess.CalledProcessError(128, ["git", "add", "."])
    )
    result = CICDGitHubOrchestrator(tmp_path).git_commit_push("msg")
    assert result["success"] is False
    assert "returned non-zero exit status 128" in result["error"]
    assert git.verbs == ["add"]


def test_commit_push_timeout(tmp_path, monkeypatch):
    git = install_git(
        monkeypatch, commit_exc=subprocess.TimeoutExpired(["git", "commit"], 30)
    )
    result = CICDGitHubOrchestrator(tmp_path).git_commit_push("msg")
    assert result == {"success": False, "error": "Git operation timed out"}
    assert git.verbs == ["add", "commit"]


@pytest.mark.parametrize(
    "kw,expected",
    [
        ({}, {"success": True, "output": "Already up to date."}),
        ({"pull_rc": 1}, {"success": False, "error": "merge conflict"}),
        (
            {"pull_exc": subprocess.TimeoutExpired(["git", "pull"], 120)},
            {"success": False, "error": "Git pull timed out"},
        ),
        ({"pull_exc": FileNotFoundError("git")}, {"success": False, "error": "git"}),
    ],
    ids=["ok", "nonzero", "timeout", "git-missing"],
)
def test_git_pull_outcomes(tmp_path, monkeypatch, kw, expected):
    git = install_git(monkeypatch, **kw)
    assert CICDGitHubOrchestrator(tmp_path).git_pull() == expected
    assert git.calls[0][0] == ["git", "pull"]


# --------------------------------------------------------------------------
# validate_post_roundtrip
# --------------------------------------------------------------------------
def test_validate_post_roundtrip_all_green(tmp_path, monkeypatch):
    build_refactor_workspace(tmp_path)
    seen = ranking_probe(monkeypatch)
    orch = CICDGitHubOrchestrator(tmp_path)
    orch.post_metrics = snapshot(duplicate_files=0)
    result = orch.validate_post_roundtrip()
    assert result == {
        "imports_valid": True,
        "no_duplicates": True,
        "structure_intact": True,
        "errors": [],
    }
    assert seen == ["13_CORE_SYSTEMS.DMAIC.DMAIC_V3.core.ranking_engine"]


def test_validate_post_roundtrip_import_failure_and_missing_structure(
    tmp_path, monkeypatch, capsys
):
    ranking_probe(
        monkeypatch, error=ModuleNotFoundError("No module named '13_CORE_SYSTEMS'")
    )
    orch = CICDGitHubOrchestrator(tmp_path)
    orch.post_metrics = snapshot(duplicate_files=3)
    result = orch.validate_post_roundtrip()
    assert result["imports_valid"] is False
    assert result["errors"] == [
        "Import validation failed: No module named '13_CORE_SYSTEMS'"
    ]
    assert result["no_duplicates"] is False
    assert result["structure_intact"] is False
    out = capsys.readouterr().out
    assert "3 duplicates found" in out and "Structure compromised" in out


def test_validate_post_roundtrip_without_post_metrics_or_engine_class(
    tmp_path, monkeypatch, capsys
):
    ranking_probe(monkeypatch, has_engine=False)
    result = CICDGitHubOrchestrator(tmp_path).validate_post_roundtrip()
    assert result["imports_valid"] is False and result["errors"] == []
    assert result["no_duplicates"] is False
    assert "0 duplicates found" in capsys.readouterr().out


# --------------------------------------------------------------------------
# execute_full_pipeline: fail-closed gate and full roundtrip
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "git_kw",
    [
        {"status_rc": 128},
        {"status": "!! ignored.txt\n"},
        {"status": "XY weird\n"},
        {"status": "M\n"},
        {"status_exc": FileNotFoundError("git")},
        {"status_exc": subprocess.TimeoutExpired(["git", "status"], 30)},
    ],
    ids=[
        "nonzero-exit",
        "ignored-code",
        "unknown-code",
        "truncated",
        "git-missing",
        "timeout",
    ],
)
def test_pipeline_blocks_on_unknown_git_evidence_before_any_mutation(
    tmp_path, monkeypatch, git_kw
):
    build_refactor_workspace(tmp_path)
    git = install_git(monkeypatch, **git_kw)
    ranking_probe(monkeypatch)
    orch = CICDGitHubOrchestrator(tmp_path)

    result = orch.execute_full_pipeline(dry_run=False)

    assert result["status"] == "BLOCKED_GIT_STATUS"
    assert result["stages"]["git_status_before"]["has_changes"] is None
    assert result["stages"]["git_status_before"]["error"]
    assert "refactoring_plan" not in result["stages"]
    assert git.verbs == ["status"]  # no add/commit/push/pull
    # Live mode, yet nothing moved or deleted.
    assert (
        tmp_path / "12_ORGANIZED_BY_CATEGORY" / "MISC_SCRIPTS" / "test_widget.py"
    ).exists()
    assert (tmp_path / "legacy" / "ranking_engine.py").exists()
    assert report_files(tmp_path, "cicd_pipeline_*.json") == []
    assert len(report_files(tmp_path, "metrics_pre_*.json")) == 1
    assert report_files(tmp_path, "metrics_post_*.json") == []


@pytest.mark.parametrize(
    "scan",
    [
        {"has_changes": 1},
        {"has_changes": "false"},
        {},
        {"has_changes": False, "error": "partial"},
    ],
    ids=["int-truthy", "string", "missing-key", "error-with-bool"],
)
def test_pipeline_blocks_on_non_boolean_scan_evidence(tmp_path, monkeypatch, scan):
    git = install_git(monkeypatch)
    orch = CICDGitHubOrchestrator(tmp_path)
    monkeypatch.setattr(orch, "git_status", lambda: dict(scan))
    result = orch.execute_full_pipeline(dry_run=False)
    assert result["status"] == "BLOCKED_GIT_STATUS"
    assert git.calls == []


def test_live_pipeline_with_changes_roundtrips_and_writes_report(
    tmp_path, monkeypatch, capsys
):
    build_refactor_workspace(tmp_path)
    git = install_git(monkeypatch, status=" M 13_CORE_SYSTEMS/x.py\n?? new.py\n")
    ranking_probe(monkeypatch)
    orch = CICDGitHubOrchestrator(tmp_path)

    result = orch.execute_full_pipeline(dry_run=False)

    assert "status" not in result
    stages = result["stages"]
    assert stages["git_status_before"]["modified"] == ["13_CORE_SYSTEMS/x.py"]
    assert stages["git_status_before"]["untracked"] == ["new.py"]
    assert git.verbs == ["status", "add", "commit", "push", "pull"]
    commit_cmd = git.calls[2][0]
    assert (
        commit_cmd[3] == f"CI/CD: Refactoring and reconciliation - {orch.execution_id}"
    )
    assert (
        stages["git_push"]["success"] is True and stages["git_pull"]["success"] is True
    )
    assert len(stages["refactoring_results"]["moves_executed"]) == 2
    assert stages["pre_metrics"]["duplicates"] == 0
    assert stages["post_validation"]["structure_intact"] is True
    # The duplicate ranking engine was deleted -> one fewer python file.
    assert (
        stages["post_metrics"]["python_files"]
        == stages["pre_metrics"]["python_files"] - 1
    )

    report = report_files(tmp_path, "cicd_pipeline_*.json")
    assert len(report) == 1
    assert json.loads(report[0].read_text(encoding="utf-8")) == result
    assert "PIPELINE COMPLETE" in capsys.readouterr().out


def test_live_pipeline_failed_push_skips_pull(tmp_path, monkeypatch):
    git = install_git(monkeypatch, status=" M a.py\n", push_rc=1)
    ranking_probe(monkeypatch)
    result = CICDGitHubOrchestrator(tmp_path).execute_full_pipeline(dry_run=False)
    assert git.verbs == ["status", "add", "commit", "push"]
    assert result["stages"]["git_push"] == {
        "success": False,
        "error": "rejected: non-fast-forward",
    }
    assert "git_pull" not in result["stages"]


def test_live_pipeline_commit_gate_uses_pre_refactor_status(tmp_path, monkeypatch):
    """Stale-status behaviour: ``has_changes`` is sampled *before* refactoring.

    On a clean tree a live run still moves/deletes files but never commits
    them, because the commit gate consults the pre-refactor scan.
    """
    build_refactor_workspace(tmp_path)
    git = install_git(monkeypatch, status="")
    ranking_probe(monkeypatch)
    result = CICDGitHubOrchestrator(tmp_path).execute_full_pipeline(dry_run=False)
    assert result["stages"]["git_status_before"]["has_changes"] is False
    assert len(result["stages"]["refactoring_results"]["moves_executed"]) == 2
    assert not (tmp_path / "legacy" / "ranking_engine.py").exists()
    assert git.verbs == ["status"]
    assert "git_push" not in result["stages"]


def test_dry_run_pipeline_with_changes_never_mutates_or_pushes(
    tmp_path, monkeypatch, capsys
):
    build_refactor_workspace(tmp_path)
    git = install_git(monkeypatch, status="MM dirty.py\n")
    ranking_probe(monkeypatch)
    result = CICDGitHubOrchestrator(tmp_path).execute_full_pipeline(dry_run=True)
    assert result["dry_run"] is True and "status" not in result
    assert git.verbs == ["status"]
    assert len(result["stages"]["refactoring_results"]["moves_executed"]) == 2
    assert (
        tmp_path / "12_ORGANIZED_BY_CATEGORY" / "MISC_SCRIPTS" / "test_widget.py"
    ).exists()
    assert (tmp_path / "legacy" / "ranking_engine.py").exists()
    assert result["stages"]["metrics_comparison"]["improvements"] == []


def test_pipeline_prints_detected_improvements(tmp_path, monkeypatch, capsys):
    install_git(monkeypatch, status="")
    ranking_probe(monkeypatch)
    write(tmp_path / "a.py", "dup = 1\n")
    write(tmp_path / "b.py", "dup = 1\n")
    orch = CICDGitHubOrchestrator(tmp_path)
    real_collect = orch.collect_metrics

    def collect_then_dedupe(label):
        metrics = real_collect(label)
        if label == "PRE":
            (tmp_path / "b.py").unlink()  # simulate an external de-dup between scans
        return metrics

    monkeypatch.setattr(orch, "collect_metrics", collect_then_dedupe)
    result = orch.execute_full_pipeline(dry_run=True)
    assert result["stages"]["metrics_comparison"]["improvements"] == [
        "Removed 1 duplicate files"
    ]
    out = capsys.readouterr().out
    assert "IMPROVEMENTS DETECTED" in out and "- Removed 1 duplicate files" in out


# --------------------------------------------------------------------------
# main(): exit-code propagation, end to end (pipeline is NOT stubbed)
# --------------------------------------------------------------------------
def _argv(monkeypatch, ws: Path, *extra):
    monkeypatch.setattr(
        sys, "argv", ["cicd_github_orchestrator.py", "--workspace", str(ws), *extra]
    )


@pytest.mark.parametrize(
    "git_kw",
    [
        {"status_rc": 128},
        {"status": "?! odd\n"},
        {"status_exc": OSError("git unavailable")},
    ],
    ids=["nonzero", "unknown-status", "oserror"],
)
@pytest.mark.parametrize("dry", [True, False], ids=["dry-run", "live"])
def test_cli_returns_2_when_git_scan_is_unknown(
    tmp_path, monkeypatch, capsys, git_kw, dry
):
    install_git(monkeypatch, **git_kw)
    ranking_probe(monkeypatch)
    _argv(monkeypatch, tmp_path, *(["--dry-run"] if dry else []))
    assert cgo.main() == 2
    out = capsys.readouterr().out
    assert "[BLOCKED] CI/CD pipeline cannot claim success" in out
    assert "[OK] CI/CD pipeline executed successfully" not in out
    assert "DRY RUN complete" not in out


@pytest.mark.parametrize(
    "dry,expected",
    [
        (True, "[OK] DRY RUN complete - no changes made"),
        (False, "[OK] CI/CD pipeline executed successfully"),
    ],
    ids=["dry-run", "live"],
)
def test_cli_clean_scan_returns_0(tmp_path, monkeypatch, capsys, dry, expected):
    install_git(monkeypatch, status="")
    ranking_probe(monkeypatch)
    _argv(monkeypatch, tmp_path, *(["--dry-run"] if dry else []))
    assert cgo.main() == 0
    out = capsys.readouterr().out
    assert expected in out and "[BLOCKED]" not in out
    assert len(report_files(tmp_path, "cicd_pipeline_*.json")) == 1


def test_cli_explicit_success_status_is_accepted(tmp_path, monkeypatch, capsys):
    install_git(monkeypatch, status="")
    _argv(monkeypatch, tmp_path, "--dry-run")
    monkeypatch.setattr(
        CICDGitHubOrchestrator,
        "execute_full_pipeline",
        lambda self, dry_run=False: {"status": "SUCCESS"},
    )
    assert cgo.main() == 0


@pytest.mark.parametrize(
    "status",
    ["success", "BLOCKED", "", 0, False],
    ids=["lowercase", "blocked", "empty", "zero", "false"],
)
def test_cli_fails_closed_for_any_status_other_than_SUCCESS(
    tmp_path, monkeypatch, capsys, status
):
    _argv(monkeypatch, tmp_path)
    monkeypatch.setattr(
        CICDGitHubOrchestrator,
        "execute_full_pipeline",
        lambda self, dry_run=False: {"status": status},
    )
    assert cgo.main() == 2
    assert "[BLOCKED]" in capsys.readouterr().out


# Finding F1 (a rejected live push exited 0) is fixed in PR #2391.  Its CLI
# exit-code assertions live there (tests/test_f1_orchestrator_push_failure_exit.py),
# so this wave asserts neither the old nor the new exit code and merges in
# either order.


def test_script_entrypoint_propagates_blocked_exit_code_to_shell(
    tmp_path, monkeypatch, capsys
):
    # Executes the file as ``__main__`` so ``raise SystemExit(main())`` is exercised.
    git = FakeGit(status_rc=128)
    monkeypatch.setattr(subprocess, "run", git)
    _argv(monkeypatch, tmp_path, "--dry-run")
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(MODULE_PATH), run_name="__main__")
    assert exc.value.code == 2
    assert git.verbs == ["status"]
    assert "[BLOCKED]" in capsys.readouterr().out
