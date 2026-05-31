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
RTM_SUMMARY_FILENAME = "rtm_summary.json"

# Default repo root: two levels above this file (src/qplant_presentation_engine/rtm.py → repo root)
_DEFAULT_REPO_DIR = Path(__file__).resolve().parents[2]


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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
            "id": "REQ-001",
            "title": "Runtime entry is executable",
            "description": (
                "python -m qplant_presentation_engine executes successfully "
                "and produces runtime evidence."
            ),
            "evidence": ["runtime_status"],
        },
        {
            "id": "REQ-002",
            "title": "Scientific visualization schema is defined",
            "description": (
                "A canonical JSON/YAML schema exists covering all supported "
                "visualization types."
            ),
            "evidence": ["scientific_visualization_schema"],
        },
        {
            "id": "REQ-003",
            "title": "SVG and process-flow rendering is supported",
            "description": (
                "Process-flow YAML content exists and drives SVG rendering."
            ),
            "evidence": ["qplant_process_flow_content"],
        },
        {
            "id": "REQ-004",
            "title": "MathML rendering is supported",
            "description": (
                "Thermodynamics YAML content with equations exists and drives "
                "MathML rendering."
            ),
            "evidence": ["qplant_thermodynamics_content"],
        },
        {
            "id": "REQ-005",
            "title": "QPLANT content loads successfully",
            "description": (
                "All QPLANT YAML content files are present and accessible."
            ),
            "evidence": [
                "qplant_process_flow_content",
                "qplant_thermodynamics_content",
            ],
        },
        {
            "id": "REQ-006",
            "title": "Dashboard generation produces status evidence",
            "description": (
                "Dashboard build generates dashboard_status.json as evidence of "
                "successful execution."
            ),
            "evidence": ["dashboard_status"],
        },
        {
            "id": "REQ-007",
            "title": "Federation runtime registry is consumed",
            "description": (
                "Federation registry report is ingested and available as runtime "
                "evidence."
            ),
            "evidence": ["runtime_registry_report"],
        },
        {
            "id": "REQ-008",
            "title": "DMAIC governance snapshots are generated",
            "description": (
                "DMAIC and governance artifacts are produced as evidence of "
                "governance execution."
            ),
            "evidence": ["dmaic_snapshot", "governance_snapshot"],
        },
        {
            "id": "REQ-009",
            "title": "Schema validation is enforced",
            "description": (
                "Validation rules enforce schema conformance for all supported "
                "visualization types."
            ),
            "evidence": ["scientific_visualization_schema", "schema_validation_rules"],
        },
    ]


def _evidence_catalog(reports_dir: Path, repo_dir: Path) -> Dict[str, Dict[str, Any]]:
    runtime_status_path = _resolve_runtime_status_path(reports_dir)
    schema_path = repo_dir / "patterns" / "scientific_visualization" / "schema.json"
    validation_rules_path = repo_dir / "patterns" / "scientific_visualization" / "validation_rules.yaml"
    process_flow_path = repo_dir / "content" / "qplant" / "process_flow.yaml"
    thermodynamics_path = repo_dir / "content" / "qplant" / "thermodynamics.yaml"

    evidence_files: Dict[str, Dict[str, Any]] = {
        "runtime_status": {
            "artifact": str(runtime_status_path),
            "domain": "runtime",
            "available": runtime_status_path.exists(),
        },
        "runtime_registry_report": {
            "artifact": str(reports_dir / "runtime_registry_report.json"),
            "domain": "runtime",
            "available": (reports_dir / "runtime_registry_report.json").exists(),
        },
        "dashboard_status": {
            "artifact": str(reports_dir / "dashboard_status.json"),
            "domain": "validation",
            "available": (reports_dir / "dashboard_status.json").exists(),
        },
        "dmaic_snapshot": {
            "artifact": str(reports_dir / "dmaic_snapshot.json"),
            "domain": "dmaic",
            "available": (reports_dir / "dmaic_snapshot.json").exists(),
        },
        "governance_snapshot": {
            "artifact": str(reports_dir / "governance_snapshot.json"),
            "domain": "governance",
            "available": (reports_dir / "governance_snapshot.json").exists(),
        },
        "completion_vector": {
            "artifact": str(reports_dir / "completion_vector.json"),
            "domain": "governance",
            "available": (reports_dir / "completion_vector.json").exists(),
        },
        "scientific_visualization_schema": {
            "artifact": str(schema_path),
            "domain": "schema",
            "available": schema_path.exists(),
        },
        "schema_validation_rules": {
            "artifact": str(validation_rules_path),
            "domain": "schema",
            "available": validation_rules_path.exists(),
        },
        "qplant_process_flow_content": {
            "artifact": str(process_flow_path),
            "domain": "content",
            "available": process_flow_path.exists(),
        },
        "qplant_thermodynamics_content": {
            "artifact": str(thermodynamics_path),
            "domain": "content",
            "available": thermodynamics_path.exists(),
        },
    }
    return evidence_files


def _generate_summary(
    requirements: List[Dict[str, Any]],
    trace_matrix_rows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compute RTM coverage summary."""
    total = len(requirements)
    reqs_with_evidence = sum(1 for r in requirements if r.get("evidence"))
    uncovered = [r["id"] for r in requirements if not r.get("evidence")]
    coverage_ratio = (reqs_with_evidence / total) if total > 0 else 0.0

    row_pairs = [(row["requirement_id"], row["evidence_id"]) for row in trace_matrix_rows]
    no_duplicates = len(row_pairs) == len(set(row_pairs))

    validation_passed = coverage_ratio == 1.0 and no_duplicates

    return {
        "total_requirements": total,
        "requirements_with_evidence": reqs_with_evidence,
        "uncovered_requirements": uncovered,
        "coverage_ratio": coverage_ratio,
        "validation_passed": validation_passed,
        "generated_at": _utc_timestamp(),
    }


def generate_rtm_artifacts(
    reports_dir: Optional[Path] = None,
    rtm_dir: Optional[Path] = None,
    repo_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Generate requirements, evidence map, trace matrix, and summary for RTM."""
    resolved_reports_dir = reports_dir or (Path.cwd() / REPORTS_DIRNAME)
    resolved_rtm_dir = rtm_dir or (Path.cwd() / RTM_DIRNAME)
    resolved_repo_dir = repo_dir if repo_dir is not None else _DEFAULT_REPO_DIR

    requirements = _requirements()
    evidence_catalog = _evidence_catalog(resolved_reports_dir, resolved_repo_dir)

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
    seen_rows: set = set()

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

    rtm_summary = _generate_summary(requirements, trace_matrix_rows)

    _write_yaml(resolved_rtm_dir / REQUIREMENTS_FILENAME, requirements_yaml)
    _write_yaml(resolved_rtm_dir / EVIDENCE_MAP_FILENAME, evidence_map_yaml)
    _write_json(resolved_rtm_dir / TRACE_MATRIX_FILENAME, trace_matrix_json)
    _write_json(resolved_rtm_dir / RTM_SUMMARY_FILENAME, rtm_summary)

    return {
        "requirements": requirements_yaml,
        "evidence_map": evidence_map_yaml,
        "trace_matrix": trace_matrix_json,
        "rtm_summary": rtm_summary,
    }
