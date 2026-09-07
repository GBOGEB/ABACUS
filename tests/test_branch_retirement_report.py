from pathlib import Path
from types import SimpleNamespace

from scripts import branch_retirement_report as brr


def test_selected_base_branch_is_always_kept() -> None:
    classification, rationale = brr.classify(
        "trunk",
        "origin/trunk",
        "trunk",
        "refs/remotes/origin/trunk",
        Path("."),
        None,
        set(),
        60,
        1,
        False,
    )
    assert classification == "KEEP"
    assert "selected base branch" in rationale


def test_closed_unmerged_pr_with_unique_commits_is_not_deleted(monkeypatch) -> None:
    monkeypatch.setattr(brr, "run", lambda *args, **kwargs: SimpleNamespace(returncode=1))
    pr = brr.PullRequest(17, "closed", "CLOSED", "topic", "main", "https://example.test/pr/17", "", None)

    classification, rationale = brr.classify(
        "topic",
        "origin/topic",
        "main",
        "refs/remotes/origin/main",
        Path("."),
        pr,
        set(),
        60,
        10,
        False,
    )

    assert classification == "CHERRY-PICK THEN DELETE"
    assert "closed unmerged" in rationale


def test_delete_command_shell_quotes_branch_and_terminates_options() -> None:
    command = brr.build_delete_command("topic/$(echo-pwn);`id`")

    assert command.startswith("git push --delete origin -- ")
    assert "'topic/$(echo-pwn);`id`'" in command
