"""Lane A wave 12: .github/scripts/create_issues_from_failures.py (all GitHub mocked)."""

import json
import sys
import types

import pytest

from tests.coverage_waves.lane_a._load import load

mod = load(".github/scripts/create_issues_from_failures.py")


class FakeGhError(Exception):
    pass


class FakeIssue:
    def __init__(self, number):
        self.number = number
        self.html_url = "https://example.invalid/issues/" + str(number)
        self.comments = []
        self.edits = []

    def create_comment(self, text):
        self.comments.append(text)

    def edit(self, **kwargs):
        self.edits.append(kwargs)


class FakePull:
    def __init__(self):
        self.comments = []

    def create_issue_comment(self, text):
        self.comments.append(text)


class FakeRepo:
    full_name = "org/repo"

    def __init__(self):
        self.created = []
        self.fail_create = False
        self.fail_pull = False
        self.pull = FakePull()
        self.next_number = 100

    def create_issue(self, title, body, labels):
        if self.fail_create:
            raise FakeGhError("boom")
        self.next_number += 1
        self.created.append(dict(title=title, body=body, labels=labels))
        return FakeIssue(self.next_number)

    def get_pull(self, number):
        if self.fail_pull:
            raise FakeGhError("no pull")
        self.pull.number = number
        return self.pull


class FakeGithub:
    instances = []

    def __init__(self, credential):
        self.credential = credential
        self.repo = FakeRepo()
        self.existing = []
        self.queries = []
        FakeGithub.instances.append(self)

    def get_repo(self, name):
        self.repo_name = name
        return self.repo

    def search_issues(self, query):
        self.queries.append(query)
        return iter(self.existing)


@pytest.fixture
def gh(monkeypatch):
    FakeGithub.instances = []
    monkeypatch.setattr(mod, "Github", FakeGithub)
    monkeypatch.setattr(mod, "GithubException", FakeGhError)
    return FakeGithub


def _creator(gh, pr=None):
    return mod.CIIssueCreator("cred", "org/repo", pr)


def test_ensure_client_returns_existing(gh):
    assert mod._ensure_github_client() == (FakeGithub, FakeGhError)


def test_ensure_client_installs_and_imports(monkeypatch, capsys):
    calls = []
    fake_module = types.ModuleType("github")
    fake_module.Github = FakeGithub
    fake_module.GithubException = FakeGhError
    monkeypatch.setattr(mod, "Github", None)
    monkeypatch.setattr(mod, "GithubException", mod.GithubException)
    monkeypatch.setattr("subprocess.check_call", calls.append)
    monkeypatch.setitem(sys.modules, "github", fake_module)
    assert mod._ensure_github_client() == (FakeGithub, FakeGhError)
    assert calls[0][1:] == ["-m", "pip", "install", "-q", "PyGithub"]
    assert "Installing PyGithub" in capsys.readouterr().out


def test_init_wires_repo(gh):
    creator = _creator(gh, 7)
    inst = gh.instances[0]
    assert inst.credential == "cred"
    assert inst.repo_name == "org/repo"
    assert creator.pr_number == 7
    assert creator.created_issues == []
    assert creator.closed_issues == []


def test_parse_test_report(gh, tmp_path, capsys):
    creator = _creator(gh)
    missing = creator.parse_test_report(str(tmp_path / "none.json"))
    assert missing == {"tests": [], "summary": {}}
    assert "Test report not found" in capsys.readouterr().out
    path = tmp_path / "r.json"
    path.write_text(json.dumps({"tests": [1]}), encoding="utf-8")
    assert creator.parse_test_report(str(path)) == {"tests": [1]}


def test_get_existing_issues_query(gh):
    creator = _creator(gh)
    gh.instances[0].existing = [FakeIssue(3)]
    found = creator.get_existing_issues("t::x")
    assert [i.number for i in found] == [3]
    query = gh.instances[0].queries[0]
    assert query == 'repo:org/repo is:issue is:open label:ci-failure "t::x"'


def test_create_issue_skips_existing(gh, capsys):
    creator = _creator(gh)
    gh.instances[0].existing = [FakeIssue(9)]
    assert creator.create_issue_for_test({"nodeid": "a.py::t"}) is None
    assert "already exists" in capsys.readouterr().out
    assert gh.instances[0].repo.created == []


def test_create_issue_integration_with_pr_links(gh):
    creator = _creator(gh, 42)
    test = {
        "nodeid": "tests/test_integration.py::test_flow",
        "call": {"longrepr": "AssertionError", "duration": 1.5},
    }
    url = creator.create_issue_for_test(test)
    repo = gh.instances[0].repo
    assert url.endswith("/101")
    assert creator.created_issues == [101]
    made = repo.created[0]
    assert made["title"].endswith("CI Failure: test_flow")
    assert made["labels"] == [
        "ci-failure",
        "automated",
        "priority:high",
        "integration-test",
    ]
    assert "**Related PR:** #42" in made["body"]
    assert "1.50s" in made["body"]
    assert repo.pull.number == 42
    assert "#101" in repo.pull.comments[0]


def test_create_issue_unit_label_without_pr(gh):
    creator = _creator(gh)
    url = creator.create_issue_for_test({"nodeid": "tests/unit/test_x.py::test_a"})
    made = gh.instances[0].repo.created[0]
    assert url is not None
    assert made["labels"] == ["ci-failure", "automated", "priority:medium", "unit-test"]
    assert "No error message available" in made["body"]
    assert gh.instances[0].repo.pull.comments == []


def test_create_issue_name_without_separator(gh):
    creator = _creator(gh)
    creator.create_issue_for_test({"call": {"longrepr": "ImportError: x"}})
    made = gh.instances[0].repo.created[0]
    assert made["title"].endswith("CI Failure: Unknown Test")
    assert made["labels"] == ["ci-failure", "automated", "priority:high"]
    assert "**File:** `Unknown`" in made["body"]


