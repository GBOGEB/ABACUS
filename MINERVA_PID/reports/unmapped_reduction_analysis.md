# Unmapped Element Reduction Analysis — Wave W003 Phase 1

**Project:** MINERVA CryoCell / QCELL & RFCELL P&ID — colour-line model
**Wave:** W003 (Layer Hierarchy), Phase 1
**Method:** Legend-driven reclassification of previously-unmapped SVG elements.

---

## 1. Summary

| Metric | Count |
| --- | ---: |
| Unmapped elements (entering W003, from W002) | **982** |
| Reclassified into a known category | **870** |
| Still unresolved | **112** |
| Reduction achieved | **88.6 %** |

The 982 elements that W002 could not bind to a colour-line were re-examined against
the extracted legend symbols and against their geometric/shape signature (dot, triangle,
bubble, rectangle, leader line, arrow, structural path). 870 of them (88.6 %) were
confidently routed to a functional category. The residual **112** are all in a single
bucket — `UNRESOLVED_OTHER_COLOUR` — corresponding to the magenta / non-canonical
colour family that has no legend entry yet.

## 2. Reclassified categories (870)

| Category | Count | Meaning |
| --- | ---: | --- |
| `symbol_glyph_or_heatload_marker` | 236 | Symbol glyphs and heat-load marker fragments |
| `structure_leader_or_signal_line` | 211 | Leader lines / signal (dashed) lines |
| `spec_change_dot_uncoloured` | 153 | Spec-change dots with no colour fill |
| `instrument_bubble` | 146 | Instrument bubbles (circles around tags) |
| `structure_symbol_path` | 57 | Structural symbol outlines |
| `annotation_flow_arrow` | 40 | Flow-direction arrows used as annotation |
| `structure_boundary_or_titleblock` | 27 | Scope boundary / title-block rectangles |
| **Total** | **870** | |

Representative element IDs per category are stored in
`data/model/unmapped_reduction.json → examples`.

## 3. Still unresolved (112)

| Category | Count | Disposition |
| --- | ---: | --- |
| `UNRESOLVED_OTHER_COLOUR` | 112 | **DEFERRED** — magenta / non-canonical colour family |

These elements (e.g. `path42`, `path44`, `path62`, `path63`) carry a fill colour outside
the canonical palette (BLUE→A, CYAN→B, GREEN→W, OLIVE→S, GREY→V, ORANGE→D, RED→E,
BLACK→structure). No legend swatch maps to them. They are **honestly retained as
unresolved** rather than force-fit, and are tracked in `TODO.md` for a future
legend-augmentation pass.

## 4. Provenance

- Engine: `src/abacus_svg_pid/build_w003_w004.py` (Phase 1)
- Geometry extraction: `src/abacus_svg_pid/geometry.py` (CTM-resolved bbox/centroid/shape)
- Machine-readable output: `data/model/unmapped_reduction.json`
