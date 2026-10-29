"""Bradley-Terry pairwise ranking adapter for the DELTA_1 federation.

The *canonical* implementation lives in CODEX at
``pca_engine/src/pca_engine/bradley_terry.py`` (NumPy-based, domain-neutral).
ABACUS (ARTIFACT_RANKING_CLASSIFICATION_SYSTEM) and cryoplant-project
(docs/offer_eval DMAIC_BT analyses) each describe/re-derive the same pairwise
ranking idea. This adapter gives all three a single call site:

  * If the canonical ``pca_engine.bradley_terry.fit_bradley_terry`` is
    importable, delegate to it (single source of truth).
  * Otherwise, use a compact, dependency-free MM (minorization-maximization)
    fallback with the *same input/output contract*, so a repo that has not
    vendored pca_engine still ranks deterministically.

Contract (both paths):
    fit_bradley_terry(ids, comparisons, iterations=..., tolerance=...) -> dict
      ids:          sequence of >=2 unique item ids
      comparisons:  sequence of {"a": id, "b": id, "a_score": float,
                    "b_score": float} rows (a_score > b_score => a beat b)
    returns {"strengths": {id: float}, "ranking": [ids high->low],
             "iterations": int, "engine": "canonical"|"fallback"}
"""
from __future__ import annotations

from typing import Any, Sequence

try:  # canonical implementation (CODEX pca_engine), optional
    from pca_engine.bradley_terry import fit_bradley_terry as _canonical_fit
    CANONICAL_BT_AVAILABLE = True
except Exception:  # pragma: no cover - depends on install layout
    _canonical_fit = None
    CANONICAL_BT_AVAILABLE = False


def _validate(ids: Sequence[str], comparisons: Sequence[dict[str, Any]]) -> list[str]:
    names = [str(x) for x in ids]
    if len(names) < 2 or len(set(names)) != len(names):
        raise ValueError("ids must contain at least two unique items")
    allowed = set(names)
    for row in comparisons:
        a, b = str(row.get("a")), str(row.get("b"))
        if a == b or a not in allowed or b not in allowed:
            raise ValueError("each comparison must reference two distinct known ids")
    return names


def _wins_matrix(names: list[str], comparisons: Sequence[dict[str, Any]]):
    idx = {n: i for i, n in enumerate(names)}
    n = len(names)
    # wins[i][j] = number of times i beat j (fractional ties allowed as 0.5)
    wins = [[0.0] * n for _ in range(n)]
    for row in comparisons:
        a, b = str(row["a"]), str(row["b"])
        a_score = float(row.get("a_score", 0.0))
        b_score = float(row.get("b_score", 0.0))
        i, j = idx[a], idx[b]
        if a_score > b_score:
            wins[i][j] += 1.0
        elif b_score > a_score:
            wins[j][i] += 1.0
        else:
            wins[i][j] += 0.5
            wins[j][i] += 0.5
    return wins


def _fallback_fit(ids, comparisons, iterations: int = 2000,
                  tolerance: float = 1.0e-11) -> dict:
    """Pure-Python Bradley-Terry via MM updates (no NumPy)."""
    names = _validate(ids, comparisons)
    n = len(names)
    wins = _wins_matrix(names, comparisons)
    total_wins = [sum(wins[i][j] for j in range(n)) for i in range(n)]

    p = [1.0 / n] * n  # strengths
    used = 0
    for used in range(1, iterations + 1):
        new_p = [0.0] * n
        for i in range(n):
            denom = 0.0
            for j in range(n):
                if i == j:
                    continue
                games = wins[i][j] + wins[j][i]
                if games > 0:
                    denom += games / (p[i] + p[j])
            new_p[i] = (total_wins[i] / denom) if denom > 0 else p[i]
        s = sum(new_p) or 1.0
        new_p = [x / s for x in new_p]
        delta = max(abs(new_p[i] - p[i]) for i in range(n))
        p = new_p
        if delta < tolerance:
            break

    strengths = {names[i]: p[i] for i in range(n)}
    ranking = sorted(strengths, key=lambda k: strengths[k], reverse=True)
    return {"strengths": strengths, "ranking": ranking,
            "iterations": used, "engine": "fallback"}


def _normalize_for_canonical(comparisons: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rescale each comparison's scores so a_score + b_score == 1.

    The federation contract accepts raw/absolute scores (e.g. 2 vs 1); the
    canonical CODEX engine requires normalized probability-style scores. This
    keeps a single caller-facing contract across both engines.
    """
    out: list[dict[str, Any]] = []
    for row in comparisons:
        a_score = float(row.get("a_score", 0.0))
        b_score = float(row.get("b_score", 0.0))
        total = a_score + b_score
        if total <= 0:
            a_norm = b_norm = 0.5
        else:
            a_norm = a_score / total
            b_norm = b_score / total
        out.append({"a": row["a"], "b": row["b"],
                    "a_score": a_norm, "b_score": b_norm})
    return out


def fit_bradley_terry(ids, comparisons, iterations: int = 2000,
                      tolerance: float = 1.0e-11) -> dict:
    """Rank items by pairwise comparisons (canonical engine if available)."""
    if CANONICAL_BT_AVAILABLE and _canonical_fit is not None:
        result = _canonical_fit(ids, _normalize_for_canonical(comparisons),
                                iterations=iterations, tolerance=tolerance)
        if isinstance(result, dict):
            result.setdefault("engine", "canonical")
            if "strengths" in result and "ranking" not in result:
                strengths = result["strengths"]
                result["ranking"] = sorted(strengths, key=lambda k: strengths[k],
                                           reverse=True)
            return result
        # Unexpected canonical shape -> wrap defensively.
        return {"strengths": result, "engine": "canonical"}
    return _fallback_fit(ids, comparisons, iterations=iterations,
                         tolerance=tolerance)


def rank_pairwise(ids, comparisons, **kwargs) -> list[str]:
    """Convenience wrapper returning just the ranked id list (high -> low)."""
    return fit_bradley_terry(ids, comparisons, **kwargs)["ranking"]
