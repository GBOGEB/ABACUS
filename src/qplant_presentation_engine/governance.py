"""Generate governance evidence artifacts from DMAIC and runtime evidence."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

from .dmaic import REPORTS_DIRNAME, build_dmaic_snapshot


PHASE_ORDER = ("define", "measure", "analyze", "improve", "control")


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _completion_vector(phase_status: Mapping[str, Mapping[str, Any]]) -> Dict[str, int]:
    return {
        phase: 1 if bool((phase_status.get(phase) or {}).get("complete")) else 0
        for phase in PHASE_ORDER
    }


def generate_governance_artifacts(
    reports_dir: Optional[Path] = None,
    governance_output_path: Optional[Path] = None,
    completion_output_path: Optional[Path] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Create governance_snapshot.json and completion_vector.json artifacts."""
    resolved_reports_dir = reports_dir or (Path.cwd() / REPORTS_DIRNAME)
    dmaic_snapshot = build_dmaic_snapshot(reports_dir=resolved_reports_dir)

    phase_status = dmaic_snapshot.get("phase_status", {})
    vector = _completion_vector(phase_status if isinstance(phase_status, Mapping) else {})
    completed_phases = sum(vector.values())
    total_phases = len(PHASE_ORDER)
    governance_passed = completed_phases == total_phases

    completion_vector = {
        "artifact": "completion_vector",
        "generated_at": _utc_timestamp(),
        "phase_order": list(PHASE_ORDER),
        "vector": vector,
        "completed_phases": completed_phases,
        "total_phases": total_phases,
    }

    source_metrics = dmaic_snapshot.get("source_metrics", {})
    truth_principles = source_metrics.get("truth_principles", []) if isinstance(source_metrics, Mapping) else []

    governance_snapshot = {
        "artifact": "governance_snapshot",
        "generated_at": _utc_timestamp(),
        "governance_passed": governance_passed,
        "completion": {
            "completed_phases": completed_phases,
            "total_phases": total_phases,
            "completion_ratio": f"{completed_phases}/{total_phases}",
        },
        "evidence": {
            "dmaic_snapshot": str(resolved_reports_dir / "dmaic_snapshot.json"),
            "dashboard_status": str(resolved_reports_dir / "dashboard_status.json"),
            "runtime_registry_report": str(resolved_reports_dir / "runtime_registry_report.json"),
        },
        "truth_matrix": {
            "integrated": bool(dmaic_snapshot.get("truth_matrix_integrated")),
            "truth_score": source_metrics.get("truth_score") if isinstance(source_metrics, Mapping) else None,
            "principles": truth_principles if isinstance(truth_principles, list) else [],
        },
    }

    resolved_governance_output = governance_output_path or (resolved_reports_dir / "governance_snapshot.json")
    resolved_completion_output = completion_output_path or (resolved_reports_dir / "completion_vector.json")
    _write_json(resolved_governance_output, governance_snapshot)
    _write_json(resolved_completion_output, completion_vector)

    return governance_snapshot, completion_vector
