import copy

import pytest

from DMAIC_V3.core.integrity import sha256_json
from DMAIC_V3.core.mcp_execution_contract import MCPRequest, execute_mcp


def test_mcp_preserves_parent_and_returns_finding_receipt():
    payload = {"child": "QPS", "value": 42}
    request = MCPRequest("T1", "TRIGGERED", payload, sha256_json(payload))
    before = copy.deepcopy(payload)
    finding, receipt = execute_mcp(request, lambda p: {"finding": p["value"] * 2})
    assert payload == before
    assert finding == {"finding": 84}
    assert receipt.parent_sha256 == receipt.returned_parent_sha256
    assert receipt.authority == "ANALYTICAL_FINDING_ONLY"


def test_bad_parent_hash_fails_closed():
    request = MCPRequest("T2", "AD_HOC", {"x": 1}, "bad")
    with pytest.raises(ValueError, match="SHA256"):
        execute_mcp(request, lambda p: {})


def test_worker_parent_mutation_is_rejected():
    payload = {"x": 1}
    request = MCPRequest("T3", "BURST", payload, sha256_json(payload))
    def mutating_worker(parent):
        parent["x"] = 2
        return {"finding": "bad"}
    with pytest.raises(RuntimeError, match="mutated"):
        execute_mcp(request, mutating_worker)


def test_same_finding_has_same_digest():
    payload1 = {"x": 1}
    payload2 = {"x": 1}
    _, first = execute_mcp(MCPRequest("T4", "BACKGROUND", payload1, sha256_json(payload1)), lambda p: {"a": 1})
    _, second = execute_mcp(MCPRequest("T4", "BACKGROUND", payload2, sha256_json(payload2)), lambda p: {"a": 1})
    assert first.finding_sha256 == second.finding_sha256
