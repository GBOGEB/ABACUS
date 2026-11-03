"""Behaviour tests for ci_monitor_local.py.

PyGithub is not installed in CI, so a stand-in ``github`` module is supplied
only while the module loads (the pip-install fallback is never reached) and
the GitHub client is replaced with in-memory fakes.
"""

import sys
import types

import pytest

from tests.coverage_waves.lane_b._l2_loader import load


class _FakeGithubException(Exception):
    pass


def _fake_github_module():
    fake = types.ModuleType("github")

    class Github:
        def __init__(self, *args, **kwargs):
            raise AssertionError("real Github client must be patched in tests")

    fake.Github = Github
    fake.GithubException = _FakeGithubException
    return fake


mod = load(
    "ci_monitor_local.py",
    name="abn_ci_monitor_local",
    deps={"github": _fake_github_module()},
)

CRED = "fake-cred-value"


def _check(name, conclusion, status="completed"):
    return types.SimpleNamespace(
        name=name, status=status, conclusion=conclusion, html_url="https://c/" + name
    )


def _commit(sha, checks):
    return types.SimpleNamespace(sha=sha, get_check_runs=lambda: list(checks))


class _FakePR:
    def __init__(self, commits, title="Fix things"):
        self.commits = commits
        self.title = title
        self.comments = []

    def get_commits(self):
        return iter(self.commits)

    def create_issue_comment(self, text):
        self.comments.append(text)


class _FakeRepo:
    full_name = "owner/repo"

    def __init__(self, pr, runs=(), issue_error=None):
        self.pr = pr
        self.runs = list(runs)
        self.issue_error = issue_error
        self.created = []
        self.run_queries = []

    def get_pull(self, number):
        self.pr_number = number
        return self.pr

    def get_workflow_runs(self, head_sha, status):
        self.run_queries.append((head_sha, status))
        return self.runs

    def create_issue(self, title, body, labels):
        if self.issue_error is not None:
            raise self.issue_error
        self.created.append(dict(title=title, body=body, labels=labels))
        return types.SimpleNamespace(number=100 + len(self.created))


def _install_client(monkeypatch, repo, existing=()):
    seen = dict(queries=[])

    class Client:
        def __init__(self, cred):
            seen["cred"] = cred

        def get_repo(self, name):
            seen["repo"] = name
            return repo

        def search_issues(self, query):
            seen["queries"].append(query)
            return iter(existing)

    monkeypatch.setattr(mod, "Github", Client)
    return seen


def _monitor(monkeypatch, commits, existing=(), **repo_kwargs):
    repo = _FakeRepo(_FakePR(commits), **repo_kwargs)
    seen = _install_client(monkeypatch, repo, existing)
    return mod.LocalCIMonitor(CRED, "owner/repo", 7), repo, seen


MIXED = [
    _commit("old0000000", []),
    _commit(
        "abcdef123456",
        [
            _check("lint", "success"),
            _check("tests", "failure"),
            _check("docs", None, status="in_progress"),
        ],
    ),
]


def test_constructor_wires_repo_and_pull(monkeypatch):
    monitor, repo, seen = _monitor(monkeypatch, MIXED)
    assert seen["cred"] == CRED
    assert seen["repo"] == "owner/repo"
    assert repo.pr_number == 7
    assert monitor.pr_number == 7


def test_ci_status_without_commits(monkeypatch):
    monitor, _, _ = _monitor(monkeypatch, [])
    assert monitor.get_ci_status() == {"status": "unknown", "checks": []}


def test_ci_status_counts_latest_commit(monkeypatch):
    monitor, _, _ = _monitor(monkeypatch, MIXED)

    status = monitor.get_ci_status()

    assert status["commit"] == "abcdef1"
    assert status["status"] == "failed"
    assert (status["total"], status["failed"], status["pending"]) == (3, 1, 1)
    assert sum(1 for c in status["checks"] if c["conclusion"] == "success") == 1
    assert status["checks"][0]["url"] == "https://c/lint"


def test_ci_status_pending_success_and_empty(monkeypatch):
    pending, _, _ = _monitor(
        monkeypatch, [_commit("p" * 10, [_check("a", "success"), _check("b", None)])]
    )
    assert pending.get_ci_status()["status"] == "pending"

    green, _, _ = _monitor(monkeypatch, [_commit("g" * 10, [_check("a", "success")])])
    assert green.get_ci_status()["status"] == "success"

    empty, _, _ = _monitor(monkeypatch, [_commit("e" * 10, [])])
    assert empty.get_ci_status()["status"] == "success"


def test_display_status_lists_checks(monkeypatch, capsys):
    monitor, _, _ = _monitor(monkeypatch, MIXED)

    monitor.display_status(monitor.get_ci_status())

    out = capsys.readouterr().out
    assert "CI/CD Status for PR #7" in out
    assert "Title: Fix things" in out
    assert "Commit: abcdef1" in out
    assert "FAILED" in out
    assert "Total Checks: 3" in out
    assert "tests: failure" in out
    assert "docs: in_progress" in out


