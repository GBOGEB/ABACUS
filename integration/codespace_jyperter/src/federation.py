"""
Federation assimilation stub for GBOGEB/codespace_jyperter (DELTA_1 auxiliary plane).

This module mirrors what GBOGEB/codespace_jyperter should expose at
``src/federation.py``.  It is kept in ABACUS under
``integration/codespace_jyperter/src/federation.py`` as the authoritative
integration record and can be copied verbatim into the codespace_jyperter
repository.

Provides the assimilate() entry point consumed by:
  - scripts/recursive_build.py --smoke --index GLOBAL_index.json
  - integration/codespace_jyperter/tests/test_smoke_federation.py

The canonical federation spec lives at:
  runtime/federation/codex-abacus-federation.yaml

The global federation manifest lives at:
  federation/manifest.yaml (ABACUS root)
  integration/codespace_jyperter/federation/manifest.yaml (this integration stub)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

# When run from the ABACUS repo the manifest stub lives at the integration path.
# When copied to codespace_jyperter it will resolve to federation/manifest.yaml
# relative to that repo's root.
_THIS_DIR = Path(__file__).resolve().parent

# Integration stub manifest (within ABACUS repo).
_INTEGRATION_MANIFEST = _THIS_DIR.parent / "federation" / "manifest.yaml"

# Authoritative DELTA_1 spec (lives in ABACUS repo root).
_ABACUS_ROOT = _THIS_DIR.parent.parent.parent
_FEDERATION_SPEC = _ABACUS_ROOT / "runtime" / "federation" / "codex-abacus-federation.yaml"


def assimilate(context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Entry point for codespace_jyperter federation assimilation checks.

    Verifies that the required federation manifest and authoritative DELTA_1
    spec files exist and returns a status dictionary.  Called by
    recursive_build --smoke and the smoke-test suite.

    Args:
        context: Optional dict of caller-supplied metadata (e.g. session_id,
                 iteration).  Ignored if None.

    Returns:
        dict with keys:
            status (str): "ok" | "degraded" | "error"
            manifest_found (bool): True if the integration manifest exists
            spec_found (bool): True if runtime/federation/codex-abacus-federation.yaml exists
            repo (str): "GBOGEB/codespace_jyperter"
            plane (str): "auxiliary"
            details (list[str]): Human-readable messages
    """
    context = context or {}
    details: list[str] = []
    errors = 0

    manifest_found = _INTEGRATION_MANIFEST.is_file()
    if manifest_found:
        details.append(f"manifest OK: {_INTEGRATION_MANIFEST.name}")
    else:
        details.append(f"manifest MISSING: {_INTEGRATION_MANIFEST}")
        errors += 1

    spec_found = _FEDERATION_SPEC.is_file()
    if spec_found:
        details.append(f"spec OK: {_FEDERATION_SPEC.name}")
    else:
        details.append(f"spec MISSING: {_FEDERATION_SPEC}")
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
        "repo": "GBOGEB/codespace_jyperter",
        "plane": "auxiliary",
        "details": details,
        "context": context,
    }
