# Migration Guide: v0.32 → v2.3
> *Reconstructed from code — 2026-05-16 22:34*

## Overview
v2.3 introduces the MCP (Model Context Protocol) integration layer and upgraded agent framework.

## What Changes
1. **Agent Framework** — New agent orchestrator with memory optimization
2. **MCP Integration** — IDE connectivity (VS Code, Cursor)
3. **Knowledge Layer** — Unified KEB/GBOGEB knowledge integration
4. **Optimized Agents** — Documentation and recursive framework agents

## Key New Files
- `local_mcp/agent_orchestrator_v3.0.py` — Memory-optimized orchestrator
- `local_mcp/knowledge_integration_v2.3.py` — Unified knowledge layer
- `local_mcp/agents/` — Upgraded agent implementations

## Migration Steps
1. Install MCP dependencies from project requirements (`DMAIC_V3/requirements.txt`) and local MCP module imports
2. Configure agent orchestrator
3. Set up IDE integration if using VS Code/Cursor
4. Validate with agent import tests

## ⚠️ Known Issue
`local_mcp` contains dotted version filenames (for example `agent_orchestrator_v3.0.py`) that are not importable via standard dotted module paths.
Use import shims/aliases or rename modules for stable package imports.
