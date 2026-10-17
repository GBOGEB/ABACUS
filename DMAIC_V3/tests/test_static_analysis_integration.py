"""Integration tests for fail-closed deployment report scanner receipts."""

import json
import threading

import pytest

from DMAIC_V3.core.test_system_bridge import (
    MCPControlPoint,
    TestExecutionResult,
    TestSystemBridge,
)


@pytest.fixture
def bridge(tmp_path):
    instance = object.__new__(TestSystemBridge)
    instance.workspace_root = tmp_path
    instance.output_root = tmp_path / "out"
    instance.mcp = MCPControlPoint(tmp_path / ".mcp")
    instance.version_file = tmp_path / "VERSION"
    instance.actions_file = tmp_path / "actions.json"
    instance.test_results_lock = threading.Lock()
    instance.deployment_metrics = None
    instance.test_results = {
        "smoke": TestExecutionResult(
            test_name="smoke",
            returncode=0,
            stdout="one passed",
            stderr="",
            success=True,
            duration_seconds=0.1,
        )
    }
    return instance


def test_nonzero_scanner_retains_first_red_in_saved_report(bridge, tmp_path):
    bridge.run_static_analysis = lambda: {
        "flake8": {
            "returncode": 1,
            "output": "DMAIC_V3/core/test_system_bridge.py:73:5: E301 missing line",
        }
    }
    metrics = bridge.generate_deployment_metrics()
    assert metrics.tests_total == 1
    assert metrics.tests_failed == 0
    assert metrics.static_analysis_passed is False
    assert metrics.deployment_ready is False
    path = bridge.save_deployment_report(tmp_path / "out" / "receipt.json")
    receipt = json.loads(path.read_text(encoding="utf-8"))
    evidence = receipt["deployment_metrics"]["static_analysis_evidence"]
    assert evidence["status"] == "FAIL"
    assert evidence["findings"][0]["source_path"] == (
        "DMAIC_V3/core/test_system_bridge.py"
    )
    assert evidence["findings"][0]["line"] == 73
    assert evidence["findings"][0]["column"] == 5
    assert evidence["findings"][0]["rule"] == "E301"


def test_scanner_failure_unknown_remains_not_deployment_ready(bridge):
    bridge.run_static_analysis = lambda: {
        "flake8": {"error": "scanner could not execute"}
    }
    metrics = bridge.generate_deployment_metrics()
    assert metrics.static_analysis_passed is False
    assert metrics.deployment_ready is False
    evidence = bridge.static_analysis_evidence
    assert evidence["status"] == "UNKNOWN"
    assert evidence["finding_count"] is None


def test_executed_clean_flake8_keeps_independent_deployment_semantics(bridge):
    bridge.run_static_analysis = lambda: {
        "flake8": {"returncode": 0, "output": ""},
        "mypy": None,
        "pylint": None,
    }
    metrics = bridge.generate_deployment_metrics()
    assert metrics.tests_total == 1
    assert metrics.static_analysis_passed is True
    assert bridge.static_analysis_evidence["status"] == "PASS"
    assert metrics.deployment_ready is True
    assert "merge_admission" not in bridge.static_analysis_evidence


def test_zero_tests_never_green_even_with_clean_static(bridge):
    bridge.test_results.clear()
    bridge.run_static_analysis = lambda: {
        "flake8": {"returncode": 0, "output": ""}
    }
    metrics = bridge.generate_deployment_metrics()
    assert metrics.tests_total == 0
    assert metrics.deployment_ready is False
    assert bridge.static_analysis_evidence["status"] == "PASS"
