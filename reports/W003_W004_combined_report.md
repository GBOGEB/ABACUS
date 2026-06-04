# W003 + W004 Combined Build Report — Layer Hierarchy & Geometric Tracing

**Project:** MINERVA CryoCell / QCELL & RFCELL P&ID — colour-line-first model
**Programme:** Mott MacDonald / SCK CEN / MYRRHA-MINERVA Phase 1
**Waves:** W003 (Layer Hierarchy) + W004 (Geometric Tracing) — combined 10-phase build
**Baseline:** W002 (`5d43a9e`)
**Toolchain:** Python standard library + `cairosvg` (PDF render) + `openpyxl` (Excel)

---

## Executive summary

This build extends the W002 colour-line decomposition with a full hierarchy of
**13 top-level layers (21 named sub-layers)** and a geometric flow-tracing pass.
Headline outcomes:

- Unmapped elements reduced **982 → 112** (88.6 % resolved).
- **13 top-level layers (21 named sub-layers)** assigned; QCELL annotated **1834**
  elements (14 sub-layers used), RFCELL **591** (12 sub-layers).
- **132** flow arrows traced, **77** floating arrows isolated, **36** junctions.
- **297** components cataloged to Excel + HTML.
- **22** handover diamonds and **5/5** scope boundaries validated.
- PEMO SSOT emitted as YAML 1.2 with **122** control loops and **60** heat loads.

The build follows "Claim ≠ Complete" discipline: every number below is a real runtime
count from the engines. Items that cannot yet be computed are marked **DEFERRED** and
tracked in `docs/TODO.md` and `docs/CAPABILITY_MATRIX.md`.

---

## Phase 1 — Legend-based unmapped reduction

| Metric | Count |
| --- | ---: |
| Unmapped before | 982 |
| Reclassified | 870 |
| Still unresolved | 112 (UNRESOLVED_OTHER_COLOUR / magenta family) |

Top categories: symbol/heatload markers 236, leader/signal lines 211, uncoloured
spec-dots 153, instrument bubbles 146, structure paths 57, flow arrows 40, boundary/
titleblock 27. Detail → `reports/unmapped_reduction_analysis.md`.

## Phase 2 — Element pairing engine

| Pairing | Count |
| --- | ---: |
| Text → component pairs | 315 |
| Text colour-classified | 533 |
| Dots paired to lines | 205 |
| Heat-load triangles paired | 100 |
| Arrows paired to lines | 132 |
| Arrows floating (unpaired) | 77 |

**Pairing-distance quality (752 paired elements with `distance_px`):** median
**25.35 px**, p90 **355.4 px**, max **1040.2 px**. On a 1527 px-wide canvas a
1040 px pairing is almost certainly wrong, so pairs above the p90 (~355 px) are
flagged **LOW-CONFIDENCE** and must not be trusted as ground truth; the **77**
floating arrows are left unmatched rather than force-paired (governance: no
silent deletion of unresolved data). Tight median (25 px) confirms the bulk of
pairings are sound.

Output → `data/model/paired_elements.json`.

## Phase 3 — Text standardization

Target font `Consolas, 'DejaVu Sans Mono', monospace`; 4 mm-based tiers.

| Tier | mm | Nodes |
| --- | ---: | ---: |
| major_header | 3.0 | 148 |
| instrument_tag | 2.2 | 157 |
| segment_label_vertical | 2.5 | 17 |
| annotation | 1.8 | 211 |

533 text nodes total. Detail → `reports/text_standardization_report.md`.

## Phase 4 — 13 top-level layers (21 named sub-layers)

Per-layer element counts (assignment model):

| Layer | Count |
| --- | ---: |
| 02_ScopeBoundaries_Main | 565 |
| 04A_Lines_A_BLUE | 103 |
| 04B_Lines_B_CYAN | 43 |
| 04C_Lines_W_GREEN | 61 |
| 04D_Lines_S_OLIVE | 67 |
| 04E_Lines_V_GREY | 40 |
| 04F_Lines_D_ORANGE | 65 |
| 05_HeatLoads_ALL | 100 |
| 06_SegmentNames_Vertical_Black | 17 |
| 07_Equipment_Major | 372 |
| 08_Instruments_Bubbles | 162 |
| 09_Control_Elements | 51 |
| 10_Signals_Dashed | 54 |
| 11_Text_ColorCoded | 516 |
| 12_Dots_SpecChanges_ALL | 205 |

