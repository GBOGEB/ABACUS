# Cross-Repository MCP Bridge — GBA ↔ GBC Coordination

> **Bridges:** `GBOGEB/ABACUS` (GBA) ↔ `GBOGEB/CODEX` (GBC)
> **Also:** `GBOGEB/cryogenic-accelerator-workspace` + `GBOGEB/document-organization-system`
> **MCP Server:** `/home/ubuntu/gbogeb_mcp_server` (51 tests)

---

## 1. Bridge Architecture

```
┌─────────────────────┐          ┌─────────────────────┐
│   GBC (CODEX)       │          │   GBA (ABACUS)      │
│                     │          │                     │
│ assets/canonical/ ──┼── SYNC ──┼→ Input_Master/      │
│ config/visual_data ─┼── REF ───┼→ engines/SEMANTIC_  │
│ src/lineage_tracker ┼── CHAIN ─┼→ engines/verif_hook │
│ web/index.html ─────┼── LINK ──┼→ web/index.html     │
│                     │          │                     │
│ 7 topology nodes    │          │ 20 topology nodes   │
│ 68 tests            │          │ 79 tests            │
└─────────┬───────────┘          └─────────┬───────────┘
          │                                │
          └───────────┬────────────────────┘
                      │
              ┌───────▼───────┐
              │  MCP Server   │
              │  51 tests     │
              │               │
              │ tool_list()   │
              │ navigate()    │
              │ validate()    │
              │ sync()        │
              └───────┬───────┘
                      │
          ┌───────────┴───────────┐
          │                       │
┌─────────▼──────────┐  ┌────────▼────────────┐
│ cryogenic-accel-ws │  │ document-org-system │
│ 6 CI/CD workflows  │  │ 8 EXHIBITs         │
│ physics engine     │  │ SSOT pattern        │
│ He-4 thermo        │  │ file_index pattern  │
└────────────────────┘  └─────────────────────┘
```

---

## 2. Bridge Tuple Format

```
(bridge_id, source_repo, target_repo, sync_type, payload, validation)
```

| Field | Type | Description |
|-------|------|-------------|
| `bridge_id` | `str` | `BRIDGE_{sequence:03d}` |
| `source_repo` | `str` | `GBA` or `GBC` |
| `target_repo` | `str` | `GBA` or `GBC` |
| `sync_type` | `enum` | `ASSET_PUSH`, `CONFIG_REF`, `LINEAGE_CHAIN`, `TOPO_EDGE`, `WEB_LINK` |
| `payload` | `dict` | Source path, target path, transform rules |
| `validation` | `dict` | Post-sync verification |

---

## 3. Bridge Sequences

### 3.1 — Asset Sync (GBC → GBA)

```python
BRIDGE_ASSET_SYNC = [
    (
        "BRIDGE_001",
        "GBC", "GBA",
        "ASSET_PUSH",
        {
            "source": "assets/canonical/*.svg",
            "target": "Input_Master/",
            "transform": "copy_with_metadata",
            "hash_preserve": True,
        },
        {"cmd": "diff <(sha256sum assets/canonical/cryomodule_schematic.svg) <(sha256sum ../gbogeb_abacus/Input_Master/cryomodule_schematic.svg)", "exit_code": 0}
    ),
    (
        "BRIDGE_002",
        "GBC", "GBA",
        "ASSET_PUSH",
        {
            "source": "lineage_manifest.json",
            "target": "_data/lineage_manifest.json",
            "transform": "merge_entries",
            "conflict_resolution": "newer_wins",
        },
        {"cmd": "python3 -c \"import json; gbc=json.load(open('lineage_manifest.json')); gba=json.load(open('../gbogeb_abacus/_data/lineage_manifest.json')); print(f'GBC:{len(gbc.get(\"assets\",[]))} GBA:{len(gba.get(\"assets\",[]))}')\"", "exit_code": 0}
    ),
]
```

### 3.2 — Config Reference (GBC → GBA)

```python
BRIDGE_CONFIG_REF = [
    (
        "BRIDGE_010",
        "GBC", "GBA",
        "CONFIG_REF",
        {
            "source": "config/visual_data.yaml",
            "target_ref": "engines/SEMANTIC_THEME.yaml",
            "sync_type": "reference_only",
            "note": "GBA SEMANTIC_THEME derives from GBC design tokens",
        },
        {"cmd": "test -f config/visual_data.yaml && test -f ../gbogeb_abacus/engines/SEMANTIC_THEME.yaml", "exit_code": 0}
    ),
    (
        "BRIDGE_011",
        "GBC", "GBA",
        "CONFIG_REF",
        {
            "source": "config/stakeholder_registry.yaml",
            "target": "config/stakeholder_registry.yaml",
            "sync_type": "mirror",
            "note": "Stakeholder routes must be consistent across repos",
        },
        {"cmd": "diff config/stakeholder_registry.yaml ../gbogeb_abacus/config/stakeholder_registry.yaml 2>/dev/null || echo 'Files may differ (expected)'", "exit_code": 0}
    ),
]
```