def test_display_status_without_checks(monkeypatch, capsys):
    monitor, _, _ = _monitor(monkeypatch, [_commit("e" * 10, [])])

    monitor.display_status(monitor.get_ci_status())

    out = capsys.readouterr().out
    assert "SUCCESS" in out
    assert "Check Details" not in out


@pytest.mark.parametrize(
    "value,expected",
    [
        ("success", "SUCCESS"),
        ("failed", "FAILED"),
        ("pending", "PENDING"),
        ("other", "UNKNOWN"),
    ],
)
def test_format_status(monkeypatch, value, expected):
    monitor, _, _ = _monitor(monkeypatch, [])
    assert monitor._format_status(value).endswith(expected)


def test_check_icons_are_distinct(monkeypatch):
    monitor, _, _ = _monitor(monkeypatch, [])
    names = ["success", "failure", "cancelled", "skipped", None, "neutral"]
    icons = [monitor._get_check_icon(n) for n in names]
    assert len(set(icons[:5])) == 5
    assert icons[4] == icons[5]


def test_fetch_test_results_without_commits(monkeypatch, capsys):
    monitor, repo, _ = _monitor(monkeypatch, [])

    assert monitor.fetch_test_results() is None
    assert "No commits found" in capsys.readouterr().out
    assert repo.run_queries == []


def test_fetch_test_results_reports_test_artifacts(monkeypatch, capsys):
    artifacts = [
        types.SimpleNamespace(name="Test-Results"),
        types.SimpleNamespace(name="coverage"),
    ]
    run = types.SimpleNamespace(get_artifacts=lambda: artifacts)
    monitor, repo, _ = _monitor(monkeypatch, MIXED, runs=[run])

    assert monitor.fetch_test_results() is None

    assert repo.run_queries == [("abcdef123456", "completed")]
    out = capsys.readouterr().out
    assert "Found artifact: Test-Results" in out
    assert "coverage" not in out


def test_create_issues_noop_without_failures(monkeypatch, capsys):
    monitor, repo, seen = _monitor(monkeypatch, MIXED)

    monitor.create_issues_from_failures(dict(failed=0, checks=[]))

    assert "No failures to create issues for" in capsys.readouterr().out
    assert repo.created == []
    assert seen["queries"] == []


def test_create_issues_files_issue_and_comments_on_pr(monkeypatch, capsys):
    monitor, repo, seen = _monitor(monkeypatch, MIXED)

    monitor.create_issues_from_failures(monitor.get_ci_status())

    assert len(repo.created) == 1
    issue = repo.created[0]
    assert issue["title"].endswith("CI Failure: tests")
    assert "ci-failure" in issue["labels"]
    assert "**PR:** #7" in issue["body"]
    assert "https://c/tests" in issue["body"]
    assert 'label:ci-failure "tests"' in seen["queries"][0]
    assert repo.pr.comments == [
        "\U0001f517 Created issue #101 for failing check: tests"
    ]
    assert "Created issue #101" in capsys.readouterr().out


def test_create_issue_skips_when_one_exists(monkeypatch, capsys):
    existing = [types.SimpleNamespace(number=55)]
    monitor, repo, _ = _monitor(monkeypatch, MIXED, existing=existing)

    monitor._create_issue_for_check(dict(name="tests", conclusion="failure", url="u"))

    assert repo.created == []
    assert "Issue already exists for tests: #55" in capsys.readouterr().out


def test_create_issue_reports_github_errors(monkeypatch, capsys):
    monitor, repo, _ = _monitor(
        monkeypatch, MIXED, issue_error=_FakeGithubException("forbidden")
    )

    monitor._create_issue_for_check(dict(name="tests", conclusion="failure", url="u"))

    assert repo.pr.comments == []
    assert "Failed to create issue: forbidden" in capsys.readouterr().out


def _sequence_monitor(monkeypatch, statuses):
    monitor, _, _ = _monitor(monkeypatch, MIXED)
    queue = list(statuses)
    monkeypatch.setattr(monitor, "get_ci_status", lambda: queue.pop(0))
    monkeypatch.setattr(monitor, "display_status", lambda status: None)
    sleeps = []
    monkeypatch.setattr(mod.time, "sleep", sleeps.append)
    return monitor, sleeps


def test_watch_ci_polls_until_success(monkeypatch, capsys):
    monitor, sleeps = _sequence_monitor(
        monkeypatch, [dict(status="pending"), dict(status="success")]
    )

    monitor.watch_ci(interval=5)

    assert sleeps == [5]
    out = capsys.readouterr().out
    assert "Waiting 5s" in out
    assert "All checks passed" in out


