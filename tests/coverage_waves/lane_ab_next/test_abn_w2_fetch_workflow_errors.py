"""Behaviour tests for scripts/fetch_workflow_errors.py."""

import runpy
import types

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

mod = load("scripts/fetch_workflow_errors.py", name="abn_fetch_workflow_errors")
SCRIPT = REPO_ROOT / "scripts" / "fetch_workflow_errors.py"

PROBLEM_WORKFLOW = "\n".join(
    [
        "name: ci",
        "steps:",
        "  - run: pip install -r requirements.txt",
        "  - run: python setup.py install",
        "  - run: cat pyproject.toml",
        "  - uses: actions/setup-python",
        "    with:",
        "      python-version: '3.11'",
        "  - run: pytest",
        "  - run: docker build .",
        "  - run: pre-commit run",
        "",
    ]
)
CLEAN_WORKFLOW = "name: lint\nsteps:\n  - run: echo hello\n"


def _fake_run(sha="0123456789abcdef0123"):
    calls = []

    def fake(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return types.SimpleNamespace(stdout=sha + "\n")

    return fake, calls


def _write_workflows(root, files):
    wf = root / ".github" / "workflows"
    wf.mkdir(parents=True)
    for name, text in files.items():
        (wf / name).write_bytes(text.encode("utf-8"))
    return wf


def test_get_workflow_runs_returns_sha_and_prints_short(monkeypatch, capsys):
    fake, calls = _fake_run()
    monkeypatch.setattr(mod.subprocess, "run", fake)

    assert mod.get_workflow_runs() == "0123456789abcdef0123"

    assert calls[0][0] == ["git", "rev-parse", "HEAD"]
    assert calls[0][1]["check"] is True
    out = capsys.readouterr().out
    assert "commit: 01234567" in out
    assert "0123456789abcdef0123" not in out
    assert "GBOGEB/ABACUS/actions" in out


def test_get_workflow_runs_returns_none_on_git_error(monkeypatch, capsys):
    def boom(cmd, **kwargs):
        raise mod.subprocess.CalledProcessError(128, cmd)

    monkeypatch.setattr(mod.subprocess, "run", boom)

    assert mod.get_workflow_runs() is None
    assert "Error getting commit SHA" in capsys.readouterr().out


def test_analyze_without_workflow_dir_returns_none(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    assert mod.analyze_workflow_files() is None
    assert "No .github/workflows directory found" in capsys.readouterr().out


def test_analyze_flags_every_missing_reference(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_workflows(tmp_path, {"ci.yml": PROBLEM_WORKFLOW, "lint.yml": CLEAN_WORKFLOW})

    issues = dict(mod.analyze_workflow_files())

    assert list(issues) == ["ci.yml"]
    joined = "\n".join(issues["ci.yml"])
    assert len(issues["ci.yml"]) == 7
    assert "requirements.txt but file doesn't exist" in joined
    assert "setup.py but file doesn't exist" in joined
    assert "pyproject.toml but file doesn't exist" in joined
    assert "Python 3.11/3.12" in joined
    assert "no tests/ directory found" in joined
    assert "no Dockerfile found" in joined
    assert "no .pre-commit-config.yaml found" in joined
    out = capsys.readouterr().out
    assert "Checking: ci.yml" in out
    assert "Checking: lint.yml" in out
    assert "No obvious issues detected" in out


def test_analyze_satisfied_references_produce_no_issues(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for name in (
        "requirements.txt",
        "setup.py",
        "pyproject.toml",
        "Dockerfile",
        ".pre-commit-config.yaml",
    ):
        (tmp_path / name).write_bytes(b"x")
    (tmp_path / "test").mkdir()
    text = PROBLEM_WORKFLOW.replace("'3.11'", "'3.10'")
    _write_workflows(tmp_path, {"ci.yml": text})

    assert mod.analyze_workflow_files() == []


def test_analyze_reports_unreadable_workflow(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    wf = _write_workflows(tmp_path, {})
    (wf / "broken.yml").mkdir()

    assert mod.analyze_workflow_files() == []
    assert "Error reading file" in capsys.readouterr().out


def test_check_required_files_all_missing(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    missing = mod.check_required_files()

    assert len(missing) == 8
    assert any("pytest.ini" in item for item in missing)
    out = capsys.readouterr().out
    assert "Missing:" in out


def test_check_required_files_all_present(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    for name in (
        "requirements.txt",
        "setup.py",
        "pyproject.toml",
        "pytest.ini",
        ".pre-commit-config.yaml",
        "Dockerfile",
    ):
        (tmp_path / name).write_bytes(b"x")
    (tmp_path / "tests").mkdir()
    (tmp_path / "docs").mkdir()

    assert mod.check_required_files() == []
    out = capsys.readouterr().out
    assert "docs/ - Documentation directory" in out
    assert "Missing:" not in out


def test_generate_report_with_issues_lists_actions(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    fake, _ = _fake_run()
    monkeypatch.setattr(mod.subprocess, "run", fake)
    _write_workflows(tmp_path, {"ci.yml": PROBLEM_WORKFLOW})

    assert mod.generate_report() is None

    out = capsys.readouterr().out
    assert "Found issues in 1 workflow files" in out
    assert "Missing 8 required files" in out
    for line in (
        "Create requirements.txt",
        "Create setup.py",
        "Create pyproject.toml",
        "Create pytest.ini",
        "Create .pre-commit-config.yaml",
        "Create Dockerfile",
        "Create tests/ directory",
    ):
        assert line in out
    assert "Common fixes" in out


def test_generate_report_clean_repo(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    fake, _ = _fake_run()
    monkeypatch.setattr(mod.subprocess, "run", fake)

    mod.generate_report()

    out = capsys.readouterr().out
    assert "Found issues" not in out
    assert "No .github/workflows directory found" in out
    assert "Create missing required files" in out


def test_main_runs_report(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    fake, calls = _fake_run()
    monkeypatch.setattr("subprocess.run", fake)

    runpy.run_path(str(SCRIPT), run_name="__main__")

    assert calls
    assert "GITHUB ACTIONS FAILURE ANALYSIS" in capsys.readouterr().out


@pytest.mark.parametrize(
    "exc, message",
    [
        (KeyboardInterrupt(), "Analysis interrupted by user"),
        (RuntimeError("kaput"), "Error during analysis: kaput"),
    ],
)
def test_main_exits_one_on_failure(tmp_path, monkeypatch, capsys, exc, message):
    monkeypatch.chdir(tmp_path)

    def boom(cmd, **kwargs):
        raise exc

    monkeypatch.setattr("subprocess.run", boom)

    with pytest.raises(SystemExit) as info:
        runpy.run_path(str(SCRIPT), run_name="__main__")

    assert info.value.code == 1
    assert message in capsys.readouterr().out
