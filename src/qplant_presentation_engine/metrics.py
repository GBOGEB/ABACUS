"""Initial runtime metrics for W001.1."""

from typing import Dict, Any


_INITIAL_METRICS: Dict[str, Any] = {
    "forward_pca": 0,
    "backward_pca": 0,
    "geti": 0,
    "runtime_ready": True,
}


def load_metrics() -> Dict[str, Any]:
    """Return the initial runtime metrics payload."""
    return dict(_INITIAL_METRICS)

