import json
from pathlib import Path
import pytest
from DMAIC_V3.core.agent_manager import AgentConfig, AgentManager


def manager(tmp_path):
    mgr=AgentManager(tmp_path,tmp_path/"out")
    mgr.agents["analysis_cryo_dm"]=AgentConfig("cryo_dm","analysis","2.3.0",tmp_path/"agent.py",True,{})
    return mgr


def test_representative_execution_is_deterministic(tmp_path):
    mgr=manager(tmp_path)
    runner=lambda payload:{"value":payload["value"]*2}
    a=mgr.execute_callable("analysis_cryo_dm",runner,{"value":3})
    b=mgr.execute_callable("analysis_cryo_dm",runner,{"value":3})
    assert a==b
    assert a["status"]=="success"
    assert a["authority"]=="ANALYTICAL_FINDING_ONLY"
    assert len(a["sha256"])==64


def test_adversarial_runner_failure_is_receipted_not_raised(tmp_path):
    mgr=manager(tmp_path)
    def fail(_): raise ValueError("boom")
    receipt=mgr.execute_callable("analysis_cryo_dm",fail,{})
    assert receipt["status"]=="failed"
    assert receipt["result"] is None
    assert receipt["error"]=="ValueError: boom"
    assert len(receipt["sha256"])==64


def test_unknown_and_disabled_agents_fail_closed(tmp_path):
    mgr=manager(tmp_path)
    with pytest.raises(KeyError): mgr.execute_callable("unknown",lambda p:p,{})
    mgr.agents["analysis_cryo_dm"].enabled=False
    with pytest.raises(RuntimeError): mgr.execute_callable("analysis_cryo_dm",lambda p:p,{})


def test_discovery_does_not_create_missing_source_files(tmp_path):
    mgr=AgentManager(tmp_path,tmp_path/"out")
    mgr.initialize_all_agents()
    assert not (tmp_path/"local_mcp"/"agents").exists()
    registry=json.loads((tmp_path/"out"/"agent_registry.json").read_text())
    assert registry["authority"]=="ANALYTICAL_RUNTIME_ONLY"
    assert len(registry["agents"])==12


def test_compatibility_phase_view_does_not_claim_execution(tmp_path):
    mgr=manager(tmp_path)
    view=mgr.orchestrate_phase("phase1_define",{})
    assert view["agents_executed"]==0
    assert view["agents_ready"]==1
    assert view["authority"]=="ANALYTICAL_RUNTIME_ONLY"
