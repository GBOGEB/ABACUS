# Capability Matrix — v6.0 (W003 + W004)

Honest "Claim ≠ Complete" accounting. Every row is one of:
**CAN** (implemented & verified by runtime counts) ·
**CANNOT** (not possible with current source data / toolchain) ·
**DID NOT / DEFERRED** (possible but intentionally not done this wave).

---

## CAN — implemented and verified

| Capability | Evidence |
| --- | --- |
| Reduce unmapped elements via legend reclassification | 982 → 112 (88.6 %) |
| CTM-resolved geometry extraction (bbox/centroid/shape) | `geometry.py`; 7 shape classes |
| Pair text → components | 315 pairs |
| Colour-classify text nodes | 533 nodes |
| Pair dots / heat-load triangles / arrows → lines | 205 / 100 / 132 |
| Pairing distance quality (honest caveat) | 752 pairs, median 25px. 10% above 355px flagged low-confidence; max 1040px (known outlier, deferred to W005 review) |
| Standardize text to Consolas + 4 mm tiers | 533 nodes tiered |
| Assign 13 top-level layers (21 named sub-layers) per element | `layer_assignment.json` |
| Render layered SVG + PDF | QCELL 1834/14, RFCELL 591/12 |
| Build interactive layer-toggle atlas | `layered_atlas_v6.html` |
| Trace flow arrows + junctions | 132 arrows, 36 junctions |
| Parse vertical-letter nomenclature into tree | 33 segments, 8 parents |
| Catalog components to Excel + HTML | 297 components |
| Catalog spec-change dots by line | S 40, V 10, B 2, uncol. 153 |
| Detect scope boundaries | 5/5 (QM/QVB/vac/Jumper/QINFRA) |
| Detect handover diamonds (TP#NNN) | 22 |
| Emit PEMO YAML 1.2 SSOT | 122 loops, 60 heat loads |
| Reconcile as-drawn catalog vs design nomenclature XLSX (W005) | 97 design tags vs 141 as-drawn real tags; per-TYPE coverage delta |
| Detect orthogonal tag schemes (design circuit-seq vs as-drawn instance) | 0 exact overlap — reported honestly, not forced |
| Flag instrument TYPES missing from catalog (W005) | 10 design TYPES (FT/FV/HX/J/LE/LI/PV/RD/SV/V) absent |
| Flag RFCELL template placeholders as non-reconcilable | 24 placeholders (TTxxx/EHx11…) flagged |
| Apply documented PPT instrument re-allocations | 2 (TT535→PZ coldest, TT525→PZ warmest) |
| Emit canonical merged instrument register (SSOT) | `data/excel/canonical_register_v1.yaml`, 238 entries |

## CANNOT — blocked by source data / toolchain

| Capability | Reason |
| --- | --- |
| Map the 112 residual magenta elements to a line | No legend swatch exists for that colour family in the source SVG |
| Confirm true 3-D pipe routing / elevations | Source is 2-D schematic; no z-data |
| Resolve the single degenerate-transform coordinate outlier to a real position | Source transform is mathematically degenerate; mitigated by using viewBox bounds |

## DID NOT / DEFERRED — possible, deferred to a later wave

| Capability | Status / target wave |
| --- | --- |
| Recover the U line (top-left, currently black) | DEFERRED — needs colour re-attribution pass |
| Bind the 77 floating arrows to source lines | DEFERRED — needs nearest-line heuristic |
| Populate 04G_E_RED line layer (geometry) | DEFERRED — RED currently text-only |
| Populate manifold COLD/WARM header layers (03A/03B) | DEFERRED — reserved placeholders |
| Design ↔ as-drawn tag cross-map (keyed on TYPE+circuit+position) | **DELIVERED — W006.** Confidence-scored bidirectional map; 43/97 mapped (0 HIGH / 39 MEDIUM / 4 LOW), 54 unmapped. HIGH requires independent corroborator. See `reports/W006_CROSSMAP_REPORT.md` |
| Extend as-drawn catalog to the 10 missing design TYPES (FV/SV/FT/V/HX/J/LE/LI/PV/RD) | DEFERRED — W003/W004 category sheets covered only CV/EH/HV/LS/PT/TT |
| Exhaustive parse of the 65 MB QSYS instrumentation PPT | DEFERRED — cost; 2 documented re-allocations encoded from cited slides |
| Cross-drawing identity reconciliation (QCELL↔RFCELL) | DEFERRED — Wave W006 |
| Temperature/pressure annotation per segment | DEFERRED — Wave W007 |
| CI / GitHub Actions workflow | **DELIVERED — W007.** Workflow `ci/minerva-pid-test.yml` (Py 3.10–3.12 matrix) regenerates via `./make.sh`, runs 48 standalone-runner assertions under `coverage.py` (no pytest), enforces a golden-file gate (`tests/test_golden_files.py` + `tests/golden/`), checks `--clean` reproducibility, uploads artifacts. Staged for one-time maintainer activation (GitHub App lacks `workflows` permission). See `docs/W007_CI_IMPLEMENTATION.md` + `reports/W007_CICD_REPORT.md` |
| Coverage reporting (pytest-cov-free) | **DELIVERED — W007.** `coverage run -p` over standalone runners → combine/report/xml; `.coveragerc` + `[tool.coverage.*]`. ~18% reported honestly (tests target pure fns; `build_*` run via make.sh), not gated |
| Golden-file regression gate | **DELIVERED — W007.** Invariant snapshots (line model, catalog counts, crossmap stats) generated from verified runtime output; deterministic (volatile XLSX bytes excluded) |
| Pre-commit hooks | **DELIVERED (advisory) — W007.** `.pre-commit-config.yaml` hygiene + black/flake8 (opt-in; not CI-enforced to avoid mass reformat) |
| Interactive cross-map viewer (layer toggle, pan/zoom, tag search, metadata) | **DELIVERED — W006 Option B, completed under the W008 viewer enhancement.** `publish/interactive_viewer.html` now implements Phases UI‑1…UI‑5 of `docs/W006_INTERACTIVE_UI_PLAN.md`: tag→SVG highlight + zoom-to-box (43/43 mapped tags locatable), confidence triage (0 HIGH / 39 MEDIUM / 4 LOW / 54 unmapped — real W006 counts), confirm/reject/suggest validations (localStorage), CSV/JSON/PNG export + browser-print PDF, QCELL∥RFCELL compare (synced zoom; RFCELL visual-reference only), dual-tag search, type filter, keyboard shortcuts. Single self-contained offline HTML. See `docs/W008_VIEWER_USER_GUIDE.md` + `reports/W008_VIEWER_ENHANCEMENT_REPORT.md` |
| UI framework / web app | DEFERRED — single-file static HTML (no bundler) by design |
