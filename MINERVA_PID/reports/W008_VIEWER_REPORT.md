# W008 — Interactive Viewer Enhancement Report

**Wave:** W008 (completes W006 Option B — see `docs/W006_INTERACTIVE_UI_PLAN.md`)
**Status:** ✅ Complete
**Generator:** `src/abacus_svg_pid/build_viewer.py`
**Output:** `publish/interactive_viewer.html` (single self-contained file, ~2.5 MB, no build step / no external assets)
**Tests:** `tests/test_w008_viewer.py` (6 tests, green) · full suite 50 tests green
**Honesty mandate:** every UI affordance shows provenance (`reasons[]`) and confidence; the heuristic crossmap is **read-only** — human decisions live in a separate triage file consumed by `KNOWN_SEEDS` on the next `build_w006_crossmap` run.

---

## 1. Summary

The W006 scaffold (layer toggles, pan/zoom, tag search, a confidence-coloured table and a placeholder popup) has been replaced by a **production-ready engineering review surface**. The viewer turns the W006 cross-map (43 of 97 design tags mapped, 44.3 %, all MEDIUM/LOW heuristic proposals) into an efficient manual triage workflow.

| Metric | Value |
|---|---|
| Design tags (rows, design mode) | 97 |
| As-drawn real tags (rows, as-drawn mode) | 141 |
| Mapped pairs | 43 (0 HIGH · 39 MEDIUM · 4 LOW) |
| Unmapped design tags | 54 |
| Hit-testable SVG markers injected | 141 (139 QCELL · 2 RFCELL) |
| Layers in the navigation tree | 21 |
| Sheets embedded | QCELL + RFCELL |

---

## 2. Features implemented

### 2.1 Core features (the five from the UI plan)

**(a) Tag ↔ SVG element highlighting — bidirectional**
- Each real as-drawn instrument is overlaid with a hit-testable marker (a `<g class="tag-mk" data-tag="…">` containing a visible ring + a transparent click circle), positioned from its catalog `x/y` in the shared `0 0 1527.2727 1080` viewBox.
- **Row/search → drawing:** selecting a row outlines the corresponding marker, flashes it, and pans/zooms the drawing to centre it (auto-zooms to ≥2.4× if zoomed out).
- **Drawing → table:** clicking a marker selects the matching table row and opens the metadata popup. If the clicked as-drawn tag has no design claim while in *design* mode, the viewer auto-pivots to *as-drawn* mode so it can still be shown.

**(b) Confidence-based triage workflow**
- Filter chips for **tier** (HIGH/MEDIUM/LOW/unmapped or unclaimed), **type** (CV/TT/PT/…), and **circuit band** (40K/4.5K/2K/WATER/VACUUM/ROOM).
- Quick views: *all*, *unmapped/unclaimed only*, *needs review (MEDIUM/LOW)*, *confirmed (triaged)*.
- Live free-text search across tag / type / band / location.
- Sortable columns (click any header; toggles asc/desc).
- Per-row **Confirm / Defer / Reject** controls (and the same in the popup), persisted to `localStorage` and exportable as `triage_decisions.json`. Confirmed pairs are emitted into a `known_seeds` map ready to feed the engine's `KNOWN_SEEDS` dict.

**(c) Export & per-layer controls**
- 21-layer grouped, collapsible tree with per-layer show/hide checkboxes, per-group master checkbox, and *all on / all off*.
- **Export filtered table → CSV** (columns adapt to the active mode).
- **Export composited view → SVG** (per panel; honours current layer visibility, strips the marker overlay).
- **Export any single layer → SVG** (per-panel dropdown; clones the drawing and keeps only the chosen `lyr-NN` class).
- **Export triage decisions → `triage_decisions.json`** (KNOWN_SEEDS feedback file).

**(d) Side-by-side QCELL vs RFCELL comparison**
- The *Compare* sheet button renders both atlases in two synchronised panels. A highlighted tag lights up on whichever sheet(s) it appears, and each panel keeps its own independent zoom/pan plus its own export controls.