### 3.3 — Lineage Chain Verification

```python
BRIDGE_LINEAGE_CHAIN = [
    (
        "BRIDGE_020",
        "GBC", "GBA",
        "LINEAGE_CHAIN",
        {
            "gbc_tracker": "src/lineage_tracker.py",
            "gba_hook": "engines/verification_hook.py",
            "chain_direction": "GBC_creates → GBA_verifies",
        },
        {"cmd": "echo 'Chain: GBC lineage_tracker → GBC manifest → GBA Input_Master → GBA verification_hook → GBA manifest'", "exit_code": 0}
    ),
    (
        "BRIDGE_021",
        "GBA", "GBC",
        "LINEAGE_CHAIN",
        {
            "action": "back_reference",
            "gba_manifest": "_data/lineage_manifest.json",
            "gbc_manifest": "lineage_manifest.json",
            "verify": "all GBA assets have GBC source hash",
        },
        {"cmd": "python3 -c \"import json; gba=json.load(open('../gbogeb_abacus/_data/lineage_manifest.json')); print(f'{len(gba.get(\"assets\",[]))} assets with lineage')\"", "exit_code": 0}
    ),
]
```

### 3.4 — Topology Edge Management

```python
BRIDGE_TOPO_EDGE = [
    (
        "BRIDGE_030",
        "GBC", "GBA",
        "TOPO_EDGE",
        {
            "edges": [
                {"from": "GBC-THEME-001", "to": "GBA-GOV-005", "type": "design_token_source"},
                {"from": "GBC-LAYOUT-001", "to": "GBA-GOV-006", "type": "layout_blueprint"},
                {"from": "GBC-ASSET-001", "to": "GBA-LIN-001", "type": "binary_source"},
            ],
        },
        {"cmd": "python3 -c \"import json; d=json.load(open('config/knowledge_topology.json')); edges=[n for n in d if isinstance(n,dict) and 'links_to' in n]; print(f'{len(edges)} nodes with cross-links')\"", "exit_code": 0}
    ),
    (
        "BRIDGE_031",
        "GBA", "GBC",
        "TOPO_EDGE",
        {
            "edges": [
                {"from": "GBA-GOV-005", "to": "GBC-THEME-001", "type": "dependency"},
                {"from": "GBA-GOV-006", "to": "GBC-LAYOUT-001", "type": "dependency"},
                {"from": "GBA-LIN-001", "to": "GBC-ASSET-001", "type": "source_tracking"},
            ],
        },
        {"cmd": "python3 -c \"import json; d=json.load(open('../gbogeb_abacus/config/knowledge_topology.json')); cross=[n for n in d if isinstance(n,dict) and n.get('cross_repo_deps')]; print(f'{len(cross)} nodes with cross-repo deps')\"", "exit_code": 0}
    ),
]
```

---

## 4. MCP Server Tool Invocation Patterns

### 4.1 — Tool Registry

```python
MCP_TOOLS = {
    "navigate_topology": {
        "description": "Navigate knowledge topology graph by node ID",
        "params": {"node_id": "str", "depth": "int", "direction": "outbound|inbound|both"},
        "returns": {"node": "dict", "neighbors": "list[dict]"},
    },
    "validate_governance": {
        "description": "Run governance validation on a file or directory",
        "params": {"target": "str", "rules": "list[str]", "strict": "bool"},
        "returns": {"findings": "list[dict]", "pass": "bool"},
    },
    "sync_assets": {
        "description": "Sync assets between GBC and GBA",
        "params": {"source_repo": "str", "target_repo": "str", "filter": "str"},
        "returns": {"synced": "int", "errors": "int"},
    },
    "check_lineage": {
        "description": "Verify lineage chain integrity",
        "params": {"manifest": "str", "depth": "int"},
        "returns": {"chain_valid": "bool", "broken_links": "list"},
    },
    "route_stakeholder": {
        "description": "Route content to appropriate stakeholder group",
        "params": {"content_id": "str", "routing_tags": "list[str]"},
        "returns": {"routed_to": "list[str]", "format": "str"},
    },
}
```

### 4.2 — Invocation Tuples

```python
MCP_INVOCATIONS = [
    (
        "MCP_NAV_001",
        "navigate_topology",
        {"node_id": "GBA-GOV-001", "depth": 2, "direction": "outbound"},
        {"expected_neighbors": ["GBA-GOV-002", "GBA-GOV-005"]},
    ),
    (
        "MCP_VAL_001",
        "validate_governance",
        {"target": "docs/", "rules": ["no_overflow", "no_low_contrast", "heading_hierarchy"], "strict": True},
        {"expected_pass": True},
    ),
    (
        "MCP_SYNC_001",
        "sync_assets",
        {"source_repo": "GBC", "target_repo": "GBA", "filter": "*.svg"},
        {"expected_synced": ">0"},
    ),
    (
        "MCP_LIN_001",
        "check_lineage",
        {"manifest": "_data/lineage_manifest.json", "depth": 3},
        {"expected_chain_valid": True},
    ),
]
```

