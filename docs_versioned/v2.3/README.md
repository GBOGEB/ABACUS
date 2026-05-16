# ABACUS v2.3 — MCP Integration & Agent Framework
> *Reconstructed from code — 2026-05-16 22:34*

## Overview
v2.3 introduces the Model Context Protocol (MCP) integration layer with upgraded agents.

## Key Components
| Component | File | Description |
|-----------|------|-------------|
| Agent Orchestrator | `local_mcp/agent_orchestrator_v3.0.py` | Memory-optimized, coordinates all agents |
| Knowledge Integration | `local_mcp/knowledge_integration_v2.3.py` | Unified KEB/GBOGEB knowledge layer |
| Doc Framework | `local_mcp/agents/documentation_framework_v2.3_OPTIMIZED.py` | Automated doc generation |
| Recursive Framework | `local_mcp/agents/recursive_framework_v2.3_OPTIMIZED.py` | Self-improvement loops |

## Architecture
```
IDE (VS Code/Cursor) 
  └─→ MCP Protocol Layer
       └─→ Agent Orchestrator v3.0
            ├─→ Documentation Agent
            ├─→ Recursive Agent  
            ├─→ KEB Task Scheduler
            └─→ GBOGEB Observer
```

## ⚠️ Known Issues
- Missing `local_mcp/__init__.py` — prevents direct package import
- Requires MCP protocol dependencies
