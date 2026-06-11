# Phase 1 — Consolidated TODO List
> Generated: 2026-05-12 | Source: backlog.json, SLIDE_PACKAGES_STATUS.md, code comments, VISUAL_CATALOG.md

---

## 🔴 CRITICAL Priority

| # | Category | Description | File Location | Status |
|---|----------|-------------|---------------|--------|
| C-1 | Build | ~~Fix version label in docs/index.html from v3.1.0 → v4.0.0~~ | `docs/index.html` | ✅ DONE (Phase 1) |
| C-2 | Build | ~~Fix stale 4-compressor references in index_v4_0.html~~ | `docs/index_v4_0.html` | ✅ DONE (Phase 1) |
| C-3 | Build | ~~Rebuild triage pages with v4.0.0 config~~ | `docs/*.html` | ✅ DONE (Phase 1) |
| C-4 | Build | ~~Fix stale motor power (400→315 kW) in compressor pages~~ | `docs/compressors/*.html`, `src/build_dense_slides.py` | ✅ DONE (Phase 1) |

## 🟡 HIGH Priority

| # | Category | Description | File Location | Status |
|---|----------|-------------|---------------|--------|
| H-1 | Code | Clarify HSD Twin Combi M=N+ specification (TASK-001) | `docs/compressors/HP_Redundancy_Analysis.html` | New |
| H-2 | Docs | Add deprecation banner to index_v3_1.html | `docs/index_v3_1.html` | New |
| H-3 | Build | ~~Unify fragmented build scripts into single entry point~~ | `build.sh`, `src/build_*.py` | ✅ DONE (Phase 1) |
| H-4 | Build | ~~Consolidate TODO lists from all sources~~ | This file | ✅ DONE (Phase 1) |
| H-5 | Docs | Add SSoT (config.yaml) reference to all generated pages | `src/build_*.py` generators | New |
| H-6 | Docs | Document derogation in SoR matrix | SoR matrix | New |
| H-7 | Build | ~~Update version labels in heroes/*.html from v2.1.0 → v4.0.0~~ | `docs/heroes/*.html` | ✅ DONE (Phase 1) |

## 🟢 MEDIUM Priority

| # | Category | Description | File Location | Status |
|---|----------|-------------|---------------|--------|
| M-1 | Code | Review energy cost €0.15/kWh accuracy (TASK-003) | `src/compressor_reliability.py`, `data/config.yaml` | New |
| M-2 | Docs | Regenerate heroes/*.html with v4.0 data or mark as "v3.0 reference" | `docs/heroes/*.html` | New |
| M-3 | Build | Add `<meta name="dashboard-version" content="4.0.0">` to all HTML | All generators | New |
| M-4 | Build | CI/CD integration — version consistency check after each build | `.github/workflows/` | New |
| M-5 | Docs | Add SSoT annotation footer to STAKEHOLDER_PRESENTATION.html | `docs/STAKEHOLDER_PRESENTATION.html` | New |

## 🔵 LOW Priority

| # | Category | Description | File Location | Status |
|---|----------|-------------|---------------|--------|
| L-1 | Code | Add dynamic simulation of WCS scenarios (TASK-004) | `src/wcs_scenarios.py` | New |
| L-2 | Code | Create mobile-responsive CSS for charts (TASK-005) | `docs/`, `assets/` | New |
| L-3 | Docs | Overlay plots with isolines (Charts 1-3) | `src/generate_visuals_v3.py` | New |
| L-4 | Docs | Secondary axis plots (Charts 4-5) | `src/generate_visuals_v3.py` | New |
| L-5 | Docs | Material-specific comparisons (Charts 6-9) | `src/generate_visuals_v3.py` | New |
| L-6 | Docs | Operating condition matrices (Charts 10-13) | `src/generate_visuals_v3.py` | New |
| L-7 | Docs | Enhanced cost analysis (Charts 14-18) | `src/generate_visuals_v3.py` | New |
| L-8 | Code | Interactive Valve Selector (select valve → see all impacts) | Future feature | New |
| L-9 | Code | Scenario Builder (define conditions → get recommendation) | Future feature | New |
| L-10 | Code | Cost Optimizer (find optimal valve mix for budget) | Future feature | New |
| L-11 | Code | Risk Explorer (adjust MTBF/MTTR/He price → see cost distribution) | Future feature | New |
| L-12 | Docs | Delete or archive docs/presentation.html (v2.5.0 artifact) | `docs/presentation.html` | New |
| L-13 | Build | Automate STAKEHOLDER_PRESENTATION generation from config.yaml | `src/build_stakeholder.py` (new) | New |

---

## Summary

| Priority | Total | Done | Remaining |
|----------|-------|------|-----------|
| 🔴 CRITICAL | 4 | 4 | 0 |
| 🟡 HIGH | 7 | 3 | 4 |
| 🟢 MEDIUM | 5 | 0 | 5 |
| 🔵 LOW | 13 | 0 | 13 |
| **TOTAL** | **29** | **7** | **22** |

## Sources Consolidated
1. `docs/backlog.json` — 7 tasks (3 DONE, 4 open)
2. `SLIDE_PACKAGES_STATUS.md` — 12 action items
3. `VISUAL_CATALOG.md` — 9 enhancement items
4. Code comments (`TODO`/`FIXME`) — 3 items (SoR matrix refs)
5. Phase 1 analysis findings — direct observation
