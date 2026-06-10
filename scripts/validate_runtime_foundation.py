#!/usr/bin/env python3
"""Validate W007 runtime foundation evidence."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "docs" / "runtime-artifact-manifest.json"
TRACE_MATRIX_PATH = REPO_ROOT / "docs" / "api" / "rtm_trace_matrix.json"
RUNTIME_PORTAL_PATH = REPO_ROOT / "docs" / "runtime.html"

REQUIRED_CAPABILITIES = {
    "github_pages_portal",
    "ssot_dashboard",
    "rtm_validator",
    "artifact_manifest_validation",
    "release_automation",
    "visualization_layer",
}


def _relative(path: Path, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _load_json(path: Path, repo_root: Path, errors: List[str]) -> Dict[str, Any]:
    if not path.exists():
        errors.append(f"missing JSON artifact: {_relative(path, repo_root)}")
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON in {_relative(path, repo_root)}: {exc}")
        return {}
    if not isinstance(data, dict):
        errors.append(f"JSON artifact must be an object: {_relative(path, repo_root)}")
        return {}
    return data


def _validate_manifest(manifest: Mapping[str, Any], repo_root: Path, errors: List[str]) -> None:
    if manifest.get("wave") != "W007":
        errors.append("runtime manifest wave must be W007")

    entries = manifest.get("artifacts")
    if not isinstance(entries, list) or not entries:
        errors.append("runtime manifest must define non-empty artifacts list")
        return

    capabilities = set()
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            errors.append(f"runtime manifest artifact #{index} must be an object")
            continue

        capability = entry.get("capability")
        if isinstance(capability, str):
            capabilities.add(capability)
        else:
            errors.append(f"runtime manifest artifact #{index} missing capability")

        path_value = entry.get("path")
        if not isinstance(path_value, str) or not path_value:
            errors.append(f"runtime manifest artifact #{index} missing path")
            continue

        artifact_path = repo_root / path_value
        if not artifact_path.exists():
            errors.append(f"manifest artifact path does not exist: {path_value}")

        if entry.get("status") != "active":
            errors.append(f"manifest artifact must be active: {path_value}")

    missing_capabilities = sorted(REQUIRED_CAPABILITIES - capabilities)
    for capability in missing_capabilities:
        errors.append(f"runtime manifest missing capability: {capability}")


def _validate_trace_matrix(trace_matrix: Mapping[str, Any], repo_root: Path, errors: List[str]) -> None:
    rows = trace_matrix.get("rows")
    if not isinstance(rows, list) or not rows:
        errors.append("RTM trace matrix must contain traceability rows")
        return

    required_fields = {"requirement_id", "evidence_id", "evidence_artifact", "available"}
    missing_evidence: List[str] = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            errors.append(f"RTM trace row #{index} must be an object")
            continue

        missing_fields = sorted(required_fields - set(row))
        if missing_fields:
            errors.append(f"RTM trace row #{index} missing fields: {', '.join(missing_fields)}")

        evidence_id = str(row.get("evidence_id", f"row-{index}"))
        evidence_artifact = row.get("evidence_artifact")
        available = row.get("available") is True

        if not available:
            missing_evidence.append(evidence_id)
            continue

        if not isinstance(evidence_artifact, str) or not evidence_artifact:
            errors.append(f"RTM trace row #{index} evidence_artifact must be a non-empty string")
            missing_evidence.append(evidence_id)
            continue

        artifact_path = repo_root / evidence_artifact
        if not artifact_path.exists():
            missing_evidence.append(evidence_id)

    if missing_evidence:
        errors.append(f"RTM trace matrix has unavailable or missing evidence: {', '.join(missing_evidence)}")

def _validate_runtime_portal(portal_path: Path, errors: List[str]) -> None:
    if not portal_path.exists():
        errors.append("missing runtime portal: docs/runtime.html")
        return
    portal_html = portal_path.read_text(encoding="utf-8")
    for expected in (
        "W007 Runtime Foundation",
        "SSOT Dashboard",
        "Traceability",
        "runtime-artifact-manifest.json",
        "Visualization Layer",
    ):
        if expected not in portal_html:
            errors.append(f"runtime portal missing visible section: {expected}")


def validate_runtime_foundation(repo_root: Path = REPO_ROOT) -> List[str]:
    """Return validation errors for the W007 runtime foundation contract."""
    manifest_path = repo_root / "docs" / "runtime-artifact-manifest.json"
    trace_matrix_path = repo_root / "docs" / "api" / "rtm_trace_matrix.json"
    runtime_portal_path = repo_root / "docs" / "runtime.html"

    errors: List[str] = []
    manifest = _load_json(manifest_path, repo_root, errors)
    if manifest:
        _validate_manifest(manifest, repo_root, errors)

    trace_matrix = _load_json(trace_matrix_path, repo_root, errors)
    if trace_matrix:
        _validate_trace_matrix(trace_matrix, errors)

    _validate_runtime_portal(runtime_portal_path, errors)
    return errors


def main() -> int:
    errors = validate_runtime_foundation()
    if errors:
        print("W007 runtime foundation validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("W007 runtime foundation validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