**(e) Design ↔ As-drawn toggle mode**
- The *Design* / *As-drawn* segmented control pivots the entire table and highlight behaviour between the design register (97 circuit-sequential tags such as `CV001`, with location + circuit band) and the as-drawn catalog (141 SVG-instance tags such as `CV560`, with sheet + layer + ISA class). Filters and stats rebuild for the active register.

### 2.2 UI / UX enhancements
- **Search** box in the top bar (also drives filtering + auto-selects the first hit).
- **Colour-coded confidence indicators:** tier pills (green HIGH / amber MEDIUM / orange LOW / slate unmapped / purple unclaimed) plus a per-row confidence score bar.
- **21-layer tree navigation** grouped by the layer contract's logical groups (00–13, with 03/04 fanned out), each group collapsible.
- **Responsive layout:** flex split with a collapsible sidebar (hamburger ☰ under 860 px); the table panel is vertically resizable.
- **Zoom & pan:** per-panel mouse-wheel zoom (cursor-anchored) and drag-to-pan, plus +/− /reset buttons in each panel header.
- **Deep-link URL hash** (`#mode=…&sheet=…&tag=…&q=…&flag=…`) so a reviewer can share an exact view; the viewer restores state on load.
- **Metadata popup** showing type, band, tier, confidence, sheet, location/layer, ISA class, xy, full provenance `reasons[]`, and inline triage buttons.

---

## 3. Usage instructions

### 3.1 Build / regenerate
```bash
cd MINERVA_PID
export PYTHONPATH=src
python3 -m abacus_svg_pid.build_viewer       # regenerates publish/interactive_viewer.html
# or simply:
./make.sh                                     # full pipeline; viewer is the final step
```
The output is a single self-contained HTML file — open `publish/interactive_viewer.html` directly in any modern browser (no server required).

### 3.2 Reviewer workflow (triage)
1. Open the viewer; it starts in **Design** mode on the **QCELL** sheet.
2. Use **Quick views → needs review** (or the tier chips) to focus on MEDIUM/LOW proposals.
3. Click a row → the drawing pans to the proposed as-drawn bubble and the popup shows *why* the heuristic proposed it.
4. Decide with **✓ Confirm / ~ Defer / ✗ Reject** (decisions persist locally).
5. When done, click **⬇ Triage** to download `triage_decisions.json`.
6. Wire the `known_seeds` block into `build_w006_crossmap.py`'s `KNOWN_SEEDS` dict and re-run `./make.sh`; confirmed pairs are legitimately promoted to **HIGH** with reason `KNOWN_SEED` (this is the only honest path to HIGH — `test_no_fabricated_high_without_corroboration` guards it).

### 3.3 Other tasks
- **Compare drawings:** *Compare* button → QCELL + RFCELL side by side, synced highlight.
- **Inspect as-drawn coverage:** *As-drawn* mode → 141 instances; *unclaimed only* shows the 98 instances no design tag mapped to.
- **Isolate / export a layer:** in a panel header pick a layer from *export layer…*; toggle layers in the sidebar tree then *⬇SVG* to export the composited view.
- **Share a view:** copy the URL — the hash encodes mode/sheet/selected-tag/search/quick-view.

---

## 4. Technical architecture

