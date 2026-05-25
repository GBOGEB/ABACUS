"""Validation helpers for Phase-2 reconstruction manifest artifacts."""

from pathlib import Path
from typing import Any, Dict, List, Sequence

REQUIRED_COMPONENTS = (
    "semantic tuple ledger",
    "reconstruction manifest",
    "active invariant ledger",
    "semantic debt tracking",
    "branch DAG",
    "semantic delta log",
    "replay/reconstruction workflow",
    "PR evaluation matrix",
    "semantic runtime code stubs",
    "metrics-driven automation stub",
    "viewer runtime scaffold",
    "checksums",
    "recursive continuation rules",
    "MANTRA/DMAIC continuity",
)

REQUIRED_COMPONENT_FIELDS = ("name", "artifact", "file_refs", "workflow_refs", "test_refs")


def default_required_components() -> Sequence[str]:
    """Return required semantic component names for Phase-2 reconstruction."""
    return REQUIRED_COMPONENTS


def _validate_path_refs(refs: Any, key: str, repo_root: Path) -> List[str]:
    errors: List[str] = []
    if not isinstance(refs, list) or not refs:
        return [f"{key} must be a non-empty list"]
    for idx, ref in enumerate(refs):
        if not isinstance(ref, str) or not ref.strip():
            errors.append(f"{key}[{idx}] must be a non-empty string path")
            continue
        if not (repo_root / ref).exists():
            errors.append(f"{key}[{idx}] path does not exist: {ref}")
    return errors


def validate_reconstruction_manifest(payload: Dict[str, Any], repo_root: Path) -> List[str]:
    """Validate reconstruction manifest structure and mapped repository references."""
    errors: List[str] = []
    if not isinstance(payload, dict):
        return ["payload must be an object"]

    if not payload.get("manifest_version"):
        errors.append("manifest_version is required")

    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append("artifacts must be a non-empty list")
    else:
        for idx, artifact in enumerate(artifacts):
            path = f"artifacts[{idx}]"
            if not isinstance(artifact, dict):
                errors.append(f"{path} must be an object")
                continue
            if not artifact.get("name"):
                errors.append(f"{path} missing required field: name")
            artifact_path = artifact.get("path")
            if not artifact_path:
                errors.append(f"{path} missing required field: path")
            elif not (repo_root / str(artifact_path)).exists():
                errors.append(f"{path}.path does not exist: {artifact_path}")

    component_map = payload.get("component_map")
    if not isinstance(component_map, list) or not component_map:
        errors.append("component_map must be a non-empty list")
        return errors

    present_components = set()
    for idx, component in enumerate(component_map):
        path = f"component_map[{idx}]"
        if not isinstance(component, dict):
            errors.append(f"{path} must be an object")
            continue
        for field in REQUIRED_COMPONENT_FIELDS:
            if field not in component:
                errors.append(f"{path} missing required field: {field}")
        component_name = component.get("name")
        if isinstance(component_name, str):
            present_components.add(component_name)
        errors.extend(_validate_path_refs(component.get("file_refs"), f"{path}.file_refs", repo_root))
        errors.extend(_validate_path_refs(component.get("workflow_refs"), f"{path}.workflow_refs", repo_root))
        errors.extend(_validate_path_refs(component.get("test_refs"), f"{path}.test_refs", repo_root))

    for required in REQUIRED_COMPONENTS:
        if required not in present_components:
            errors.append(f"component_map missing required component: {required}")

    return errors
