# Version Changelog — MINERVA QCELL/RFCELL Colour-Line Model

All notable changes to the colour-line-first P&ID model are documented here.
Versioning tracks the wave roadmap (`configs/wave_registry.json`).

---

## v6.0 — W003 + W004 (Layer Hierarchy & Geometric Tracing)

**Baseline:** v5 / W002 (`5d43a9e`)

### Added
- **13 top-level layers (21 named sub-layers) visual hierarchy** with per-element
  layer assignment (`data/model/layer_assignment.json`).
- **Layered atlas v6** — interactive layer-toggle viewer (`publish/layered_atlas_v6.html`).
- **13-layer rendered drawings** — `output_v6/{QCELL,RFCELL}/*_13layers.{svg,pdf}`
  (QCELL 1834 elements / 14 layers, RFCELL 591 / 12 layers).
- **Element pairing engine** — text↔component, dot↔line, triangle↔line, arrow↔line
  (`data/model/paired_elements.json`).
- **Text standardization model** — Consolas monospace, 4 mm-based tiers
  (`data/model/text_standardization.json`, `reports/text_standardization_report.md`).
- **Geometric flow tracing** — 132 arrows, 77 floating, 36 junctions
  (`data/model/flow_topology.json`).
- **Vertical-letter nomenclature parser** — 33 segments into parent-header tree
  (`data/model/segment_nomenclature.json`).
- **Component catalog** — 297 components to Excel + HTML
  (`reports/COMPONENT_CATALOG.xlsx`, `publish/component_catalog.html`).
- **Spec-dot catalog** (`data/model/spec_dots_catalog.json`).
- **Scope boundary validation** — 5/5 boundaries, 22 handover diamonds
  (`data/model/scope_boundary_validation.json`, `reports/scope_boundary_validation.md`).
- **PEMO SSOT** — YAML 1.2 with 122 control loops, 60 heat loads
  (`data/pemo/ic_system_v1.2.yaml`).
- **Geometry engine** — CTM-resolved extraction (`src/abacus_svg_pid/geometry.py`).
- **Build orchestrators** — `build_w003_w004.py`, `build_catalog.py`, `build_atlas_v6.py`.
- Phase reports + Phase 10 docs (this changelog, BUILD_MANIFEST, CAPABILITY_MATRIX,
  TODO, GITHUB_PR_PLAN).

### Changed
- Unmapped elements reduced **982 → 112** (88.6 % resolved) via legend-driven
  reclassification (`reports/unmapped_reduction_analysis.md`).
- `configs/wave_registry.json` — W003 & W004 marked `complete`; current wave → W005.
- `reports/navigation.json` — advanced to W003/W004 complete, next W005.

### Deferred (honest gaps)
- 112 magenta / non-canonical colour elements — no legend swatch.
- U line (top-left, black) recovery.
- 04G_E_RED line layer currently empty (RED maps to E text only).
- 77 floating arrows not yet bound to a source line.
- Manifold COLD/WARM header layers (03A/03B) reserved.

---

## v5.0 — W002 (Colour Line Decomposition & Validation)

- Colour inventory, line model, per-line JSON, W002 validation report, colour-line
  collage (`publish/colour_line_collage.html`). Commit `5d43a9e`.

## v1–v4 — W001 (Source Ingestion & Style Extraction)

- Real QCELL/RFCELL SVGs ingested into `data/svg/`; element / colour / style extraction
  with correct inline-style precedence.
