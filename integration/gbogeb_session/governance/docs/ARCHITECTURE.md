# ARCHITECTURE.md — System Architecture Overview

> **Version:** 1.0.0  
> **System:** GBOGEB/ABACUS — Deterministic Engineering Publication Compiler

---

## System Overview

GBOGEB/ABACUS is a **governed publishing platform** that transforms design blueprints into deterministic, accessible, and traceable engineering publications. It operates across three parallel domains:

1. **Rendering Engine** — Constraint-driven layout, typography, and theme application
2. **Publication Governance** — Linting, contrast checking, and compliance validation
3. **Knowledge Lineage System** — Immutable traceability from source to output

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      GBOGEB/CODEX                           │
│               (Design & Theme Blueprint)                    │
│                                                             │
│  themes/  │  designs/  │  content/  │  layouts/             │
└─────────────────────┬───────────────────────────────────────┘
                      │ Binary Export
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                     GBOGEB/ABACUS                           │
│              (Governance & Processing Engine)                │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ Input Gate   │    │  A6 Engines  │    │ Jekyll Build │  │
│  │              │    │              │    │              │  │
│  │ Input_Master/│───▶│ Linter       │───▶│ _layouts/    │  │
│  │ .mock files  │    │ Contrast     │    │ _includes/   │  │
│  │ Verification │    │ Slide ID     │    │ assets/      │  │
│  │ Hook         │    │ Lineage      │    │              │  │
│  └──────────────┘    └──────────────┘    └──────┬───────┘  │
│                                                  │          │
│  ┌──────────────┐    ┌──────────────┐           │          │
│  │ _data/       │    │ config/      │           │          │
│  │ manifest.json│    │ schemas      │           ▼          │
│  │              │    │ contracts    │    ┌──────────────┐  │
│  └──────────────┘    └──────────────┘    │ _site/       │  │
│                                          │ (HTML output)│  │
│  ┌──────────────┐    ┌──────────────┐    └──────────────┘  │
│  │ .github/     │    │ tests/       │                      │
│  │ workflows    │    │ unit + integ │                      │
│  │ PR templates │    │              │                      │
│  └──────────────┘    └──────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

---

## A6 Subsystems

### A6-1: Semantic Layout Engine
- **File:** `LAYOUT_CONTRACTS.yaml`
- **Purpose:** Constraint-driven visual layout with deterministic spacing
- **Enforces:** Grid system, spacing scale, overflow prevention, slide templates

### A6-2: Typography Engine
- **Files:** `LAYOUT_CONTRACTS.yaml` (typography section)
- **Purpose:** Heading hierarchy enforcement, modular type scale (1.25 Major Third)
- **Enforces:** Font sizes, line heights, sequential heading levels

### A6-3: Contrast Governance Engine
- **Files:** `SEMANTIC_THEME.yaml`, `WCAG_CONTRAST_CHECKER.py`
- **Purpose:** WCAG AA compliance via semantic color tokens
- **Enforces:** 4.5:1 text contrast, 3:1 large text/UI components, theme switching

### A6-4: Lineage Engine
- **Files:** `LINEAGE_SCHEMA.yaml`, `verification_hook.py`, `SLIDE_ID_ENFORCER.py`
- **Purpose:** Immutable traceability from source to output
- **Enforces:** SHA256 hashing, .mock sidecars, slide_id format, manifest integrity

### A6-5: Renderer Linting
- **File:** `RENDER_LINTER.py`
- **Purpose:** ESLint-style rule enforcement for engineering decks
- **Rules:** no_overflow, no_low_contrast, no_orphan_bullets, stable_heading_hierarchy, figure_reference_required, speaker_notes_required, semantic_card_required

### A6-6: Figure Registry Browser
- **Purpose:** Knowledge graph publication with cross-referenced figures
- **Enforces:** Figure IDs, captions, alt text, bidirectional text references

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Governance Engines | Python 3.11+ | Linting, validation, verification |
| Configuration | YAML 1.2 | Schemas, contracts, themes |
| Rendering | Jekyll 4.x | HTML-first semantic output |
| Styling | CSS Custom Properties | Semantic token-based theming |
| CI/CD | GitHub Actions | Automated validation pipeline |
| Hashing | SHA256 | Immutable asset fingerprinting |
| Data | JSON | Lineage manifest, .mock sidecars |

---

## File System Layout

```
gbogeb_abacus/
├── Input_Master/           # Binary asset ingestion point
│   ├── *.pptx/.pdf/.png   # Binary assets (.gitignored)
│   └── *.mock              # Immutable sidecar metadata (tracked)
├── _data/
│   └── lineage_manifest.json  # Central lineage registry
├── engines/                # A6 governance subsystems
│   ├── RENDER_RULES.md     # Comprehensive governance rules
│   ├── SEMANTIC_THEME.yaml # Light/dark/high-contrast tokens
│   ├── LAYOUT_CONTRACTS.yaml # Spacing, grid, typography
│   ├── RENDER_LINTER.py    # ESLint-style content linter
│   ├── LINEAGE_SCHEMA.yaml # Traceability schema
│   ├── WCAG_CONTRAST_CHECKER.py # Contrast validation
│   ├── SLIDE_ID_ENFORCER.py # Slide ID format checker
│   ├── RENDER_TEST_SUITE.md # Test scenarios
│   └── verification_hook.py # Asset verification pipeline
├── config/                 # YAML schemas and contracts
├── docs/                   # Architecture documentation
├── _layouts/               # Jekyll HTML templates
├── _includes/              # Jekyll reusable components
├── assets/                 # CSS, JS, static assets
├── tests/                  # Automated test suites
├── .github/
│   ├── workflows/          # CI/CD automation
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── CODEOWNERS
├── _config.yml             # Jekyll configuration
├── Gemfile                 # Ruby dependencies
└── README.md               # Project documentation
```

---

## Security and Integrity Model

1. **Source Authority**: CODEX is the single source of truth
2. **Hash Verification**: Every binary asset is SHA256-fingerprinted
3. **Immutable Metadata**: .mock sidecar files are never edited manually
4. **Commit Pinning**: render_commit traces exact engine state
5. **Code Review**: CODEOWNERS enforces review requirements
6. **CI/CD Gates**: All governance checks must pass before merge
