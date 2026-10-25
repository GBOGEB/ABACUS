# GBOGEB MCP Server

**Model Context Protocol server for dual-repository context sharing between GBOGEB/ABACUS (GBA) and GBOGEB/CODEX (GBC).**

[![Tests](https://img.shields.io/badge/tests-51%20passed-brightgreen)]()
[![MCP](https://img.shields.io/badge/MCP-1.0-blue)]()
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)]()

---

## Overview

The GBOGEB MCP Server bridges two engineering repositories through the [Model Context Protocol](https://modelcontextprotocol.io/), giving AI assistants unified access to:

- **Knowledge Topology** — 27+ nodes, 21+ edges mapping governance engines, CI/CD pipelines, lineage tracking, and visual assets across both repos
- **Engineering Data** — Cryogenic parameters (He-4 thermodynamics), heat load budgets, mass balance calculations for the ESS accelerator facility
- **Asset Lineage** — SHA256-tracked SVG diagrams (cryomodule schematics, facility layouts, P&ID, electrical distribution, thermal flow)
- **Physics Validation** — NIST polynomial-fit He-4 enthalpy/density/viscosity calculations with lambda-point phase detection

```
┌─────────────────────────────────────────────────────────┐
│                   MCP Client                            │
│          (Claude Desktop / VS Code / etc.)              │
└────────────────────┬────────────────────────────────────┘
                     │ stdio
┌────────────────────▼────────────────────────────────────┐
│              GBOGEB MCP Server                          │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐               │
│   │ topology │ │  tools   │ │  server  │               │
│   └────┬─────┘ └────┬─────┘ └────┬─────┘               │
│        │             │            │                     │
│   ┌────▼─────────────▼────────────▼─────┐               │
│   │      TopologyNavigator              │               │
│   │   (merged GBA + GBC graph)          │               │
│   └────┬────────────────────────┬───────┘               │
│        │                        │                       │
└────────┼────────────────────────┼───────────────────────┘
         │                        │
┌────────▼──────────┐  ┌──────────▼──────────┐
│  GBOGEB/ABACUS    │  │  GBOGEB/CODEX       │
│  (GBA)            │  │  (GBC)              │
│                   │  │                     │
│ • 20 topo nodes   │  │ • 7 topo nodes      │
│ • Governance      │  │ • SVG assets        │
│ • Physics engine  │  │ • Asset validator   │
│ • CI/CD pipelines │  │ • Lineage tracker   │
│ • Engineering     │  │ • Visual registry   │
│   data (YAML)     │  │                     │
└───────────────────┘  └─────────────────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Both repositories cloned:
  - `gbogeb_abacus` (GBA)
  - `gbogeb_codex` (GBC)

### Installation

```bash
# Install from source
cd gbogeb_mcp_server
pip install -e ".[dev]"

# Or install dependencies directly
pip install mcp pyyaml
```

### Run the Server

```bash
# Via entry point
gbogeb-mcp

# Or via Python module
python -m gbogeb_mcp.server

# With custom repo paths
GBOGEB_GBA_ROOT=/path/to/abacus GBOGEB_GBC_ROOT=/path/to/codex gbogeb-mcp
```

### Run Tests

```bash
cd gbogeb_mcp_server
PYTHONPATH=src pytest tests/ -v
```

---

## MCP Client Integration

### Claude Desktop

Add to `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "gbogeb": {
      "command": "python",
      "args": ["-m", "gbogeb_mcp.server"],
      "env": {
        "GBOGEB_GBA_ROOT": "/home/ubuntu/gbogeb_abacus",
        "GBOGEB_GBC_ROOT": "/home/ubuntu/gbogeb_codex",
        "PYTHONPATH": "/home/ubuntu/gbogeb_mcp_server/src"
      }
    }
  }
}
```

### VS Code MCP Extension

Add to `.vscode/settings.json`:

```json
{
  "mcp.servers": {
    "gbogeb": {
      "command": "python",
      "args": ["-m", "gbogeb_mcp.server"],
      "env": {
        "GBOGEB_GBA_ROOT": "${workspaceFolder}/../gbogeb_abacus",
        "GBOGEB_GBC_ROOT": "${workspaceFolder}/../gbogeb_codex",
        "PYTHONPATH": "${workspaceFolder}/src"
      }
    }
  }
}
```

### Generic MCP Config

The server configuration is also available at `~/.config/mcp/servers.json`.

---

## API Reference — 7 MCP Tools

### 1. `tool_get_topology()`

Returns the full merged knowledge topology across both repositories.

**Returns:** Statistics, all nodes (grouped by repo), all edges, cross-repo edges, category definitions, repository metadata.

**Example response structure:**
```json
{
  "statistics": {
    "total_nodes": 27,
    "total_edges": 21,
    "gba_nodes": 20,
    "gbc_nodes": 7,
    "cross_repo_edges": 9
  },
  "nodes": {"GBA": [...], "GBC": [...]},
  "edges": [...],
  "cross_repo_edges": [...],
  "categories": {"governance": {"color": "#6d28d9", "icon": "fa-shield-halved"}, ...}
}
```

### 2. `tool_query_node(node_id: str)`

Query detailed information about a specific topology node.

**Parameters:**
- `node_id` — Node identifier (e.g., `"GBA-GOV-001"`, `"GBC-ASSET-001"`)

**Returns:** Node metadata, file path/preview, upstream/downstream nodes, incoming/outgoing edges.

**Example:**
```
tool_query_node("GBA-GOV-001")
→ Render Rules Engine: governance node, outputs to GBA-GOV-002 and GBA-GOV-005
```

### 3. `tool_search_engineering_data(query: str)`

Full-text search across all engineering data in both repositories.

**Parameters:**
- `query` — Search term (e.g., `"cryomodule"`, `"heat load"`, `"SRF"`, `"valve"`)

**Searches:** Knowledge topology nodes, engineering_data.yaml, visual_data.yaml, stakeholder registry, lineage manifest.

**Returns:** Matches grouped by source with line numbers and content snippets.

### 4. `tool_get_asset_lineage(asset_id: str)`

Retrieve full lineage and provenance for a tracked visual asset.

**Parameters:**
- `asset_id` — Asset ID (e.g., `"GBC-ASSET-001"`) or filename (e.g., `"cryomodule_schematic.svg"`)

**Returns:** SHA256 hash, processing status, file existence, GBA consumers, visual registry metadata, topology connections.

### 5. `tool_validate_physics(data: dict | None = None)`

Run Helium-4 thermodynamic physics validation using the GBA HeliumPropertyEngine.

**Parameters:**
- `data` — Optional dict with keys: `temperature_K`, `pressure_bar`, `return_temperature_K`, `Q_static_W`, `Q_dynamic_W`

**Without arguments:** Validates the full `engineering_data.yaml` (enthalpy, mass balance, lambda-point).

**Example:**
```
tool_validate_physics({"temperature_K": 2.0, "Q_static_W": 24.5, "Q_dynamic_W": 47.8})
→ enthalpy, density, viscosity, phase detection, mass balance ṁ = Q/Δh
```

### 6. `tool_list_assets()`

List all tracked binary and SVG assets across both repositories.

**Returns:** Manifest assets (with SHA256 hashes), visual registry assets (with dimensions), SVG files on disk, counts and version info.

### 7. `tool_get_test_status()`

Run test suites for both GBA and GBC repositories and report results.

**Returns:** Per-repo pass/fail/error counts, individual test names and statuses, summary lines.

---

## Project Structure

```
gbogeb_mcp_server/
├── pyproject.toml              # Package metadata, deps, entry point
├── README.md                   # This file
├── src/
│   └── gbogeb_mcp/
│       ├── __init__.py         # Package version
│       ├── server.py           # FastMCP server + tool registrations
│       ├── tools.py            # 7 tool implementations
│       └── topology.py         # Knowledge graph navigator
└── tests/
    ├── __init__.py
    └── test_mcp_server.py      # 51 tests covering all tools
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GBOGEB_GBA_ROOT` | `/home/ubuntu/gbogeb_abacus` | Path to GBOGEB/ABACUS repo |
| `GBOGEB_GBC_ROOT` | `/home/ubuntu/gbogeb_codex` | Path to GBOGEB/CODEX repo |

## Knowledge Topology Categories

| Category | Color | Icon | Description |
|---|---|---|---|
| Governance | `#6d28d9` | 🛡️ | Render rules, linters, WCAG |
| Lineage | `#0891b2` | 🔗 | Asset tracking, SHA256 hashes |
| Theme | `#d946ef` | 🎨 | Design tokens, semantic themes |
| CI/CD | `#f59e0b` | ⚙️ | GitHub Actions pipelines |
| Web | `#10b981` | 🌐 | Hub landing pages, galleries |
| Example | `#3b82f6` | 🧪 | Demo SPAs, multi-view tools |
| Config | `#64748b` | 🎚️ | Tuning, topology, registries |
| Layout | `#ec4899` | 📊 | Grid blueprints, spacing |
| Asset | `#ef4444` | 📦 | Binary/SVG master assets |

---

## License

MIT — GBOGEB Engineering Team
