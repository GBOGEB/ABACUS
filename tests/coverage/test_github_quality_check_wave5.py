from types import SimpleNamespace

import pytest

import DMAIC_V3.generators.github_quality_check as quality_module
from DMAIC_V3.generators.github_quality_check import GitHubQualityCheck


@pytest.mark.unit
def test_cleanup_and_core_validation_cover_keep_remove_valid_invalid_missing(tmp_path):
    checker = GitHubQualityCheck(tmp_path)
    checker.CORE_PYTHON_FILES = {
        "keep/test_core.py",
        "invalid.py",
        "missing.py",
    }

    keep = tmp_path / "keep" / "test_core.py"
    keep.parent.mkdir()
    keep.write_text("value = 1\n", encoding="utf-8")

    removable = tmp_path / "scratch" / "test_remove.py"
    removable.parent.mkdir()
    removable.write_text("value = 2\n", encoding="utf-8")

    invalid = tmp_path / "invalid.py"
    invalid.write_text("def broken(:\n", encoding="utf-8")

    checker.cleanup_temporary_files()
    assert keep.exists()
    assert not removable.exists()
    assert "scratch/test_remove.py" in [
        item.replace("\\", "/") for item in checker.report["removed_files"]
    ]

    checker.validate_core_files()
    assert checker.report["quality_checks"]["core_files_valid"] == 1
    assert checker.report["quality_checks"]["core_files_invalid"] == 2
    assert "keep/test_core.py" in checker.report["kept_files"]


@pytest.mark.unit
def test_quality_tool_wrappers_capture_subprocess_results(tmp_path, monkeypatch):
    checker = GitHubQualityCheck(tmp_path)
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout="tool ok", stderr="")

    monkeypatch.setattr(quality_module.subprocess, "run", fake_run)

    checker.run_linting()
    checker.run_formatting_check()
    checker.run_type_checking()

    assert checker.report["quality_checks"]["flake8_exit_code"] == 0
    assert checker.report["quality_checks"]["black_exit_code"] == 0
    assert checker.report["quality_checks"]["mypy_exit_code"] == 0
    assert len(calls) == 3


@pytest.mark.unit
def test_generated_repo_files_existing_git_and_report(tmp_path, capsys):
    checker = GitHubQualityCheck(tmp_path)
    (tmp_path / ".git").mkdir()

    checker.create_gitignore()
    checker.create_gitattributes()
    checker.initialize_git_repo()
    checker.create_requirements_txt()
    checker.create_setup_py()
    checker.save_report()
    checker.print_summary()

    assert (tmp_path / ".gitignore").exists()
    assert (tmp_path / ".gitattributes").exists()
    assert (tmp_path / "requirements.txt").exists()
    assert (tmp_path / "setup.py").exists()
    assert checker.report["git_status"]["repo_exists"] is True
    assert checker.report["git_status"]["gitignore_created"] is True
    assert checker.report["git_status"]["gitattributes_created"] is True
    assert checker.report["git_status"]["requirements_created"] is True
    assert checker.report["git_status"]["setup_created"] is True
    assert list((tmp_path / "output" / "quality_reports").glob("github_quality_report_*.json"))
    assert "GITHUB QUALITY CHECK SUMMARY" in capsys.readouterr().out


@pytest.mark.unit
def test_run_all_checks_calls_each_stage_in_order(tmp_path, monkeypatch):
    checker = GitHubQualityCheck(tmp_path)
    order = []
    stages = [
        "cleanup_temporary_files",
        "validate_core_files",
        "run_linting",
        "run_formatting_check",
        "run_type_checking",
        "create_gitignore",
        "create_gitattributes",
        "initialize_git_repo",
        "create_requirements_txt",
        "create_setup_py",
        "save_report",
        "print_summary",
    ]

    for name in stages:
        monkeypatch.setattr(checker, name, lambda name=name: order.append(name))

    checker.run_all_checks()
    assert order == stages
