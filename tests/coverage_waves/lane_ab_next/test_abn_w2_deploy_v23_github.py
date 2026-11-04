"""Behaviour tests for scripts/deploy_v23_github.py (git and gh are faked)."""

import json
import runpy

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

mod = load("scripts/deploy_v23_github.py", name="abn_deploy_v23_github")


class _Result:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _FakeRun:
    """Answers argv lists by matching a tuple prefix; honours check=True."""

    def __init__(self, table=None, default=None):
        self.table = table or {}
        self.default = default or _Result(0, "")
        self.calls = []

    def __call__(self, cmd, **kwargs):
        self.calls.append((list(cmd), kwargs))
        answer = self.default
        for prefix, value in self.table.items():
            if tuple(cmd[: len(prefix)]) == prefix:
                answer = value
                break
        if isinstance(answer, list):
            answer = answer.pop(0)
        if isinstance(answer, BaseException):
            raise answer
        if kwargs.get("check") and answer.returncode != 0:
            raise mod.subprocess.CalledProcessError(
                answer.returncode, cmd, answer.stdout, answer.stderr
            )
        return answer


@pytest.fixture
def dep(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return mod.GitHubDeploymentV23(branch="feat/x")


def _fake(monkeypatch, table=None, default=None):
    fake = _FakeRun(table, default)
    monkeypatch.setattr(mod.subprocess, "run", fake)
    return fake


def _unified(tmp_path, skip=()):
    folder = tmp_path / "ABACUS-UNIFIED"
    folder.mkdir(exist_ok=True)
    names = [
        "DOCUMENTATION_INDEX.md",
        "HONEST_MATURITY_ASSESSMENT.md",
        "HONEST_STATE_SUMMARY.md",
        "KNOWLEDGE_PACK_INDEX.md",
        "MASTER_PIPELINE_REPORT.md",
        "ORCHESTRATOR_RANKING.md",
        "PHASE_AGENT_MATRIX.md",
        "PRODUCTION_READINESS_ASSESSMENT.md",
        "PRODUCTION_ROADMAP.md",
        "QUICK_REFERENCE.md",
        "README.md",
        "VALIDATION_REPORT.md",
    ]
    for name in names:
        if name not in skip:
            (folder / name).write_bytes(b"# doc\n")


def _pipeline(tmp_path):
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "v23-cicd.yml").write_bytes(b"name: v23\n")


def _roundtrip(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "git_github_roundtrip.sh").write_bytes(b"echo ok\n")


def test_init_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    d = mod.GitHubDeploymentV23()
    assert d.branch == "feature/dow-integration"
    assert d.repo_root == tmp_path
    assert d.deployment_log == []


def test_log_appends_and_prints(dep, capsys):
    dep.log("hello", "WARNING")
    assert len(dep.deployment_log) == 1
    assert dep.deployment_log[0].endswith("[WARNING] hello")
    assert "[WARNING] hello" in capsys.readouterr().out


def test_run_command_logs_stdout(dep, tmp_path, monkeypatch):
    fake = _fake(monkeypatch, {("git", "status"): _Result(0, " clean \n")})
    res = dep.run_command(["git", "status"])
    assert res.returncode == 0
    cmd, kwargs = fake.calls[0]
    assert cmd == ["git", "status"]
    assert kwargs["check"] is True
    assert kwargs["cwd"] == tmp_path
    assert any("Running: git status" in e for e in dep.deployment_log)
    assert any(e.endswith("[DEBUG] Output: clean") for e in dep.deployment_log)


def test_run_command_without_stdout_skips_output_log(dep, monkeypatch):
    _fake(monkeypatch, {}, _Result(0, ""))
    dep.run_command(["true"], check=False)
    assert not any("Output:" in e for e in dep.deployment_log)


def test_run_command_failure_logs_stderr_and_reraises(dep, monkeypatch):
    _fake(monkeypatch, {}, _Result(2, "", "fatal: nope"))
    with pytest.raises(mod.subprocess.CalledProcessError):
        dep.run_command(["git", "push"])
    errors = [e for e in dep.deployment_log if "[ERROR]" in e]
    assert any("Command failed" in e for e in errors)
    assert any("Error: fatal: nope" in e for e in errors)


