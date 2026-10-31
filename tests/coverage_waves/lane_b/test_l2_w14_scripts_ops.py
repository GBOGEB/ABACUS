"""Lane-B wave 14: fetch_workflow_errors (subprocess faked; no git or gh runs).

The other wave-14 ops scripts are owned by #2533 (lane_ab_next).
"""

import runpy
import types

import pytest

from ._l2_loader import REPO_ROOT, load

fw = load("scripts/fetch_workflow_errors.py")
subprocess = fw.subprocess  # the stdlib module, reached without a direct import


def _done(returncode=0, stdout="", stderr=""):
    return types.SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


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
