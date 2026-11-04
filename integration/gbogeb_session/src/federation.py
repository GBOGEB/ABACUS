"""Federation assimilation stub for the GBOGEB session-2026-05-22 node.

Mirrors the convention of integration/cryoplant_project/src/federation.py.
Provides assimilate() returning a summary of the session node for smoke tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

_THIS_DIR = Path(__file__).resolve().parent
_NODE_ROOT = _THIS_DIR.parent


def assimilate() -> Dict[str, Any]:
    """Return a static summary describing this assimilated session node."""
    components = {
        "governance": _NODE_ROOT / "governance" / "engines",
        "mcp_server": _NODE_ROOT / "mcp_server" / "src",
        "orchestration_docs": _NODE_ROOT / "orchestration_docs",
        "handover": _NODE_ROOT / "handover",
    }
    return {
        "node": "GBOGEB/session-2026-05-22",
        "plane": "runtime",
        "status": "draft",
        "supersedes": "feat/mcp-orchestration-session-2026-05-22-noworkflows",
        "components_present": {k: p.exists() for k, p in components.items()},
    }
