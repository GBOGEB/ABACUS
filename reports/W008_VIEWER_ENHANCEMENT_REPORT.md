# W008 — Interactive Cross-Map Viewer Enhancement · Report

**Delivery-sequence label:** W008
**Functional scope:** completion of **W006 Option B** (interactive UI),
Phases UI‑1 … UI‑5 of `docs/W006_INTERACTIVE_UI_PLAN.md`.
**Date:** 2026-06-07
**Status:** DELIVERED (with honestly-labelled limitations)

---

## 1. Summary

W006 left an intentionally minimal **scaffold** viewer
(`publish/interactive_viewer.html`) that could toggle layers, pan/zoom, search
the table and show a metadata popup — but explicitly *could not* highlight SVG
elements, triage, export, or compare. W008 upgrades it into a full-featured,
**single-file, offline** tool implementing every phase of the W006 UI plan,
while preserving the project's **honesty invariants** (no fabricated numbers,
human decisions kept separate from the heuristic map).

## 2. Naming / governance note (transparency)

`configs/wave_registry.json` reserves the **W008** id for a different,
unrelated scope — **"Round-Trip Reassembly"** — and **W009** for "Publication &
Sign-Off". This deliverable was requested under the *W008* label in the current
delivery sequence, but functionally it is the completion of **W006 Option B**,
not the round-trip-reassembly work. To avoid misrepresentation:

- The **W006** registry entry is updated to mark **Option B DELIVERED**.
- The registry **W008 "Round-Trip Reassembly"** scope is **left open** (not
  falsely marked complete); a note records that the *W008 label* was used for
  the viewer delivery and that round-trip reassembly remains a future wave.
- `docs/CAPABILITY_MATRIX.md` viewer row moves **SCAFFOLDED → DELIVERED**.

## 3. Real data (authoritative)

Source: `reports/W006_crossmap_statistics.json` (regenerable via `./make.sh`).

| Metric | Value |
|---|---|
| design tags | 97 |
| as-drawn real tags | 141 |
| mapped pairs | 43 |
| HIGH / MEDIUM / LOW | **0 / 39 / 4** |
| unmapped design | 54 |
| as-drawn unclaimed | 98 |
| mapped tags locatable in atlas | 43 / 43 |

The build asserts row-derived counts == this file (a hard **honesty gate**);
the W008 test suite re-checks the same equality independently.

> These replace the *placeholder* numbers that floated around in early task
> descriptions (e.g. "30 HIGH / 10 MEDIUM / 3 LOW", "52 unmapped"). Those were
> **never real** and are not used anywhere in the deliverable.

## 4. What was built (by phase)

| Phase | Plan item | Delivered |
|---|---|---|
| UI‑1 | Tag ↔ SVG element linking | ✅ `data-pidtag` injected at build time (47 annotations over 43 mapped tags; 100 % of mapped tags locatable). Click/search → pulse box + zoom-to-box via screen-CTM bbox. |
| UI‑2 | Confidence triage workflow | ✅ ALL/MAPPED/HIGH/MEDIUM/LOW/UNMAPPED filters; per-row confirm/reject/suggest persisted to `localStorage`; export validations JSON; reset. |
| UI‑3 | Comparison & filtering | ✅ Single/Compare tabs; QCELL ∥ RFCELL with synced zoom/pan; type filter; dual-tag search. |
| UI‑4 | Export & sharing | ✅ CSV, JSON (+validations), current-view PNG (offline canvas), Print→PDF (browser). |
| UI‑5 | RFCELL + multi-sheet | ◑ RFCELL atlas embedded for **visual comparison only** (W006 cross-map is QCELL-only — labelled honestly). Multi-sheet cross-map remains modelling scope. |

Plus UX polish: loading overlay, missing-data error states, keyboard shortcuts
(`Ctrl+F/E/L`, `Esc`, `+`/`-`/`0`), tooltips, selection breadcrumb, toasts.

## 5. Implementation notes

- **No external dependencies.** The output references no CDN/`<script src>`/
  `<link>`/`@import`/`url(http…)`. The two atlas SVGs (QCELL ≈ 1.5 MB,
  RFCELL ≈ 0.9 MB) and all data/JS/CSS are inlined → final file ≈ 2.5 MB.
- **Tag annotation** is a stdlib regex pass (`_annotate_svg`) that adds
  `data-pidtag` to atlas text/`tspan` elements matching known as-drawn tags
  (exact + multi-token). No coordinate guessing; runtime uses `getScreenCTM()`
  for an accurate bbox regardless of nested SVG transforms.
- **viewBox-based pan/zoom** (`PanZoom`) replaces the old div-transform, which
  makes zoom-to-element exact and enables synced compare panes.
- **Honesty layer:** the viewer never edits the heuristic cross-map; validation
  decisions live only in `localStorage`/exported JSON.
- Template kept in `build_viewer_template.py`; substitution is **token-based**
  (`__TOKEN__` + `.replace`) because the CSS/JS contain literal braces.

## 6. Files

| File | Change |
|---|---|
| `src/abacus_svg_pid/build_viewer.py` | rewritten: annotation, honest stats, token substitution, cross-check assertions |
| `src/abacus_svg_pid/build_viewer_template.py` | **new** — full HTML/CSS/JS template |
| `tests/test_w008_viewer.py` | **new** — 7 standalone assertions (no pytest) |
| `make.sh` | step 6 comment updated (W006 scaffold → W008 full viewer) |
| `docs/W008_VIEWER_USER_GUIDE.md` | **new** — user guide |
| `reports/W008_VIEWER_ENHANCEMENT_REPORT.md` | **new** — this report |
| `configs/wave_registry.json` | W006 Option B → DELIVERED; W008 note (round-trip reassembly still open) |
| `docs/CAPABILITY_MATRIX.md` | viewer row SCAFFOLDED → DELIVERED |

## 7. Verification

- `./make.sh` → exit 0; viewer rebuilt with `design_tags=97 mapped=43 HIGH=0
  MEDIUM=39 LOW=4 unmapped=54 locatable=43`.
- All standalone suites pass: colour 5, golden 4, integration 5, W003+W004 10,
  W005 11, W006 13, **W008 7** → **55 assertions**.
- Browser smoke-test (manual): row click highlights & frames the as-drawn
  element with a pulsing box; validation toggles persist; Compare shows both
  atlases with synced zoom; counts match the statistics file.

## 8. Known gaps / honest limitations

1. **0 HIGH pairs** — real property of the heuristic data (0.75 ceiling), not a
   UI defect.
2. **PDF = browser print** (no bundled PDF engine — would break the
   single-file/offline/no-CDN constraint).
3. **RFCELL has no W006 cross-map** — compare pane is visual-reference only.
4. **Round-Trip Reassembly** (registry W008) and multi-sheet cross-mapping
   remain **future** work — explicitly not claimed here.
