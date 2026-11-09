"""Behaviour tests for DMAIC_V3/phases/_LEGACY_phase0_setup.py."""

import sys
from collections import namedtuple
from types import SimpleNamespace

import pytest

from tests.coverage_waves.lane_a._load import load

p0 = load("DMAIC_V3/phases/_LEGACY_phase0_setup.py")

Usage = namedtuple("Usage", "total used free")


def make_config(tmp_path, **overrides):
    workspace = tmp_path / "ws"
    workspace.mkdir(exist_ok=True)
    phase0 = SimpleNamespace(
        python_min_version="3.0",
        required_disk_space_mb=1,
        check_git=True,
        auto_create_venv=True,
        venv_name=str(tmp_path / "venv"),
        validate_dependencies=True,
        fail_on_warning=False,
    )
    for key, value in overrides.pop("phase0", {}).items():
        setattr(phase0, key, value)
    paths = SimpleNamespace(
        workspace_root=workspace,
        output_root=tmp_path / "out",
        state_dir=tmp_path / "state",
    )
    for key, value in overrides.pop("paths", {}).items():
        setattr(paths, key, value)
    return SimpleNamespace(
        phase0=phase0, paths=paths, max_iterations=overrides.get("max_iterations", 3)
    )


@pytest.fixture
def setup(tmp_path):
    return p0.Phase0Setup(make_config(tmp_path))


def names(results):
    return [r.name for r in results]


def test_check_result_defaults():
    r = p0.CheckResult(name="n", passed=True, message="m")
    assert r.severity == "error"
    assert r.details == {}


def test_add_result_routes_by_pass_and_severity(setup):
    setup._add_result(p0.CheckResult("a", True, "ok"))
    setup._add_result(p0.CheckResult("b", False, "w", severity="warning"))
    setup._add_result(p0.CheckResult("c", False, "e"))
    assert names(setup.checks_passed) == ["a"]
    assert names(setup.checks_warnings) == ["b"]
    assert names(setup.checks_failed) == ["c"]


def test_python_version_ok(setup):
    setup._check_python_version()
    assert setup.checks_passed[0].details["required"] == "3.0"


def test_python_version_too_old(tmp_path):
    s = p0.Phase0Setup(make_config(tmp_path, phase0={"python_min_version": "99.0"}))
    s._check_python_version()
    assert s.checks_failed[0].name == "Python Version"


def test_system_requirements(setup):
    setup._check_system_requirements()
    res = setup.checks_passed[0]
    assert res.details["os"] == sys.platform
    assert "architecture" in res.details


def test_disk_space_ok_uses_parent_when_output_exists(setup, monkeypatch, tmp_path):
    setup.config.paths.output_root.mkdir()
    seen = []

    def fake_usage(path):
        seen.append(path)
        return Usage(0, 0, 10 * 1024 * 1024)

    monkeypatch.setattr(p0.shutil, "disk_usage", fake_usage)
    setup._check_disk_space()
    assert seen == [tmp_path]
    assert setup.checks_passed[0].details["available_mb"] == 10


