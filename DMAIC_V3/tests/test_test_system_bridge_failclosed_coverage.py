"""C4 behavioral tests for fail-closed DMAIC test-system bridge admission."""

import json
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
    instance.deployment_metrics = None
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
        raise bridge_module.subprocess.TimeoutExpired(cmd=["stub"], timeout=3)

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
    marker_index = cmd.index("DMAIC_V3/tests") + 1
    assert cmd[marker_index:marker_index + 2] == ["-m", "unit"]
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


def test_scanner_success_and_error_returns_source_bound_result(bridge, monkeypatch):
    calls = []

    def successful_scanner(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout="static ok", stderr="")

    monkeypatch.setattr(bridge_module.subprocess, "run", successful_scanner)
    green = bridge_module.TestSystemBridge.run_static_analysis(bridge)
    assert green["flake8"] == {"returncode": 0, "output": "static ok"}
    assert calls[0][0][1:3] == ["-m", "flake8"]

    def missing_scanner(*_args, **_kwargs):
        raise FileNotFoundError("scanner binary unavailable")

    monkeypatch.setattr(bridge_module.subprocess, "run", missing_scanner)
    red = bridge_module.TestSystemBridge.run_static_analysis(bridge)
    assert "scanner binary unavailable" in red["flake8"]["error"]
    assert "returncode" not in red["flake8"]


def test_pytest_suite_with_no_optional_args_does_not_invent_filters(
    bridge, monkeypatch
):
    calls = []

    def record(name, command):
        calls.append((name, command))
        return successful_result(name)

    monkeypatch.setattr(bridge, "run_test", record)
    bridge.run_pytest_suite()
    name, command = calls[0]
    assert name == "pytest_suite"
    assert command[:3] == [sys.executable, "-m", "pytest"]
    assert "-m" not in command[3:]
    assert "--maxfail=5" in command


def test_failed_test_without_error_signature_is_not_runtime_traceback(bridge):
    bridge.test_results["no-traceback"] = bridge_module.TestExecutionResult(
        test_name="no-traceback",
        returncode=5,
        stdout="",
        stderr="test failed without exception stack",
        success=False,
        duration_seconds=0.1,
    )
    assert bridge.detect_runtime_errors() == []
    metrics = bridge.generate_deployment_metrics()
    assert metrics.tests_failed == 1
    assert metrics.deployment_ready is False


def test_nonlist_action_history_is_not_appended_as_a_list(bridge):
    bridge.actions_file.write_text('{"old": "wrong root type"}', encoding="utf-8")
    bridge.log_action("safe-start", "one canonical action")
    actions = json.loads(bridge.actions_file.read_text(encoding="utf-8"))
    assert [action["type"] for action in actions] == ["safe-start"]


def test_source_runner_without_declared_artifacts_does_not_forge_receipts(
    bridge, monkeypatch
):
    monkeypatch.setattr(
        bridge_module.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0, stdout="no output", stderr=""
        ),
    )
    measured = bridge.run_test("no_artifacts", ["stub"])
    assert measured.success is True
    assert measured.artifacts_expected == []
    assert measured.artifacts_found == []
    assert measured.artifacts_match is False


def test_missing_report_and_metrics_are_generated_at_default_path(bridge):
    bridge.test_results["good"] = successful_result("good")
    report = bridge.save_deployment_report()
    assert report == bridge.output_root / "deployment_report.json"
    assert bridge.deployment_metrics is not None
    stored = json.loads(report.read_text(encoding="utf-8"))
    assert stored["deployment_metrics"]["tests_total"] == 1
    assert stored["deployment_metrics"]["deployment_ready"] is True


@pytest.mark.parametrize("failing_phase", [None, "integration"])
def test_sequential_cycle_requires_every_independent_phase(
    bridge, monkeypatch, failing_phase
):
    seen = []

    def phase(test_path=None, markers=None):
        seen.append(markers)
        result = successful_result(markers)
        if markers == failing_phase:
            result.success = False
            result.returncode = 2
            result.stderr = "Error: seeded integration failure"
        bridge.test_results[markers] = result
        return result

    monkeypatch.setattr(bridge, "run_pytest_suite", phase)
    admitted = bridge.execute_full_test_cycle()
    assert seen == ["unit", "integration", "smoke"]
    assert admitted is (failing_phase is None)
    assert bridge.deployment_metrics.tests_total == 3
    assert bridge.deployment_metrics.tests_failed == (failing_phase is not None)
    report = json.loads(
        (bridge.output_root / "deployment_report.json").read_text(encoding="utf-8")
    )
    assert report["deployment_metrics"]["deployment_ready"] is admitted


@pytest.mark.parametrize("failing_phase", [None, "integration_tests"])
def test_parallel_cycle_preserves_all_three_worker_receipts(
    bridge, monkeypatch, failing_phase
):
    names = []

    def completed_batch(configs, max_workers):
        assert max_workers == 3
        for config in configs:
            name = config["name"]
            names.append(name)
            result = successful_result(name)
            if name == failing_phase:
                result.success = False
                result.returncode = 1
                result.stderr = "Error: simulated negative worker"
            bridge.test_results[name] = result
        return dict(bridge.test_results)

    monkeypatch.setattr(bridge, "run_tests_parallel", completed_batch)
    admitted = bridge.execute_full_test_cycle_parallel(max_workers=3)
    assert names == ["unit_tests", "integration_tests", "smoke_tests"]
    assert admitted is (failing_phase is None)
    assert bridge.deployment_metrics.tests_total == 3
    assert bridge.deployment_metrics.tests_failed == (failing_phase is not None)


def test_phase_context_records_positive_and_negative_exit(bridge):
    with bridge_module.IdempotentPhase("test", bridge) as phase:
        assert phase is not None
    with pytest.raises(ValueError, match="seeded"):
        with bridge_module.IdempotentPhase("test", bridge):
            raise ValueError("seeded")
    records = [
        json.loads(line)
        for line in bridge.mcp.log_file.read_text(encoding="utf-8").splitlines()
    ]
    assert [entry["status"] for entry in records[-4:]] == [
        "enter", "success", "enter", "failed"
    ]
