"""Lane A wave 13: DMAIC_V3.generators.github_quality_check in a sandbox root."""

import json
import types
from pathlib import Path

import pytest

from DMAIC_V3.generators import github_quality_check as gqc


def _touch(path, data=b""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


@pytest.fixture
def checker(tmp_path):
    return gqc.GitHubQualityCheck(tmp_path)


def test_init_report_shape(checker, tmp_path):
    assert checker.root_dir == tmp_path
    assert checker.report["removed_files"] == []
    assert set(checker.report) == {
        "timestamp",
        "removed_files",
        "kept_files",
        "quality_checks",
        "git_status",
    }


def test_cleanup_removes_temporary_and_keeps_core(checker, tmp_path, capsys):
    core = _touch(tmp_path / "DMAIC_V3" / "generators" / "test_real_execution.py")
    _touch(tmp_path / "pkg" / "test_thing.py")
    _touch(tmp_path / "pkg" / "debug_x.py")
    _touch(tmp_path / "nb.ipynb")
    _touch(tmp_path / "pkg" / "__pycache__" / "m.cpython.pyc")
    _touch(tmp_path / "keep.py")
    checker.cleanup_temporary_files()
    out = capsys.readouterr().out
    assert core.exists()
    assert (tmp_path / "keep.py").exists()
    assert not (tmp_path / "pkg" / "test_thing.py").exists()
    assert not (tmp_path / "pkg" / "__pycache__").exists()
    removed = {Path(p).as_posix() for p in checker.report["removed_files"]}
    assert {"pkg/test_thing.py", "pkg/debug_x.py", "nb.ipynb"} <= removed
    assert "pkg/__pycache__" in removed
    assert "(core file)" in out
    assert "[REMOVE DIR]" in out


def test_cleanup_reports_failures(checker, tmp_path, monkeypatch, capsys):
    _touch(tmp_path / "temp_a.py")
    (tmp_path / ".idea").mkdir()

    def deny(self, *a, **k):
        raise PermissionError("locked")

    def deny_tree(path, *a, **k):
        raise OSError("busy")

    monkeypatch.setattr(Path, "unlink", deny)
    monkeypatch.setattr("shutil.rmtree", deny_tree)
    checker.cleanup_temporary_files()
    out = capsys.readouterr().out
    assert "Failed to remove temp_a.py: locked" in out
    assert "Failed to remove .idea: busy" in out
    assert checker.report["removed_files"] == []
    assert "Removed 0 temporary files" in out


def test_validate_core_files(checker, tmp_path, capsys):
    _touch(tmp_path / "master_document_system" / "master_engine.py", b"x = 1\n")
    _touch(tmp_path / "master_document_system" / "quick_start.py", b"def (:\n")
    checker.validate_core_files()
    checks = checker.report["quality_checks"]
    total = len(gqc.GitHubQualityCheck.CORE_PYTHON_FILES)
    assert checks["core_files_valid"] == 1
    assert checks["core_files_invalid"] == total - 1
    assert checker.report["kept_files"] == ["master_document_system/master_engine.py"]
    out = capsys.readouterr().out
    assert "[INVALID] master_document_system/quick_start.py" in out
    assert "[MISSING]" in out


def _fake_run(record, rc=0, stdout="out", stderr="warn"):
    def fake(cmd, **kw):
        record.append((cmd, kw))
        return types.SimpleNamespace(returncode=rc, stdout=stdout, stderr=stderr)

    return fake


@pytest.mark.parametrize(
    "method,tool,prefix",
    [
        ("run_linting", "flake8", "flake8"),
        ("run_formatting_check", "black", "black"),
        ("run_type_checking", "mypy", "mypy"),
    ],
)
def test_quality_tools_success(checker, monkeypatch, capsys, method, tool, prefix):
    record = []
    monkeypatch.setattr("subprocess.run", _fake_run(record, rc=3))
    getattr(checker, method)()
    cmd, kw = record[0]
    assert cmd[1:3] == ["-m", tool]
    assert kw["cwd"] == str(checker.root_dir)
    checks = checker.report["quality_checks"]
    assert checks[prefix + "_exit_code"] == 3
    assert checks[prefix + "_output"] == "out"
    assert "warn" in capsys.readouterr().out


@pytest.mark.parametrize(
    "method,prefix",
    [
        ("run_linting", "flake8"),
        ("run_formatting_check", "black"),
        ("run_type_checking", "mypy"),
    ],
)
def test_quality_tools_errors(checker, monkeypatch, method, prefix):
    def fail(cmd, **kw):
        raise FileNotFoundError("no tool")

    monkeypatch.setattr("subprocess.run", fail)
    getattr(checker, method)()
    assert checker.report["quality_checks"][prefix + "_error"] == "no tool"


def test_quality_tool_without_stderr(checker, monkeypatch, capsys):
    monkeypatch.setattr("subprocess.run", _fake_run([], stdout="clean", stderr=""))
    checker.run_linting()
    assert "clean" in capsys.readouterr().out


def test_config_file_writers(checker, tmp_path):
    checker.create_gitignore()
    checker.create_gitattributes()
    checker.create_requirements_txt()
    checker.create_setup_py()
    assert "__pycache__/" in (tmp_path / ".gitignore").read_text(encoding="utf-8")
    attrs = (tmp_path / ".gitattributes").read_text(encoding="utf-8")
    assert "*.py text eol=lf" in attrs
    reqs = (tmp_path / "requirements.txt").read_text(encoding="utf-8")
    assert "PyYAML>=6.0.1" in reqs
    setup = (tmp_path / "setup.py").read_text(encoding="utf-8")
    compile(setup, "setup.py", "exec")
    assert checker.report["git_status"] == {
        "gitignore_created": True,
        "gitattributes_created": True,
        "requirements_created": True,
        "setup_created": True,
    }


def test_initialize_git_repo_existing(checker, tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()
    record = []
    monkeypatch.setattr("subprocess.run", _fake_run(record))
    checker.initialize_git_repo()
    assert record == []
    assert checker.report["git_status"]["repo_exists"] is True


def test_initialize_git_repo_new_and_error(checker, monkeypatch, capsys):
    record = []
    monkeypatch.setattr("subprocess.run", _fake_run(record))
    checker.initialize_git_repo()
    assert [r[0] for r in record] == [["git", "init"], ["git", "branch", "-M", "main"]]
    assert record[0][1]["check"] is True
    assert checker.report["git_status"]["repo_initialized"] is True

    def fail(cmd, **kw):
        raise OSError("git missing")

    monkeypatch.setattr("subprocess.run", fail)
    checker.initialize_git_repo()
    assert checker.report["git_status"]["init_error"] == "git missing"
    assert "Failed to initialize git" in capsys.readouterr().out


def test_save_report_and_summary(checker, tmp_path, capsys):
    checker.report["removed_files"] = ["a"]
    checker.report["quality_checks"]["flake8_exit_code"] = 0
    checker.report["git_status"]["repo_exists"] = True
    checker.save_report()
    files = list((tmp_path / "output" / "quality_reports").glob("*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text(encoding="utf-8"))
    assert data["removed_files"] == ["a"]
    checker.print_summary()
    out = capsys.readouterr().out
    assert "Removed files: 1" in out
    assert "flake8_exit_code: 0" in out
    assert "repo_exists: True" in out
    assert "NEXT STEPS:" in out


def test_run_all_checks_in_sandbox(checker, tmp_path, monkeypatch, capsys):
    record = []
    monkeypatch.setattr("subprocess.run", _fake_run(record, rc=0, stderr=""))
    _touch(tmp_path / "temp_x.py")
    checker.run_all_checks()
    assert not (tmp_path / "temp_x.py").exists()
    assert (tmp_path / "setup.py").exists()
    tools = [r[0][2] for r in record if r[0][0] != "git"]
    assert tools == ["flake8", "black", "mypy"]
    assert "GITHUB QUALITY CHECK SUMMARY" in capsys.readouterr().out


def test_main_targets_repo_root(monkeypatch):
    seen = []

    def fake_run_all(self):
        seen.append(self.root_dir)

    monkeypatch.setattr(gqc.GitHubQualityCheck, "run_all_checks", fake_run_all)
    gqc.main()
    assert seen == [Path(gqc.__file__).parent.parent.parent]
