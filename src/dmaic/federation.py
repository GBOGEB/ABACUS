"""
Federation assimilation stub for GBOGEB/ABACUS (DELTA_1 runtime plane).

Provides the assimilate() entry point consumed by:
  - scripts/recursive_build.py --smoke --index GLOBAL_index.json
  - DMAIC_V3/tests/test_smoke_federation.py

The canonical federation spec lives at:
  runtime/federation/codex-abacus-federation.yaml

The global federation manifest lives at:
  federation/manifest.yaml
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

# Path from this file to the repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

FEDERATION_MANIFEST = _REPO_ROOT / "federation" / "manifest.yaml"
FEDERATION_SPEC = _REPO_ROOT / "runtime" / "federation" / "codex-abacus-federation.yaml"


def assimilate(context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Entry point for federation assimilation checks.

    Verifies that the required federation manifest and spec files exist and
    returns a status dictionary.  Called by recursive_build --smoke and the
    smoke-test suite.

    Args:
        context: Optional dict of caller-supplied metadata (e.g. session_id,
                 iteration).  Ignored if None.

    Returns:
        dict with keys:
            status (str): "ok" | "degraded" | "error"
            manifest_found (bool): True if federation/manifest.yaml exists
            spec_found (bool): True if runtime/federation/codex-abacus-federation.yaml exists
            details (list[str]): Human-readable messages
    """
    context = context or {}
    details: list[str] = []
    errors = 0

    manifest_found = FEDERATION_MANIFEST.is_file()
    if manifest_found:
        details.append(f"manifest OK: {FEDERATION_MANIFEST.relative_to(_REPO_ROOT)}")
    else:
        details.append(f"manifest MISSING: {FEDERATION_MANIFEST.relative_to(_REPO_ROOT)}")
        errors += 1

    spec_found = FEDERATION_SPEC.is_file()
    if spec_found:
        details.append(f"spec OK: {FEDERATION_SPEC.relative_to(_REPO_ROOT)}")
    else:
        details.append(f"spec MISSING: {FEDERATION_SPEC.relative_to(_REPO_ROOT)}")
        errors += 1

    if errors == 0:
        status = "ok"
    elif errors < 2:
        status = "degraded"
    else:
        status = "error"

    return {
        "status": status,
        "manifest_found": manifest_found,
        "spec_found": spec_found,
        "details": details,
        "context": context,
    }
