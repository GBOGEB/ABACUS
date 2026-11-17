"""Expanded report-output and failure-boundary tests for MIP C1.

Test-only: no real remote GitHub API calls, git push, or branch deletion.
"""

import csv
from pathlib import Path

import pytest

from scripts import branch_retirement_report as brr


def _record(branch="feature/keep", classification="KEEP", command=""):
    return brr.BranchRecord(
        branch=branch,
        ref=f"origin/{branch}",
        sha="a" * 40,
        last_commit_iso="2026-10-10T12:00:00+00:00",
        age_days=7,
        ahead=None,
        behind=None,
        pr=None,
        classification=classification,
        rationale="test-only evidence",
        delete_command=command,
    )


def test_csv_keeps_unknown_counts_blank_and_source_sha(tmp_path):
    target = tmp_path / "retire.csv"
    brr.write_csv([_record()], target)
    with target.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 1
    assert rows[0]["sha"] == "a" * 40
    assert rows[0]["ahead"] == ""
    assert rows[0]["behind"] == ""
    assert rows[0]["age_days"] == "7"
    assert rows[0]["classification"] == "KEEP"


def test_delete_script_empty_is_inert(tmp_path):
    target = tmp_path / "delete.sh"
    brr.write_deletion_script([_record()], target)
    text = target.read_text(encoding="utf-8")
    assert "No delete commands generated." in text
    assert "git push --delete" not in text


def test_delete_script_uses_only_explicit_delete_records(tmp_path):
    target = tmp_path / "delete.sh"
    deleted = _record("topic", "DELETE", brr.build_delete_command("topic"))
    protected = _record("main", "KEEP")
    brr.write_deletion_script([protected, deleted], target)
    text = target.read_text(encoding="utf-8")
    assert text.count("git push --delete") == 1
    assert "origin -- topic" in text
    assert "origin -- main" not in text


@pytest.mark.parametrize("branch", ["space name", "feat/'quoted'", "semi;colon"])
def test_delete_command_quotes_untrusted_branch_name(branch):
    import shlex

    assert brr.build_delete_command(branch) == (
        "git push --delete origin -- " + shlex.quote(branch)
    )


def test_report_marks_unknown_age_and_counts_blank(tmp_path, monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(brr, "default_base", lambda repo: "main")
    params = SimpleNamespace(base=None, stale_days=60)
    target = tmp_path / "report.md"
    rec = brr.BranchRecord(
        branch="topic",
        ref="origin/topic",
        sha="b" * 40,
        last_commit_iso="unknown",
        age_days=None,
        ahead=None,
        behind=None,
        pr=None,
        classification="KEEP",
        rationale="no PR metadata; manual review",
        delete_command="",
    )
    brr.write_markdown([rec], ["PR metadata unavailable"], target, tmp_path, params)
    text = target.read_text(encoding="utf-8")
    assert "PR metadata unavailable" in text
    assert "no PR metadata; manual review" in text
    assert "Base branch: `main`" in text
    assert "unknown" in text


def test_parse_args_preserves_default_nondestructive_controls():
    args = brr.parse_args([])
    assert args.force_stale is False
    assert args.no_fetch is False
    assert args.protect_pr == []
    assert args.stale_days == 60


def test_build_records_is_conservative_without_origin(monkeypatch, tmp_path):
    from types import SimpleNamespace

    monkeypatch.setattr(brr, "optional_git", lambda *a: "")
    monkeypatch.setattr(brr, "remote_branches", lambda repo: [])
    monkeypatch.setattr(brr, "fetch_prs", lambda repo, slug: {})
    rows, warnings = brr.build_records(
        tmp_path,
        SimpleNamespace(
            no_fetch=True, base="main", protect_pr=[], stale_days=60, force_stale=False
        ),
    )
    assert rows == []
    assert any("No origin remote" in w for w in warnings)
    assert any("Base ref" in w for w in warnings)


def test_main_rejects_checkout_without_git_metadata(tmp_path):
    assert brr.main(["--repo", str(tmp_path)]) == 2
