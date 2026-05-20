# Multi-View Engineering Tool Generator

> GBOGEB/ABACUS integrated example — cryogenic accelerator engineering workflows

## Overview

A comprehensive **Single Page Application (SPA)** demonstrating how GBOGEB/ABACUS governance
engines drive a real-world engineering workspace. Edit YAML data on the left; watch HMI dashboards,
presentations, and technical reports update in real-time on the right.

### Features

| Feature | Description |
|---------|-------------|
| **Split-pane interface** | Resizable left (code) / right (render) panels |
| **Live YAML→render pipeline** | Edit SSOT YAML, all views update instantly (300ms debounce) |
| **3 themes** | `userstyle` (clean light), `corporate` (purple accent), `focus` (high-contrast dark) |
| **Interactive Plotly graphs** | Heat load distribution bar chart with theme-aware colors |
| **Inline SVG diagrams** | P&ID schematic: cryomodule → valve → heat exchanger, data-bound |
| **HMI Dashboard** | Metric cards, component status, real-time indicators |
| **Marp Presentation** | 6-slide design review, auto-generated from YAML |
| **Technical Report** | Full document with tables, equations, flowcharts |
| **Physics Validator** | Python engine: NIST polynomials, lambda-point, mass balance |
| **GBOGEB/ABACUS hooks** | `verification_hook`, `SEMANTIC_THEME`, `RENDER_RULES` integration |

## Directory Structure

```
examples/multi_view_workspace/
├── README.md                              ← this file
├── output/
│   ├── context/
│   │   ├── engineering_data.yaml          ← SSOT configuration
│   │   └── physics_validator.py           ← Helium-4 property engine
│   └── documents/
│       ├── index.html                     ← main SPA
│       ├── main_html_plaintext.txt        ← LLM-optimized transfer format
│       ├── report.md                      ← technical report (Markdown)
│       └── report.pdf                     ← generated PDF (via WeasyPrint)
└── scripts/
    └── generate_pdf.py                    ← PDF generation script
```

## Quick Start

### 1. View the SPA

Open `output/documents/index.html` in any modern browser — no server required.

### 2. Run the Physics Validator

```bash
cd output/context
python3 physics_validator.py
```

Expected output:
```
══ Overall: PASS ══
```

### 3. Generate PDF Report

```bash
pip install weasyprint markdown pyyaml

# Default (userstyle theme)
python3 scripts/generate_pdf.py

# Corporate theme
python3 scripts/generate_pdf.py --theme corporate

# Focus (dark) theme
python3 scripts/generate_pdf.py --theme focus
```

## Engineering Domain

- **Facility:** European Spallation Source — Cryogenic Distribution
- **Coolant:** Helium-4 (He-II superfluid at 2.0 K)
- **Key equation:** `ṁ = (Q_static + Q_dynamic) / Δh`
- **Topology:** Cryomodule (CM-01) → Control Valve (CV-01) → Heat Exchanger (HX-01)

## GBOGEB/ABACUS Integration

This example demonstrates integration with the core governance engines:

- **`verification_hook`** — validates YAML schema integrity
- **`SEMANTIC_THEME`** — CSS custom property tokens (`--color-primary`, etc.)
- **`RENDER_RULES`** — figure prefixes, equation numbering, cross-ref validation

## License

Part of the GBOGEB/ABACUS repository. See root `LICENSE` for terms.
