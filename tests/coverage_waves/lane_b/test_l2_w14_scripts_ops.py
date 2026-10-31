"""Lane-B wave 14: ops scripts (metrics dump, T0 diagnostics, workflow tooling)."""

import csv
import json
import runpy
import shutil
import types
import urllib.parse

import pytest

from ._l2_loader import REPO_ROOT, load

dm = load("scripts/dmaic_metrics_dump.py")
fw = load("scripts/fetch_workflow_errors.py")
dv = load("scripts/deploy_v23_github.py")
ci = load("scripts/create_github_issues.py")
oi = load("scripts/open_github_issues.py")
subprocess = fw.subprocess  # the stdlib module, reached without a direct import


def _done(returncode=0, stdout="", stderr=""):
    return types.SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


# ------------------------------------------------------------ dmaic metrics


def test_dump_dmaic_metrics_writes_csv(tmp_path):
    out = tmp_path / "nested" / "dir"
    dm.dump_dmaic_metrics([{"phase": "D", "score": 1}, {"phase": "M", "score": 2}], out)
    with open(out / "dmaic_metrics.csv", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows == [{"phase": "D", "score": "1"}, {"phase": "M", "score": "2"}]


def test_dump_dmaic_metrics_empty(tmp_path):
    dm.dump_dmaic_metrics([], tmp_path)
    assert (tmp_path / "dmaic_metrics.csv").read_text(encoding="utf-8").strip() == ""


# --------------------------------------------------------- T0 diagnostics


def _load_t0(tmp_path, monkeypatch, name, run_result=0, which="npx"):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return _done(returncode=run_result)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(shutil, "which", lambda tool: which)
    mod = load("scripts/t0_deep_diagnostics.py", name=name)
    return mod, calls


def test_t0_all_probes_run(tmp_path, monkeypatch, capsys):
    (tmp_path / "a.yml").write_text("a: 1\n", encoding="utf-8")
    (tmp_path / "playwright.config.ts").write_text("x", encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "validate_qps_w04_dow_receipt.py").write_text(
        "print(1)\n", encoding="utf-8"
    )
    mod, calls = _load_t0(tmp_path, monkeypatch, "l2_w14_t0_full")
    report = json.loads(capsys.readouterr().out)
    assert report["schema"] == "ops-kpi-v1" and report["phase"] == "T0"
    probes = {p["name"]: p for p in report["probes"]}
    assert list(probes) == [
        "artifact_hash_scan",
        "yaml_parse",
        "playwright_list",
        "dow_contract_dry_run",
    ]
    assert all(p["status"] == "ok" for p in probes.values())
    assert probes["artifact_hash_scan"]["detail"]["files"] == 3
    assert len(calls) == 3
    assert calls[1] == "npx playwright test --list"


def test_t0_everything_skipped_or_failed(tmp_path, monkeypatch, capsys):
    (tmp_path / "x.yaml").write_text("a: 1\n", encoding="utf-8")
    _load_t0(tmp_path, monkeypatch, "l2_w14_t0_skip", run_result=2, which=None)
    probes = {p["name"]: p for p in json.loads(capsys.readouterr().out)["probes"]}
    assert probes["yaml_parse"]["status"] == "failed"
    assert probes["yaml_parse"]["detail"] == {"returncode": 2}
    assert probes["playwright_list"]["status"] == "skipped"
    assert probes["dow_contract_dry_run"]["detail"] == "validator unavailable"


def test_t0_no_yaml_and_probe_helpers(tmp_path, monkeypatch, capsys):
    mod, _ = _load_t0(tmp_path, monkeypatch, "l2_w14_t0_empty")
    probes = {p["name"]: p for p in json.loads(capsys.readouterr().out)["probes"]}
    assert probes["yaml_parse"] == {
        "name": "yaml_parse",
        "status": "skipped",
        "duration_ms": 0,
        "detail": "no yaml",
    }
    assert probes["artifact_hash_scan"]["detail"]["files"] == 0

    def boom():
        raise RuntimeError("x")

    failed = mod.probe("f", fn=boom)
    assert failed["status"] == "failed" and failed["detail"] == {
        "error": "RuntimeError"
    }
    idle = mod.probe("idle")
    assert idle["status"] == "ok" and idle["detail"] is None


def test_t0_hash_pack_tolerates_unreadable(tmp_path, monkeypatch, capsys):
    mod, _ = _load_t0(tmp_path, monkeypatch, "l2_w14_t0_hash")
    capsys.readouterr()
    (tmp_path / "a.txt").write_bytes(b"abc")
    (tmp_path / "b.txt").write_bytes(b"de")
    real_open = open

    def flaky_open(path, mode="r", *args, **kwargs):
        if str(path).endswith("b.txt"):
            raise OSError("locked")
        return real_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(mod, "open", flaky_open, raising=False)
    result = mod.hash_pack()
    assert result["files"] == 2 and result["bytes"] == 3


# -------------------------------------------------- fetch_workflow_errors


def test_get_workflow_runs_ok_and_error(monkeypatch, capsys):
    monkeypatch.setattr(
        fw.subprocess, "run", lambda *a, **k: _done(stdout="abc123ff99\n")
    )
    assert fw.get_workflow_runs() == "abc123ff99"
    assert "abc123ff" in capsys.readouterr().out

    def failing(*args, **kwargs):
        raise subprocess.CalledProcessError(128, ["git"])

    monkeypatch.setattr(fw.subprocess, "run", failing)
    assert fw.get_workflow_runs() is None
    assert "Error getting commit SHA" in capsys.readouterr().out


def test_analyze_workflow_files_no_dir(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert fw.analyze_workflow_files() is None
    assert "No .github/workflows" in capsys.readouterr().out


def test_analyze_workflow_files_flags_issues(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "bad.yml").write_text(
        "requirements.txt setup.py pyproject.toml python-version: '3.12'\n"
        "pytest docker pre-commit\n",
        encoding="utf-8",
    )
    (wf / "clean.yml").write_text("name: lint\n", encoding="utf-8")
    (wf / "dir.yml").mkdir()
    issues = dict(fw.analyze_workflow_files())
    assert list(issues) == ["bad.yml"]
    assert len(issues["bad.yml"]) == 7
    out = capsys.readouterr().out
    assert "No obvious issues detected" in out
    assert "Error reading file" in out


def test_analyze_workflow_files_satisfied(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for name in [
        "requirements.txt",
        "setup.py",
        "pyproject.toml",
        "Dockerfile",
        ".pre-commit-config.yaml",
    ]:
        (tmp_path / name).write_text("", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "ok.yml").write_text(
        "requirements.txt setup.py pyproject.toml python-version: '3.10'\n"
        "pytest docker pre-commit\n",
        encoding="utf-8",
    )
    assert fw.analyze_workflow_files() == []


def test_check_required_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "Dockerfile").write_text("", encoding="utf-8")
    missing = fw.check_required_files()
    assert len(missing) == 7
    assert not any("Dockerfile" in item for item in missing)


def test_generate_report_with_gaps(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(fw.subprocess, "run", lambda *a, **k: _done(stdout="f" * 40))
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "w.yml").write_text("docker\n", encoding="utf-8")
    fw.generate_report()
    out = capsys.readouterr().out
    assert "Found issues in 1 workflow files" in out
    assert "Missing 8 required files" in out
    for hint in [
        "Create requirements.txt",
        "Create setup.py",
        "Create pyproject.toml",
        "Create pytest.ini",
        "Create .pre-commit-config.yaml",
        "Create Dockerfile",
        "Create tests/ directory",
    ]:
        assert hint in out


def test_generate_report_clean(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(fw.subprocess, "run", lambda *a, **k: _done(stdout="e" * 40))
    for name in [
        "requirements.txt",
        "setup.py",
        "pyproject.toml",
        "pytest.ini",
        ".pre-commit-config.yaml",
        "Dockerfile",
    ]:
        (tmp_path / name).write_text("", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "docs").mkdir()
    fw.generate_report()
    out = capsys.readouterr().out
    assert "Missing" not in out and "Found issues" not in out
    assert "RECOMMENDED ACTIONS" in out


@pytest.mark.parametrize(
    "raised,code,text",
    [
        (None, None, "SUMMARY"),
        (KeyboardInterrupt, 1, "interrupted"),
        (RuntimeError, 1, "Error during"),
    ],
)
def test_fetch_workflow_errors_entrypoint(
    tmp_path, monkeypatch, capsys, raised, code, text
):
    monkeypatch.chdir(tmp_path)

    def fake_run(*args, **kwargs):
        if raised:
            raise raised("stop")
        return _done(stdout="d" * 40)

    monkeypatch.setattr(subprocess, "run", fake_run)
    path = str(REPO_ROOT / "scripts" / "fetch_workflow_errors.py")
    if code is None:
        runpy.run_path(path, run_name="__main__")
    else:
        with pytest.raises(SystemExit) as exc:
            runpy.run_path(path, run_name="__main__")
        assert exc.value.code == code
    assert text in capsys.readouterr().out


# ------------------------------------------------------- deploy_v23_github


@pytest.fixture
def deployer(tmp_path, monkeypatch):
    calls = []
    plan = {}

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        action = plan.get(cmd[0] + " " + cmd[1] if len(cmd) > 1 else cmd[0])
        if isinstance(action, BaseException):
            raise action
        if action is not None:
            return action
        return _done(stdout="ok")

    monkeypatch.setattr(dv.subprocess, "run", fake_run)
    obj = dv.GitHubDeploymentV23(branch="feat/x")
    obj.repo_root = tmp_path
    obj.calls, obj.plan = calls, plan
    return obj


def _cpe(stderr=""):
    return subprocess.CalledProcessError(1, ["git"], stderr=stderr)


def test_run_command_logs_output_and_errors(deployer):
    deployer.plan["git status"] = _done(stdout="")
    assert deployer.run_command(["git", "status"]).returncode == 0
    assert not any("Output:" in e for e in deployer.deployment_log)
    deployer.plan["git log"] = _done(stdout="line\n")
    deployer.run_command(["git", "log"])
    assert deployer.deployment_log[-1].endswith("[DEBUG] Output: line")
    deployer.plan["git fail"] = _cpe(stderr="boom")
    with pytest.raises(subprocess.CalledProcessError):
        deployer.run_command(["git", "fail"])
    assert deployer.deployment_log[-1].endswith("[ERROR] Error: boom")
    deployer.plan["git quiet"] = _cpe()
    with pytest.raises(subprocess.CalledProcessError):
        deployer.run_command(["git", "quiet"])
    assert "Command failed" in deployer.deployment_log[-1]


UNIFIED_DOCS = [
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


def test_verify_abacus_unified_files(deployer, tmp_path):
    assert deployer.verify_abacus_unified_files() is False
    (tmp_path / "ABACUS-UNIFIED").mkdir()
    for name in ["README.md", "QUICK_REFERENCE.md"]:
        (tmp_path / "ABACUS-UNIFIED" / name).write_text("x", encoding="utf-8")
    assert deployer.verify_abacus_unified_files() is False
    assert any("Missing 10 files" in e for e in deployer.deployment_log)
    for name in UNIFIED_DOCS:
        (tmp_path / "ABACUS-UNIFIED" / name).write_text("x", encoding="utf-8")
    assert deployer.verify_abacus_unified_files() is True


def test_stage_commit_push(deployer):
    assert deployer.stage_v23_changes() is True
    assert sum("Staged: " in e for e in deployer.deployment_log) == 7
    deployer.plan["git add"] = _cpe()
    assert deployer.stage_v23_changes() is True
    assert sum("Failed to stage" in e for e in deployer.deployment_log) == 7
    assert deployer.commit_v23_deployment() is True
    assert deployer.push_to_remote() is True
    assert ["git", "push", "origin", "feat/x"] in deployer.calls
    deployer.plan["git commit"] = _cpe()
    deployer.plan["git push"] = _cpe()
    assert deployer.commit_v23_deployment() is False
    assert deployer.push_to_remote() is False


def test_create_pr_paths(deployer):
    assert "V2.3 Complete Deployment" in deployer.create_pr_body()
    assert deployer.create_github_pr() is True
    pr_call = deployer.calls[-1]
    assert pr_call[:3] == ["gh", "pr", "create"] and "feat/x" in pr_call
    deployer.plan["gh pr"] = _done(returncode=1)
    assert deployer.create_github_pr() is False
    deployer.plan["gh --version"] = FileNotFoundError("gh")
    assert deployer.create_github_pr() is False
    assert "install GitHub CLI" in deployer.deployment_log[-1]


def test_create_issues_counts(deployer):
    assert deployer.create_github_issues() is True
    assert deployer.deployment_log[-1].endswith("Created 3/3 issues")
    deployer.plan["gh issue"] = _done(returncode=1)
    assert deployer.create_github_issues() is False
    deployer.plan["gh issue"] = OSError("nope")
    assert deployer.create_github_issues() is False
    assert deployer.deployment_log[-1].endswith("Created 0/3 issues")


def test_verify_ci_and_roundtrip(deployer, tmp_path):
    assert deployer.verify_ci_cd_pipeline() is False
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "v23-cicd.yml").write_text("x", encoding="utf-8")
    assert deployer.verify_ci_cd_pipeline() is True

    assert deployer.run_roundtrip_test() is True
    assert "skipping" in deployer.deployment_log[-1]
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "git_github_roundtrip.sh").write_text("", encoding="utf-8")
    assert deployer.run_roundtrip_test() is True
    deployer.plan["bash " + str(tmp_path / "scripts" / "git_github_roundtrip.sh")] = (
        _done(returncode=3)
    )
    assert deployer.run_roundtrip_test() is False
    deployer.plan["bash " + str(tmp_path / "scripts" / "git_github_roundtrip.sh")] = (
        OSError("no bash")
    )
    assert deployer.run_roundtrip_test() is False


def test_generate_deployment_report(deployer, tmp_path):
    deployer.log("hello")
    report = deployer.generate_deployment_report()
    saved = json.loads((tmp_path / "v23_deployment_report.json").read_text())
    assert saved["branch"] == "feat/x" and saved["version"] == "V2.3.0"
    assert saved["deployment_log"][0].endswith("[INFO] hello")
    assert report["branch"] == "feat/x"


def _stub_steps(monkeypatch, obj, outcome):
    for name in [
        "verify_abacus_unified_files",
        "stage_v23_changes",
        "commit_v23_deployment",
        "push_to_remote",
        "verify_ci_cd_pipeline",
        "create_github_pr",
        "create_github_issues",
        "run_roundtrip_test",
    ]:
        monkeypatch.setattr(obj, name, lambda: outcome)


def test_deploy_full_success(deployer, monkeypatch, tmp_path):
    _stub_steps(monkeypatch, deployer, True)
    assert deployer.deploy() is True
    assert "100% SUCCESS" in deployer.deployment_log[-1]
    assert (tmp_path / "v23_deployment_report.json").exists()


def test_deploy_partial_with_raising_step(deployer, monkeypatch):
    _stub_steps(monkeypatch, deployer, True)

    def boom():
        raise RuntimeError("bad step")

    monkeypatch.setattr(deployer, "push_to_remote", boom)
    assert deployer.deploy() is False
    log = "\n".join(deployer.deployment_log)
    assert "Step failed: bad step" in log
    assert "FAIL - Push to remote" in log
    assert "7/8 steps successful" in log


@pytest.mark.parametrize("ok,code", [(True, 0), (False, 1)])
def test_deploy_main_exit_code(tmp_path, monkeypatch, ok, code):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(dv.GitHubDeploymentV23, "deploy", lambda self: ok)
    with pytest.raises(SystemExit) as exc:
        dv.main()
    assert exc.value.code == code


# ------------------------------------------------------ create_github_issues


def test_generate_issue_files(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    ci.generate_issue_files()
    out_dir = tmp_path / "github_issues"
    issue_files = sorted(out_dir.glob("issue_*.md"))
    assert len(issue_files) == len(ci.ISSUES)
    first = issue_files[0].read_text(encoding="utf-8")
    assert first.startswith("# " + ci.ISSUES[0]["title"])
    assert "`P1`" in first
    readme = (out_dir / "README.md").read_text(encoding="utf-8")
    assert "Total issues: 5" in readme
    assert readme.count("gh issue create") == 5
    quick = (out_dir / "QUICK_REFERENCE.md").read_text(encoding="utf-8")
    assert "P0 - Critical" in quick and "P2 - Nice to Have" in quick
    assert "Done!" in capsys.readouterr().out


def test_generate_issue_files_without_priorities(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    issue = {"title": "Plain issue", "body": "b", "labels": ["docs"]}
    monkeypatch.setattr(ci, "ISSUES", [issue])
    ci.generate_issue_files()
    readme = (tmp_path / "github_issues" / "README.md").read_text(encoding="utf-8")
    assert "**Plain issue** - Priority: P2" in readme
    quick = (tmp_path / "github_issues" / "QUICK_REFERENCE.md").read_text("utf-8")
    assert "P0 - Critical" not in quick
    assert "P1 - Important" not in quick
    assert "P2 - Nice" not in quick


# -------------------------------------------------------- open_github_issues


def test_create_github_issue_url_roundtrips():
    url = oi.create_github_issue_url("T & x", "body\nline", ["a", "b"])
    base, query = url.split("?", 1)
    assert base == "https://github.com/GBOGEB/ABACUS/issues/new"
    params = urllib.parse.parse_qs(query)
    assert params == {"title": ["T & x"], "body": ["body\nline"], "labels": ["a,b"]}


def test_open_issues_main_opens_each(monkeypatch, capsys):
    opened, slept = [], []
    monkeypatch.setattr(oi.webbrowser, "open", lambda url: opened.append(url))
    monkeypatch.setattr(oi.time, "sleep", lambda s: slept.append(s))
    oi.main()
    assert len(opened) == len(oi.ISSUES)
    assert slept == [3] * (len(oi.ISSUES) - 1)
    assert "All issue creation pages opened" in capsys.readouterr().out


def test_open_issues_main_reports_browser_error(monkeypatch, capsys):
    def broken(url):
        raise RuntimeError("no browser")

    monkeypatch.setattr(oi.webbrowser, "open", broken)
    monkeypatch.setattr(oi.time, "sleep", lambda s: pytest.fail("should not sleep"))
    oi.main()
    out = capsys.readouterr().out
    assert out.count("Error: no browser") == len(oi.ISSUES)
    assert "Manual URL: https://github.com/GBOGEB/ABACUS/issues/new?" in out
