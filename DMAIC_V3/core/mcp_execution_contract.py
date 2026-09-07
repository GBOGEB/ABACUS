"""Governed MCP execution envelope for DMAIC 3.4.

This contract is intentionally independent of versioned legacy MCP filenames. MCP
workers may return analytical findings but cannot establish or mutate engineering
truth.
"""
from __future__ import annotations

import copy
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import asdict, dataclass
from typing import Any, Callable, Literal

from .integrity import sha256_json

MCPMode = Literal["BACKGROUND", "AD_HOC", "TRIGGERED", "PIPELINE_SPECIFIC", "BURST"]


@dataclass(frozen=True)
class MCPRequest:
    task_id: str
    mode: MCPMode
    payload: dict[str, Any]
    parent_sha256: str
    timeout_seconds: float = 10.0


@dataclass(frozen=True)
class MCPReceipt:
    task_id: str
    mode: MCPMode
    parent_sha256: str
    returned_parent_sha256: str
    finding_sha256: str | None
    status: str
    authority: str = "ANALYTICAL_FINDING_ONLY"
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _run_worker(worker: Callable[[dict[str, Any]], Any], payload: dict[str, Any]) -> Any:
    return worker(payload)


def execute_mcp(request: MCPRequest, worker: Callable[[dict[str, Any]], Any]) -> tuple[Any, MCPReceipt]:
    actual_parent = sha256_json(request.payload)
    if actual_parent != request.parent_sha256:
        raise ValueError("MCP parent payload SHA256 mismatch")

    isolated_payload = copy.deepcopy(request.payload)
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_run_worker, worker, isolated_payload)
        try:
            finding = future.result(timeout=request.timeout_seconds)
        except TimeoutError as exc:
            future.cancel()
            receipt = MCPReceipt(
                task_id=request.task_id,
                mode=request.mode,
                parent_sha256=request.parent_sha256,
                returned_parent_sha256=sha256_json(request.payload),
                finding_sha256=None,
                status="timeout",
                error=f"worker timeout after {request.timeout_seconds} seconds",
            )
            raise TimeoutError(receipt.error) from exc

    returned_parent = sha256_json(request.payload)
    if returned_parent != request.parent_sha256:
        raise RuntimeError("MCP parent payload changed outside worker isolation")

    isolated_parent = sha256_json(isolated_payload)
    if isolated_parent != request.parent_sha256:
        raise RuntimeError("MCP worker mutated isolated parent payload")

    receipt = MCPReceipt(
        task_id=request.task_id,
        mode=request.mode,
        parent_sha256=request.parent_sha256,
        returned_parent_sha256=returned_parent,
        finding_sha256=sha256_json(finding),
        status="success",
    )
    return finding, receipt
