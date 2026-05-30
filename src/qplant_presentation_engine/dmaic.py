"""Build DMAIC governance snapshot artifacts from existing evidence reports."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional


REPORTS_DIRNAME = "reports"
INPUT_FILES = {
    "runtime_status": "runtime_status.json",
    "runtime_registry_report": "runtime_registry_report.json",
    "dashboard_status": "dashboard_status.json",
    "truth_matrix_snapshot": "truth_matrix_snapshot.json",
    "pca_snapshot": "pca_snapshot.json",
    "geti_snapshot": "geti_snapshot.json",
}


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


def _runtime_coverage_map(runtime_registry_report: Mapping[str, Any]) -> Dict[str, Any]:
    repositories = runtime_registry_report.get("repositories")
    if not isinstance(repositories, Mapping):
        return {}
    return {
        str(repo): data.get("runtime_coverage", "N/A")
        for repo, data in repositories.items()
        if isinstance(data, Mapping)
    }


def build_dmaic_snapshot(
    reports_dir: Optional[Path] = None,
    output_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Convert runtime/dashboard evidence into a DMAIC snapshot artifact."""
    resolved_reports_dir = reports_dir or (Path.cwd() / REPORTS_DIRNAME)

    runtime_status = _read_json(resolved_reports_dir / INPUT_FILES["runtime_status"])
    runtime_registry_report = _read_json(resolved_reports_dir / INPUT_FILES["runtime_registry_report"])
    dashboard_status = _read_json(resolved_reports_dir / INPUT_FILES["dashboard_status"])
    truth_matrix_snapshot = _read_json(resolved_reports_dir / INPUT_FILES["truth_matrix_snapshot"])
    pca_snapshot = _read_json(resolved_reports_dir / INPUT_FILES["pca_snapshot"])
    geti_snapshot = _read_json(resolved_reports_dir / INPUT_FILES["geti_snapshot"])

    runtime_ok = runtime_status.get("runtime_status") == "ok"
    validation_ready = runtime_status.get("validation_status") == "ready"
    dashboard_generated = bool(dashboard_status.get("dashboard_generated"))
    runtime_registry_consumed = bool(dashboard_status.get("runtime_registry_consumed"))
    truth_matrix_integrated = bool(truth_matrix_snapshot.get("principles"))
    pca_available = "forward_pca" in pca_snapshot and "backward_pca" in pca_snapshot
    geti_available = "geti" in geti_snapshot
    registry_available = bool(_runtime_coverage_map(runtime_registry_report))

    phase_status = {
        "define": {
            "complete": runtime_ok,
            "evidence": ["runtime_status"],
        },
        "measure": {
            "complete": validation_ready and pca_available and geti_available,
            "evidence": ["runtime_status", "pca_snapshot", "geti_snapshot"],
        },
        "analyze": {
            "complete": truth_matrix_integrated and registry_available,
            "evidence": ["truth_matrix_snapshot", "runtime_registry_report"],
        },
        "improve": {
            "complete": dashboard_generated,
            "evidence": ["dashboard_status"],
        },
        "control": {
            "complete": runtime_registry_consumed and dashboard_generated,
            "evidence": ["dashboard_status", "runtime_registry_report"],
        },
    }

    dmaic_snapshot = {
        "artifact": "dmaic_snapshot",
        "generated_at": _utc_timestamp(),
        "inputs": {key: str(resolved_reports_dir / filename) for key, filename in INPUT_FILES.items()},
        "phase_status": phase_status,
        "source_metrics": {
            "runtime_status": runtime_status.get("runtime_status", "unknown"),
            "validation_status": runtime_status.get("validation_status", "unknown"),
            "dashboard_status": dashboard_status.get("status", "unknown"),
            "runtime_coverage": _runtime_coverage_map(runtime_registry_report),
            "forward_pca": pca_snapshot.get("forward_pca"),
            "backward_pca": pca_snapshot.get("backward_pca"),
            "geti": geti_snapshot.get("geti"),
            "truth_score": truth_matrix_snapshot.get("truth_score"),
            "truth_principles": truth_matrix_snapshot.get("principles", []),
        },
        "truth_matrix_integrated": truth_matrix_integrated,
    }

    resolved_output = output_path or (resolved_reports_dir / "dmaic_snapshot.json")
    _write_json(resolved_output, dmaic_snapshot)
    return dmaic_snapshot
