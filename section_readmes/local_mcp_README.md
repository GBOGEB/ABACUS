# local_mcp — V2.3 Agent Framework & MCP Integration

**Status:** ACTIVE | **Role:** Agent orchestration and IDE integration

## Purpose
Contains the V2.3 agent orchestrator and upgraded agents for the Model Context Protocol (MCP) integration layer. Provides IDE connectivity (VS Code, Cursor) and agent coordination.

## Key Files
| File | Purpose |
|------|---------|
| `agent_orchestrator_v3.0.py` | Memory-optimized orchestrator (4M constraint) |
| `knowledge_integration_v2.3.py` | KEB/GBOGEB unified knowledge layer |
| `agents/documentation_framework_v2.3_OPTIMIZED.py` | Documentation agent |
| `agents/recursive_framework_v2.3_OPTIMIZED.py` | Recursive improvement agent |

## Note
Import failures here are primarily due to dotted filenames (for example `agent_orchestrator_v3.0.py` and `knowledge_integration_v2.3.py`), which are not valid Python module names. Run these as scripts, rename to importable module names, or load by file path via `importlib`.
