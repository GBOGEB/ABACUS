"""Behaviour tests for github_azure_deployment_helper.py (lane ab-next, wave 1)."""

import ast
import json
import runpy

import pytest
import yaml

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

gad = load("github_azure_deployment_helper.py", name="abn_github_azure_helper")

PKG = "ABACUS_V21_DEPLOYMENT_PACKAGE"


class _Completed:
    def __init__(self, returncode, stdout, stderr):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _helper(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    return gad.GitHubAzureDeploymentHelper()


def _script(helper, monkeypatch, responses):
    """Route run_command through a table keyed by the command tuple."""
    calls = []

    def fake(cmd, check=False):
        calls.append(list(cmd))
        return responses.get(tuple(cmd), (0, "", ""))

    monkeypatch.setattr(helper, "run_command", fake)
    return calls


def _messages(helper):
    return [step["message"] for step in helper.results["steps"]]


def test_init_uses_cwd_and_in_progress_status(monkeypatch, tmp_path):
    helper = _helper(monkeypatch, tmp_path)
    assert helper.project_root == tmp_path
    assert helper.results["status"] == "in_progress"
    assert helper.results["steps"] == []
    assert "T" in helper.results["timestamp"]


def test_log_prints_and_records_step(monkeypatch, tmp_path, capsys):
    helper = _helper(monkeypatch, tmp_path)
    helper.log("hello world", "SUCCESS")
    helper.log("default level")
    out = capsys.readouterr().out
    assert "[SUCCESS] hello world" in out
    assert "[INFO] default level" in out
    assert helper.results["steps"][0]["status"] == "SUCCESS"
    assert helper.results["steps"][1]["status"] == "INFO"
    assert helper.results["steps"][0]["message"] == "hello world"


def test_run_command_success_passes_expected_kwargs(monkeypatch, tmp_path):
    helper = _helper(monkeypatch, tmp_path)
    seen = {}

    def fake_run(cmd, **kwargs):
        seen["cmd"] = cmd
        seen.update(kwargs)
        return _Completed(0, "out", "err")

    monkeypatch.setattr(gad.subprocess, "run", fake_run)
    assert helper.run_command(["git", "status"], check=True) == (0, "out", "err")
    assert seen["cmd"] == ["git", "status"]
    assert seen["capture_output"] is True
    assert seen["text"] is True
    assert seen["check"] is True
    assert seen["errors"] == "replace"


def test_run_command_called_process_error_returns_its_fields(monkeypatch, tmp_path):
    helper = _helper(monkeypatch, tmp_path)

    def fake_run(cmd, **kwargs):
        raise gad.subprocess.CalledProcessError(3, cmd, output="o", stderr="e")

    monkeypatch.setattr(gad.subprocess, "run", fake_run)
    assert helper.run_command(["git", "x"], check=True) == (3, "o", "e")


def test_run_command_other_exception_returns_minus_one(monkeypatch, tmp_path):
    helper = _helper(monkeypatch, tmp_path)

    def fake_run(cmd, **kwargs):
        raise FileNotFoundError("git missing")

    monkeypatch.setattr(gad.subprocess, "run", fake_run)
    assert helper.run_command(["git"]) == (-1, "", "git missing")


@pytest.mark.parametrize(
    "response, expected",
    [
        (
            (
                0,
                "upstream\thttps://u/x.git (fetch)\n"
                "origin\thttps://example.invalid/r.git (fetch)\n"
                "origin\thttps://example.invalid/r.git (push)\n",
            ),
            "https://example.invalid/r.git",
        ),
        ((0, "origin\thttps://example.invalid/r.git (push)\n"), None),
        ((0, "origin(fetch)\n"), None),
        ((0, ""), None),
        ((128, "origin\thttps://example.invalid/r.git (fetch)\n"), None),
    ],
)
def test_check_git_remote(monkeypatch, tmp_path, response, expected):
    helper = _helper(monkeypatch, tmp_path)
    code, out = response
    _script(helper, monkeypatch, {("git", "remote", "-v"): (code, out, "")})
    assert helper.check_git_remote() == expected


def test_sync_pull_without_remote_returns_false(monkeypatch, tmp_path, capsys):
    helper = _helper(monkeypatch, tmp_path)
    monkeypatch.setattr(helper, "check_git_remote", lambda: None)
    assert helper.sync_with_github_pull() is False
    assert "No remote repository configured" in _messages(helper)


def test_sync_pull_fetch_failure(monkeypatch, tmp_path, capsys):
    helper = _helper(monkeypatch, tmp_path)
    monkeypatch.setattr(helper, "check_git_remote", lambda: "url")
    _script(helper, monkeypatch, {("git", "fetch", "origin"): (1, "", "net down")})
    assert helper.sync_with_github_pull() is False
    assert "Fetch failed: net down" in _messages(helper)


def test_sync_pull_success_defaults_branch_to_main(monkeypatch, tmp_path, capsys):
    helper = _helper(monkeypatch, tmp_path)
    monkeypatch.setattr(helper, "check_git_remote", lambda: "url")
    calls = _script(
        helper, monkeypatch, {("git", "branch", "--show-current"): (1, "", "err")}
    )
    assert helper.sync_with_github_pull() is True
    assert ["git", "pull", "--rebase", "origin", "main"] in calls
    assert "Successfully pulled latest changes from GitHub" in _messages(helper)


def test_sync_pull_uses_current_branch(monkeypatch, tmp_path, capsys):
    helper = _helper(monkeypatch, tmp_path)
    monkeypatch.setattr(helper, "check_git_remote", lambda: "url")
    calls = _script(
        helper, monkeypatch, {("git", "branch", "--show-current"): (0, "dev\n", "")}
    )
    assert helper.sync_with_github_pull() is True
    assert ["git", "pull", "--rebase", "origin", "dev"] in calls
    assert "Current branch: dev" in _messages(helper)


@pytest.mark.parametrize(
    "out, err",
    [("", "CONFLICT (content): x.py"), ("Merge conflict in y.py", "")],
)
def test_sync_pull_conflict_returns_false(monkeypatch, tmp_path, capsys, out, err):
    helper = _helper(monkeypatch, tmp_path)
    monkeypatch.setattr(helper, "check_git_remote", lambda: "url")
    _script(
        helper,
        monkeypatch,
        {
            ("git", "branch", "--show-current"): (0, "main\n", ""),
            ("git", "pull", "--rebase", "origin", "main"): (1, out, err),
        },
    )
    assert helper.sync_with_github_pull() is False
    msgs = _messages(helper)
    assert "MERGE CONFLICTS DETECTED!" in msgs
    assert "3. Run: git rebase --continue" in msgs


def test_sync_pull_other_failure(monkeypatch, tmp_path, capsys):
    helper = _helper(monkeypatch, tmp_path)
    monkeypatch.setattr(helper, "check_git_remote", lambda: "url")
    _script(
        helper,
        monkeypatch,
        {
            ("git", "branch", "--show-current"): (0, "main\n", ""),
            ("git", "pull", "--rebase", "origin", "main"): (1, "", "auth failed"),
        },
    )
    assert helper.sync_with_github_pull() is False
    assert "Pull failed: auth failed" in _messages(helper)
    assert "MERGE CONFLICTS DETECTED!" not in _messages(helper)


def test_prepare_no_local_changes(monkeypatch, tmp_path, capsys):
    helper = _helper(monkeypatch, tmp_path)
    calls = _script(
        helper, monkeypatch, {("git", "status", "--short"): (0, "  \n", "")}
    )
    assert helper.prepare_local_changes() is True
    assert "No local changes to commit" in _messages(helper)
    assert not any(c[:2] == ["git", "commit"] for c in calls)


def _commit_table():
    return {
        ("git", "status", "--short"): (0, " M a.py\n?? b.py\n", ""),
        ("git", "add", "abacus_v21_*.py"): (128, "", "no match"),
    }


def test_prepare_commit_success(monkeypatch, tmp_path, capsys):
    helper = _helper(monkeypatch, tmp_path)
    table = _commit_table()
    calls = _script(helper, monkeypatch, table)
    assert helper.prepare_local_changes() is True
    msgs = _messages(helper)
    assert "Found 2 changed files" in msgs
    assert "Added: ABACUS_V21_DEPLOYMENT_PACKAGE/" in msgs
    assert "Added: abacus_v21_*.py" not in msgs
    commit = [c for c in calls if c[:2] == ["git", "commit"]][0]
    assert commit[3].startswith("ABACUS v2.1 Deployment Package - ")
    assert any(m.startswith("Commit created: ") for m in msgs)


@pytest.mark.parametrize(
    "out, err",
    [("nothing to commit, working tree clean", ""), ("", "nothing to commit")],
)
def test_prepare_nothing_to_commit(monkeypatch, tmp_path, capsys, out, err):
    helper = _helper(monkeypatch, tmp_path)
    table = _commit_table()

    def fake(cmd, check=False):
        if cmd[:2] == ["git", "commit"]:
            return 1, out, err
        return table.get(tuple(cmd), (0, "", ""))

    monkeypatch.setattr(helper, "run_command", fake)
    assert helper.prepare_local_changes() is True
    assert "No changes to commit" in _messages(helper)


def test_prepare_commit_failure(monkeypatch, tmp_path, capsys):
    helper = _helper(monkeypatch, tmp_path)
    table = _commit_table()

    def fake(cmd, check=False):
        if cmd[:2] == ["git", "commit"]:
            return 1, "", "hook rejected"
        return table.get(tuple(cmd), (0, "", ""))

    monkeypatch.setattr(helper, "run_command", fake)
    assert helper.prepare_local_changes() is False
    assert "Commit failed: hook rejected" in _messages(helper)


def test_push_success_uses_branch(monkeypatch, tmp_path, capsys):
    helper = _helper(monkeypatch, tmp_path)
    calls = _script(
        helper, monkeypatch, {("git", "branch", "--show-current"): (0, "feat\n", "")}
    )
    assert helper.push_to_github() is True
    assert ["git", "push", "origin", "feat"] in calls
    assert "Successfully pushed to GitHub!" in _messages(helper)


def test_push_rejected(monkeypatch, tmp_path, capsys):
    helper = _helper(monkeypatch, tmp_path)
    _script(
        helper,
        monkeypatch,
        {
            ("git", "branch", "--show-current"): (1, "", ""),
            ("git", "push", "origin", "main"): (1, "", "! [REJECTED] non-fast"),
        },
    )
    assert helper.push_to_github() is False
    assert "Push rejected - remote has changes you don't have" in _messages(helper)


def test_push_other_failure(monkeypatch, tmp_path, capsys):
    helper = _helper(monkeypatch, tmp_path)
    _script(
        helper,
        monkeypatch,
        {
            ("git", "branch", "--show-current"): (0, "main\n", ""),
            ("git", "push", "origin", "main"): (1, "", "denied"),
        },
    )
    assert helper.push_to_github() is False
    assert "Push failed: denied" in _messages(helper)


def test_generate_azure_script_writes_valid_python(monkeypatch, tmp_path, capsys):
    helper = _helper(monkeypatch, tmp_path)
    (tmp_path / PKG).mkdir()
    assert helper.generate_azure_deployment_script() is True
    path = tmp_path / PKG / "azure_deployment.py"
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    classes = [n.name for n in tree.body if isinstance(n, ast.ClassDef)]
    assert classes == ["AzureDeployer"]
    assert 'self.resource_group = "abacus-v21-rg"' in text
    assert any(m.startswith("Created: ") for m in _messages(helper))


def test_generate_azure_script_needs_existing_package_dir(monkeypatch, tmp_path):
    helper = _helper(monkeypatch, tmp_path)
    with pytest.raises(FileNotFoundError):
        helper.generate_azure_deployment_script()


def test_generate_workflow_creates_parents_and_valid_yaml(
    monkeypatch, tmp_path, capsys
):
    helper = _helper(monkeypatch, tmp_path)
    assert helper.generate_github_actions_azure_workflow() is True
    path = tmp_path / PKG / ".github" / "workflows" / "azure-deploy.yml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["name"] == "Deploy to Azure"
    assert data["env"]["AZURE_WEBAPP_NAME"] == "abacus-v21"
    steps = data["jobs"]["build-and-deploy"]["steps"]
    assert steps[0]["uses"] == "actions/checkout@v4"


def test_generate_instructions_writes_and_prints(monkeypatch, tmp_path, capsys):
    helper = _helper(monkeypatch, tmp_path)
    helper.generate_instructions()
    out = capsys.readouterr().out
    text = (tmp_path / "GITHUB_AZURE_DEPLOYMENT_INSTRUCTIONS.txt").read_text(
        encoding="utf-8"
    )
    assert "AZURE DEPLOYMENT OPTIONS" in text
    assert "AZURE DEPLOYMENT OPTIONS" in out
    assert any(m.startswith("Instructions saved to: ") for m in _messages(helper))


def test_save_report_marks_completed(monkeypatch, tmp_path, capsys):
    helper = _helper(monkeypatch, tmp_path)
    helper.log("first")
    helper.save_report()
    data = json.loads((tmp_path / "GITHUB_SYNC_REPORT.json").read_text("utf-8"))
    assert data["status"] == "completed"
    assert [s["message"] for s in data["steps"]] == ["first"]
    assert helper.results["steps"][-1]["message"].startswith("Report saved: ")


@pytest.mark.parametrize(
    "failing, message",
    [
        ("sync_with_github_pull", "GitHub pull failed or has conflicts"),
        ("prepare_local_changes", "Failed to prepare local changes"),
        ("push_to_github", "Failed to push to GitHub"),
    ],
)
def test_run_stops_at_first_failing_step(
    monkeypatch, tmp_path, capsys, failing, message
):
    helper = _helper(monkeypatch, tmp_path)
    for name in ("sync_with_github_pull", "prepare_local_changes", "push_to_github"):
        result = name != failing
        monkeypatch.setattr(helper, name, lambda result=result: result)
    assert helper.run() is False
    assert any(m.startswith(message) for m in _messages(helper))
    assert not (tmp_path / "GITHUB_SYNC_REPORT.json").exists()


def test_run_full_success_generates_everything(monkeypatch, tmp_path, capsys):
    helper = _helper(monkeypatch, tmp_path)
    (tmp_path / PKG).mkdir()
    for name in ("sync_with_github_pull", "prepare_local_changes", "push_to_github"):
        monkeypatch.setattr(helper, name, lambda: True)
    assert helper.run() is True
    out = capsys.readouterr().out
    assert "GitHub sync and Azure deployment preparation completed!" in out
    assert (tmp_path / PKG / "azure_deployment.py").is_file()
    assert (tmp_path / PKG / ".github" / "workflows" / "azure-deploy.yml").is_file()
    assert (tmp_path / "GITHUB_AZURE_DEPLOYMENT_INSTRUCTIONS.txt").is_file()
    report = json.loads((tmp_path / "GITHUB_SYNC_REPORT.json").read_text("utf-8"))
    assert report["status"] == "completed"


def test_main_guard_runs_helper(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return _Completed(1, "", "not a git repository")

    monkeypatch.setattr("subprocess.run", fake_run)
    runpy.run_path(
        str(REPO_ROOT / "github_azure_deployment_helper.py"), run_name="__main__"
    )
    out = capsys.readouterr().out
    assert calls == [["git", "remote", "-v"]]
    assert "No remote repository configured" in out
    assert not (tmp_path / "GITHUB_SYNC_REPORT.json").exists()
