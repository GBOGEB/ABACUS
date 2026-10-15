"""C1 tests for conservative branch-retirement and non-destructive decisions.

Coverage target: scripts/branch_retirement_report.py.
No git network calls or actual branch deletion are performed.
"""

from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import branch_retirement_report as brr


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://github.com/GBOGEB/ABACUS.git", "GBOGEB/ABACUS"),
        ("git@github.com:GBOGEB/ABACUS.git", "GBOGEB/ABACUS"),
        ("https://github.com/GBOGEB/ABACUS", "GBOGEB/ABACUS"),
        ("https://example.com/GBOGEB/ABACUS.git", None),
        ("", None),
    ],
)
def test_origin_slug_requires_github(url, expected):
    assert brr.normalize_origin_repo(url) == expected


@pytest.mark.parametrize(
    ("branch", "protected"),
    [
        ("main", True),
        ("master", True),
        ("develop", True),
        ("release/v1", True),
        ("hotfix/severity-1", True),
        ("feature/proposal", False),
        ("release-candidate", False),
    ],
)
def test_branch_name_protection(branch, protected):
    assert brr.is_protected_branch(branch) is protected


def test_default_base_prefers_remote_head(monkeypatch):
    monkeypatch.setattr(
        brr,
        "optional_git",
        lambda repo, *args: "origin/develop" if "symbolic-ref" in args else "",
    )
    assert brr.default_base(Path(".")) == "develop"


def test_default_base_uses_main_if_remote_head_unknown(monkeypatch):
    monkeypatch.setattr(
        brr,
        "optional_git",
        lambda repo, *args: "a" * 40 if "origin/main" in args else "",
    )
    assert brr.default_base(Path(".")) == "main"


def test_default_base_fails_conservatively(monkeypatch):
    monkeypatch.setattr(brr, "optional_git", lambda *args, **kwargs: "")
    assert brr.default_base(Path(".")) == "main"


def _pr(state="OPEN", number=24):
    return brr.PullRequest(
        number, "test", state, "topic", "main",
        "https://github.com/GBOGEB/ABACUS/pull/24", "", None
    )


def _classify(monkeypatch, pr, *, merged=False, age=None, force=False, protected=()):
    monkeypatch.setattr(
        brr, "run", lambda *args, **kwargs: SimpleNamespace(
            returncode=0 if merged else 1
        ),
    )
    return brr.classify(
        "topic", "origin/topic", "main", "refs/remotes/origin/main",
        Path("."), pr, set(protected), 60, age, force
    )


def test_open_pr_is_never_deleted_even_when_reachable(monkeypatch):
    result, reason = _classify(monkeypatch, _pr(), merged=True)
    assert result == "KEEP"
    assert "open PR" in reason


def test_operator_protected_pr_is_kept(monkeypatch):
    result, reason = _classify(
        monkeypatch, _pr("MERGED"), merged=True, protected=(24,)
    )
    assert result == "KEEP"
    assert "explicitly protected" in reason


def test_proven_reachable_branch_may_be_retired(monkeypatch):
    result, reason = _classify(monkeypatch, None, merged=True)
    assert result == "DELETE"
    assert "reachable" in reason


def test_merged_pr_with_unreachable_tip_may_be_retired(monkeypatch):
    result, reason = _classify(monkeypatch, _pr("MERGED"))
    assert result == "DELETE"
    assert "merged" in reason


def test_closed_unmerged_pr_preserves_unique_commits(monkeypatch):
    result, reason = _classify(monkeypatch, _pr("CLOSED"))
    assert result == "CHERRY-PICK THEN DELETE"
    assert "unique commits" in reason


@pytest.mark.parametrize("age", [None, 1, 59, 60, 120])
def test_unknown_pr_never_auto_deleted_without_override(monkeypatch, age):
    result, _ = _classify(monkeypatch, None, age=age)
    assert result != "DELETE"


def test_force_stale_requires_known_age_and_threshold(monkeypatch):
    assert _classify(monkeypatch, None, age=60, force=True)[0] == "DELETE"
    assert _classify(monkeypatch, None, age=59, force=True)[0] == "KEEP"
    assert _classify(monkeypatch, None, age=None, force=True)[0] == "KEEP"


def test_active_unmerged_pr_classified_for_merge_not_delete(monkeypatch):
    result, reason = _classify(monkeypatch, _pr("REVIEW"))
    assert result == "MERGE"
    assert "unique commits" in reason


def test_invalid_commit_time_carries_unknown_age(monkeypatch):
    monkeypatch.setattr(brr, "optional_git", lambda *args, **kwargs: "invalid")
    value, age = brr.commit_age(Path("."), "origin/topic", brr.datetime.now(
        brr.timezone.utc
    ))
    assert value == "invalid"
    assert age is None


def test_missing_commit_time_carries_unknown_age(monkeypatch):
    monkeypatch.setattr(brr, "optional_git", lambda *args, **kwargs: "")
    assert brr.commit_age(
        Path("."), "origin/topic", brr.datetime.now(brr.timezone.utc)
    ) == ("unknown", None)


def test_optional_git_returns_empty_after_failed_command(monkeypatch):
    monkeypatch.setattr(
        brr, "run", lambda *args, **kwargs: SimpleNamespace(
            stdout="unsafe", returncode=1
        ),
    )
    assert brr.optional_git(Path("."), "status") == ""


def test_missing_gh_command_never_fabricates_pr_metadata(monkeypatch):
    monkeypatch.setattr(brr, "has_command", lambda value: False)
    assert brr.fetch_prs(Path("."), "GBOGEB/ABACUS") == {}


def test_remote_branches_ignore_head_and_empty_lines(monkeypatch):
    monkeypatch.setattr(
        brr,
        "optional_git",
        lambda *args, **kwargs: (
            "origin/HEAD aaa\n\norigin/main bbb\norigin/topic ccc"
        ),
    )
    assert brr.remote_branches(Path(".")) == [
        ("origin/main", "bbb"), ("origin/topic", "ccc")
    ]
