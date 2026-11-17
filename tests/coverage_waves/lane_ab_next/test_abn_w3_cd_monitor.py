"""Behaviour tests for cd_monitor.py.

PyGithub is not installed in CI, so a stand-in ``github`` module is supplied
only while the module loads (the pip-install fallback is never reached) and
the GitHub client is replaced with in-memory fakes.
"""

import json
import sys
import types
from datetime import datetime

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
    "cd_monitor.py", name="abn_cd_monitor", deps={"github": _fake_github_module()}
)

CRED = "fake-cred-value"
WHEN = datetime(2026, 1, 2, 3, 4, 5)


def _status(state, description="", url=""):
    return types.SimpleNamespace(
        state=state, description=description, target_url=url, created_at=WHEN
    )


def _deployment(dep_id, env, statuses, creator="alice", sha="abcdef0123456789"):
    return types.SimpleNamespace(
        id=dep_id,
        environment=env,
        ref="main",
        sha=sha,
        created_at=WHEN,
        creator=types.SimpleNamespace(login=creator) if creator else None,
        get_statuses=lambda: iter(statuses),
    )


class _FakeRepo:
    def __init__(self, deployments=(), fail=False):
        self.deployments = list(deployments)
        self.fail = fail

    def get_deployments(self):
        if self.fail:
            raise RuntimeError("api down")
        return self.deployments

    def get_deployment(self, dep_id):
        for dep in self.deployments:
            if dep.id == dep_id:
                return dep
        raise LookupError("no deployment %d" % dep_id)


def _install_client(monkeypatch, repo):
    seen = {}

    class Client:
        def __init__(self, cred):
            seen["cred"] = cred

        def get_repo(self, name):
            seen["repo"] = name
            return repo

    monkeypatch.setattr(mod, "Github", Client)
    return seen


def _sample_repo():
    return _FakeRepo(
        [
            _deployment(
                1, "production", [_status("success", "ok", "https://x/1")], sha="1" * 40
            ),
            _deployment(2, "staging", [_status("failure", "broke")], creator=None),
            _deployment(3, "staging", [_status("pending")]),
            _deployment(4, "production", [], sha="4" * 40),
            _deployment(5, "staging", [_status("weird")]),
        ]
    )


def _monitor(monkeypatch, repo):
    seen = _install_client(monkeypatch, repo)
    return mod.CDMonitor(CRED, "owner/repo"), seen


def test_constructor_resolves_repo(monkeypatch):
    monitor, seen = _monitor(monkeypatch, _FakeRepo())
    assert seen == {"cred": CRED, "repo": "owner/repo"}
    assert monitor.repo_name == "owner/repo"


def test_get_deployments_maps_fields_and_defaults(monkeypatch, capsys):
    monitor, _ = _monitor(monkeypatch, _sample_repo())

    deps = monitor.get_deployments()

    assert [d["id"] for d in deps] == [1, 2, 3, 4, 5]
    first = deps[0]
    assert first["sha"] == "1111111"
    assert first["created_at"] == "2026-01-02T03:04:05Z"
    assert first["creator"] == "alice"
    assert first["status"] == "success"
    assert first["url"] == "https://x/1"
    assert deps[1]["creator"] == "unknown"
    assert deps[3]["status"] == "unknown"
    assert deps[3]["description"] == ""
    assert deps[3]["url"] == ""
    assert "Fetching deployments for owner/repo" in capsys.readouterr().out


def test_get_deployments_filters_by_environment(monkeypatch):
    monitor, _ = _monitor(monkeypatch, _sample_repo())

    deps = monitor.get_deployments("staging")

    assert [d["id"] for d in deps] == [2, 3, 5]


def test_get_deployments_swallows_api_errors(monkeypatch, capsys):
    monitor, _ = _monitor(monkeypatch, _FakeRepo(fail=True))

    assert monitor.get_deployments() == []
    assert "Error fetching deployments: api down" in capsys.readouterr().out


def test_display_deployments_empty(monkeypatch, capsys):
    monitor, _ = _monitor(monkeypatch, _FakeRepo())

    monitor.display_deployments([])

    assert "No deployments found" in capsys.readouterr().out


def test_display_deployments_groups_and_limits(monkeypatch, capsys):
    monitor, _ = _monitor(monkeypatch, _FakeRepo())
    deps = []
    for i in range(7):
        deps.append(
            dict(
                environment="prod",
                sha="s%d" % i,
                status="error" if i == 0 else "success",
                created_at="t",
                creator="bob",
                description="desc %d" % i if i == 1 else "",
                url="https://u/%d" % i if i == 2 else "",
            )
        )
    deps.append(
        dict(
            environment="qa",
            sha="qa1",
            status="mystery",
            created_at="t",
            creator="c",
            description="",
            url="",
        )
    )

    monitor.display_deployments(deps)

    out = capsys.readouterr().out
    assert "Environment: prod" in out
    assert "Environment: qa" in out
    assert "s4 - success" in out
    assert "s5" not in out
    assert "Description: desc 1" in out
    assert "URL: https://u/2" in out
    assert "qa1 - mystery" in out


def test_check_health_success(monkeypatch, capsys):
    monitor, _ = _monitor(monkeypatch, _sample_repo())

    health = monitor.check_deployment_health(1)

    assert health == {
        "healthy": True,
        "status": "success",
        "message": "ok",
        "url": "https://x/1",
        "updated_at": "2026-01-02T03:04:05Z",
    }
    assert "Checking health for deployment 1" in capsys.readouterr().out


def test_check_health_failure_with_empty_fields(monkeypatch):
    repo = _FakeRepo([_deployment(9, "e", [_status("failure", None, None)])])
    monitor, _ = _monitor(monkeypatch, repo)

    health = monitor.check_deployment_health(9)

    assert health["healthy"] is False
    assert health["message"] == ""
    assert health["url"] == ""