def test_disk_space_insufficient_uses_cwd(setup, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    seen = []

    def fake_usage(path):
        seen.append(path)
        return Usage(0, 0, 0)

    monkeypatch.setattr(p0.shutil, "disk_usage", fake_usage)
    setup._check_disk_space()
    assert seen[0].resolve() == tmp_path.resolve()
    assert setup.checks_warnings[0].message.startswith("Insufficient")


def test_disk_space_error(setup, monkeypatch):
    def boom(path):
        raise OSError("nope")

    monkeypatch.setattr(p0.shutil, "disk_usage", boom)
    setup._check_disk_space()
    assert "nope" in setup.checks_warnings[0].message


def test_git_disabled(tmp_path, monkeypatch):
    s = p0.Phase0Setup(make_config(tmp_path, phase0={"check_git": False}))

    def fail(*a, **k):
        raise AssertionError("should not run")

    monkeypatch.setattr("subprocess.run", fail)
    s._check_git_availability()
    assert s.checks_passed == s.checks_warnings == []


@pytest.mark.parametrize("rc,bucket", [(0, "checks_passed"), (1, "checks_warnings")])
def test_git_result_codes(setup, monkeypatch, rc, bucket):
    def fake_run(cmd, **kwargs):
        assert cmd == ["git", "--version"]
        return SimpleNamespace(returncode=rc, stdout="git version 9.9\n")

    monkeypatch.setattr("subprocess.run", fake_run)
    setup._check_git_availability()
    result = getattr(setup, bucket)[0]
    assert result.name == "Git Availability"
    if rc == 0:
        assert result.details["version"] == "git version 9.9"


def test_git_exception(setup, monkeypatch):
    def fake_run(cmd, **kwargs):
        raise FileNotFoundError("git missing")

    monkeypatch.setattr("subprocess.run", fake_run)
    setup._check_git_availability()
    assert "git missing" in setup.checks_warnings[0].message


def test_venv_disabled(tmp_path):
    s = p0.Phase0Setup(make_config(tmp_path, phase0={"auto_create_venv": False}))
    s._setup_virtual_environment()
    assert s.checks_passed == s.checks_warnings == []


def test_venv_already_active(setup, monkeypatch):
    monkeypatch.setattr(sys, "base_prefix", "/base", raising=False)
    monkeypatch.setattr(sys, "prefix", "/venv")
    setup._setup_virtual_environment()
    assert setup.checks_passed[0].message.startswith("Already")


def not_in_venv(monkeypatch):
    monkeypatch.delattr(sys, "real_prefix", raising=False)
    monkeypatch.setattr(sys, "base_prefix", sys.prefix)


def test_venv_exists(setup, monkeypatch, tmp_path):
    not_in_venv(monkeypatch)
    (tmp_path / "venv").mkdir()
    setup._setup_virtual_environment()
    assert setup.checks_passed[0].message.startswith("Virtual environment exists")


def test_venv_missing(setup, monkeypatch):
    not_in_venv(monkeypatch)
    setup._setup_virtual_environment()
    assert setup.checks_warnings[0].message.startswith("Virtual environment not")


def test_dependencies_disabled(tmp_path):
    s = p0.Phase0Setup(make_config(tmp_path, phase0={"validate_dependencies": False}))
    s._validate_dependencies()
    assert s.checks_passed == s.checks_failed == []


def test_dependencies_all_present(setup):
    setup._validate_dependencies()
    assert setup.checks_passed[0].details["checked"][0] == "pathlib"


def test_dependencies_missing(setup, monkeypatch):
    real_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "json":
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    setup._validate_dependencies()
    monkeypatch.undo()
    assert setup.checks_failed[0].details["missing"] == ["json"]


def test_configuration_valid(setup):
    setup._validate_configuration()
    assert setup.checks_passed[0].message == "Configuration valid"


def test_configuration_all_issues(tmp_path):
    cfg = make_config(
        tmp_path,
        paths={"workspace_root": None, "output_root": None},
        max_iterations=0,
    )
    s = p0.Phase0Setup(cfg)
    s._validate_configuration()
    assert s.checks_failed[0].details["issues"] == [
        "Workspace root not set",
        "Output root not set",
        "Max iterations must be >= 1",
    ]


def test_workspace_valid_and_output_created(setup, tmp_path):
    setup._validate_workspace()
    assert names(setup.checks_passed) == ["Workspace", "Output Directory"]
    assert (tmp_path / "out").is_dir()


def test_workspace_missing(tmp_path):
    s = p0.Phase0Setup(make_config(tmp_path, paths={"workspace_root": tmp_path / "x"}))
    s._validate_workspace()
    assert s.checks_failed[0].message.startswith("Workspace does not exist")


def test_workspace_is_file(tmp_path):
    f = tmp_path / "file.txt"
    f.write_bytes(b"x")
    s = p0.Phase0Setup(make_config(tmp_path, paths={"workspace_root": f}))
    s._validate_workspace()
    assert s.checks_failed[0].message.startswith("Workspace is not a directory")


def test_workspace_unreadable(setup, monkeypatch):
    monkeypatch.setattr(p0.os, "access", lambda path, mode: False)
    setup._validate_workspace()
    assert setup.checks_failed[0].message.startswith("No read access")


def test_output_dir_cannot_be_created(tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_bytes(b"x")
    s = p0.Phase0Setup(make_config(tmp_path, paths={"output_root": blocker / "sub"}))
    s._validate_workspace()
    assert s.checks_failed[0].name == "Output Directory"
    assert s.checks_failed[0].message.startswith("Cannot create output directory")


def test_previous_state_found(setup, tmp_path):
    (tmp_path / "state").mkdir()
    (tmp_path / "state" / "execution_state.json").write_bytes(b"{}")
    setup._check_previous_state()
    assert setup.checks_passed[0].details["can_resume"] is True


def test_previous_state_fresh(setup):
    setup._check_previous_state()
    assert setup.checks_passed[0].details == {"can_resume": False}


def test_report_with_failures_and_warnings(setup, capsys):
    setup._add_result(p0.CheckResult("ok", True, "fine"))
    setup._add_result(p0.CheckResult("w", False, "warn", severity="warning"))
    setup._add_result(p0.CheckResult("e", False, "err"))
    success, results = setup._generate_report()
    out = capsys.readouterr().out
    assert success is False
    assert results["total_checks"] == 3
    assert results["checks"]["failed"] == [{"name": "e", "message": "err"}]
    assert results["checks"]["warnings"] == [{"name": "w", "message": "warn"}]
    assert "FAILED CHECKS:" in out
    assert "WARNINGS:" in out


@pytest.mark.parametrize("fail_on_warning,expected", [(True, False), (False, True)])
def test_report_warning_policy(tmp_path, fail_on_warning, expected):
    s = p0.Phase0Setup(
        make_config(tmp_path, phase0={"fail_on_warning": fail_on_warning})
    )
    s._add_result(p0.CheckResult("w", False, "warn", severity="warning"))
    success, results = s._generate_report()
    assert success is expected
    assert results["warnings"] == 1


def test_execute_end_to_end(setup, monkeypatch):
    monkeypatch.setattr(p0.shutil, "disk_usage", lambda p: Usage(0, 0, 1 << 30))
    monkeypatch.setattr(
        "subprocess.run",
        lambda cmd, **k: SimpleNamespace(returncode=0, stdout="git version 1"),
    )
    monkeypatch.setattr(sys, "base_prefix", "/base", raising=False)
    monkeypatch.setattr(sys, "prefix", "/venv")
    success, results = setup.execute()
    assert success is True
    assert results["failed"] == 0
    assert results["passed"] == results["total_checks"] == 10