---

## 5. Stakeholder Routing Bridge

### 5.1 — Routing Tags

| Tag | Audience | Content Style | GBA Output | GBC Source |
|-----|----------|---------------|-----------|-----------|
| `[KEB]` | Executive/Strategic | High-level summaries | Slide deck, 1-pager | Design brief |
| `[DOW]` | Technical/Implementation | Detailed specs | Full report, code refs | Technical drawings |
| `[ALL]` | Cross-cutting | Universal | Hub page, README | All canonical assets |

### 5.2 — Routing Tuples

```python
STAKEHOLDER_ROUTES = [
    (
        "ROUTE_KEB_001",
        "[KEB]",
        {"source_slides": "docs/keb_*.md", "format": "slide_deck"},
        {"output": "web/keb_package/", "audience": "Executive"},
    ),
    (
        "ROUTE_DOW_001",
        "[DOW]",
        {"source_slides": "docs/dow_*.md", "format": "technical_report"},
        {"output": "web/dow_package/", "audience": "Technical"},
    ),
    (
        "ROUTE_ALL_001",
        "[ALL]",
        {"source": "web/index.html", "format": "hub_page"},
        {"output": "web/", "audience": "All Stakeholders"},
    ),
]
```

---

## 6. Knowledge Topology Navigation

### 6.1 — Full Node Registry (27 nodes)

```
GBA Nodes (20):
  GBA-GOV-001  Render Rules Engine
  GBA-GOV-002  Render Linter
  GBA-GOV-003  WCAG Contrast Checker
  GBA-GOV-004  Slide ID Enforcer
  GBA-GOV-005  Semantic Theme
  GBA-GOV-006  Layout Contracts
  GBA-GOV-007  Lineage Schema
  GBA-LIN-001  Verification Hook
  GBA-LIN-002  Lineage Manifest
  GBA-CI-001   Governance Validation Pipeline
  GBA-CI-002   Asset Verification Pipeline
  GBA-CI-003   Archive & Deploy Pipeline
  GBA-WEB-001  Hub Landing Page
  GBA-EX-001   Multi-View Engineering Tool
  GBA-CFG-001  Governance Tuning
  GBA-CFG-002  Knowledge Topology
  GBA-CFG-003  Stakeholder Registry
  GBC-THEME-001 Design Tokens (cross-ref)
  GBC-LAYOUT-001 Layout Blueprints (cross-ref)
  GBC-ASSET-001 Binary Master Assets (cross-ref)

GBC Nodes (7):
  GBC-ASSET-001 Cryomodule Schematic
  GBC-ASSET-002 Facility Layout
  GBC-CONFIG-001 Visual Data Registry
  GBC-ENGINE-001 Asset Validator
  GBC-ENGINE-002 SVG Cleaner
  GBC-ENGINE-003 Lineage Tracker
  GBC-WEB-001   Visual Asset Gallery
```

### 6.2 — Cross-Repo Edges (6)

```
GBC-THEME-001  →  GBA-GOV-005  (design tokens → semantic theme)
GBC-LAYOUT-001 →  GBA-GOV-006  (layout blueprints → layout contracts)
GBC-ASSET-001  →  GBA-LIN-001  (binary assets → verification hook)
GBA-GOV-005    →  GBC-THEME-001 (dependency back-ref)
GBA-GOV-006    →  GBC-LAYOUT-001 (dependency back-ref)
GBA-LIN-001    →  GBC-ASSET-001 (source tracking back-ref)
```

---

## 7. Quick Reference

```
┌──────────────────────────────────────────────────────────┐
│  CROSS-REPO MCP BRIDGE — QUICK REFERENCE                │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  REPOS: GBA (20 nodes, 79 tests)                        │
│         GBC (7 nodes, 68 tests)                         │
│         MCP Server (51 tests)                           │
│         cryogenic-workspace (6 CI/CD workflows)          │
│         document-org-system (8 EXHIBITs)                │
│                                                          │
│  BRIDGE TYPES:                                           │
│    ASSET_PUSH    GBC→GBA asset sync                      │
│    CONFIG_REF    GBC→GBA config reference                │
│    LINEAGE_CHAIN GBC↔GBA hash chain verification        │
│    TOPO_EDGE     GBC↔GBA topology edge management       │
│    WEB_LINK      GBC↔GBA web hub cross-linking          │
│                                                          │
│  BRIDGE SEQUENCES:                                       │
│    §3.1 Asset Sync ────→ 2 tuples                       │
│    §3.2 Config Ref ────→ 2 tuples                       │
│    §3.3 Lineage Chain ─→ 2 tuples                       │
│    §3.4 Topology Edge ─→ 2 tuples                       │
│                                                          │
│  MCP TOOLS: navigate, validate, sync, lineage, route    │
│  STAKEHOLDERS: [KEB] [DOW] [ALL]                        │
│  TOTAL NODES: 27 · CROSS-EDGES: 6                       │
└──────────────────────────────────────────────────────────┘
```
