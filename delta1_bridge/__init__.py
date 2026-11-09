"""delta1_bridge -- minimal, additive DELTA_1 federation bridge/adapter.

This package is a small, dependency-light shared layer that lets the DELTA_1
federation repositories (GBOGEB/CODEX, GBOGEB/ABACUS, GBOGEB/cryoplant-project)
exchange and reuse three overlapping concerns through one stable contract:

  1. A uniform federation *status / assimilate* interface (``adapter``) so every
     repo answers "who am I, what is my federation plane, is my metrics feed
     valid?" the same way -- compatible with cryoplant-project's existing
     ``src/federation.py:assimilate()`` and CODEX's ``src/bridge_adapter.py``.

  2. A single shared **DMAIC metrics schema** (``schema``) that both
     ``CODEX:docs/api/metrics.json`` and ``ABACUS:docs/api/dmaic_metrics.json``
     already conform to, with one validator instead of per-repo copies.

  3. A thin **Bradley-Terry ranking adapter** (``ranking``) that re-uses the
     canonical ``pca_engine.bradley_terry.fit_bradley_terry`` implementation
     from CODEX when importable, and otherwise falls back to a compact,
     dependency-free (no NumPy) pure-Python MM solver with the same contract --
     so ABACUS and cryoplant stop re-implementing pairwise ranking.

Design rules (honour the federation's existing conventions):
  * Standard library only. No third-party runtime deps; NumPy is optional.
  * Pure read / compute. No network, no writes to governed SSOT.
  * Additive. Nothing here deletes or restructures existing repo code.
"""
from __future__ import annotations

from .schema import (
    DMAIC_METRICS_REQUIRED_KEYS,
    validate_metrics,
    load_and_validate_metrics,
)
from .adapter import (
    GREEK_TRACE_SEQUENCE,
    KNOWN_REPOS,
    RepoDescriptor,
    detect_repo,
    federation_status,
    assimilate,
)
from .ranking import fit_bradley_terry, rank_pairwise, CANONICAL_BT_AVAILABLE

__all__ = [
    "DMAIC_METRICS_REQUIRED_KEYS",
    "validate_metrics",
    "load_and_validate_metrics",
    "GREEK_TRACE_SEQUENCE",
    "KNOWN_REPOS",
    "RepoDescriptor",
    "detect_repo",
    "federation_status",
    "assimilate",
    "fit_bradley_terry",
    "rank_pairwise",
    "CANONICAL_BT_AVAILABLE",
]

__version__ = "0.1.0"
