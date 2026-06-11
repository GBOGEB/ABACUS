# Phase 1 — Configuration Validation Report

## Config.yaml Key Parameters (SSOT)
| Parameter | Value | Status |
|-----------|-------|--------|
| HP Compressors | 3 (FSD575 SFC) | ✅ |
| Motor Power | 315 kW | ✅ |
| Package Power | 348.54 kW | ✅ |
| Per-unit Flow | 112.54 g/s @ 72 Hz | ✅ |
| 3-skid Max Flow | 337.62 g/s | ✅ |
| Compressor CAPEX | €600,000 (3 × €200k) | ✅ |
| Total CAPEX | €1,420,000 | ✅ |
| HP Outlet Pressure | 14 barg nominal | ✅ |
| HCC Inlet | 1050 mbar | ✅ |
| VLP Suction | 400 mbar nominal | ✅ |

## Files Fixed (Stale Config Values)
| File | Issue | Fix |
|------|-------|-----|
| `docs/index_v4_0.html:472` | "4× with VFD" | → "3× with VFD" |
| `docs/index_v4_0.html:544` | "~400 kW" motor power | → "315 kW" |
| `docs/index_v4_0.html:632` | Old 4-unit comparison row | Removed (superseded) |
| `docs/index_v4_0.html:633` | Highlighted row had 4×50%, €820k | → 3×50%, €600k |
| `docs/compressors/HP_Redundancy_Analysis.html:111` | "FSD575, 400 kW" | → "FSD575, 315 kW" |

## Files Already Correct
- `docs/STAKEHOLDER_PRESENTATION.html` — ✅ All values match config.yaml
- `docs/compressors/HP_Redundancy_Analysis.html` — ✅ (after fix)
- `docs/compressors/WCS_HP_Protection.html` — ✅
- `docs/liquid_he/Liquid_Operations_Guide.html` — ✅

## Files Needing Review (⚠️ Manual)
| File | Issue | Note |
|------|-------|------|
| `docs/index_v4_0.html:659,1471` | Reliability formulas reference "4 ×" | Historical reliability derivation for comparison; formulas are mathematically correct for the N+1 model being shown |
| `docs/heroes/*.html` | Version labels updated but may need content regeneration | Generated from templates |

## Files NOT Changed (Historical/Archival)
- `docs/index_v3_1.html` — v3.1.0 archive (all 4-compressor refs are period-correct)
- `docs/index_v3.html` — v3.0.0 archive
