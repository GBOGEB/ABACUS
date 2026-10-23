"""Lane L1: behavioural coverage for ``github_tracking_manager``.

Hermetic: the PyGithub client is replaced by in-memory fakes, every state file
is written under ``tmp_path`` (the module writes relative to the CWD, so each
test ``chdir``s into ``tmp_path``), and ``subprocess.run``/``check_call`` are
replaced so no real ``gh``/``git``/``pip`` process is ever launched.

The module is executed from its file path under a private module name so the
canonical ``sys.modules["github_tracking_manager"]`` entry is never replaced
and PyGithub need not be installed on the runner.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "github_tracking_manager.py"
REPO_NAME = "GBOGEB/ABACUS"
T0 = datetime(2026, 10, 1, 12, 0, 0)
T1 = datetime(2026, 10, 2, 9, 30, 0)

# The frozen source uses datetime.utcnow(); its 3.12 deprecation is not under test.
pytestmark = pytest.mark.filterwarnings(
    "ignore:datetime.datetime.utcnow:DeprecationWarning"
)


# --------------------------------------------------------------------------
# Fakes
# --------------------------------------------------------------------------
class FakeRepo:
    def __init__(self):
        self.pulls: dict[int, SimpleNamespace] = {}
        self.created_issues: list[dict] = []
        self.next_issue = 900
        self.create_error: Exception | None = None
        self.get_pull_calls: list[int] = []

    def get_pull(self, number):
        self.get_pull_calls.append(number)
        if number not in self.pulls:
            raise RuntimeError(f"404 pull {number} not found")
        return self.pulls[number]

    def create_issue(self, title, body, labels):
        if self.create_error is not None:
            raise self.create_error
        self.next_issue += 1
        self.created_issues.append({"title": title, "body": body, "labels": labels})
        return SimpleNamespace(
            number=self.next_issue,
            title=title,
            labels=[SimpleNamespace(name=label) for label in labels],
            created_at=T0,
        )


def make_check(
    run_id, conclusion="success", status="completed", started=T0, completed=T1
):
    return SimpleNamespace(
        id=run_id,
        name=f"ci-job-{run_id}",
        status=status,
        conclusion=conclusion,
        started_at=started,
        completed_at=completed,
        html_url=f"https://example.invalid/runs/{run_id}",
    )


def make_commit(sha, checks):
    return SimpleNamespace(sha=sha, get_check_runs=lambda: list(checks))


def make_pr(
    *,
    title="Add feature",
    branch="feat/x",
    merged=False,
    merged_at=None,
    closed_at=None,
    reviewers=(),
    commits=(),
    files=(),
):
    return SimpleNamespace(
        title=title,
        head=SimpleNamespace(ref=branch),
        created_at=T0,
        user=SimpleNamespace(login="octocat"),
        merged=merged,
        merged_at=merged_at,
        closed_at=closed_at,
        get_reviews=lambda: [SimpleNamespace(login=r) for r in reviewers],
        get_commits=lambda: list(commits),
        get_files=lambda: [SimpleNamespace(filename=f) for f in files],
    )


class FakeGithubFactory:
    """Stands in for ``github.Github``; records tokens and repo lookups."""

    def __init__(self, repo: FakeRepo):
        self.repo = repo
        self.tokens: list[str] = []
        self.repo_lookups: list[str] = []

    def __call__(self, token):
        self.tokens.append(token)
        factory = self

        class _Client:
            def get_repo(self, name):
                factory.repo_lookups.append(name)
                return factory.repo

        return _Client()


def _exec_module(name: str):
    spec = importlib.util.spec_from_file_location(name, MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------
@pytest.fixture
def gtm(monkeypatch):
    fake_github = types.ModuleType("github")
    fake_github.Github = object  # replaced per-test via the ``github`` fixture
    monkeypatch.setitem(sys.modules, "github", fake_github)
    return _exec_module("_l1_github_tracking_manager")


@pytest.fixture
def repo():
    return FakeRepo()


@pytest.fixture
def client(gtm, repo, monkeypatch):
    factory = FakeGithubFactory(repo)
    monkeypatch.setattr(gtm, "Github", factory)
    return factory


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    return tmp_path


@pytest.fixture
def manager(gtm, client, workdir):
    return gtm.GitHubTrackingManager("tok-test", REPO_NAME)


def _disk_state(workdir: Path):
    return json.loads((workdir / "github_tracking_state.json").read_text())


# --------------------------------------------------------------------------
# Import-time dependency fallback (lines 25-28)
# --------------------------------------------------------------------------
def test_missing_pygithub_triggers_pip_install_then_reimport(gtm, monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "github", None)  # forces ImportError
    installed = types.ModuleType("github")

    class InstalledGithub:
        pass

    installed.Github = InstalledGithub
    calls = []

    def fake_check_call(cmd):
        calls.append(cmd)
        sys.modules["github"] = installed  # simulate a successful install

    monkeypatch.setattr(gtm.subprocess, "check_call", fake_check_call)
    module = _exec_module("_l1_gtm_fallback_ok")

    assert calls == [
        [sys.executable, "-m", "pip", "install", "-q", "PyGithub", "PyYAML"]
    ]
    assert module.Github is InstalledGithub
    assert "Installing PyGithub" in capsys.readouterr().out


def test_failed_pygithub_install_aborts_import(gtm, monkeypatch):
    monkeypatch.setitem(sys.modules, "github", None)

    def failing_check_call(cmd):
        raise gtm.subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(gtm.subprocess, "check_call", failing_check_call)
    with pytest.raises(gtm.subprocess.CalledProcessError):
        _exec_module("_l1_gtm_fallback_fail")


# --------------------------------------------------------------------------
# Construction, state load/save round-trip, malformed / missing state
# --------------------------------------------------------------------------
def test_init_without_state_file_creates_empty_state(manager, client, workdir):
    assert client.tokens == ["tok-test"]
    assert client.repo_lookups == [REPO_NAME]
    assert manager.repo_name == REPO_NAME
    assert manager.json_file == Path("github_tracking_state.json")
    state = manager.state
    assert state["metadata"]["repository"] == REPO_NAME
    assert state["metadata"]["version"] == "1.0.0"
    assert state["metadata"]["last_updated"].endswith("Z")
    assert state["pull_requests"] == {} and state["issues"] == {}
    assert state["ci_cd_history"] == {
        "ci_runs": [],
        "cd_deployments": [],
        "missed_opportunities": [],
    }
    assert state["copilot_feedback_queue"] == [] and state["action_items"] == []
    # Missing artifact: constructing must not create files on its own.
    assert not (workdir / "github_tracking_state.json").exists()
    assert not (workdir / "github_tracking_state.yaml").exists()


def test_save_then_reload_round_trips_json_and_yaml(gtm, client, workdir, capsys):
    first = gtm.GitHubTrackingManager("tok", REPO_NAME)
    first.create_action_item(
        "Fix flaky test", "desc", priority="high", category="ci", related_pr=7
    )
    first._save_state()
    out = capsys.readouterr().out
    assert (
        "State saved to github_tracking_state.json and github_tracking_state.yaml"
        in out
    )

    json_state = _disk_state(workdir)
    yaml_state = yaml.safe_load((workdir / "github_tracking_state.yaml").read_text())
    assert json_state == yaml_state == first.state

    second = gtm.GitHubTrackingManager("tok", REPO_NAME)
    assert second.state == first.state
    assert second.state["action_items"][0]["title"] == "Fix flaky test"


def test_save_state_refreshes_last_updated(manager, workdir):
    manager.state["metadata"]["last_updated"] = "stale"
    manager._save_state()
    assert manager.state["metadata"]["last_updated"] != "stale"
    assert (
        _disk_state(workdir)["metadata"]["last_updated"]
        == manager.state["metadata"]["last_updated"]
    )


def test_malformed_json_state_fails_closed(gtm, client, workdir):
    (workdir / "github_tracking_state.json").write_text(
        "{not valid json", encoding="utf-8"
    )
    with pytest.raises(json.JSONDecodeError):
        gtm.GitHubTrackingManager("tok", REPO_NAME)
    # The corrupt file is left untouched rather than silently reset.
    assert (workdir / "github_tracking_state.json").read_text() == "{not valid json"


def test_yaml_only_state_is_ignored_json_is_source_of_truth(gtm, client, workdir):
    (workdir / "github_tracking_state.yaml").write_text(
        yaml.safe_dump({"pull_requests": {"1": {}}}), encoding="utf-8"
    )
    mgr = gtm.GitHubTrackingManager("tok", REPO_NAME)
    assert mgr.state["pull_requests"] == {}


# --------------------------------------------------------------------------
# sync_pr
# --------------------------------------------------------------------------
def test_sync_pr_new_open_pr_records_fields(manager, repo, workdir, capsys):
    repo.pulls[5] = make_pr(reviewers=("alice", "bob"))
    manager.sync_pr(5)

    pr = manager.state["pull_requests"]["5"]
    assert pr["number"] == 5
    assert pr["title"] == "Add feature"
    assert pr["branch"] == "feat/x"
    assert pr["author"] == "octocat"
    assert pr["status"] == "open"
    assert pr["created_at"] == T0.isoformat() + "Z"
    assert pr["reviewers"] == ["alice", "bob"]
    assert "merged_at" not in pr and "closed_at" not in pr
    assert _disk_state(workdir)["pull_requests"]["5"] == pr
    assert "PR #5 synced: open" in capsys.readouterr().out


def test_sync_pr_twice_is_idempotent_and_updates_stale_status(manager, repo, workdir):
    repo.pulls[5] = make_pr(reviewers=("alice",))
    manager.sync_pr(5)
    manager.state["pull_requests"]["5"]["tags"].append("keep-me")

    repo.pulls[5] = make_pr(
        title="Add feature v2",
        merged=True,
        merged_at=T1,
        closed_at=T1,
        reviewers=("alice",),
    )
    manager.sync_pr(5)

    assert list(manager.state["pull_requests"]) == ["5"]
    pr = manager.state["pull_requests"]["5"]
    assert pr["status"] == "merged"
    assert pr["title"] == "Add feature v2"
    assert pr["merged_at"] == pr["closed_at"] == T1.isoformat() + "Z"
    assert pr["reviewers"] == ["alice"]
    assert pr["tags"] == ["keep-me"]  # locally-tracked fields survive a resync
    assert _disk_state(workdir)["pull_requests"]["5"]["status"] == "merged"


def test_sync_pr_closed_without_merge(manager, repo):
    repo.pulls[6] = make_pr(closed_at=T1)
    manager.sync_pr(6)
    pr = manager.state["pull_requests"]["6"]
    assert pr["status"] == "closed"
    assert pr["closed_at"] == T1.isoformat() + "Z"
    assert "merged_at" not in pr


def test_sync_pr_fetch_error_leaves_state_and_disk_untouched(manager, workdir, capsys):
    manager.sync_pr(404)
    assert manager.state["pull_requests"] == {}
    assert not (workdir / "github_tracking_state.json").exists()
    assert "Error fetching PR #404" in capsys.readouterr().out


# --------------------------------------------------------------------------
# sync_ci_runs
# --------------------------------------------------------------------------
def test_sync_ci_runs_untracked_pr_syncs_pr_and_records_runs(
    manager, repo, workdir, capsys
):
    checks = [
        make_check(1, "success"),
        make_check(2, None, status="in_progress", started=None, completed=None),
    ]
    repo.pulls[9] = make_pr(commits=[make_commit("aaa", checks)])
    manager.sync_ci_runs(9)

    pr = manager.state["pull_requests"]["9"]
    assert [r["run_id"] for r in pr["ci_runs"]] == [1, 2]
    first, second = pr["ci_runs"]
    assert first["conclusion"] == "success"
    assert first["started_at"] == T0.isoformat() + "Z"
    assert first["completed_at"] == T1.isoformat() + "Z"
    assert first["workflow"] == "ci-job-1"
    assert first["url"].endswith("/runs/1")
    assert second["started_at"] is None and second["completed_at"] is None
    history = manager.state["ci_cd_history"]["ci_runs"]
    assert [(h["run_id"], h["pr_number"]) for h in history] == [(1, 9), (2, 9)]
    assert _disk_state(workdir)["pull_requests"]["9"]["ci_runs"] == pr["ci_runs"]
    assert "Synced 2 CI runs" in capsys.readouterr().out


def test_sync_ci_runs_duplicate_sync_dedupes_per_pr_but_appends_history(manager, repo):
    """Per-PR run list is keyed by run_id; the global history is an append log.

    Documents current behaviour: re-syncing the same check run updates it in
    place on the PR, but appends a second copy to ``ci_cd_history.ci_runs``.
    """
    repo.pulls[9] = make_pr(
        commits=[make_commit("aaa", [make_check(1, None, status="in_progress")])]
    )
    manager.sync_ci_runs(9)
    repo.pulls[9] = make_pr(commits=[make_commit("aaa", [make_check(1, "failure")])])
    manager.sync_ci_runs(9)

    runs = manager.state["pull_requests"]["9"]["ci_runs"]
    assert len(runs) == 1
    assert runs[0]["conclusion"] == "failure" and runs[0]["status"] == "completed"
    history = manager.state["ci_cd_history"]["ci_runs"]
    assert [h["conclusion"] for h in history] == [None, "failure"]


def test_sync_ci_runs_stale_sha_runs_are_retained_without_sha(manager, repo):
    """Only the latest commit's checks are fetched; runs from an older head SHA
    stay in the PR record and nothing records which SHA they belong to."""
    old = make_commit("old-sha", [make_check(10, "failure")])
    repo.pulls[3] = make_pr(commits=[old])
    manager.sync_ci_runs(3)

    new = make_commit("new-sha", [make_check(11, "success")])
    repo.pulls[3] = make_pr(commits=[old, new])
    manager.sync_ci_runs(3)

    runs = manager.state["pull_requests"]["3"]["ci_runs"]
    assert [(r["run_id"], r["conclusion"]) for r in runs] == [
        (10, "failure"),
        (11, "success"),
    ]
    assert all("sha" not in key for r in runs for key in r)


def test_sync_ci_runs_no_commits_returns_without_saving(manager, repo, workdir, capsys):
    repo.pulls[4] = make_pr(commits=[])
    manager.sync_ci_runs(4)
    assert manager.state["pull_requests"] == {}
    assert not (workdir / "github_tracking_state.json").exists()
    assert "No commits found" in capsys.readouterr().out


def test_sync_ci_runs_error_is_reported_not_raised(manager, workdir, capsys):
    manager.sync_ci_runs(404)
    assert manager.state["ci_cd_history"]["ci_runs"] == []
    assert not (workdir / "github_tracking_state.json").exists()
    assert "Error syncing CI runs: 404 pull 404 not found" in capsys.readouterr().out


# --------------------------------------------------------------------------
# capture_copilot_feedback / create_action_item
# --------------------------------------------------------------------------
def test_capture_feedback_for_tracked_pr_updates_queue_and_pr(manager, repo, workdir):
    repo.pulls[12] = make_pr()
    manager.sync_pr(12)
    fid = manager.capture_copilot_feedback(
        12, "suggestion", "Use pathlib", file="a.py", line=3
    )

    assert fid.startswith("fb_12_")
    queued = manager.state["copilot_feedback_queue"]
    assert len(queued) == 1
    assert queued[0]["id"] == fid
    assert queued[0]["status"] == "pending"
    assert queued[0]["source"] == "github_copilot"
    assert queued[0]["implementation_pr"] is None
    pr_fb = manager.state["pull_requests"]["12"]["copilot_feedback"]
    assert pr_fb[0]["message"] == "Use pathlib"
    assert pr_fb[0]["action_taken"] is False
    assert pr_fb[0]["file"] == "a.py" and pr_fb[0]["line"] == 3
    assert _disk_state(workdir)["copilot_feedback_queue"][0]["id"] == fid


def test_capture_feedback_for_untracked_pr_only_queues(manager, workdir):
    fid = manager.capture_copilot_feedback(77, "review", "LGTM", source="human")
    assert manager.state["pull_requests"] == {}
    assert manager.state["copilot_feedback_queue"][0]["source"] == "human"
    assert _disk_state(workdir)["copilot_feedback_queue"][0]["id"] == fid


def test_duplicate_feedback_within_same_clock_tick_collides_on_id(
    gtm, manager, monkeypatch
):
    """Finding: feedback/action IDs derive solely from ``utcnow().timestamp()``.

    Two captures inside one clock tick (coarse on Windows) receive the same ID
    and the queue holds two distinct records sharing it; nothing de-duplicates
    identical submissions either.
    """
    fixed = datetime(2026, 10, 21, 8, 0, 0)

    class FrozenDatetime(datetime):
        @classmethod
        def utcnow(cls):
            return fixed

    monkeypatch.setattr(gtm, "datetime", FrozenDatetime)
    a = manager.capture_copilot_feedback(1, "bug", "same message")
    b = manager.capture_copilot_feedback(1, "bug", "same message")
    assert a == b
    assert [f["id"] for f in manager.state["copilot_feedback_queue"]] == [a, a]

    x = manager.create_action_item("t", "d")
    y = manager.create_action_item("t", "d")
    assert x == y == f"action_{fixed.timestamp()}"
    assert len(manager.state["action_items"]) == 2


def test_create_action_item_records_all_fields(manager, workdir, capsys):
    aid = manager.create_action_item(
        "Add branch protection",
        "Require CI",
        priority="critical",
        category="ci",
        related_pr=11,
        related_issue=22,
    )
    item = manager.state["action_items"][0]
    assert item["id"] == aid and aid.startswith("action_")
    assert item["priority"] == "critical"
    assert item["category"] == "ci"
    assert item["status"] == "pending"
    assert (item["related_pr"], item["related_issue"]) == (11, 22)
    assert _disk_state(workdir)["action_items"] == [item]
    assert f"Action item created: {aid}" in capsys.readouterr().out


# --------------------------------------------------------------------------
# analyze_missed_opportunities
# --------------------------------------------------------------------------
def test_analyze_merged_pr_without_ci_or_tests(manager, repo, workdir, capsys):
    repo.pulls[20] = make_pr(
        merged=True, commits=[make_commit("s", [])], files=["src/app.py"]
    )
    manager.analyze_missed_opportunities(20)

    opps = manager.state["ci_cd_history"]["missed_opportunities"]
    assert [o["type"] for o in opps] == ["ci_missing", "test_coverage"]
    assert opps[0]["priority"] == "high" and opps[1]["priority"] == "medium"
    assert _disk_state(workdir)["ci_cd_history"]["missed_opportunities"] == opps
    assert "Found 2 missed opportunities" in capsys.readouterr().out


def test_analyze_merged_with_failing_checks_and_tests_present(manager, repo):
    checks = [
        make_check(1, "failure"),
        make_check(2, "failure"),
        make_check(3, "success"),
    ]
    repo.pulls[21] = make_pr(
        merged=True,
        commits=[make_commit("s", checks)],
        files=["src/app.py", "tests/test_app.py"],
    )
    manager.analyze_missed_opportunities(21)
    opps = manager.state["ci_cd_history"]["missed_opportunities"]
    assert [o["type"] for o in opps] == ["ci_failure_merged"]
    assert opps[0]["description"] == "PR merged with 2 failing checks"
    assert opps[0]["priority"] == "critical"


def test_analyze_merged_pr_with_no_files_and_green_ci_is_clean(
    manager, repo, workdir, capsys
):
    repo.pulls[22] = make_pr(
        merged=True, commits=[make_commit("s", [make_check(1)])], files=[]
    )
    manager.analyze_missed_opportunities(22)
    assert manager.state["ci_cd_history"]["missed_opportunities"] == []
    assert "No missed opportunities found" in capsys.readouterr().out
    assert (workdir / "github_tracking_state.json").exists()


@pytest.mark.parametrize(
    "pr",
    [
        make_pr(merged=False, files=["src/app.py"]),
        make_pr(merged=True, commits=[], files=["src/app.py"]),
    ],
    ids=["unmerged", "merged-no-commits"],
)
def test_analyze_non_applicable_prs_find_nothing(manager, repo, pr):
    repo.pulls[23] = pr
    manager.analyze_missed_opportunities(23)
    assert manager.state["ci_cd_history"]["missed_opportunities"] == []


def test_analyze_twice_appends_duplicate_opportunities(manager, repo):
    """Documents current behaviour: re-analysis is not idempotent."""
    repo.pulls[24] = make_pr(merged=True, commits=[make_commit("s", [])], files=[])
    manager.analyze_missed_opportunities(24)
    manager.analyze_missed_opportunities(24)
    assert [
        o["type"] for o in manager.state["ci_cd_history"]["missed_opportunities"]
    ] == [
        "ci_missing",
        "ci_missing",
    ]


def test_analyze_error_is_reported(manager, workdir, capsys):
    manager.analyze_missed_opportunities(999)
    assert manager.state["ci_cd_history"]["missed_opportunities"] == []
    assert not (workdir / "github_tracking_state.json").exists()
    assert "Error analyzing opportunities" in capsys.readouterr().out


# --------------------------------------------------------------------------
# create_sub_issue
# --------------------------------------------------------------------------
def test_create_sub_issue_creates_parent_and_child_records(manager, repo, workdir):
    number = manager.create_sub_issue(100, "Split work", "Details here")

    assert number == 901
    sent = repo.created_issues[0]
    assert sent["title"] == "[Sub-Issue] Split work"
    assert sent["body"] == "**Parent Issue:** #100\n\nDetails here"
    assert sent["labels"] == ["sub-issue", "automated"]
    issues = manager.state["issues"]
    assert issues["100"]["sub_issues"] == [901]
    assert issues["100"]["title"] == "" and issues["100"]["parent_issue"] is None
    child = issues["901"]
    assert child["parent_issue"] == 100
    assert child["labels"] == ["sub-issue", "automated"]
    assert child["created_at"] == T0.isoformat() + "Z"
    assert _disk_state(workdir)["issues"] == issues


def test_create_sub_issue_twice_reuses_parent_and_creates_two_children(manager, repo):
    first = manager.create_sub_issue(100, "Same", "same body")
    second = manager.create_sub_issue(100, "Same", "same body")
    # No de-duplication: an identical request opens a second GitHub issue.
    assert (first, second) == (901, 902)
    assert len(repo.created_issues) == 2
    assert manager.state["issues"]["100"]["sub_issues"] == [901, 902]


def test_create_sub_issue_api_failure_returns_none(manager, repo, workdir, capsys):
    repo.create_error = RuntimeError("403 forbidden")
    assert manager.create_sub_issue(100, "t", "d") is None
    assert manager.state["issues"] == {}
    assert not (workdir / "github_tracking_state.json").exists()
    assert "Error creating sub-issue: 403 forbidden" in capsys.readouterr().out


# --------------------------------------------------------------------------
# review_feedback_queue / generate_report
# --------------------------------------------------------------------------
def test_review_feedback_queue_empty(manager, capsys):
    manager.review_feedback_queue()
    assert "No pending feedback items" in capsys.readouterr().out


def test_review_feedback_queue_lists_only_pending(manager, capsys):
    manager.capture_copilot_feedback(1, "bug", "with file", file="x.py", line=9)
    manager.capture_copilot_feedback(2, "style", "no file")
    manager.capture_copilot_feedback(3, "nit", "already handled")
    manager.state["copilot_feedback_queue"][2]["status"] = "implemented"
    capsys.readouterr()

    manager.review_feedback_queue()
    out = capsys.readouterr().out
    assert "Found 2 pending feedback items" in out
    assert "1. [BUG] PR #1" in out and "File: x.py:9" in out
    assert "2. [STYLE] PR #2" in out
    assert "already handled" not in out
    assert out.count("File:") == 1


def test_generate_report_for_tracked_pr(manager, repo, capsys):
    repo.pulls[30] = make_pr(
        title="Tracked", commits=[make_commit("s", [make_check(1)])]
    )
    manager.sync_ci_runs(30)
    manager.capture_copilot_feedback(30, "x", "y")
    capsys.readouterr()
    manager.generate_report(30)
    out = capsys.readouterr().out
    assert "PR #30: Tracked" in out
    assert "Branch: feat/x" in out and "Author: octocat" in out
    assert "CI Runs: 1" in out and "Copilot Feedback: 1" in out


def test_generate_report_unknown_pr(manager, capsys):
    manager.generate_report(31)
    assert "PR #31 not found in tracking state" in capsys.readouterr().out


def test_generate_report_summary_counts(manager, capsys):
    manager.capture_copilot_feedback(1, "a", "b")
    manager.create_action_item("t", "d")
    manager.create_action_item("done", "d")
    manager.state["action_items"][1]["status"] = "done"
    capsys.readouterr()
    manager.generate_report()
    out = capsys.readouterr().out
    assert "Total PRs: 0" in out
    assert "Pending Feedback: 1" in out
    assert "Action Items: 1" in out


# --------------------------------------------------------------------------
# get_github_token
# --------------------------------------------------------------------------
def _completed(gtm, cmd, rc=0, out="", err=""):
    return gtm.subprocess.CompletedProcess(cmd, rc, stdout=out, stderr=err)


def test_token_from_gh_cli(gtm, monkeypatch):
    seen = []

    def fake_run(cmd, **kw):
        seen.append((cmd, kw))
        return _completed(gtm, cmd, out="gho_cli_token\n")

    monkeypatch.setattr(gtm.subprocess, "run", fake_run)
    monkeypatch.setenv("GITHUB_TOKEN", "env-token")
    assert gtm.get_github_token() == ("gho_cli_token", "GitHub CLI")
    assert seen[0][0] == ["gh", "auth", "token"]
    assert seen[0][1]["check"] is True


@pytest.mark.parametrize("behaviour", ["empty", "nonzero", "missing-binary"])
def test_token_falls_back_to_env(gtm, monkeypatch, behaviour):
    def fake_run(cmd, **kw):
        if behaviour == "empty":
            return _completed(gtm, cmd, out="  \n")
        if behaviour == "nonzero":
            raise gtm.subprocess.CalledProcessError(1, cmd)
        raise FileNotFoundError("gh")

    monkeypatch.setattr(gtm.subprocess, "run", fake_run)
    monkeypatch.setenv("GITHUB_TOKEN", "env-token")
    assert gtm.get_github_token() == ("env-token", "Environment Variable")


def test_token_absent_everywhere(gtm, monkeypatch):
    monkeypatch.setattr(
        gtm.subprocess,
        "run",
        lambda cmd, **kw: (_ for _ in ()).throw(
            gtm.subprocess.CalledProcessError(4, cmd)
        ),
    )
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    assert gtm.get_github_token() == (None, None)


# --------------------------------------------------------------------------
# main() CLI
# --------------------------------------------------------------------------
def _cli(gtm, monkeypatch, argv, *, gh_cli_out=None, git_remote=None, git_error=None):
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        if cmd[:2] == ["gh", "auth"]:
            if gh_cli_out is None:
                raise gtm.subprocess.CalledProcessError(1, cmd)
            return _completed(gtm, cmd, out=gh_cli_out)
        if cmd[:2] == ["git", "remote"]:
            if git_error is not None:
                raise git_error
            if git_remote is None:
                return _completed(gtm, cmd, rc=2, err="no such remote")
            return _completed(gtm, cmd, out=git_remote)
        raise AssertionError(f"unexpected subprocess call {cmd}")

    monkeypatch.setattr(gtm.subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "argv", ["github_tracking_manager.py", *argv])
    return calls


def test_main_without_any_token_exits_1(gtm, workdir, monkeypatch, capsys):
    _cli(gtm, monkeypatch, ["--repo", REPO_NAME])
    with pytest.raises(SystemExit) as exc:
        gtm.main()
    assert exc.value.code == 1
    assert "GitHub authentication required" in capsys.readouterr().out


@pytest.mark.parametrize(
    "remote,error",
    [
        (None, None),  # git remote exits non-zero
        ("https://gitlab.example/x/y.git\n", None),  # not a GitHub remote
        (None, OSError("git not installed")),  # git binary missing
    ],
    ids=["remote-nonzero", "non-github-remote", "git-missing"],
)
def test_main_without_resolvable_repo_exits_1(
    gtm, workdir, monkeypatch, capsys, client, remote, error
):
    _cli(
        gtm,
        monkeypatch,
        ["--token", "t", "--report"],
        git_remote=remote,
        git_error=error,
    )
    with pytest.raises(SystemExit) as exc:
        gtm.main()
    assert exc.value.code == 1
    assert "Repository name required" in capsys.readouterr().out
    assert client.tokens == []  # never reached GitHub


@pytest.mark.parametrize(
    "remote",
    [
        "https://github.com/GBOGEB/ABACUS.git\n",
        "git@github.com:GBOGEB/ABACUS.git\n",
    ],
    ids=["https", "ssh"],
)
def test_main_repo_from_git_remote(gtm, workdir, monkeypatch, capsys, client, remote):
    _cli(gtm, monkeypatch, ["--report"], gh_cli_out="cli-tok\n", git_remote=remote)
    gtm.main()
    out = capsys.readouterr().out
    assert "Authenticated via: GitHub CLI" in out
    assert f"Repository: {REPO_NAME}" in out
    assert client.tokens == ["cli-tok"]
    assert client.repo_lookups == [REPO_NAME]
    assert "Total PRs: 0" in out


def test_main_repo_from_env_and_no_action(gtm, workdir, monkeypatch, capsys, client):
    calls = _cli(gtm, monkeypatch, [])
    monkeypatch.setenv("GITHUB_TOKEN", "env-tok")
    monkeypatch.setenv("GITHUB_REPOSITORY", "org/from-env")
    gtm.main()
    out = capsys.readouterr().out
    assert "Authenticated via: Environment Variable" in out
    assert client.repo_lookups == ["org/from-env"]
    assert "No action specified" in out
    assert not any(c[:2] == ["git", "remote"] for c in calls)


def test_main_runs_every_requested_action_end_to_end(
    gtm, workdir, monkeypatch, capsys, client, repo
):
    repo.pulls[40] = make_pr(
        merged=True,
        merged_at=T1,
        closed_at=T1,
        commits=[make_commit("s", [make_check(1, "failure")])],
        files=["src/app.py"],
    )
    calls = _cli(
        gtm,
        monkeypatch,
        [
            "--token",
            "cli-arg",
            "--repo",
            REPO_NAME,
            "--sync-pr",
            "40",
            "--sync-ci",
            "40",
            "--analyze",
            "40",
            "--review-feedback",
            "--report",
            "--pr",
            "40",
        ],
    )
    gtm.main()
    out = capsys.readouterr().out
    assert "Authenticated via: Command Line" in out
    assert calls == []  # explicit token + repo: no gh/git subprocess at all
    state = _disk_state(workdir)
    assert state["pull_requests"]["40"]["status"] == "merged"
    assert [r["run_id"] for r in state["pull_requests"]["40"]["ci_runs"]] == [1]
    assert [o["type"] for o in state["ci_cd_history"]["missed_opportunities"]] == [
        "ci_failure_merged",
        "test_coverage",
    ]
    assert "No pending feedback items" in out
    assert "PR #40: Add feature" in out
    assert "No action specified" not in out
