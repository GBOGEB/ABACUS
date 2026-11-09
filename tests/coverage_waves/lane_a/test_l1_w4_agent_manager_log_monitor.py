"""Lane A wave 4: DMAIC_V3.core.agent_manager and DMAIC_V3.monitoring.log_monitor."""

import json
import logging
from pathlib import Path

import pytest

from DMAIC_V3.core import agent_manager as am
from DMAIC_V3.monitoring import log_monitor as lm


@pytest.fixture
def manager(tmp_path):
    agents = tmp_path / "ws" / "local_mcp" / "agents"
    agents.mkdir(parents=True)
    (agents / "analysis_cryo_dm_v2.3_OPTIMIZED.py").write_bytes(b"")
    (agents / "framework_v2.3_OPTIMIZED.py").write_bytes(b"")
    (agents / "monitoring_health_checker_OPTIMIZED.py").write_bytes(b"")
    (agents / "iteration_tracker_OPTIMIZED.py").write_bytes(b"")
    cfg = tmp_path / "ws" / "config" / "agents"
    cfg.mkdir(parents=True)
    (cfg / "analysis_cryo_dm.json").write_bytes(json.dumps({"depth": 2}).encode())
    return am.AgentManager(tmp_path / "ws", tmp_path / "out")


def test_agent_config_defaults():
    cfg = am.AgentConfig("n", "c", "1", Path("p"))
    assert cfg.config == {} and cfg.enabled is True
    assert am.AgentConfig("n", "c", "1", Path("p"), config={"a": 1}).config == {"a": 1}


def test_initialize_all_agents_discovers_patterns(manager, tmp_path):
    status = manager.initialize_all_agents()
    assert status["analysis"]["cryo_dm"]["available"] is True
    assert status["analysis"]["cryo_dm"]["version"] == "2.3.0"
    assert status["documentation"]["framework"]["available"] is True
    assert status["monitoring"]["health_checker"]["available"] is True
    assert status["recursive"]["iteration_tracker"]["available"] is True
    missing = status["knowledge"]["context_manager"]
    assert missing == {
        "available": False,
        "version": "missing",
        "path": str(
            tmp_path
            / "ws"
            / "local_mcp"
            / "agents"
            / "knowledge_context_manager_v2.3_OPTIMIZED.py"
        ),
    }
    assert manager.agents["analysis_cryo_dm"].config == {"depth": 2}
    assert manager.agents["analysis_smoke_test"].config == {}
    registry = json.loads((tmp_path / "out" / "agent_registry.json").read_text("utf-8"))
    assert registry["authority"] == "ANALYTICAL_RUNTIME_ONLY"
    assert registry["version"] == am.__version__
    assert len(registry["agents"]) == 12
    assert list(registry["agents"]) == sorted(registry["agents"])


def test_phase_mapping_and_orchestration(manager):
    assert manager.get_agents_for_phase("phase1_define") == []
    manager.initialize_all_agents()
    names = [a.name for a in manager.get_agents_for_phase("phase1_define")]
    assert names == ["cryo_dm", "document_consumer"]
    assert manager.get_agents_for_phase("unknown") == []

    view = manager.orchestrate_phase("phase1_define", {})
    assert view["agents_executed"] == 0
    assert view["agents_ready"] == 1
    assert view["results"]["cryo_dm"]["status"] == "ready"
    assert view["results"]["document_consumer"] == {
        "status": "skipped",
        "version": "missing",
        "reason": "disabled or missing",
    }


def test_execute_callable_success_failure_and_guards(manager):
    manager.initialize_all_agents()
    ok = manager.execute_callable("analysis_cryo_dm", lambda p: p["n"] * 2, {"n": 4})
    assert ok["status"] == "success" and ok["result"] == 8 and ok["error"] is None
    body = {k: v for k, v in ok.items() if k != "sha256"}
    assert ok["sha256"] == am.AgentManager._receipt_digest(body)

    def boom(payload):
        raise ValueError("bad payload")

    failed = manager.execute_callable("analysis_cryo_dm", boom, {})
    assert failed["status"] == "failed"
    assert failed["error"] == "ValueError: bad payload"
    assert failed["result"] is None

    with pytest.raises(KeyError, match="unknown agent"):
        manager.execute_callable("nope", boom, {})
    with pytest.raises(RuntimeError, match="disabled or missing"):
        manager.execute_callable("knowledge_context_manager", boom, {})


def test_receipt_digest_handles_non_json_values():
    digest = am.AgentManager._receipt_digest({"path": Path("x"), "é": 1})
    assert len(digest) == 64


def _write(path, text):
    path.write_bytes(text.encode())
    return path


def test_log_monitor_defaults():
    monitor = lm.LogMonitor()
    assert monitor.log_dir == Path("logs")
    assert monitor.anomaly_thresholds["error_rate"] == 0.05
    assert monitor.patterns["phase_start"].search("Starting Phase 3").group(1) == "3"
    assert monitor.patterns["quality_gate"].search("Quality Gate X passed")


def test_scan_logs_from_directory(tmp_path):
    _write(
        tmp_path / "a.log",
        "INFO ok\nERROR boom\nWARNING careful\nTraceback deprecated call\n",
    )
    _write(tmp_path / "ignored.txt", "ERROR not a log\n")
    monitor = lm.LogMonitor(tmp_path)
    results = monitor.scan_logs()
    assert [e["line"] for e in results["errors"]] == [2, 4]
    assert [w["line"] for w in results["warnings"]] == [3, 4]
    assert results["summary"] == {
        "total_errors": 2,
        "total_warnings": 2,
        "health_score": 86,
    }
    assert results["anomalies"] == []
    report = monitor.generate_report(results)
    assert "Health Score: 86/100" in report
    assert report.startswith("=" * 80)


def test_scan_logs_anomalies_and_floor(tmp_path):
    lines = ["ERROR"] * 11 + ["WARN"] * 51
    log = _write(tmp_path / "x.log", "\n".join(lines) + "\n")
    results = lm.LogMonitor(tmp_path).scan_logs([log])
    types = [a["type"] for a in results["anomalies"]]
    assert types == ["high_error_rate", "high_warning_rate"]
    assert results["summary"]["health_score"] == 0


def test_scan_file_error_is_logged(tmp_path, caplog):
    monitor = lm.LogMonitor(tmp_path)
    with caplog.at_level(logging.ERROR):
        out = monitor._scan_file(tmp_path / "missing.log")
    assert out == {"errors": [], "warnings": []}
    assert "Error scanning" in caplog.text


@pytest.mark.parametrize("errors,warnings,score", [(0, 0, 100), (1, 1, 93), (30, 0, 0)])
def test_health_score(errors, warnings, score):
    assert lm.LogMonitor()._calculate_health_score(errors, warnings) == score
