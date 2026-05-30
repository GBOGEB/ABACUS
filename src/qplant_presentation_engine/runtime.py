"""Executable runtime path for the QPLANT Presentation Engine."""

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


def run_runtime() -> Tuple[int, List[str], Dict[str, str]]:
    """Run the runtime path and return exit code, status report, and metadata."""
    metadata = load_runtime_metadata()
    report = run_smoke_test()
    exit_code = 0 if all(line.startswith("[OK]") for line in report) else 1
    return exit_code, report, metadata
