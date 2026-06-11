# W002 — Colour-Line Decomposition & Validation Report

**Project:** MINERVA QCELL P&ID — colour-line-first engineering process model
**Owner:** Mott MacDonald / SCK CEN — MYRRHA-MINERVA Phase 1
**Wave:** W002 — Colour Line Decomposition & Validation · Status: ACTIVE
**Pipeline:** `src/abacus_svg_pid/parser.py` + `cli.py` (pure standard library)

> Geometry, arrow tracing and sequential component ordering are intentionally
> **DEFERRED to W004** (placeholders `"DEFERRED_W004"` in the model). W003
> (layer/mechanical-section engine), UI, PPT and CI workflows are **not** run.

---

## 1. SVG sources found

Real source drawings copied into `data/svg/` as the first action:

| File | Status |
|------|--------|
| `PFD-PID MINERVA QCELL-LB.svg` | ✅ loaded |
| `PFD-PID MINERVA RFCELL seen by ACR.svg` | ✅ loaded |

**SVG files loaded: 2** (STOP gate ≥ 2 satisfied).

## 2. PDF / PPT references found

| File | Location |
|------|----------|
| `PFD-PID_MINERVA_QCELL-LB.pdf` | `data/pdf/` ✅ |
| `QCELL_P&ID.pptx` | `data/ppt/` ✅ |

## 3. Colour-extraction correctness (bug fix)

Colour/style is read with **inline-style precedence**:
`style.get(key) or elem.attrib.get(key)` — inline `style="stroke:…"` overrides the
presentation attribute. (The previous reversed order was the defect this wave fixes.)
The "effective process colour" of each element is its stroke when present, else its fill
(the QCELL drawing draws most lines as filled paths where stroke == fill).

## 4. Colour bins detected → canonical process codes

Clustering is by **RGB colour-distance to canonical anchors** (threshold 90),
not exact-hex matching, so shade variants collapse onto the right line.

| Canonical bin | Anchor hex | Process code(s) | Role |
|---|---|---|---|
| BLUE / NAVY | `#0000ff` / `#000080` | **A** / **A′** | 4.5 K main + internal branch |
| CYAN / TEAL | `#00ffff` / `#008080` | **B** / **B′** | 2 K internal line |
| GREEN | `#00ff00` / `#008000` | **W** | coupler (splits from BLUE A in QM) |
| OLIVE | `#808000` | **S** | warm S line |
| GREY | `#999999` / `#808080` | **V** | vent line (per module, to outside) |
| RED / ORANGE | `#ff0000` / `#ff8000` | **D** / **E** | warm/cold manifold |
| BLACK | `#000000` / `#1a1a1a` | structure | boundary / symbols / unknown |

## 5. Path / line elements per canonical process code

| Process code | Element count |
|---|---|
| A (4.5 K main, BLUE) | 171 |
| A′ (internal branch, NAVY) | 70 |
| B (2 K internal, CYAN) | 105 |
| W (coupler, GREEN) | 160 |
| S (S line, OLIVE) | 125 |
| V (vent, GREY) | 116 |
| D (manifold, RED) | 116 |
| E (manifold, ORANGE) | 9 |
| structure / unknown (BLACK + other) | 982 |

## 6. Unique stroke colours

**15** unique `#rrggbb` stroke colours across the two drawings;
**220** unique `(stroke_hex, stroke_width)` pairs catalogued in
`data/model/colour_inventory.json`.

## 7. Text labels per file

| File | Text nodes |
|---|---|
| `PFD-PID MINERVA QCELL-LB.svg` | 566 |
| `PFD-PID MINERVA RFCELL seen by ACR.svg` | 128 |

## 8. Boundaries / mechanical sections detected (via label scan)

| Boundary | Example labels matched |
|---|---|
| **QM** | "scope QM", "Cryomodule (QM)", "QCELL-QM" |
| **Jumper** | "Jumper" |
| **QVB** | "scope QVB", "scope QVB (AUB)", "QVB INVAC" |
| **QINFRA** | "scope QINFRA", "QINFRA - Implementation by NFS" |
| **vacuum barrier** | "vacuum barrier" |

All five expected scope/boundary features are present in the QCELL drawing.

## 9. Unresolved colours

Black family (`#000000` ×728, `#1a1a1a` ×142) is treated as **structure /
boundary / symbols** (expected, not a process line).

Truly **unmapped "other"** colours (outside the canonical mapping, flagged for
engineering review — they are isolated into `unknown_black_or_other.json`):

| Hex | Occurrences | Note |
|---|---|---|
| `#ff00ff` (magenta) | 78 | Largest unresolved bin — instrument-air / annotation line; needs a canonical assignment. |
| `#bf512e` | 8 | Brown/terracotta — possible RED/ORANGE tint beyond threshold. |
| `#d35f5f` | 8 | Dusky red — possible RED tint. |
| `#ffffff` | 10 | White (background fill); non-process. |
| `#80b3ff` | 4 | Light-blue tint — possible BLUE fill. |
| `#55ff99` | 3 | Light-green tint — possible GREEN fill. |
| `#800000` | 1 | Maroon — possible RED tint. |

## 10. Confidence notes

- **High confidence:** A, A′, B, W, S, V, D mappings — exact anchor hits (distance 0).
- **Medium:** E (ORANGE) only 9 elements; verify against legend "E 60 K; 13 bar".
- **Low / flagged:** the seven "other" colours above; magenta in particular has a
  material footprint (78 elements) and must be resolved before W008 reassembly.
- `arrows_detected` and `sequential_components` are **DEFERRED_W004** — line
  ordering is preserved as-found (no geometric re-ordering performed).
- Tag association is a **label-seed** best-effort only; validated geometric
  proximity association is W005.

---

## Success criteria (runtime counts — all non-zero)

| # | Criterion | Value |
|---|---|---|
| 1 | SVG files loaded | **2** |
| 2 | Unique stroke colours | **15** |
| 3 | Path elements per process code | A 171 · A′ 70 · B 105 · W 160 · S 125 · V 116 · D 116 · E 9 · unknown 982 |
| 4 | Text nodes per file | QCELL 566 · RFCELL 128 |
| 5 | Colours that could not be mapped | 7 "other" hexes (magenta `#ff00ff` ×78 + 6 tints); black family = structure |

**Generated artefacts:** `data/model/colour_inventory.json`,
`data/model/line_model.json`, `data/model/lines/{blue_A, cyan_B_2K,
green_W_coupler, grey_V_vent, olive_S_line, red_orange_D_E,
unknown_black_or_other}.json`, `reports/navigation.json`,
`publish/colour_line_collage.html` (+ `publish/assets/*.png`).
