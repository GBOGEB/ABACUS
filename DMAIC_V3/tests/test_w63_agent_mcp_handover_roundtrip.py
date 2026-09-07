import copy

import pytest

from DMAIC_V3.core.agent_mcp_handover_roundtrip import execute_agent_mcp_handover


def test_representative_roundtrip_preserves_parent():
    payload = {"child": "QPS", "operating_point": "OP1", "value": 42}
    before = copy.deepcopy(payload)
    receipt = execute_agent_mcp_handover("P3-REP", payload, lambda p: {"finding": p["value"] * 2})
    assert payload == before
    assert receipt["zero_delta"] is True
    assert receipt["parent_sha256"] == receipt["returned_parent_sha256"]
    assert receipt["finding"] == {"finding": 84}
    assert receipt["authority"] == "ANALYTICAL_FINDING_ONLY"
    assert receipt["child_disposition"] == "DEFER_TO_CHILD"


def test_repeat_roundtrip_is_deterministic_except_task_identity():
    one = execute_agent_mcp_handover("P3-DET", {"x": 1}, lambda p: {"finding": p["x"]})
    two = execute_agent_mcp_handover("P3-DET", {"x": 1}, lambda p: {"finding": p["x"]})
    assert one == two


def test_adversarial_worker_mutation_fails_closed():
    payload = {"x": 1}
    before = copy.deepcopy(payload)

    def mutate(parent):
        parent["x"] = 99
        return {"finding": "invalid"}

    with pytest.raises(RuntimeError, match="mutated"):
        execute_agent_mcp_handover("P3-ADV", payload, mutate)
    assert payload == before


def test_worker_failure_propagates_without_child_disposition():
    def fail(_):
        raise ValueError("representative worker failure")

    with pytest.raises(ValueError, match="worker failure"):
        execute_agent_mcp_handover("P3-FAIL", {"x": 1}, fail)