- **Generation:** `build_viewer.py` (stdlib-first, optional PyYAML with a regex fallback) loads the crossmap, confidence, as-drawn catalog and the canonical register, joins them into two row models (`designRows`, `asdrawnRows`), embeds both annotated atlas SVGs, and emits one HTML file via token replacement (no f-string brace hazards, CSS/JS kept literal).
- **SVG embedding:** each atlas SVG is parked in a `<script type="text/html" id="svg-SHEET">` block and inflated into a panel via `innerHTML` on demand (so Compare/sheet-switch can rebuild panels). Atlas SVGs contain no `</script>`, so this is safe.
- **Marker overlay:** `_inject_overlay()` inserts a `<g id="tag-overlay">` of per-instrument markers **inside** each `</svg>`, in the same user-coordinate space, keyed by as-drawn `data-tag`. This delivers tag↔element linking **without mutating the fragile source geometry** (no CTM/transform edits) — the trade-off is approximate placement (see limitations).
- **Layer model:** the 21-layer contract from `configs/layers.yaml` maps 1:1 to the `lyr-00…lyr-20` classes the atlas already carries (verified against `build_w003_w004.LAYER_ORDER`). Toggling adds a `hide-NN` class to each `.svgpan`; runtime-generated CSS rules `.svgpan.hide-NN .lyr-NN{display:none}` do the hiding.
- **State & data flow:** a single client-side `S` state object drives filtering/sorting/rendering; the heuristic crossmap is never mutated. Triage lives only in `localStorage` (`minerva_triage`) and the exported JSON — preserving the honesty invariant.
- **No dependencies / no build step:** pure HTML + CSS + vanilla JS, consistent with the repo's `./make.sh` reproducibility discipline. Derived output is git-ignored and regenerated on demand.

---

## 5. Known limitations

1. **Marker placement is approximate.** Highlight markers come from each instrument's catalog `x/y` (assign-distance median ~20 px), **not** a hit-test of the original drawn bubble. A tag lights up the correct neighbourhood, but the ring can sit slightly off the exact glyph. A future pass could annotate the bubbles in place during `build_atlas_v6` for pixel-exact hits.
2. **RFCELL marker sparsity.** Only 2 RFCELL instances carry coordinates in the as-drawn catalog (the W003/W004 category sheets are QCELL-dominant), so RFCELL highlighting is sparse — though the full RFCELL atlas still renders in Compare mode.
3. **No HIGH-confidence pairs yet.** `KNOWN_SEEDS` is empty by design; all 43 mapped pairs are MEDIUM/LOW heuristic proposals awaiting human triage. HIGH only appears after confirmed seeds are fed back and the engine re-runs.
4. **Triage is local until exported.** Decisions persist in browser `localStorage` and must be exported + wired into `KNOWN_SEEDS` to influence the map; this is deliberate (the viewer must not edit the heuristic crossmap).
5. **Export is SVG + CSV, not PNG.** Vector exports (current view + per-layer) and filtered-table CSV are provided; client-side PNG rasterisation was out of scope (an exported SVG can be rasterised externally).

---

## 6. Examples (verified in-browser)

- **Tag → element:** selecting `CV001` (design) centres and flashes the `CV560` marker on QCELL and opens the popup `CV001 ↔ CV560` (type CV, band 40K, conf 0.75, MEDIUM, location "pressurized GHe to 40K circuit", reasons `TYPE_MATCH · CIRCUIT_MATCH(40K) · ORDER_MATCH(#0/3)`).
- **Element → row:** clicking the `CV500` marker selects design row `CV002` and opens its popup.
- **Compare:** *Compare* renders QCELL + RFCELL with markers shown; a selected tag highlights on the sheet it lives on while each panel zooms independently.
- **As-drawn pivot:** table switches to 141 instances; *unclaimed only* isolates the un-mapped catalog instances; headers pivot to as-drawn / design / sheet / layer.
- **Triage:** Confirm on `CV001` turns the control green and persists; **⬇ Triage** downloads `triage_decisions.json` with a populated `known_seeds` block.

---

## 7. Definition-of-done check (vs `docs/W006_INTERACTIVE_UI_PLAN.md` §6)

| DoD item | Status |
|---|---|
| 1. Tag ↔ SVG element linking, both directions (UI-1) | ✅ (overlay-marker based; approximate placement noted) |
| 2. Triage decisions persist and feed `KNOWN_SEEDS` (UI-2) | ✅ (localStorage + `triage_decisions.json` export) |
| 3. Filters + unmapped view (UI-3) | ✅ (tier/type/band chips + quick views) |
| 4. PNG/CSV export + deep links (UI-4) | ◑ CSV + **SVG** export + deep-link hash done; PNG raster deferred |
| 5. RFCELL sheet support (UI-5) | ✅ (sheet selector + Compare) |
| 6. `tests/test_w008_viewer.py` green; viewer step in `make.sh` exits 0 | ✅ |
