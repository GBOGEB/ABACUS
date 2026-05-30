"""Truth-matrix scoring from measurable runtime and CI evidence."""

from typing import Any, Dict, Mapping

from .truth_matrix import TRUTH_RULES


def _evaluate_rule(rule: str, evidence: Mapping[str, bool]) -> Dict[str, Any]:
    if rule == "chat_is_not_repo":
        score = bool(evidence.get("repo_artifact_present", False)) and not bool(
            evidence.get("chat_evidence_present", False)
        )
    elif rule == "architecture_is_not_runtime":
        score = bool(evidence.get("runtime_executed", False)) and not bool(
            evidence.get("architecture_only_evidence", False)
        )
    elif rule == "claimed_is_not_validated":
        claimed_runtime_ready = bool(evidence.get("claimed_runtime_ready", False))
        validation_ready = bool(evidence.get("validation_ready", False))
        score = (not claimed_runtime_ready) or validation_ready
    elif rule == "exists_in_repo_is_not_ci_execution":
        score = bool(evidence.get("ci_execution_observed", False))
    else:
        score = False

    return {"principle": rule, "satisfied": score, "score": 1.0 if score else 0.0}


def build_truth_matrix_snapshot(evidence: Mapping[str, bool]) -> Dict[str, Any]:
    """Build rule-level and aggregate truth matrix metrics."""
    rows = [_evaluate_rule(rule, evidence) for rule in TRUTH_RULES]
    truth_score = round(sum(row["score"] for row in rows) / len(rows), 4) if rows else 0.0
    return {
        "truth_score": truth_score,
        "principles": rows,
        "evidence": dict(evidence),
    }