Empty layers (00 grid, 01 titleblock, 03A/03B manifolds, 04G_E_RED, 13 legend) are
reserved placeholders for future waves. Rendered artifacts:

- `output_v6/QCELL/QCELL_13layers.svg` + `.pdf` — 1834 elements annotated, 14 layers used
- `output_v6/RFCELL/RFCELL_13layers.svg` + `.pdf` — 591 elements annotated, 12 layers used
- Interactive layer-toggle atlas → `publish/layered_atlas_v6.html`

Elements are annotated **in place** with `class="lyr-NN"` to preserve CTM transforms.

**Layer sum-check (exact reconciliation):** `1888 drawable + 533 text = 2421`
total elements assigned, with **no drops and no double-counts** — every input
element lands in exactly one layer bucket. (The 1888 drawable = 1375 QCELL +
513 RFCELL; shapes: 670 triangle / 374 line / 239 path / 205 dot / 162 bubble /
132 arrow / 106 rect.) The in-place atlas annotation reports **2425**
(1834 QCELL + 591 RFCELL); the **+4** difference versus 2421 is group-wrapper
`<g>` elements that receive a class during annotation but are not leaf drawables
— documented here honestly rather than reconciled away.

## Phase 5 — Geometric tracing (flow topology)

| Metric | Count |
| --- | ---: |
| Flow arrows traced | 132 |
| Floating arrows | 77 |
| Junctions | 36 |

Output → `data/model/flow_topology.json`.

## Phase 6 — Vertical-letter nomenclature parser

Parsed **33** segment labels into a parent-header tree:

| Parent | Children |
| --- | --- |
| A (4.5 K main, BLUE) | A, A', AK, AK1, AK2, AL, AL1, AL2, AS, AX, AZ1, AZ2 |
| D (manifold, ORANGE) | D, D', DJ, DS, DZ |
| V (vent, GREY) | V501, V502, V503, VH |
| E (manifold, RED) | E, E' |
| B (2 K, CYAN) | B, B', BZ |
| S (warm, OLIVE) | S, SW |
| W (coupler, GREEN) | W, W' |
| U (TOP-LEFT) | **DEFERRED** — currently black, flagged for recovery |

Output → `data/model/segment_nomenclature.json`.

## Phase 7 — Component catalog

**297** components cataloged with line assignment, tag, prefix and coordinates.
Spec-change dots by line: S 40, V 10, B 2, uncoloured 153.

- `reports/COMPONENT_CATALOG.xlsx`
- `publish/component_catalog.html`
- `data/model/spec_dots_catalog.json`

## Phase 8 — Scope boundary validation

5/5 boundaries (QM, QVB, vacuum_barrier, Jumper, QINFRA), **22** handover diamonds
(TP#101…TP#604), **19** W-line bottom-right elements. Detail →
`reports/scope_boundary_validation.md`.

## Phase 9 — PEMO YAML 1.2 SSOT

`data/pemo/ic_system_v1.2.yaml` — **122** control loops, **60** heat loads emitted as a
single source of truth.

## Phase 10 — Documentation

`docs/VERSION_CHANGELOG.md`, `docs/BUILD_MANIFEST.json`, `docs/CAPABILITY_MATRIX.md`,
`docs/TODO.md`, `docs/GITHUB_PR_PLAN.md`, plus this report and the layered atlas.

---

## Deferred / honest gaps

| Item | Status |
| --- | --- |
| 112 magenta / non-canonical colour elements | DEFERRED — no legend swatch |
| U line (top-left, currently black) | DEFERRED — recovery in future wave |
| 04G_E_RED line layer (0 elements) | DEFERRED — RED currently maps to E text only |
| 77 floating arrows | Isolated, not yet bound to a source line |
| Manifold COLD/WARM header layers (03A/03B) | Reserved placeholders |

## Reproduction

```bash
cd /home/ubuntu/pid_project
PYTHONPATH=src python3 -m abacus_svg_pid.build_w003_w004   # phases 1-9 models
PYTHONPATH=src python3 -m abacus_svg_pid.build_catalog     # phase 7 xlsx+html
PYTHONPATH=src python3 -m abacus_svg_pid.build_atlas_v6    # phase 4 svg/pdf/atlas
```

All HTML deliverables are static files (no server required).
