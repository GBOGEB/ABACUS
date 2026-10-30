"""Lane A wave 7: small DMAIC_V3 modules.

Legacy agent stubs and launcher, the AgentManager -> MCP handover roundtrip,
the one-shot orchestrator fix scripts, run_phase1 and the generators package.
"""

import runpy
import sys

import pytest

from DMAIC_V3 import generators, run_phase1
from DMAIC_V3.core import agent_mcp_handover_roundtrip as rt
from DMAIC_V3.core.integrity import sha256_json
from tests.coverage_waves.lane_a._load import REPO, load

AGENTS = "DMAIC_V3/local_mcp/agents/"
STUBS = {
    "analysis_cryo_dm_v2.3_OPTIMIZED.py": "CryoDmAgent",
    "analysis_document_consumer_v2.3_OPTIMIZED.py": "DocumentConsumerAgent",
    "analysis_smoke_test_v2.3_OPTIMIZED.py": "SmokeTestAgent",
    "documentation_framework_v2.3_OPTIMIZED.py": "FrameworkAgent",
    "documentation_style_extractor_v2.3_OPTIMIZED.py": "StyleExtractorAgent",
    "knowledge_context_manager_v2.3_OPTIMIZED.py": "ContextManagerAgent",
    "knowledge_dependency_graph_v2.3_OPTIMIZED.py": "DependencyGraphAgent",
    "monitoring_health_checker_v2.3_OPTIMIZED.py": "HealthCheckerAgent",
    "monitoring_performance_tracker_v2.3_OPTIMIZED.py": "PerformanceTrackerAgent",
    "recursive_iteration_tracker_v2.3_OPTIMIZED.py": "IterationTrackerAgent",
}


@pytest.mark.parametrize("filename,cls_name", sorted(STUBS.items()))
def test_legacy_agent_stub_contract(filename, cls_name):
    module = load(AGENTS + filename)
    agent_cls = getattr(module, cls_name)
    default = agent_cls()
    assert default.config == {}
    assert default.version == module.__version__ == "0.0.0-stub"
    configured = agent_cls({"k": 1})
    assert configured.config == {"k": 1}
    with pytest.raises(NotImplementedError, match=cls_name + " is a stub"):
        configured.execute(1, x=2)


def test_legacy_launcher_targets_canonical_agent(monkeypatch):
    module = load(AGENTS + "analysis_artifact_analyzer_v2.3_OPTIMIZED.py")
    canonical = REPO / "local_mcp" / "agents"
    assert module.CANONICAL_AGENT == canonical / module.CANONICAL_AGENT.name
    assert module.CANONICAL_AGENT.is_file()
    calls = []
    monkeypatch.setattr(
        "runpy.run_path", lambda path, run_name: calls.append((path, run_name))
    )
    module.main()
    assert calls == [(str(module.CANONICAL_AGENT), "__main__")]


def test_agent_mcp_handover_roundtrip():
    payload = {"files": ["a", "b"], "n": 2}
    receipt = rt.execute_agent_mcp_handover("t9", payload, lambda p: {"count": p["n"]})
    assert receipt["finding"] == {"count": 2}
    assert receipt["parent_sha256"] == sha256_json(payload)
    assert receipt["returned_parent_sha256"] == receipt["parent_sha256"]
    assert receipt["finding_sha256"] == sha256_json({"count": 2})
    assert receipt["mcp_receipt"]["mode"] == "PIPELINE_SPECIFIC"
    assert receipt["zero_delta"] is True
    assert receipt["child_disposition"] == "DEFER_TO_CHILD"


def test_agent_mcp_handover_rejects_isolated_mutation():
    def mutate(p):
        p["n"] = 3

    with pytest.raises(RuntimeError, match="mutated isolated parent"):
        rt.execute_agent_mcp_handover("t9", {"n": 2}, mutate)


