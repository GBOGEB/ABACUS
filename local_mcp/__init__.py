"""
local_mcp – V2.3 Agent Framework & MCP Integration
====================================================
Model Context Protocol integration layer for ABACUS.
Provides IDE connectivity (VS Code, Cursor) and agent coordination.

Key components:
    - AgentOrchestratorV3: Memory-optimized multi-agent coordinator
    - KnowledgeIntegrationV23: Unified KEB/GBOGEB knowledge layer
    - agents/: Individual agent implementations (cryo, docs, recursive)
"""

import importlib.util
from pathlib import Path

__version__ = "2.3.0"
__all__ = [
    "AgentOrchestratorV3",
    "KnowledgeIntegrationV23",
]

_DIR = Path(__file__).parent

# Mapping: exported name → (loader alias, filename in package dir, class attribute)
_LAZY_EXPORTS = {
    "AgentOrchestratorV3": ("local_mcp._orchestrator", "agent_orchestrator_v3.0.py", "AgentOrchestratorV3"),
    "KnowledgeIntegrationV23": ("local_mcp._knowledge", "knowledge_integration_v2.3.py", "KnowledgeIntegrationV23"),
}


def _load_dotted_module(loader_name: str, filename: str):
    """Load a module whose filename contains dots (e.g. v2.3) that cannot be
    imported via the normal ``import`` machinery.  Uses
    ``importlib.util.spec_from_file_location`` which accepts arbitrary paths.
    """
    path = _DIR / filename
    spec = importlib.util.spec_from_file_location(loader_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot locate {filename!r} inside {_DIR}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def __getattr__(name: str):
    """PEP 562 lazy attribute resolution – heavy modules are only imported the
    first time an attribute is actually accessed, keeping ``import local_mcp``
    lightweight.
    """
    if name in _LAZY_EXPORTS:
        loader_name, filename, attr = _LAZY_EXPORTS[name]
        try:
            mod = _load_dotted_module(loader_name, filename)
        except Exception as exc:
            raise ImportError(
                f"Could not load {attr!r} from {filename!r}: {exc}"
            ) from exc
        value = getattr(mod, attr, None)
        if value is None:
            raise ImportError(f"{attr!r} not found in {filename!r}")
        # Cache on the module so subsequent accesses skip __getattr__
        globals()[name] = value
        return value
    raise AttributeError(f"module 'local_mcp' has no attribute {name!r}")
