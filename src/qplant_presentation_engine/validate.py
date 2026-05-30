"""Runtime validation checks for the QPLANT Presentation Engine."""

from importlib import import_module
from typing import Dict


def validate_runtime() -> Dict[str, bool]:
    """Validate runtime availability for critical W001.1 checks."""
    status = {
        "package_import": False,
        "runtime_entry": False,
        "metrics_availability": False,
        "truth_matrix_availability": False,
    }

    try:
        import_module("qplant_presentation_engine")
        status["package_import"] = True
    except Exception:
        return status

    try:
        runtime_module = import_module("qplant_presentation_engine.runtime")
        status["runtime_entry"] = hasattr(runtime_module, "run_runtime")
    except Exception:
        status["runtime_entry"] = False

    try:
        metrics_module = import_module("qplant_presentation_engine.metrics")
        metrics = metrics_module.load_metrics()
        status["metrics_availability"] = isinstance(metrics, dict) and bool(metrics)
    except Exception:
        status["metrics_availability"] = False

    try:
        truth_module = import_module("qplant_presentation_engine.truth_matrix")
        rules = getattr(truth_module, "TRUTH_RULES", [])
        status["truth_matrix_availability"] = isinstance(rules, list) and bool(rules)
    except Exception:
        status["truth_matrix_availability"] = False

    return status

