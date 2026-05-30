"""Forward and backward PCA metric helpers."""

from typing import Mapping, Tuple


def _ratio(values: Mapping[str, bool], dimensions: Tuple[str, ...]) -> float:
    if not dimensions:
        return 0.0
    hits = sum(1 for key in dimensions if bool(values.get(key, False)))
    return round(hits / len(dimensions), 4)


def calculate_forward_pca(evidence: Mapping[str, bool]) -> float:
    """Calculate forward PCA from measurable runtime evidence."""
    return _ratio(
        evidence,
        ("repo_artifact_present", "runtime_executed", "validation_ready"),
    )


def calculate_backward_pca(evidence: Mapping[str, bool]) -> float:
    """Calculate backward PCA from measurable CI/runtime evidence."""
    return _ratio(
        evidence,
        ("ci_execution_observed", "runtime_executed", "validation_ready"),
    )