CLEAN = """from typing import Any
import json
'''Pipeline.
- Everything tracked even if incomplete
'''
from DMAIC_V3.core.planning_matrix_tracker import PlanningMatrixTracker
class P:
    def __init__(self):
        if self.enable_idempotency_flag:
            enable_idempotency(enabled=True)

    def run(self):
        start_time = datetime.now()
        phases_executed = []
        try:
            pass
        except Exception as e:
            print(f"\\n[ERROR] Pipeline failed: {e}")
            import traceback
            traceback.print_exc()
            return False
"""


def test_fix_orchestrator_steps(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "full_pipeline_orchestrator_clean.py").write_bytes(CLEAN.encode())
    runpy.run_path(str(REPO / "DMAIC_V3" / "fix_orchestrator_step1.py"))
    step1 = (tmp_path / "full_pipeline_orchestrator.py").read_text(encoding="utf-8")
    lines = step1.splitlines()
    assert lines[0] == "import json" and lines[1] == "from typing import Any"
    assert (
        lines.index(
            "from DMAIC_V3.convergence.background_change_detector import "
            "BackgroundChangeDetector"
        )
        == lines.index(
            "from DMAIC_V3.core.planning_matrix_tracker import PlanningMatrixTracker"
        )
        + 1
    )
    assert "- Background change detection (non-blocking)" in lines
    assert "Step 1: Fixed header" in capsys.readouterr().out

    runpy.run_path(str(REPO / "DMAIC_V3" / "fix_orchestrator_step2.py"))
    step2 = (tmp_path / "full_pipeline_orchestrator.py").read_text(encoding="utf-8")
    assert "self.bg_change_detector = BackgroundChangeDetector(" in step2
    assert "self.bg_change_detector.start()" in step2
    assert "finally:" in step2 and "self.bg_change_detector.stop()" in step2
    assert "All 5 integration points added" in capsys.readouterr().out


def test_fix_orchestrator_step1_without_matches(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "full_pipeline_orchestrator_clean.py").write_bytes(b"x = 1\ny = 2\n")
    runpy.run_path(str(REPO / "DMAIC_V3" / "fix_orchestrator_step1.py"))
    out = (tmp_path / "full_pipeline_orchestrator.py").read_bytes()
    assert out.replace(b"\r\n", b"\n") == b"x = 1\ny = 2\n"


class _FakePhase1:
    result = {"success": True, "files_scanned": 3}
    seen = []

    def __init__(self, config, state_manager):
        self.state_manager = state_manager

    def run(self, iteration):
        _FakePhase1.seen.append(iteration)
        return dict(_FakePhase1.result)


@pytest.fixture
def phase1(monkeypatch):
    _FakePhase1.seen = []
    monkeypatch.setattr(run_phase1, "DMAICConfig", lambda: "cfg")
    monkeypatch.setattr(run_phase1, "StateManager", lambda cfg: ("state", cfg))
    monkeypatch.setattr(run_phase1, "Phase1Define", _FakePhase1)
    return _FakePhase1


def test_run_phase1_success(phase1, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["run_phase1.py", "--iteration", "4"])
    run_phase1.main()
    assert phase1.seen == [4]
    out = capsys.readouterr().out
    assert "[OK] Phase 1 Complete!" in out
    assert "Files scanned: 3" in out and "Output: N/A" in out


def test_run_phase1_failure_exits(phase1, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["run_phase1.py"])
    monkeypatch.setattr(phase1, "result", {"success": False})
    with pytest.raises(SystemExit) as exc:
        run_phase1.main()
    assert exc.value.code == 1
    assert phase1.seen == [1]
    assert "Phase 1 Failed: Unknown error" in capsys.readouterr().out


def test_generators_version_and_victory_conditions():
    info = generators.get_version_info()
    assert info["version"] == generators.__version__ == "3.1.0"
    info["version"] = "changed"
    assert generators.VERSION_INFO["version"] == "3.1.0"
    conditions = generators.check_victory_conditions()
    assert set(conditions) == set(generators.VERSION_INFO["victory_conditions"])
    assert not any(conditions.values())