def test_run_command_failure_without_stderr(dep, monkeypatch):
    _fake(monkeypatch, {}, _Result(2, "", ""))
    with pytest.raises(mod.subprocess.CalledProcessError):
        dep.run_command(["git", "push"])
    assert not any("Error: " in e for e in dep.deployment_log)


def test_verify_unified_files_all_present(dep, tmp_path):
    _unified(tmp_path)
    assert dep.verify_abacus_unified_files() is True
    assert any("All 12 ABACUS-UNIFIED files verified" in e for e in dep.deployment_log)


def test_verify_unified_files_reports_missing(dep, tmp_path):
    _unified(tmp_path, skip=("README.md", "PRODUCTION_ROADMAP.md"))
    assert dep.verify_abacus_unified_files() is False
    warnings = [e for e in dep.deployment_log if "[WARNING] Missing:" in e]
    assert len(warnings) == 2
    assert any("Missing 2 files" in e for e in dep.deployment_log)


def test_stage_changes_continues_after_failure(dep, monkeypatch):
    fake = _fake(
        monkeypatch,
        {("git", "add", "README.md"): _Result(128, "", "pathspec")},
    )
    assert dep.stage_v23_changes() is True
    assert len(fake.calls) == 7
    assert any("Failed to stage README.md" in e for e in dep.deployment_log)
    assert any("Staged: ABACUS-UNIFIED/" in e for e in dep.deployment_log)


def test_commit_success(dep, monkeypatch):
    fake = _fake(monkeypatch)
    assert dep.commit_v23_deployment() is True
    cmd = fake.calls[0][0]
    assert cmd[:3] == ["git", "commit", "-m"]
    assert cmd[3].startswith("feat: V2.3 Complete Deployment")


def test_commit_failure(dep, monkeypatch):
    _fake(monkeypatch, {}, _Result(1, "", "nothing to commit"))
    assert dep.commit_v23_deployment() is False
    assert any("Commit failed" in e for e in dep.deployment_log)


def test_push_success_uses_branch(dep, monkeypatch):
    fake = _fake(monkeypatch)
    assert dep.push_to_remote() is True
    assert fake.calls[0][0] == ["git", "push", "origin", "feat/x"]


def test_push_failure(dep, monkeypatch):
    _fake(monkeypatch, {}, _Result(1, "", "rejected"))
    assert dep.push_to_remote() is False
    assert any("Push failed" in e for e in dep.deployment_log)


def test_create_pr_body_mentions_all_unified_files(dep):
    body = dep.create_pr_body()
    assert body.startswith("# V2.3 Complete Deployment")
    assert "VALIDATION_REPORT.md" in body
    assert "**Version:** V2.3.0" in body


def test_create_pr_success(dep, monkeypatch):
    fake = _fake(monkeypatch)
    assert dep.create_github_pr() is True
    pr_cmd, kwargs = fake.calls[1]
    assert pr_cmd[:3] == ["gh", "pr", "create"]
    assert pr_cmd[pr_cmd.index("--head") + 1] == "feat/x"
    assert pr_cmd[pr_cmd.index("--base") + 1] == "main"
    assert kwargs["check"] is False


def test_create_pr_nonzero_is_warning(dep, monkeypatch):
    _fake(monkeypatch, {("gh", "pr"): _Result(1, "", "exists")})
    assert dep.create_github_pr() is False
    assert any("already exists" in e for e in dep.deployment_log)


def test_create_pr_without_gh_cli(dep, monkeypatch):
    _fake(monkeypatch, {("gh", "--version"): FileNotFoundError("gh")})
    assert dep.create_github_pr() is False
    assert any("install GitHub CLI" in e for e in dep.deployment_log)


def test_create_issues_counts_successes(dep, monkeypatch):
    fake = _fake(
        monkeypatch,
        {("gh", "issue"): [_Result(0), _Result(1), OSError("offline")]},
    )
    assert dep.create_github_issues() is True
    assert len(fake.calls) == 3
    first = fake.calls[0][0]
    assert first[first.index("--label") + 1] == "testing,v2.3,high-priority"
    assert any("Created 1/3 issues" in e for e in dep.deployment_log)
    assert any("Failed to create issue: offline" in e for e in dep.deployment_log)


