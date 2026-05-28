"""Tuple metadata validation helpers for CI and artifact pipelines."""

from typing import Any, Dict, List, Sequence

STATUS_VALUES = {"planned", "in_progress", "validated", "blocked", "released"}
REQUIRED_TUPLE_FIELDS = (
    "tuple_id",
    "source",
    "validation_log",
    "downstream_consumer",
    "status",
)


def _require_status(value: Any, path: str) -> List[str]:
    if value not in STATUS_VALUES:
        return [f"{path} has invalid status '{value}'"]
    return []


def validate_tuple_metadata(entries: Any) -> List[str]:
    """Validate tuple metadata entries with required bridge keys."""
    errors: List[str] = []
    if not isinstance(entries, list):
        return ["tuple_metadata must be a list"]

    for idx, entry in enumerate(entries):
        path = f"tuple_metadata[{idx}]"
        if not isinstance(entry, dict):
            errors.append(f"{path} must be an object")
            continue
        for field in REQUIRED_TUPLE_FIELDS:
            if field not in entry or not entry[field]:
                errors.append(f"{path} missing required field: {field}")
        errors.extend(_require_status(entry.get("status"), f"{path}.status"))
    return errors


def validate_tracker_payload(payload: Dict[str, Any]) -> List[str]:
    """Validate tracker payload used by HTML and CI artifacts."""
    errors: List[str] = []
    if not isinstance(payload, dict):
        return ["payload must be an object"]

    status_schema = payload.get("status_schema")
    if status_schema != sorted(STATUS_VALUES):
        errors.append("status_schema must equal ['blocked', 'in_progress', 'planned', 'released', 'validated']")

    branches = payload.get("branches")
    if not isinstance(branches, list):
        errors.append("branches must be a list")
    else:
        for idx, branch in enumerate(branches):
            path = f"branches[{idx}]"
            if not isinstance(branch, dict):
                errors.append(f"{path} must be an object")
                continue
            if not branch.get("name"):
                errors.append(f"{path} missing required field: name")
            errors.extend(_require_status(branch.get("status"), f"{path}.status"))

    errors.extend(validate_tuple_metadata(payload.get("tuple_metadata")))
    return errors


def default_status_schema() -> Sequence[str]:
    return sorted(STATUS_VALUES)
