# Text Standardization Report — Wave W003 Phase 3

**Project:** MINERVA CryoCell / QCELL & RFCELL P&ID
**Wave:** W003 (Layer Hierarchy), Phase 3
**Target font:** `Consolas, 'DejaVu Sans Mono', monospace`

---

## 1. Summary

| Metric | Value |
| --- | ---: |
| Total text nodes analysed | **533** |
| Distinct raw font sizes found | 20 |
| Distinct font families found | 5 |
| Target font (standardised) | `Consolas, 'DejaVu Sans Mono', monospace` |
| Size tiers defined | 4 |

All 533 text nodes use `font-weight: normal`. The source drawing mixes inconsistent
fonts and sizes; standardization collapses these onto a single monospace stack and
four semantic size tiers (mm-based).

## 2. Current state (before standardization)

### Font families
| Family | Count |
| --- | ---: |
| (inherited / none) | 313 |
| sans-serif | 189 |
| Arial | 21 |
| 'Times New Roman' | 8 |
| 'Agency FB' | 2 |

### Most common raw sizes
| Raw size | Count |
| --- | ---: |
| 7.5px | 141 |
| 12px | 100 |
| 5.13131px | 89 |
| 3.84848px | 42 |
| 7.69697px | 24 |
| 6.41414px | 23 |
| 14.1111px | 21 |
| (other 13 sizes) | 93 |

## 3. Target size tiers (mm)

| Tier | Size (mm) | Assigned nodes | Sample tokens |
| --- | ---: | ---: | --- |
| `major_header` | 3.0 | 148 | `Q1`, `EH514TT514`, `MP-011ARC-014`, `ARC-013`, `CPLR.1` |
| `instrument_tag` | 2.2 | 157 | `TT513`, `TT523`, `TT535`, `TT536`, `TT546` |
| `annotation` | 1.8 | 211 | `x-`, `x+` (flow/offset annotations) |
| `segment_label_vertical` | 2.5 | 17 | `AK`, `XM`, `AL2`, `AL1`, `AL` |
| **Total assigned** | | **533** | |

## 4. Notes

- Vertical segment labels (17) are detected via transform-rotation angle and routed to
  their own tier (2.5 mm) and to layer `06_SegmentNames_Vertical_Black`.
- Standardization is recorded as a model (tier assignment per node); the live re-styling
  is applied in the layered atlas via the `lyr-*` class system.
- Machine-readable output: `data/model/text_standardization.json`.
- Engine: `src/abacus_svg_pid/build_w003_w004.py` (Phase 3).
