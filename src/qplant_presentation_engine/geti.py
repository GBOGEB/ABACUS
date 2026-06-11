"""Governance Evidence Traceability Index (GETI)."""


def calculate_geti(forward_pca: float, backward_pca: float, truth_score: float) -> float:
    """Compute a single measurable governance index from runtime evidence."""
    return round((forward_pca + backward_pca + truth_score) / 3.0, 4)