def test_check_health_without_statuses(monkeypatch):
    monitor, _ = _monitor(monkeypatch, _sample_repo())

    health = monitor.check_deployment_health(4)

    assert health["healthy"] is False
    assert health["status"] == "unknown"
    assert "No status" in health["message"]


def test_check_health_error(monkeypatch):
    monitor, _ = _monitor(monkeypatch, _sample_repo())

    health = monitor.check_deployment_health(404)

    assert health["status"] == "error"
    assert "no deployment 404" in health["message"]


def test_report_counts_and_save(monkeypatch, tmp_path, capsys):
    monitor, _ = _monitor(monkeypatch, _sample_repo())

    report = monitor.create_deployment_report()

    assert report["environment"] == "all"
    assert report["total_deployments"] == 5
    assert report["successful"] == 1
    assert report["failed"] == 1
    assert report["pending"] == 1
    assert report["timestamp"].endswith("Z")

    target = tmp_path / "r.json"
    monitor.save_deployment_report(report, str(target))
    assert json.loads(target.read_text())["repository"] == "owner/repo"
    assert "Deployment report saved to" in capsys.readouterr().out

    staged = monitor.create_deployment_report("staging")
    assert staged["environment"] == "staging"
    assert staged["total_deployments"] == 3


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
    out = types.SimpleNamespace(stdout=" cli-value \n", returncode=0)
    fake, calls = _fake_run({"gh": out})
    monkeypatch.setattr(mod.subprocess, "run", fake)

    assert mod.get_github_token() == ("cli-value", "GitHub CLI")
    assert calls == [["gh", "auth", "token"]]


def test_get_github_token_falls_back_to_env(monkeypatch):
    fake, _ = _fake_run({"gh": types.SimpleNamespace(stdout="  ", returncode=0)})
    monkeypatch.setattr(mod.subprocess, "run", fake)
    monkeypatch.setenv("GITHUB_TOKEN", "env-value")

    assert mod.get_github_token() == ("env-value", "Environment Variable")


def test_get_github_token_none_available(monkeypatch):
    fake, _ = _fake_run({"gh": FileNotFoundError("gh")})
    monkeypatch.setattr(mod.subprocess, "run", fake)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    assert mod.get_github_token() == (None, None)


def _run_main(monkeypatch, argv, git_result=None, repo=None, token=(None, None)):
    monkeypatch.setattr(sys, "argv", ["cd_monitor.py"] + argv)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.setattr(mod, "get_github_token", lambda: token)
    fake, calls = _fake_run({"git": git_result})
    monkeypatch.setattr(mod.subprocess, "run", fake)
    seen = _install_client(monkeypatch, repo or _sample_repo())
    mod.main()
    return seen, calls


def test_main_requires_authentication(monkeypatch, capsys):
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, [])
    assert exc.value.code == 1
    assert "GitHub authentication required" in capsys.readouterr().out


def test_main_uses_discovered_token_and_git_remote(monkeypatch, capsys):
    remote = types.SimpleNamespace(returncode=0, stdout="git@github.com:org/proj.git\n")
    seen, calls = _run_main(
        monkeypatch, [], git_result=remote, token=(CRED, "GitHub CLI")
    )

    assert seen["repo"] == "org/proj"
    assert calls == [["git", "remote", "get-url", "origin"]]
    out = capsys.readouterr().out
    assert "Authenticated via: GitHub CLI" in out
    assert "Environment: production" in out


@pytest.mark.parametrize(
    "git_result",
    [
        types.SimpleNamespace(returncode=1, stdout=""),
        types.SimpleNamespace(returncode=0, stdout="https://gitlab.com/a/b.git"),
        OSError("git missing"),
    ],
)
def test_main_exits_without_repository(monkeypatch, capsys, git_result):
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, ["--token", CRED], git_result=git_result)
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "Authenticated via: Command Line" in out
    assert "Repository name required" in out


def test_main_repo_from_environment(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["cd_monitor.py", "--token", CRED])
    monkeypatch.setenv("GITHUB_REPOSITORY", "env/repo")
    seen = _install_client(monkeypatch, _FakeRepo())

    mod.main()

    assert seen["repo"] == "env/repo"
    assert "No deployments found" in capsys.readouterr().out


def test_main_health_check_with_url(monkeypatch, capsys):
    _run_main(monkeypatch, ["--token", CRED, "--repo", "o/r", "--health-check", "1"])

    out = capsys.readouterr().out
    assert "Healthy: " in out
    assert "Status: success" in out
    assert "URL: https://x/1" in out


def test_main_health_check_without_url(monkeypatch, capsys):
    _run_main(monkeypatch, ["--token", CRED, "--repo", "o/r", "--health-check", "4"])

    out = capsys.readouterr().out
    assert "Status: unknown" in out
    assert "URL:" not in out


def test_main_report_saved_to_named_file(monkeypatch, tmp_path, capsys):
    target = tmp_path / "named.json"
    _run_main(
        monkeypatch,
        ["--token", CRED, "--repo", "o/r", "--report", "--save-report", str(target)],
    )

    assert json.loads(target.read_text())["total_deployments"] == 5
    assert "Total Deployments: 5" in capsys.readouterr().out


def test_main_report_default_file_with_environment(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    _run_main(
        monkeypatch,
        ["--token", CRED, "--repo", "o/r", "--report", "--environment", "staging"],
    )

    report = json.loads((tmp_path / "cd_deployment_report.json").read_text())
    assert report["environment"] == "staging"
    assert report["total_deployments"] == 3
    assert "Pending: 1" in capsys.readouterr().out
