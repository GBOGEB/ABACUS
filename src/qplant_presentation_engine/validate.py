"""Runtime validation checks for the QPLANT Presentation Engine."""

import logging
from importlib import import_module
from typing import Dict

logger = logging.getLogger(__name__)


def validate_runtime() -> Dict[str, bool]:
    """Validate runtime availability for critical W001.1 checks."""
    status = {
        "package_import": False,
        "runtime_entry": False,
        "metrics_availability": False,
        "truth_matrix_availability": False,
        "schema_consistency": False,
    }

    package_name = __package__ or "qplant_presentation_engine"

    try:
        import_module(package_name)
        status["package_import"] = True
    except Exception:
        logger.warning("validate_runtime: package_import failed for %r", package_name, exc_info=True)
        return status

    try:
        runtime_module = import_module(f"{package_name}.runtime")
        status["runtime_entry"] = hasattr(runtime_module, "run_runtime")
    except Exception:
        logger.warning("validate_runtime: runtime_entry check failed", exc_info=True)
        status["runtime_entry"] = False

    try:
        metrics_module = import_module(f"{package_name}.metrics")
        metrics = metrics_module.load_metrics()
        status["metrics_availability"] = isinstance(metrics, dict) and bool(metrics)
    except Exception:
        logger.warning("validate_runtime: metrics_availability check failed", exc_info=True)
        status["metrics_availability"] = False

    try:
        truth_module = import_module(f"{package_name}.truth_matrix")
        rules = getattr(truth_module, "TRUTH_RULES", [])
        status["truth_matrix_availability"] = isinstance(rules, list) and bool(rules)
    except Exception:
        logger.warning("validate_runtime: truth_matrix_availability check failed", exc_info=True)
        status["truth_matrix_availability"] = False

    try:
        schema_validation_module = import_module(f"{package_name}.schema_validation")
        schema_validation = schema_validation_module.validate_canonical_schema()
        status["schema_consistency"] = all(bool(value) for value in schema_validation.values())
    except Exception:
        logger.warning("validate_runtime: schema_consistency check failed", exc_info=True)
        status["schema_consistency"] = False

    return status
