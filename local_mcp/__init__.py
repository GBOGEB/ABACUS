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

__version__ = "2.3.0"
__all__ = [
    "AgentOrchestratorV3",
    "KnowledgeIntegrationV23",
]

# Lazy imports to avoid circular dependencies and heavy startup cost
def _import_orchestrator():
    from importlib import import_module
    mod = import_module("local_mcp.agent_orchestrator_v3.0")  # noqa: E501 – file contains dot
    return getattr(mod, "AgentOrchestratorV3", None)

def _import_knowledge():
    from importlib import import_module
    mod = import_module("local_mcp.knowledge_integration_v2.3")  # noqa: E501
    return getattr(mod, "KnowledgeIntegrationV23", None)

# For convenience when importing the package directly
try:
    AgentOrchestratorV3 = _import_orchestrator()
except Exception:
    AgentOrchestratorV3 = None

try:
    KnowledgeIntegrationV23 = _import_knowledge()
except Exception:
    KnowledgeIntegrationV23 = None
