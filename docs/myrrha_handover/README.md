# MYRRHA Warm Compressor Engineering Handover · v0.4.7

A self-contained HTML ecosystem for the **MYRRHA QPLANT Warm Compressor Station (WCS)** — comparing ALaT FSD 575 SFC vs LKT FSD 475 SFC compressor configurations.

> **Project:** C1393 – MYRRHA · SCK-CEN/CEA  
> **Scope:** Warm-end compressor pre-study comparison, technical requirements, vendor datasheets, and engineering decision support  
> **Status:** 96 % complete — production-ready handover package

---

## Quick Start

Open **`index.html`** in any modern browser. No build step, no server required.

> **Note:** An internet connection is required for views that load libraries from CDNs (Chart.js, Plotly, MathJax, etc. via `cdn.jsdelivr.net` and similar). Opening the package offline will work for most static views, but charts and equations may not render without network access.

```bash
cd myrrha_handover
python3 -m http.server 8000
# open http://localhost:8000/
```

## Package Contents

### Core Views (46 HTML files)

| File | Purpose |
|------|---------|
| `index.html` | **Entry point.** Hub with navigation, version control, headline numbers |
| `slides.html` | Interactive slide deck (← / → arrows, F = fullscreen) |
| `reports.html` | Rendered markdown reports labelled **B1–B4** |
| `tables.html` | Copyable tables with CSV / JSON export, sort, filter |
| `graphs.html` | Chart.js graphs with PNG / SVG / PDF export and zoom/pan |
| `status.html` | Progress bar, TODOs, completed items, summary tuple |
| `truth.html` | Immutable design decisions (locked parameters) |
| `utilities.html` | Math / equations / sample calcs (electricity, PCW, RCW) |
| `vendor-kaeser.html` | Kaeser compressor vendor comparison tables |
| `mt-11-kaeser-technical-requirements.html` | MT-11 Kaeser technical requirements |
| `mt-12-pvps-technical-requirements.html` | MT-12 PVPs technical requirements |
| `mt-13-report.html` | MT-13 comprehensive report |
| `hx-sizing.html` | Heat exchanger sizing calculations |
| `thermo-analysis.html` | Thermodynamic analysis |
| `operations.html` | Operations overview |
| `handover.html` | Handover checklist |

### Quality & Review

| File | Purpose |
|------|---------|
| `qa-interactive.html` | Interactive QA dashboard |
| `qa-checklist.html` | QA checklist |
| `qa-test-suite.html` | Test suite results |
| `review-dmaic.html` | DMAIC review |
| `bt-ranking.html` | Bayesian truth ranking |
| `bt-scatter.html` | Bayesian truth scatter plots |
| `bt-validation.html` | Bayesian truth validation |
| `bt-artifacts.html` | Bayesian truth artefacts |
| `action-tracker.html` | Action item tracker |
| `accessibility-audit-report.html` | Accessibility audit |
| `responsive-review.html` | Responsive design review |

### Supporting Assets

| Directory | Contents |
|-----------|----------|
| `assets/` | Shared CSS (`style.css`) and JS (`common.js`) |
| `master/` | Source-of-truth config, data, and render scripts |
| `docs/` | Design guide, editing guide, slide notes |
| `slides/` | Individual slide HTML fragments |

## Navigation

Every page shares a consistent top bar:
- **Brand + version** (left)
- **Nav links** (centre/right)
- **Theme selector** ☀ Light / ☾ Dark
- **Font selector** Aptos (body) / Consolas (mono)

## Data Sources

All data sourced from:
- ALaT pre-study (C1393) & Kaeser FSD 575 SFC datasheet
- LKT pre-study & Kaeser FSD 475 SFC datasheet
- MYRRHA warm-compressor comparison notes

See `truth.html` → "Source documents" for exact section references.

## Key Technical Comparisons

| Parameter | ALaT FSD 575 SFC | LKT FSD 475 SFC |
|-----------|-------------------|-------------------|
| Reference config | 2 units @ 72 Hz → ~220 g/s | 3 units @ ~57 Hz → 264 g/s nominal |
| Per-skid flow | 112.54 g/s @ 72 Hz | 88 g/s nominal / 96.1 g/s max |
| Discharge pressure | 15 barA | 15 barA |
| Motor rated power | 315 kW | 250 kW |
| Package power (water-cooled) | 348.54 kW | 266 kW nom / 289 kW max |

## Features

- ✅ Mobile-optimised, responsive layout
- ✅ WCAG 2.1 AA accessible
- ✅ British English throughout
- ✅ Light/dark theme support
- ✅ CSV/JSON data export
- ✅ Interactive charts with zoom/pan
- ✅ Cross-referenced source documents
- ⚠️ Internet connection required for CDN-served libraries (Chart.js, Plotly, MathJax)

## Version History

See [`CHANGELOG.md`](CHANGELOG.md) for full version history.

## Licence

Internal SCK-CEN/CEA engineering documentation. All rights reserved.