def test_create_issues_none_created(dep, monkeypatch):
    _fake(monkeypatch, {}, _Result(1))
    assert dep.create_github_issues() is False
    assert any("Created 0/3 issues" in e for e in dep.deployment_log)


def test_verify_pipeline_missing(dep):
    assert dep.verify_ci_cd_pipeline() is False


def test_verify_pipeline_present(dep, tmp_path):
    _pipeline(tmp_path)
    assert dep.verify_ci_cd_pipeline() is True


def test_roundtrip_missing_script_is_skipped_success(dep, monkeypatch):
    fake = _fake(monkeypatch)
    assert dep.run_roundtrip_test() is True
    assert fake.calls == []
    assert any("skipping" in e for e in dep.deployment_log)


def test_roundtrip_script_passes(dep, tmp_path, monkeypatch):
    _roundtrip(tmp_path)
    fake = _fake(monkeypatch)
    assert dep.run_roundtrip_test() is True
    assert fake.calls[0][0][0] == "bash"
    assert fake.calls[0][0][1].endswith("git_github_roundtrip.sh")


def test_roundtrip_script_fails(dep, tmp_path, monkeypatch):
    _roundtrip(tmp_path)
    _fake(monkeypatch, {}, _Result(1))
    assert dep.run_roundtrip_test() is False


def test_roundtrip_script_error(dep, tmp_path, monkeypatch):
    _roundtrip(tmp_path)
    _fake(monkeypatch, {("bash",): OSError("no bash")})
    assert dep.run_roundtrip_test() is False
    assert any("Roundtrip test error: no bash" in e for e in dep.deployment_log)


def test_generate_report_writes_json(dep, tmp_path):
    dep.log("entry")
    report = dep.generate_deployment_report()
    saved = json.loads((tmp_path / "v23_deployment_report.json").read_bytes())
    assert saved["branch"] == "feat/x"
    assert saved["version"] == "V2.3.0"
    assert saved["deployment_log"][0].endswith("entry")
    assert report["components"]["agents_upgraded"].startswith("6/6")


def test_deploy_all_steps_succeed(dep, tmp_path, monkeypatch, capsys):
    _unified(tmp_path)
    _pipeline(tmp_path)
    _fake(monkeypatch)
    assert dep.deploy() is True
    out = capsys.readouterr().out
    assert "Overall: 8/8 steps successful" in out
    assert "100% SUCCESS" in out
    assert (tmp_path / "v23_deployment_report.json").is_file()


def test_deploy_partial_and_step_exception(dep, tmp_path, monkeypatch, capsys):
    _fake(monkeypatch)

    def broken():
        raise RuntimeError("kaput")

    monkeypatch.setattr(dep, "verify_ci_cd_pipeline", broken)
    assert dep.deploy() is False
    out = capsys.readouterr().out
    assert "Step failed: kaput" in out
    assert "FAIL - Verify ABACUS-UNIFIED files" in out
    assert "FAIL - Verify CI/CD pipeline" in out
    assert "Overall: 6/8 steps successful" in out
    assert "DEPLOYMENT PARTIAL" in out


def _main_exit_code(monkeypatch, ok):
    monkeypatch.setattr(mod.GitHubDeploymentV23, "deploy", lambda self: ok)
    with pytest.raises(SystemExit) as exc:
        mod.main()
    return exc.value.code


def test_main_exit_zero_on_success(monkeypatch):
    assert _main_exit_code(monkeypatch, True) == 0


def test_main_exit_one_on_failure(monkeypatch):
    assert _main_exit_code(monkeypatch, False) == 1


def test_main_block_runs_deploy(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("subprocess.run", _FakeRun({}, _Result(0)))

    with pytest.raises(SystemExit) as exc:
        runpy.run_path(
            str(REPO_ROOT / "scripts" / "deploy_v23_github.py"), run_name="__main__"
        )

    assert exc.value.code == 1
    assert (tmp_path / "v23_deployment_report.json").is_file()
