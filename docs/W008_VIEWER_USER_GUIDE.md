# W008 — Interactive Cross-Map Viewer · User Guide

**Wave label (delivery sequence):** W008
**Functional scope:** completes **W006 Option B** — the interactive-UI plan in
`docs/W006_INTERACTIVE_UI_PLAN.md` (Phases UI‑1 … UI‑5).
**Artifact:** `publish/interactive_viewer.html` (single, self-contained, offline)
**Builder:** `src/abacus_svg_pid/build_viewer.py` (+ `build_viewer_template.py`)
**Status:** DELIVERED

> **Naming note (honesty):** the project `configs/wave_registry.json` reserves
> the *W008* id for a separate **"Round-Trip Reassembly"** scope, which is **not**
> part of this delivery and remains open. This document uses *W008* only as the
> label for the viewer-enhancement deliverable requested in the current delivery
> sequence; functionally it is the completion of **W006 Option B**.

---

## 1. What this is

A single HTML file that lets an engineer explore the **design ↔ as-drawn tag
cross-map** produced by W006 against the live QCELL atlas drawing. Open it by
double-clicking — it needs no server, no internet, and no install. Everything
(the atlas SVGs, the cross-map data, all JavaScript and CSS) is inlined.

## 2. Honest data footing

Every count in the UI is read from the **real** W006 artefacts; nothing is
invented. The authoritative distribution comes from
`reports/W006_crossmap_statistics.json`:

| Metric | Value |
|---|---|
| design tags | **97** |
| as-drawn real tags | **141** |
| mapped pairs | **43** |
| — HIGH confidence | **0** |
| — MEDIUM (conf 0.75) | **39** |
| — LOW (conf 0.45) | **4** |
| unmapped design tags | **54** |
| as-drawn unclaimed | **98** |
| mapped tags locatable in atlas | **43 / 43** |

> The heuristic cross-map has a confidence **ceiling of 0.75 (MEDIUM)** because
> no pair currently has an independent corroborator that would justify HIGH.
> The viewer therefore shows **0 HIGH** — the HIGH filter exists for
> completeness but is dimmed. This is the truth of the data, not a placeholder.

The build performs a **cross-check assertion**: the counts derived from the
table rows must equal the authoritative statistics file, or the build fails.

## 3. Layout

```
┌───────────────────────────── top bar ──────────────────────────────┐
│ title · Single/Compare tabs · search · type filter · Export · ?     │
├──────────────┬──────────────────────────────────────────────────────┤
│  side panel  │  viewer pane(s)  — QCELL atlas (+ RFCELL in compare)  │
│  • stats     │  zoom controls (+ / − / reset), sync toggle           │
│  • triage    ├──────────────────────────────────────────────────────┤
│    filters   │  cross-map table (one row per design tag)             │
│  • validation│                                                        │
│  • layers    │                                                        │
│  • selection │                                                        │
└──────────────┴──────────────────────────────────────────────────────┘
```

## 4. Features & how to use them

### 4.1 Tag → SVG element highlighting (Phase UI‑1)
- **Click any table row.** If the as-drawn tag is present in the atlas
  (marked with 🔍 in the first column), the viewer:
  1. highlights the matching SVG label element(s),
  2. draws a pulsing red bounding box around them,
  3. zooms/pans the drawing to frame the element.
- Annotation is done at **build time**: `build_viewer.py` injects a
  `data-pidtag="…"` attribute onto every atlas text/`tspan` whose content
  matches a known as-drawn tag (exact or multi-token). At runtime the browser
  computes the element box via the screen CTM — no coordinate guessing.

### 4.2 Confidence triage workflow (Phase UI‑2)
- **Filter buttons:** ALL (97) · MAPPED (43) · HIGH (0) · MEDIUM (39) ·
  LOW (4) · UNMAPPED (54).
- **Per-row validation:** ✓ confirm · ✗ reject · ? suggest-alternative.
  Decisions are saved in your browser (`localStorage`) and never alter the
  heuristic cross-map (honesty invariant: human decisions live in a separate
  layer). Click again to clear a decision.
- **Export validations JSON** / **reset validations** in the side panel.

### 4.3 Export controls (Phase UI‑4)
- **Cross-map → CSV** and **Cross-map → JSON** (the JSON also embeds your
  current validation decisions and the `locatable` flag).
- **Current view → PNG**: serialises the visible SVG (with current layers and
  zoom) to a PNG via an offline canvas — no external renderer.
- **Print / Save as PDF**: uses the browser's native print pipeline. This is
  deliberately **not** a bundled PDF engine (that would require a CDN/npm
  dependency, which this single-file deliverable forbids).

### 4.4 Side-by-side comparison (Phase UI‑3 / UI‑5)
- **Compare tab** shows **QCELL** (cross-mapped) beside **RFCELL**.
- **Sync zoom/pan** keeps both drawings aligned (toggle bottom-left).
- ⚠️ **RFCELL is a visual reference only** — the W006 cross-map covers QCELL
  only, so RFCELL carries no mapped pairs. The pane is labelled as such.

### 4.5 Search & navigation
- **Dual-tag search** (top bar): matches design **or** as-drawn tag; the first
  hit is auto-selected and highlighted in the drawing.
- **Type filter** dropdown (CV, TT, PT, …) narrows the table.
- **Selection breadcrumb** in the side panel shows the active pair and tier.

### 4.6 Keyboard shortcuts & polish
| Key | Action |
|---|---|
| `Ctrl/⌘ + F` | focus search |
| `Esc` | clear search / close popups / clear highlight |
| `Ctrl/⌘ + E` | open export menu |
| `Ctrl/⌘ + L` | toggle all layers |
| `+` / `-` | zoom in / out |
| `0` | reset view |
- Wheel = zoom to cursor; drag = pan. Loading overlay, missing-data error
  states, and tooltips are included.

## 5. Regenerating

```bash
./make.sh          # full pipeline; step 6 builds the viewer
# or, just the viewer (after the W006 crossmap + atlas exist):
PYTHONPATH=src python3 -m abacus_svg_pid.build_viewer
```

`publish/` is git-ignored (regenerable); the committed source of record is
`build_viewer.py`, `build_viewer_template.py`, this guide and the report.

## 6. Testing

```bash
PYTHONPATH=src python3 tests/test_w008_viewer.py
```
Standalone runner (no pytest). Asserts the annotation injector, the row
builder, the **honesty count reconciliation** against the W006 statistics, the
single-file self-containment (no external CDN/script/link), atlas embedding,
tag→element links, one table row per design tag, and that the triage / export /
highlight / keyboard machinery is present.

## 7. Known limitations (honest)

- **0 HIGH pairs** — a property of the real heuristic data, not a UI bug.
- **PDF = browser print**, by design (no bundled PDF library).
- **RFCELL has no cross-map** — shown for visual comparison only.
- Highlighting locates the **as-drawn label text**; a few atlas labels that
  concatenate several tags in one element are still resolved via multi-token
  matching, but the highlight box frames the shared label, not each glyph.
