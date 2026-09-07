"""W63 P3 AgentManager -> MCP -> handover governed roundtrip."""
from __future__ import annotations

from typing import Any, Callable

from .integrity import sha256_json
from .mcp_execution_contract import MCPRequest, execute_mcp


def execute_agent_mcp_handover(
    task_id: str,
    payload: dict[str, Any],
    agent_runner: Callable[[dict[str, Any]], Any],
) -> dict[str, Any]:
    """Execute a bounded analytical worker and preserve the parent payload exactly."""
    parent_sha = sha256_json(payload)
    finding, mcp_receipt = execute_mcp(
        MCPRequest(task_id, "PIPELINE_SPECIFIC", payload, parent_sha),
        agent_runner,
    )
    returned_parent_sha = sha256_json(payload)
    if returned_parent_sha != parent_sha:
        raise RuntimeError("handover parent payload changed")
    return {
        "task_id": task_id,
        "parent_sha256": parent_sha,
        "returned_parent_sha256": returned_parent_sha,
        "finding": finding,
        "finding_sha256": mcp_receipt.finding_sha256,
        "mcp_receipt": mcp_receipt.to_dict(),
        "child_disposition": "DEFER_TO_CHILD",
        "authority": "ANALYTICAL_FINDING_ONLY",
        "zero_delta": True,
    }
