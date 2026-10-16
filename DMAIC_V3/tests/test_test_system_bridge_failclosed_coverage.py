"""C4 behavioral tests for fail-closed DMAIC test-system bridge admission."""

import json
import subprocess
import sys
import threading
from types import SimpleNamespace

import pytest

from DMAIC_V3.core import test_system_bridge as bridge_module


@pytest.fixture
def bridge(tmp_path, monkeypatch):
    instance = object.__new__(bridge_module.TestSystemBridge)
    instance.workspace_root = tmp_path
    instance.output_root = tmp_path / "out"
    instance.mcp = bridge_module.MCPControlPoint(tmp_path / ".mcp")
    instance.test_results = {}
    instance.test_results_lock = threading.Lock()
    instance.version_file = tmp_path / "DMAIC_V3" / "VERSION"
    instance.version_file.parent.mkdir()
    instance.actions_file = tmp_path / "actions.json"
    monkeypatch.setattr(
        instance,
        "run_static_analysis",
        lambda: {"flake8": {"returncode": 0}, "mypy": None, "pylint": None},
    )
    return instance


def successful_result(name="ok"):
    return bridge_module.TestExecutionResult(
        test_name=name,
        returncode=0,
        stdout="passed",
        stderr="",
        success=True,
        duration_seconds=0.25,
    )


def test_zero_tests_cannot_report_deployment_ready(bridge):
    metrics = bridge.generate_deployment_metrics()
    assert metrics.tests_total == 0
    assert metrics.tests_passed == 0
    assert metrics.tests_failed == 0
    assert metrics.static_analysis_passed
    assert metrics.deployment_ready is False


@pytest.mark.parametrize(
    "scan",
    [
        {"flake8": {"error": "scanner crashed"}},
        {"flake8": None, "mypy": None},
        {"flake8": {"returncode": 0}, "mypy": {"error": "incomplete"}},
        {},
    ],
)
def test_missing_or_failing_static_analysis_cannot_be_green(bridge, monkeypatch, scan):
    bridge.test_results["good"] = successful_result()
    monkeypatch.setattr(bridge, "run_static_analysis", lambda: scan)
    metrics = bridge.generate_deployment_metrics()
    assert metrics.tests_total == 1
    assert metrics.tests_passed == 1
    assert metrics.static_analysis_passed is False
    assert metrics.deployment_ready is False


def test_parallel_worker_exception_is_counted_as_failed_result(bridge, monkeypatch):
    def fake_run_test(name, _command, _artifacts, _cwd, _timeout):
        if name == "raises":
            raise RuntimeError("simulated worker crash")
        result = successful_result(name)
        with bridge.test_results_lock:
            bridge.test_results[name] = result
        return result

    monkeypatch.setattr(bridge, "run_test", fake_run_test)
    results = bridge.run_tests_parallel(
        [
            {"name": "good", "command": ["stub"]},
            {"name": "raises", "command": ["stub"]},
        ],
        max_workers=2,
    )
    assert len(results) == 2
    assert results["good"].success is True
    assert results["raises"].success is False
    assert results["raises"].returncode == -1
    assert "RuntimeError" in results["raises"].stderr
    assert bridge.test_results["raises"] is results["raises"]
    metrics = bridge.generate_deployment_metrics()
    assert (metrics.tests_total, metrics.tests_failed) == (2, 1)
    assert metrics.deployment_ready is False
    assert [e["test_name"] for e in metrics.runtime_errors] == ["raises"]


def test_duplicate_parallel_names_reject_before_execution(bridge, monkeypatch):
    calls = []
    monkeypatch.setattr(bridge, "run_test", lambda *_args, **_kw: calls.append(1))
    with pytest.raises(ValueError, match="Duplicate test names"):
        bridge.run_tests_parallel(
            [{"name": "same", "command": []}, {"name": "same", "command": []}],
            max_workers=2,
        )
    assert calls == []
    assert bridge.test_results == {}


