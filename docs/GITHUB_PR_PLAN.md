# GitHub PR Plan — MINERVA QCELL/RFCELL Colour-Line Model

Branch & PR strategy mapped to the wave roadmap. One PR per wave (or combined wave),
each squashed onto `main` after engineering review. **PRs are never auto-merged.**

---

## PR1 — W002: Colour-line decomposition & validation  *(merged — `5d43a9e`)*

- Colour inventory, line model, per-line JSON, W002 validation report, colour-line
  collage. Baseline for all subsequent work.

## PR2 — W003 + W004: Layer hierarchy & geometric tracing  *(THIS PR — ready for review)*

**Branch:** `wave/w003-w004-layer-hierarchy-geometric-tracing`
**Base:** `main` (`5d43a9e`)

### Scope
- Geometry engine (`src/abacus_svg_pid/geometry.py`).
- Build orchestrators: `build_w003_w004.py`, `build_catalog.py`, `build_atlas_v6.py`.
- 10 phases: unmapped reduction (982→112), pairing, text standardization, 21-layer
  hierarchy, flow tracing, nomenclature parser, component catalog, scope-boundary
  validation, PEMO YAML SSOT, docs.
- Outputs: `data/model/*.json`, `data/pemo/ic_system_v1.2.yaml`, `reports/*.md` + xlsx,
  `publish/*.html`, `output_v6/**`, `docs/*`.
- Registry/navigation advanced; tests added.

### Review checklist
- [ ] Confirm 21-layer assignment matches engineering intent.
- [ ] Sanity-check the 297-component catalog against the drawing.
- [ ] Confirm handover-diamond list (22) and 5 scope boundaries.
- [ ] Accept the documented deferrals (U line, 112 magenta, floating arrows).

### Not merged automatically
This PR is opened for review only. Merge after sign-off.

## PR3 — W005: Tag & instrument association  *(planned)*

- Validated tag-to-line association via geometric proximity / CTM.

## PR4 — W006: Cross-drawing reconciliation  *(planned)*

- Unified line identity across QCELL & RFCELL.

## PR5 — W007: Temperature / pressure annotation  *(planned)*

## PR6 — W008: Round-trip reassembly  *(planned)*

## PR7 — W009: Publication & sign-off  *(planned)*

---

### Conventions
- One feature branch per wave; never commit directly to `main`.
- Commit identity: `Abacus Agent <agent@abacus.ai>`.
- Squash-merge with the wave id in the title.
- CI (GitHub Actions) is **planned**, not yet implemented (see `TODO.md`).
