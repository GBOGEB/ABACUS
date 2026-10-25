# CODEX_BRIDGE.md — CODEX↔ABACUS Bridge Architecture

> **Version:** 1.0.0  
> **Purpose:** Documents the relationship and data flow between GBOGEB/CODEX and GBOGEB/ABACUS

---

## Overview

The GBOGEB system operates as a **two-repository architecture**:

| Repository | Role | Contents |
|------------|------|----------|
| **GBOGEB/CODEX** | Design & Theme Blueprint | Visual themes, interface designs, canonical source content |
| **GBOGEB/ABACUS** | Governance & Processing Engine | Validation, lineage tracking, YAML compliance, rendering |

The bridge between them operates through the `Input_Master/` folder with `.mock` sidecar files providing immutable metadata.

---

## Data Flow

```
GBOGEB/CODEX                        GBOGEB/ABACUS
┌──────────────┐                    ┌──────────────────────┐
│ themes/      │                    │ Input_Master/        │
│ designs/     │── binary export ──▶│   ├── asset.pptx     │
│ content/     │                    │   └── asset.pptx.mock│
│ layouts/     │                    │                      │
└──────────────┘                    │ engines/             │
                                    │   ├── verification   │
       ▲                            │   ├── linting        │
       │                            │   ├── contrast check │
       │                            │   └── lineage track  │
       │                            │                      │
       │  canonical source ref      │ _data/               │
       └────────────────────────────│   └── manifest.json  │
                                    │                      │
                                    │ _site/ (generated)   │
                                    │   └── HTML output    │
                                    └──────────────────────┘
```

## Bridge Protocol

### Step 1: Asset Export (CODEX → ABACUS)
1. Designer creates or updates content in CODEX
2. Binary exports (PPTX, PDF, images) are placed in `Input_Master/`
3. No manual editing of exported files is permitted

### Step 2: Verification (ABACUS Input Gate)
1. `verification_hook.py` processes each binary file
2. SHA256 hash computed and stored in `.mock` sidecar
3. `lineage_manifest.json` updated with asset metadata
4. `.mock` files are committed; binaries are `.gitignored`

### Step 3: Governance Validation (ABACUS Engines)
1. `RENDER_LINTER.py` validates content structure
2. `WCAG_CONTRAST_CHECKER.py` ensures accessibility compliance
3. `SLIDE_ID_ENFORCER.py` verifies deterministic identifiers
4. All results must pass before rendering proceeds

### Step 4: Rendering (ABACUS Output)
1. Jekyll processes validated content with semantic themes
2. HTML-first output generated using `_layouts/` templates
3. Lineage records created linking output to source
4. Generated outputs carry lineage metadata

### Step 5: Lineage Closure
1. Every output is traceable back to its CODEX source
2. `derived_from` field points to CODEX repository path
3. `render_commit` pins the exact ABACUS engine state

---

## Core Principle

> **"Generated outputs are NEVER canonical."**

This means:
- PPT files exported from CODEX are **source artifacts**, not editable outputs
- HTML rendered by ABACUS is a **derived output**, not a source of truth
- Any modification to generated files creates a **lineage violation**
- The only way to change output is to update CODEX source and re-render

---

## Cross-Repository Dependencies

| ABACUS Component | CODEX Dependency | Sync Method |
|-----------------|------------------|-------------|
| `SEMANTIC_THEME.yaml` | `themes/` | Manual sync on theme update |
| `LAYOUT_CONTRACTS.yaml` | `layouts/` | Version-pinned reference |
| `Input_Master/*.mock` | Binary exports | Verification hook |
| `lineage_manifest.json` | All assets | Automated tracking |

## Bridge Integrity Checks

- **Hash verification**: SHA256 of Input_Master/ files must match .mock records
- **Manifest completeness**: Every .mock file must have a manifest entry
- **Lineage chain**: Every output must trace to a CODEX source path
- **Version pinning**: ABACUS render_commit is recorded for reproducibility