def test_required_artifact_is_not_hidden_by_zero_exit(bridge, monkeypatch, tmp_path):
    monkeypatch.setattr(
        bridge_module.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0, stdout="ok", stderr=""
        ),
    )
    failed = bridge.run_test(
        "artifact_negative", ["test"], expected_artifacts=["proof.json"], cwd=tmp_path
    )
    assert failed.returncode == 0
    assert failed.success is False
    assert failed.artifacts_match is False
    assert "missing expected artifacts: proof.json" in failed.stderr
    (tmp_path / "proof.json").write_text("{}", encoding="utf-8")
    passed = bridge.run_test(
        "artifact_positive", ["test"], expected_artifacts=["proof.json"], cwd=tmp_path
    )
    assert passed.success is True
    assert passed.artifacts_match is True
    assert passed.artifacts_found == ["proof.json"]


def test_timeout_is_recorded_as_failed_and_not_dropped(bridge, monkeypatch):
    def time_out(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd=["stub"], timeout=3)

    monkeypatch.setattr(bridge_module.subprocess, "run", time_out)
    result = bridge.run_test("timeout", ["stub"], timeout=3)
    assert result.success is False
    assert result.returncode == -1
    assert "timed out" in result.stderr
    assert bridge.test_results["timeout"] is result


def test_pytest_suite_command_keeps_markers_and_exit_proof(bridge, monkeypatch):
    captured = []

    def record(name, command, **_kwargs):
        captured.append((name, command))
        return successful_result(name)

    monkeypatch.setattr(bridge, "run_test", record)
    result = bridge.run_pytest_suite(test_path="DMAIC_V3/tests", markers="unit")
    assert result.success is True
    assert captured[0][0] == "pytest_suite"
    cmd = captured[0][1]
    assert cmd[:3] == [sys.executable, "-m", "pytest"]
    assert "DMAIC_V3/tests" in cmd
    assert cmd[cmd.index("-m") + 1] == "unit"
    assert "--maxfail=5" in cmd


def test_version_action_and_corrupt_prior_action_receipts(bridge):
    assert bridge.get_current_version() == "0.0.0"
    bridge.update_version("1.2.3")
    assert bridge.get_current_version() == "1.2.3"
    bridge.actions_file.write_text("{bad json", encoding="utf-8")
    bridge.log_action("recovered", "evidence kept", {"sha": "abc"})
    actions = json.loads(bridge.actions_file.read_text(encoding="utf-8"))
    assert len(actions) == 1
    assert actions[0]["type"] == "recovered"
    assert actions[0]["metadata"]["sha"] == "abc"
    bridge.log_action("next", "second record")
    assert len(json.loads(bridge.actions_file.read_text())) == 2


def test_setup_environment_copies_real_file_and_directory(bridge, tmp_path):
    source = tmp_path / "candidate.py"
    source.write_text("assert True", encoding="utf-8")
    file_env = bridge.setup_test_environment(source)
    source_dir = tmp_path / "tree"
    source_dir.mkdir()
    (source_dir / "test.txt").write_text("included", encoding="utf-8")
    dir_env = bridge.setup_test_environment(source_dir)
    try:
        assert (file_env / "sut").read_text(encoding="utf-8") == "assert True"
        assert (dir_env / "sut" / "test.txt").read_text(encoding="utf-8") == "included"
    finally:
        bridge_module.shutil.rmtree(file_env)
        bridge_module.shutil.rmtree(dir_env)


def test_real_report_distinguishes_success_failed_and_error_receipts(bridge, tmp_path):
    bridge.test_results["ok"] = successful_result("ok")
    bridge.test_results["bad"] = bridge_module.TestExecutionResult(
        test_name="bad",
        returncode=2,
        stdout="",
        stderr="Error: failure",
        success=False,
        duration_seconds=0.75,
    )
    metrics = bridge.generate_deployment_metrics()
    assert (metrics.tests_total, metrics.tests_passed, metrics.tests_failed) == (2, 1, 1)
    assert metrics.execution_time_seconds == pytest.approx(1.0)
    assert len(metrics.runtime_errors) == 1
    assert metrics.deployment_ready is False
    output = bridge.save_deployment_report(tmp_path / "nested" / "deployment.json")
    stored = json.loads(output.read_text(encoding="utf-8"))
    assert stored["deployment_metrics"]["tests_total"] == 2
    assert stored["deployment_metrics"]["deployment_ready"] is False
    assert stored["test_results"]["bad"]["success"] is False


def test_success_requires_real_test_and_positive_static_result(bridge):
    bridge.test_results["ok"] = successful_result()
    metrics = bridge.generate_deployment_metrics()
    assert metrics.tests_total == 1
    assert metrics.tests_failed == 0
    assert metrics.deployment_ready is True
