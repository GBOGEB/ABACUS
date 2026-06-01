"""Runtime governance metrics for W001.3."""

import os
from typing import Any, Dict, Mapping, Optional

from .geti import calculate_geti
from .pca import calculate_backward_pca, calculate_forward_pca
from .truth_matrix import TRUTH_RULES
from .truth_score import build_truth_matrix_snapshot


def _default_evidence() -> Dict[str, bool]:
    return {
        "repo_artifact_present": bool(TRUTH_RULES),
        "runtime_executed": True,
        "validation_ready": True,
        "claimed_runtime_ready": True,
        "chat_evidence_present": False,
        "architecture_only_evidence": False,
        "ci_execution_observed": os.environ.get("GITHUB_ACTIONS", "").lower() == "true",
    }


def load_metrics(evidence: Optional[Mapping[str, bool]] = None) -> Dict[str, Any]:
    """Return measurable runtime governance metrics payload."""
    measurable_evidence = _default_evidence()
    if evidence:
        measurable_evidence.update({key: bool(value) for key, value in evidence.items()})

    truth_matrix_snapshot = build_truth_matrix_snapshot(measurable_evidence)
    forward_pca = calculate_forward_pca(measurable_evidence)
    backward_pca = calculate_backward_pca(measurable_evidence)
    truth_score = float(truth_matrix_snapshot["truth_score"])
    geti = calculate_geti(forward_pca, backward_pca, truth_score)

    return {
        "forward_pca": forward_pca,
        "backward_pca": backward_pca,
        "geti": geti,
        "truth_score": truth_score,
        "runtime_ready": bool(truth_score > 0),
        "truth_matrix_snapshot": truth_matrix_snapshot,
    }
