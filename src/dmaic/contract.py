"""
Canonical DMAIC contract helpers.
Defines and validates a shared metadata contract across artifacts.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional


CONTRACT_VERSION = "1.0.0"
REQUIRED_TOP_LEVEL_FIELDS = [
    "metadata",
    "idempotency",
    "lineage",
    "recursive_hooks",
    "convergence_metrics",
    "knowledge_gain",
]


def _now_iso() -> str:
    return datetime.now().isoformat()


def ensure_contract(
    data: Dict[str, Any],
    *,
    iteration: int,
    phase: str,
    version: str = "3.3.0",
    generator: str = "unknown",
    input_hash: Optional[str] = None,
    output_hash: Optional[str] = None,
    version_history: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Ensure a dictionary contains the canonical contract sections.
    """
    payload = dict(data) if isinstance(data, dict) else {}
    iteration_lineage = list(range(0, int(iteration) + 1))
    history = version_history or [version]
    history = [str(v) for v in history if v]
    if version not in history:
        history.append(version)

    payload.setdefault("metadata", {})
    payload["metadata"].setdefault("version", version)
    payload["metadata"].setdefault("timestamp", _now_iso())
    payload["metadata"].setdefault("iteration", iteration)
    payload["metadata"].setdefault("phase", phase)
    payload["metadata"].setdefault("generator", generator)
    payload["metadata"].setdefault("dow_compliant", True)
    payload["metadata"].setdefault("contract_version", CONTRACT_VERSION)

    payload.setdefault("idempotency", {})
    payload["idempotency"].setdefault("enabled", True)
    payload["idempotency"].setdefault("input_hash", input_hash or "")
    payload["idempotency"].setdefault("output_hash", output_hash or "")
    payload["idempotency"].setdefault("cache_hit", False)
    payload["idempotency"].setdefault("cache_key", "")

    payload.setdefault("lineage", {})
    payload["lineage"].setdefault("artifact_path", "")
    payload["lineage"].setdefault("parent_artifacts", [])
    payload["lineage"].setdefault("iteration_lineage", iteration_lineage)
    payload["lineage"].setdefault("version_history", history)
    payload["lineage"].setdefault("updated_at", _now_iso())

    payload.setdefault("recursive_hooks", {})
    payload["recursive_hooks"].setdefault("consumed_from", [])
    payload["recursive_hooks"].setdefault("feeds_into", [])
    payload["recursive_hooks"].setdefault("iteration_lineage", iteration_lineage)
    payload["recursive_hooks"].setdefault("version_history", history)

    payload.setdefault("convergence_metrics", {})
    payload["convergence_metrics"].setdefault("quality_score", 0.0)
    payload["convergence_metrics"].setdefault("completeness", 0.0)
    payload["convergence_metrics"].setdefault("improvement_from_previous", 0.0)
    payload["convergence_metrics"].setdefault("convergence_status", "not_evaluated")
    payload["convergence_metrics"].setdefault("calculated_at", _now_iso())

    payload.setdefault("knowledge_gain", {})
    payload["knowledge_gain"].setdefault("patterns_discovered", [])
    payload["knowledge_gain"].setdefault("insights_generated", [])
    payload["knowledge_gain"].setdefault("learnings_captured", [])
    payload["knowledge_gain"].setdefault("improvements_suggested", [])
    payload["knowledge_gain"].setdefault("extracted_at", _now_iso())
    return payload


def validate_contract(data: Dict[str, Any]) -> List[str]:
    """
    Validate required canonical fields and basic type expectations.
    Returns a list of errors (empty means valid).
    """
    errors: List[str] = []
    if not isinstance(data, dict):
        return ["payload is not an object"]

    for field in REQUIRED_TOP_LEVEL_FIELDS:
        if field not in data:
            errors.append(f"missing top-level field: {field}")

    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        errors.append("metadata is not an object")
    else:
        for key in ["version", "timestamp", "iteration", "phase", "contract_version"]:
            if key not in metadata:
                errors.append(f"metadata missing: {key}")

    idempotency = data.get("idempotency")
    if not isinstance(idempotency, dict):
        errors.append("idempotency is not an object")
    else:
        if "enabled" not in idempotency:
            errors.append("idempotency missing: enabled")
        if "input_hash" not in idempotency:
            errors.append("idempotency missing: input_hash")
        if "output_hash" not in idempotency:
            errors.append("idempotency missing: output_hash")

    lineage = data.get("lineage")
    if not isinstance(lineage, dict):
        errors.append("lineage is not an object")
    else:
        for key in ["iteration_lineage", "version_history"]:
            if key not in lineage:
                errors.append(f"lineage missing: {key}")

    recursive_hooks = data.get("recursive_hooks")
    if not isinstance(recursive_hooks, dict):
        errors.append("recursive_hooks is not an object")
    else:
        for key in ["consumed_from", "feeds_into", "iteration_lineage"]:
            if key not in recursive_hooks:
                errors.append(f"recursive_hooks missing: {key}")

    return errors