def test_watch_ci_stops_on_failure(monkeypatch, capsys):
    monitor, sleeps = _sequence_monitor(monkeypatch, [dict(status="failed")])

    monitor.watch_ci(interval=1)

    assert sleeps == []
    assert "Some checks failed" in capsys.readouterr().out


def test_watch_ci_handles_ctrl_c(monkeypatch, capsys):
    monitor, _ = _sequence_monitor(monkeypatch, [dict(status="pending")])

    def interrupt(seconds):
        raise KeyboardInterrupt

    monkeypatch.setattr(mod.time, "sleep", interrupt)

    monitor.watch_ci(interval=1)

    assert "Stopped watching" in capsys.readouterr().out


def _fake_run(results):
    calls = []

    def fake(cmd, **kwargs):
        calls.append(cmd)
        result = results.get(cmd[0])
        if isinstance(result, BaseException):
            raise result
        return result

    return fake, calls


def test_get_github_token_prefers_cli(monkeypatch):
    fake, calls = _fake_run({"gh": types.SimpleNamespace(stdout="cli-value\n")})
    monkeypatch.setattr(mod.subprocess, "run", fake)

    assert mod.get_github_token() == ("cli-value", "GitHub CLI")
    assert calls == [["gh", "auth", "token"]]


def test_get_github_token_env_after_cli_error(monkeypatch):
    error = mod.subprocess.CalledProcessError(1, ["gh"])
    fake, _ = _fake_run({"gh": error})
    monkeypatch.setattr(mod.subprocess, "run", fake)
    monkeypatch.setenv("GITHUB_TOKEN", "env-value")

    assert mod.get_github_token() == ("env-value", "Environment Variable")


def test_get_github_token_none_when_empty(monkeypatch):
    fake, _ = _fake_run({"gh": types.SimpleNamespace(stdout="")})
    monkeypatch.setattr(mod.subprocess, "run", fake)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    assert mod.get_github_token() == (None, None)


def _run_main(monkeypatch, argv, git_result=None, token=(None, None), commits=None):
    monkeypatch.setattr(sys, "argv", ["ci_monitor_local.py"] + argv)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.setattr(mod, "get_github_token", lambda: token)
    fake, calls = _fake_run({"git": git_result})
    monkeypatch.setattr(mod.subprocess, "run", fake)
    repo = _FakeRepo(_FakePR(MIXED if commits is None else commits))
    seen = _install_client(monkeypatch, repo)
    mod.main()
    return seen, repo, calls


def test_main_requires_authentication(monkeypatch, capsys):
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, ["--pr", "7"])
    assert exc.value.code == 1
    assert "GitHub authentication required" in capsys.readouterr().out


def test_main_discovers_repo_from_git_remote(monkeypatch, capsys):
    remote = types.SimpleNamespace(
        returncode=0, stdout="https://github.com/org/proj.git\n"
    )
    seen, repo, calls = _run_main(
        monkeypatch, ["--pr", "7"], git_result=remote, token=(CRED, "GitHub CLI")
    )

    assert seen["repo"] == "org/proj"
    assert calls == [["git", "remote", "get-url", "origin"]]
    assert repo.created == []
    out = capsys.readouterr().out
    assert "Authenticated via: GitHub CLI" in out
    assert "PR Number: #7" in out
    assert "FAILED" in out


def test_main_git_remote_oserror_is_reported(monkeypatch, capsys):
    with pytest.raises(SystemExit) as exc:
        _run_main(
            monkeypatch, ["--pr", "7", "--token", CRED], git_result=OSError("nogit")
        )
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "Could not determine repository from git remote: nogit" in captured.err
    assert "Repository name required" in captured.out


@pytest.mark.parametrize(
    "git_result",
    [
        types.SimpleNamespace(returncode=128, stdout=""),
        types.SimpleNamespace(returncode=0, stdout="https://example.org/a/b.git"),
    ],
)
def test_main_exits_when_remote_is_unusable(monkeypatch, capsys, git_result):
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, ["--pr", "7", "--token", CRED], git_result=git_result)
    assert exc.value.code == 1
    assert "Authenticated via: Command Line" in capsys.readouterr().out


def test_main_create_issues_and_watch(monkeypatch, capsys):
    monkeypatch.setenv("GITHUB_REPOSITORY", "env/repo")
    monkeypatch.setattr(
        sys,
        "argv",
        ["ci_monitor_local.py", "--pr", "9", "--token", CRED, "--create-issues"]
        + ["--watch", "--interval", "2"],
    )
    repo = _FakeRepo(_FakePR(MIXED))
    seen = _install_client(monkeypatch, repo)
    monkeypatch.setattr(mod.time, "sleep", lambda seconds: None)

    mod.main()

    assert seen["repo"] == "env/repo"
    assert repo.pr_number == 9
    assert len(repo.created) == 1
    out = capsys.readouterr().out
    assert "Watching CI/CD status (checking every 2s)" in out
    assert "Some checks failed" in out