def test_create_issue_github_error(gh, capsys):
    creator = _creator(gh)
    gh.instances[0].repo.fail_create = True
    assert creator.create_issue_for_test({"nodeid": "a.py::t"}) is None
    assert "Failed to create issue" in capsys.readouterr().out
    assert creator.created_issues == []


def test_close_issue_for_test(gh):
    creator = _creator(gh)
    issues = [FakeIssue(1), FakeIssue(2)]
    gh.instances[0].existing = issues
    assert creator.close_issue_for_test("a.py::t") == 2
    assert creator.closed_issues == [1, 2]
    assert issues[0].edits == [{"state": "closed"}]
    assert "a.py::t" in issues[1].comments[0]


def test_close_issue_none_open(gh):
    assert _creator(gh).close_issue_for_test("x") == 0


def test_determine_priority(gh):
    creator = _creator(gh)
    assert creator._determine_priority("test_CORE_x", "") == "priority:high"
    assert creator._determine_priority("t", "ModuleNotFoundError") == "priority:high"
    assert creator._determine_priority("t", "assert 1 == 2") == "priority:medium"


def test_issue_body_truncates_and_handles_no_pr(gh):
    creator = _creator(gh)
    long_msg = "".join(["y"] * 2500)
    body = creator._create_issue_body("f.py::t", "f.py", long_msg, 0.0, None)
    assert "Related PR" not in body
    assert "in PR #N/A" in body
    assert "".join(["y"] * 2000) in body
    assert "".join(["y"] * 2001) not in body
    assert "pytest f.py::t -v" in body
    assert "Pull Request #" not in body
    assert "https://github.com/org/repo/actions" in body


def test_issue_body_with_pr_link(gh):
    body = _creator(gh)._create_issue_body("f.py::t", "f.py", "m", 2.0, 5)
    assert "https://github.com/org/repo/pull/5" in body
    assert "in PR #5" in body


def test_link_to_pr_without_pr_is_noop(gh):
    creator = _creator(gh)
    creator._link_to_pr(1)
    assert gh.instances[0].repo.pull.comments == []


def test_link_to_pr_error(gh, capsys):
    creator = _creator(gh, 3)
    gh.instances[0].repo.fail_pull = True
    creator._link_to_pr(1)
    assert "Could not link issue" in capsys.readouterr().out


def _report(tmp_path, tests, **summary):
    path = tmp_path / "report.json"
    path.write_text(json.dumps({"tests": tests, "summary": summary}), encoding="utf-8")
    return str(path)


def test_process_no_tests(gh, tmp_path, capsys):
    creator = _creator(gh)
    creator.process_test_results(_report(tmp_path, []))
    assert "No test results found" in capsys.readouterr().out


def test_process_all_passing_closes_issues(gh, tmp_path, capsys):
    creator = _creator(gh)
    gh.instances[0].existing = [FakeIssue(8)]
    tests = [{"nodeid": "a::t", "outcome": "passed"}, {"outcome": "skipped"}]
    creator.process_test_results(_report(tmp_path, tests, **dict(total=2, failed=0)))
    out = capsys.readouterr().out
    assert "All tests passing" in out
    assert creator.closed_issues == [8]


def test_process_failures_create_issues(gh, tmp_path, capsys):
    creator = _creator(gh)
    tests = [
        {"nodeid": "a.py::t1", "outcome": "failed"},
        {"nodeid": "a.py::t2", "outcome": "failed"},
        {"nodeid": "a.py::t3", "outcome": "passed"},
    ]
    counts = dict(total=3, failed=2)
    counts["passed"] = 1
    creator.process_test_results(_report(tmp_path, tests, **counts))
    out = capsys.readouterr().out
    assert creator.created_issues == [101, 102]
    assert "Created 2 issue(s)" in out
    assert "#101, #102" in out
    assert "Failed: 2" in out


def test_process_failures_all_duplicates(gh, tmp_path, capsys):
    creator = _creator(gh)
    gh.instances[0].existing = [FakeIssue(4)]
    tests = [{"nodeid": "a.py::t1", "outcome": "failed"}]
    creator.process_test_results(_report(tmp_path, tests, **dict(failed=1)))
    out = capsys.readouterr().out
    assert "Created 0 issue(s)" in out
    assert "Issue numbers" not in out


def test_main_requires_token(monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 1
    assert "GITHUB_TOKEN not found" in capsys.readouterr().out


def test_main_requires_repository(monkeypatch, capsys):
    monkeypatch.setenv("GITHUB_TOKEN", "x")
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 1
    assert "GITHUB_REPOSITORY not found" in capsys.readouterr().out


@pytest.mark.parametrize("raw, expected", [("12", 12), ("abc", None), (None, None)])
def test_main_runs_processing(gh, monkeypatch, tmp_path, capsys, raw, expected):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "x")
    monkeypatch.setenv("GITHUB_REPOSITORY", "org/repo")
    if raw is None:
        monkeypatch.delenv("PR_NUMBER", raising=False)
    else:
        monkeypatch.setenv("PR_NUMBER", raw)
    seen = []
    original = mod.CIIssueCreator.process_test_results

    def spy(self, report_path="test_report.json"):
        seen.append(self.pr_number)
        original(self, report_path)

    monkeypatch.setattr(mod.CIIssueCreator, "process_test_results", spy)
    mod.main()
    out = capsys.readouterr().out
    assert "Test report not found" in out
    assert seen == [expected]
    assert gh.instances[0].repo_name == "org/repo"
    assert gh.instances[0].credential == "x"
