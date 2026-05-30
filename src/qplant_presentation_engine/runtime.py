"""Executable runtime path for the QPLANT Presentation Engine."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from .metrics import load_metrics
from .truth_matrix import TRUTH_RULES
from .validate import validate_runtime


def _resolve_entrypoint_module() -> str:
    top_level_entry = (
        Path(__file__).resolve().parents[2] / "qplant_presentation_engine" / "__main__.py"
    )
    if top_level_entry.exists():
        return "qplant_presentation_engine"
    return __package__ or "qplant_presentation_engine"


_RUNTIME_METADATA = {
    "engine": "QPLANT Presentation Engine",
    "version": "W001.1",
    "entrypoint": f"python -m {_resolve_entrypoint_module()}",
}


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _write_json_artifact(filename: str, payload: Dict[str, object]) -> None:
    Path.cwd().joinpath(filename).write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )


def load_runtime_metadata() -> Dict[str, str]:
    """Load runtime metadata."""
    return dict(_RUNTIME_METADATA)


def run_smoke_test() -> List[str]:
    """Execute the W001.1 runtime smoke test and return status lines."""
    _ = load_runtime_metadata()
    metrics = load_metrics()
    rules_loaded = isinstance(TRUTH_RULES, list) and bool(TRUTH_RULES)
    validation = validate_runtime()
    validation_ready = all(validation.values())

    report = ["[OK] Runtime Started"]
    report.append("[OK] Metrics Loaded" if metrics else "[FAIL] Metrics Loaded")
    report.append("[OK] Truth Matrix Loaded" if rules_loaded else "[FAIL] Truth Matrix Loaded")
    report.append("[OK] Validation Ready" if validation_ready else "[FAIL] Validation Ready")
    return report


def generate_runtime_evidence(
    exit_code: int,
    report: List[str],
    metrics: Dict[str, object],
    validation: Dict[str, bool],
) -> None:
    """Persist runtime evidence artifacts for CI and local verification."""
    generated_at = _utc_timestamp()
    runtime_status = "ok" if all(line.startswith("[OK]") for line in report) else "failed"
    validation_ready = all(validation.values())
    validation_status = "ready" if validation_ready else "failed"

    _write_json_artifact(
        "runtime_status.json",
        {
            "command": _RUNTIME_METADATA["entrypoint"],
            "exit_code": exit_code,
            "generated_at": generated_at,
            "report": report,
            "runtime_status": runtime_status,
            "validation_status": validation_status,
        },
    )

    _write_json_artifact(
        "validation_report.json",
        {
            "checks": validation,
            "generated_at": generated_at,
            "validation_status": validation_status,
        },
    )

    _write_json_artifact(
        "pca_snapshot.json",
        {
            "backward_pca": metrics.get("backward_pca", 0),
            "forward_pca": metrics.get("forward_pca", 0),
            "generated_at": generated_at,
            "geti": metrics.get("geti", 0),
        },
    )


def run_runtime() -> Tuple[int, List[str], Dict[str, str]]:
    """Run the runtime path and return exit code, status report, and metadata."""
    metadata = load_runtime_metadata()
    report = run_smoke_test()
    exit_code = 0 if all(line.startswith("[OK]") for line in report) else 1
    generate_runtime_evidence(
        exit_code=exit_code,
        report=report,
        metrics=load_metrics(),
        validation=validate_runtime(),
    )
    return exit_code, report, metadata
