"""Generate RTM artifacts from runtime, governance, validation, and DMAIC evidence."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import yaml


REPORTS_DIRNAME = "reports"
RTM_DIRNAME = "rtm"
REQUIREMENTS_FILENAME = "requirements.yaml"
EVIDENCE_MAP_FILENAME = "evidence_map.yaml"
TRACE_MATRIX_FILENAME = "trace_matrix.json"


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_yaml(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _unique_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _resolve_runtime_status_path(reports_dir: Path) -> Path:
    primary = reports_dir / "runtime_status.json"
    if primary.exists():
        return primary
    return reports_dir / "runtime_publish_status.json"


def _requirements() -> List[Dict[str, Any]]:
    return [
        {
            "id": "REQ-RTM-001",
            "title": "Runtime evidence is traceable",
            "description": "Runtime execution and registry artifacts are mapped into RTM evidence.",
            "evidence": ["runtime_status", "runtime_registry_report"],
        },
        {
            "id": "REQ-RTM-002",
            "title": "Governance evidence is traceable",
            "description": "Governance controls and completion vector artifacts are mapped into RTM evidence.",
            "evidence": ["governance_snapshot", "completion_vector"],
        },
        {
            "id": "REQ-RTM-003",
            "title": "Validation evidence is traceable",
            "description": "Validation-oriented runtime and dashboard signals are mapped into RTM evidence.",
            "evidence": ["runtime_status", "dashboard_status"],
        },
        {
            "id": "REQ-RTM-004",
            "title": "DMAIC evidence is traceable",
            "description": "DMAIC status artifacts are mapped into RTM evidence.",
            "evidence": ["dmaic_snapshot", "governance_snapshot"],
        },
        {
            "id": "REQ-RTM-005",
            "title": "Integrated RTM matrix is generated",
            "description": "A full matrix exists across runtime, governance, validation, and DMAIC evidence.",
            "evidence": [
                "runtime_status",
                "runtime_registry_report",
                "dashboard_status",
                "dmaic_snapshot",
                "governance_snapshot",
                "completion_vector",
            ],
        },
    ]


def _evidence_catalog(reports_dir: Path) -> Dict[str, Dict[str, Any]]:
    runtime_status_path = _resolve_runtime_status_path(reports_dir)
    evidence_files = {
        "runtime_status": {
            "artifact": str(runtime_status_path),
            "domain": "runtime",
            "payload": _read_json(runtime_status_path),
        },
        "runtime_registry_report": {
            "artifact": str(reports_dir / "runtime_registry_report.json"),
            "domain": "runtime",
            "payload": _read_json(reports_dir / "runtime_registry_report.json"),
        },
        "dashboard_status": {
            "artifact": str(reports_dir / "dashboard_status.json"),
            "domain": "validation",
            "payload": _read_json(reports_dir / "dashboard_status.json"),
        },
        "dmaic_snapshot": {
            "artifact": str(reports_dir / "dmaic_snapshot.json"),
            "domain": "dmaic",
            "payload": _read_json(reports_dir / "dmaic_snapshot.json"),
        },
        "governance_snapshot": {
            "artifact": str(reports_dir / "governance_snapshot.json"),
            "domain": "governance",
            "payload": _read_json(reports_dir / "governance_snapshot.json"),
        },
        "completion_vector": {
            "artifact": str(reports_dir / "completion_vector.json"),
            "domain": "governance",
            "payload": _read_json(reports_dir / "completion_vector.json"),
        },
    }
    return {
        key: {
            "artifact": value["artifact"],
            "domain": value["domain"],
            "available": bool(value["payload"]),
        }
        for key, value in evidence_files.items()
    }


def generate_rtm_artifacts(
    reports_dir: Optional[Path] = None,
    rtm_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Generate requirements, evidence map, and trace matrix artifacts for RTM."""
    resolved_reports_dir = reports_dir or (Path.cwd() / REPORTS_DIRNAME)
    resolved_rtm_dir = rtm_dir or (Path.cwd() / RTM_DIRNAME)

    requirements = _requirements()
    evidence_catalog = _evidence_catalog(resolved_reports_dir)

    requirements_yaml = {
        "artifact": "requirements",
        "generated_at": _utc_timestamp(),
        "requirements": [
            {
                "id": requirement["id"],
                "title": requirement["title"],
                "description": requirement["description"],
            }
            for requirement in requirements
        ],
    }

    evidence_map_requirements = {}
    trace_matrix_rows: List[Dict[str, Any]] = []
    seen_rows = set()

    for requirement in requirements:
        requirement_id = requirement["id"]
        evidence_ids = _unique_preserve_order(requirement["evidence"])
        evidence_entries = []
        for evidence_id in evidence_ids:
            evidence = evidence_catalog[evidence_id]
            evidence_entries.append({"evidence_id": evidence_id, **evidence})
            row_key = (requirement_id, evidence_id)
            if row_key in seen_rows:
                continue
            seen_rows.add(row_key)
            trace_matrix_rows.append(
                {
                    "requirement_id": requirement_id,
                    "requirement_title": requirement["title"],
                    "evidence_id": evidence_id,
                    "evidence_artifact": evidence["artifact"],
                    "evidence_domain": evidence["domain"],
                    "available": evidence["available"],
                }
            )
        evidence_map_requirements[requirement_id] = {
            "title": requirement["title"],
            "evidence": evidence_entries,
        }

    evidence_map_yaml = {
        "artifact": "evidence_map",
        "generated_at": _utc_timestamp(),
        "reports_dir": str(resolved_reports_dir),
        "requirements": evidence_map_requirements,
    }

    trace_matrix_json = {
        "artifact": "trace_matrix",
        "generated_at": _utc_timestamp(),
        "rows": trace_matrix_rows,
    }

    _write_yaml(resolved_rtm_dir / REQUIREMENTS_FILENAME, requirements_yaml)
    _write_yaml(resolved_rtm_dir / EVIDENCE_MAP_FILENAME, evidence_map_yaml)
    _write_json(resolved_rtm_dir / TRACE_MATRIX_FILENAME, trace_matrix_json)

    return {
        "requirements": requirements_yaml,
        "evidence_map": evidence_map_yaml,
        "trace_matrix": trace_matrix_json,
    }
