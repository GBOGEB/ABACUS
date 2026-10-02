import json

import pytest

from DMAIC_V3.core.agent_manager import AgentManager
from DMAIC_V3.core.canonical_index import CanonicalIndexSystem
from DMAIC_V3.core.integrity import sha256_json
from DMAIC_V3.core.mcp_execution_contract import MCPRequest, execute_mcp
from DMAIC_V3.core.metrics import MetricsExporter
from DMAIC_V3.core.models import Metric, MetricType, PhaseMetrics, PhaseStatus
from DMAIC_V3.core import state as state_module
from DMAIC_V3.core.state import PhaseStatus as StatePhaseStatus
from DMAIC_V3.core.state import StateManager


@pytest.mark.unit
def test_agent_manager_loads_existing_agent_config(tmp_path):
    config_dir = tmp_path / "config" / "agents"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "analysis_cryo_dm.json"
    config_path.write_text(
        json.dumps({"mode": "bounded", "enabled": True}),
        encoding="utf-8",
    )

    manager = AgentManager(tmp_path, tmp_path / "out")

    assert manager._load_agent_config("analysis", "cryo_dm") == {
        "mode": "bounded",
        "enabled": True,
    }


@pytest.mark.unit
def test_metrics_exporter_uses_default_phase_and_csv_names(tmp_path):
    phase = PhaseMetrics(
        "control",
        4,
        duration_seconds=1.25,
        status=PhaseStatus.COMPLETED,
    )
    phase.add_metric(Metric("quality", 99.0, "%", MetricType.GAUGE))
    exporter = MetricsExporter(tmp_path)

    phase_json = exporter.export_phase_metrics_json(phase)
    csv_path = exporter.export_metrics_csv(phase)

    assert phase_json.name.startswith("control_iter4_")
    assert phase_json.suffix == ".json"
    assert csv_path.name == "control_iter4.csv"
    assert phase_json.exists()
    assert csv_path.exists()


@pytest.mark.unit
def test_mcp_detects_parent_mutation_outside_worker_isolation():
    payload = {"x": 1}
    request = MCPRequest(
        "T-parent",
        "TRIGGERED",
        payload,
        sha256_json(payload),
    )

    def mutate_outer_parent(_isolated_payload):
        payload["x"] = 2
        return {"finding": "complete"}

    with pytest.raises(RuntimeError, match="changed outside worker isolation"):
        execute_mcp(request, mutate_outer_parent)


@pytest.mark.unit
def test_canonical_name_collapses_consecutive_separators(tmp_path):
    system = CanonicalIndexSystem(tmp_path)

    assert system.generate_canonical_name("My -- Artifact") == "my_artifact"


@pytest.mark.unit
def test_state_missing_phase_and_completed_resume_paths(tmp_path):
    manager = StateManager(tmp_path / "state")
    manager.start_iteration(1)

    assert manager.is_phase_completed("missing") is False

    manager.start_phase("done", 1)
    manager.end_phase("done", StatePhaseStatus.COMPLETED)

    assert manager.get_resume_point() is None


@pytest.mark.unit
def test_state_save_failure_is_reported_without_masking(tmp_path, monkeypatch, capsys):
    manager = StateManager(tmp_path / "state")

    def fail_dump(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(state_module.json, "dump", fail_dump)

    manager._save_state()

    assert "Could not save state: disk full" in capsys.readouterr().out
