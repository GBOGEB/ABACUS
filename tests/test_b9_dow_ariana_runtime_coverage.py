"""Behavioral and artifact coverage for the DOW/Ariana integration boundary."""

import json
from types import SimpleNamespace

import pytest

from DMAIC_V3.core.dow_ariana_integration import DOWArianaIntegration


class _Bridge:
    def __init__(self, success=True):
        self.success = success
        self.calls = []

    def run_tests_parallel(self, tests, max_workers=2):
        self.calls.append((tests, max_workers))
        return {
            test["name"]: SimpleNamespace(
                success=self.success, duration_seconds=0.01
            )
            for test in tests
        }


@pytest.fixture
def integration(tmp_path):
    config = SimpleNamespace(
        version="test-version",
        paths=SimpleNamespace(
            workspace_root=tmp_path, output_root=tmp_path / "output"
        ),
    )
    state = SimpleNamespace(state_dir=tmp_path / "state")
    bridge = _Bridge()
    return DOWArianaIntegration(config, state, bridge)


def test_initialization_writes_real_configuration_and_agent_files(integration):
    for path in (
        integration.dow_config_file,
        integration.ariana_health_file,
        integration.ariana_sync_file,
    ):
        assert path.is_file()
    config = json.loads(integration.dow_config_file.read_text())
    health = json.loads(integration.ariana_health_file.read_text())
    sync = json.loads(integration.ariana_sync_file.read_text())
    assert config["version"] == "test-version"
    assert config["test_bridge_enabled"] is True
    assert health["status"] == "active"
    assert sync["sync_enabled"] is True


def test_pipeline_success_writes_report_and_auditable_result(integration):
    result = integration.execute_dow_pipeline_with_ariana(phase=1, iteration=2)
    assert result["status"] == "completed"
    assert result["success"] is True
    assert result["test_results"]["passed"] == 2
    assert result["test_results"]["failed"] == 0
    assert result["duration_seconds"] >= 0
    artifact = integration.output_root / "iteration_2/phase1_dow/phase1_dow_report.json"
    assert artifact.exists()
    assert json.loads(artifact.read_text())["iteration"] == 2
    saved = integration.dow_dir / "phase1_iteration2_result.json"
    assert json.loads(saved.read_text())["success"] is True
    assert len(integration.metrics.agent_orchestration_events) == 2
    assert integration.test_bridge.calls[0][1] == 2


def test_pipeline_records_failed_test_without_forging_success(integration):
    integration.test_bridge.success = False
    result = integration.execute_dow_pipeline_with_ariana(2, 1)
    assert result["status"] == "completed"
    assert result["success"] is False
    assert result["test_results"]["failed"] == 2
    saved = integration.dow_dir / "phase2_iteration1_result.json"
    assert json.loads(saved.read_text())["success"] is False


def test_pipeline_exception_is_persisted_as_failure(integration, monkeypatch):
    def fail_phase(_phase, _iteration):
        raise RuntimeError("isolated pipeline failure")

    monkeypatch.setattr(integration, "_execute_dow_phase", fail_phase)
    result = integration.execute_dow_pipeline_with_ariana(3, 4)
    assert result["status"] == "failed"
    assert result["success"] is False
    assert result["error"] == "isolated pipeline failure"
    saved = integration.dow_dir / "phase3_iteration4_result.json"
    assert json.loads(saved.read_text())["status"] == "failed"


def test_trace_collection_missing_valid_and_invalid(integration):
    assert integration._collect_ariana_traces(1) == []
    trace_dir = integration.workspace_root / ".ariana"
    trace_dir.mkdir()
    trace_file = trace_dir / "trace_log.json"
    trace_file.write_text('{"event": "start"}\n{"event": "end"}\n')
    assert [x["event"] for x in integration._collect_ariana_traces(1)] == [
        "start",
        "end",
    ]
    trace_file.write_text('{"valid": true}\nnot-json\n')
    assert integration._collect_ariana_traces(1) == [{"valid": True}]


def test_registry_orchestration_and_metrics_output(integration):
    registry = {
        "agents": {
            "consumer": {"name": "document_consumer", "version": "1.2"},
            "monitor": {"name": "health_checker", "version": "1.3"},
        }
    }
    integration.agents_registry_file.write_text(json.dumps(registry))
    report = integration.show_agent_orchestration_after_phase0()
    assert report["total_agents"] == 2
    assert len(report["agent_categories"]["ANALYSIS"]) == 1
    assert len(report["agent_categories"]["MONITORING"]) == 1
    assert len(report["orchestration_flow"]) == 5
    assert set(report["integration_points"]) == {
        "dow_pipeline",
        "ariana_agent",
        "test_bridge",
        "state_manager",
    }
    recorded = json.loads(
        (integration.dow_dir / "AGENT_ORCHESTRATION_REPORT.json").read_text()
    )
    assert recorded["total_agents"] == 2
    assert len(integration.metrics.agent_orchestration_events) == 2
    metrics = integration.generate_integration_metrics()
    assert metrics.dow_pipeline_status == "active"
    assert metrics.ariana_agent_status == "monitoring"
    integration.save_integration_report()
    saved = json.loads(
        (integration.dow_dir / "DOW_ARIANA_INTEGRATION_REPORT.json").read_text()
    )
    assert saved["metrics"]["dow_pipeline_status"] == "active"


def test_registry_output_fallback_list_and_transition_metadata(integration):
    integration.output_root.mkdir(parents=True)
    fallback = integration.output_root / "agent_registry.json"
    fallback.write_text(
        json.dumps({"agents": [{"name": "smoke_test", "version": "2"}]})
    )
    registry = integration._load_agents_registry()
    assert integration._get_agent_info(registry, "smoke_test")["version"] == "2"
    assert integration._get_agent_info(registry, "missing") is None
    event = integration.register_agent_orchestration_event(
        "ready", "smoke_test", "phase0", {"source": "test"}
    )
    assert event["metadata"]["source"] == "test"
    transition = integration.track_phase_transition(
        "phase0", "phase1", ["smoke_test"]
    )
    assert transition["agents_involved"] == ["smoke_test"]
    assert transition["metadata"] == {}
    assert len(integration.metrics.phase_transitions) == 1
