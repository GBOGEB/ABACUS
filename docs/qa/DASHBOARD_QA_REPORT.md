# ABACUS Dashboard Playwright QA — Accessibility & Legend/Axis Overlap

**Date:** 2026-10-26
**Scope:** Interactive chart dashboards in the ABACUS repo
**Suite:** `scripts/qa/dashboard_playwright_qa.py` (Playwright, system Chromium, `--no-sandbox`)
**Viewports measured:** 1440×900 (desktop), 1280×720 (laptop), 390×844 (mobile)

All pass/fail values below are **measured** from the actually-rendered Plotly DOM
(SVG bounding boxes and computed colours), not asserted. Raw results are in
`docs/qa/playwright/qa_results_before.json` and `qa_results_after.json`; per-chart
PNG screenshots are under `docs/qa/playwright/{before,after}/<page>/<viewport>/`.

---

## 1. Dashboards found

| Page | Library | Charts | In QA scope |
|------|---------|--------|-------------|
| `docs/metrics.html` | Plotly.js (light theme) | 6 (test growth, tests/phase, module breakdown, phase LOC, version lineage, maturity radar) | ✅ |
| `docs/dmaic-metrics.html` | Plotly.js (dark theme) | 4 (DMAIC radar, phase scores, files/phase, activity snapshot) | ✅ |
| `docs/qplant/monitoring_dashboard/index.html` | static placeholders (no real chart lib) | 0 | ⏭️ excluded (no rendered charts) |
| `docs/cryo_dashboard_v0_3_0/index.html` | Chart.js | several | ⏭️ follow-up (see §6) |
| `docs/dow/index.html` | — | 0 (governance landing page) | ⏭️ n/a |

Root-level duplicates `cryo_dashboard_v0_3_0/index.html` and
`qplant/monitoring_dashboard/index.html` are byte-identical to the `docs/` copies
(`diff -q`), so no separate QA was needed.

---

## 2. The existing K-series checks (what each K does)

The team's HTML-quality contract is `triage/W58_3PR_A_DOW_PLAYGROUND_QA.yaml`
(`required_checks`). No literal `K1`…`K8` identifiers exist in the repos; this
suite maps that contract to the K-numbering the user referenced and **adds** two
accessibility checks (K9, K10) targeting the reported defects.

| ID | Name | What it measures |
|----|------|------------------|
| K1 | `no_console_error` | No console errors / no failed resource loads (favicon on the QA static server is ignored as a harness artifact; real ≥400 responses fail) |
| K2 | `no_page_error` | No uncaught JS exceptions |
| K3 | `no_body_horizontal_overflow` | `documentElement.scrollWidth ≤ innerWidth` (no horizontal scrollbar) |
| K4 | `navigation` | Primary nav links present (skipped if the page has no nav) |
| K5 | `readable_content` | Landmark/main text content present |
| K6 | `deep_link` | Every in-page `#anchor` resolves to an element id |
| K7 | `read_only_boundary` | Only allow-listed external hosts contacted (chart CDN/fonts); localhost QA host treated as same-origin |
| K8 | `chart_render` | Every chart container has a non-zero box **and** a rendered `<svg>` |
| **K9** | **`contrast` (NEW)** | Rendered text ≥ **4.5:1** and graphic marks ≥ **3:1** vs background (WCAG AA), computed from the live SVG fills |
| **K10** | **`legend_axis_no_overlap` (NEW)** | Legend bounding box does **not** intersect the x-axis tick labels or the x-axis title, at every viewport |

---

## 3. Defects reproduced (BEFORE) and fixed (AFTER)

### Defect A — low-contrast / non-colour-blind-safe chart colours (K9)

The light dashboard (`metrics.html`) used a palette with a pale yellow
(`#fbbc04`) and mid green/cyan on a near-white background, plus an adjacent
red-vs-green distinction (unsafe for deuteranopia/protanopia).

**Measured graphic contrast vs background, BEFORE (`metrics.html`, all viewports):**

| Series colour | Contrast | WCAG AA graphic (≥3:1) |
|---------------|----------|------------------------|
| `#fbbc04` (analyze, pale yellow) | **1.62:1** | ❌ |
| `#00bcd4` (infra, cyan) | **2.18:1** | ❌ |
| `#34a853` (measure, green) | **2.90:1** | ❌ |

Minimum graphic contrast measured: **1.62:1** → **FAIL**.

**AFTER** — a shared, colour-blind-safe palette (`docs/assets/abacus_chart_theme.js`),
no red-vs-green reliance (blue / green / dark-amber / red / purple / teal /
burnt-orange, each verified against its background):

| Page | Min text contrast | Min graphic contrast | K9 |
|------|-------------------|----------------------|----|
| `metrics.html` (light) | **16.1:1** | **4.45:1** | ✅ |
| `dmaic-metrics.html` (dark) | **16.02:1** | **5.53:1** | ✅ |

### Defect B — bottom legend overlapping the diagonal x-axis label / title (K10)

A horizontal bottom legend, placed with Plotly's default auto-position, is dropped
**between** the x-axis tick labels and the x-axis title, so the legend box overlaps
the title. A dedicated, re-runnable reproduction fixture captures this:

| Fixture | K10 overlap (legend vs x-title) | K9 min graphic | Result |
|---------|---------------------------------|----------------|--------|
| `docs/qa/fixtures/naive_bottom_legend.html` (naive) | **677.2 px²** | 1.71:1 | ❌ FAIL (both viewports-wide) |
| `docs/qa/fixtures/themed_bottom_legend.html` (shared theme) | **0 px²** | 4.92:1 | ✅ PASS (all 3 viewports) |

The fix lives in the shared theme's `layout()`: for a bottom legend it turns off
x-axis automargin (which otherwise makes the title chase the legend), pins the
x-axis title at a fixed standoff, and places the horizontal legend at a defined
negative paper-y below the title band, with a reserved bottom margin that scales
up when x labels are rotated. On the real `metrics.html` version-lineage chart
(now a bottom legend + "Version" x-title) the measured legend-vs-title overlap is
**0 px²** at 1440×900, 1280×720 and 390×844.

### Defect C (incidental) — mobile horizontal overflow (K3)

`metrics.html` overflowed horizontally at 390 px (body `scrollWidth` **601 px**),
caused by the wide statistics table and a `minmax(380px,1fr)` chart grid track.
Fixed by wrapping the table in an `overflow-x:auto` container and using
`minmax(min(380px,100%),1fr)`. AFTER: `scrollWidth ≤ innerWidth` → K3 ✅.

---

## 4. Before / after summary (per page × viewport)

| Page | Viewport | BEFORE | AFTER |
|------|----------|--------|-------|
| metrics.html | 1440×900 | FAIL: K9 (1.62:1) | **10/10 ✅** |
| metrics.html | 1280×720 | FAIL: K9 (1.62:1) | **10/10 ✅** |
| metrics.html | 390×844 | FAIL: K9 (1.62:1), K3 (601px) | **10/10 ✅** |
| dmaic-metrics.html | 1440×900 | 10/10 ✅ | 10/10 ✅ |
| dmaic-metrics.html | 1280×720 | 10/10 ✅ | 10/10 ✅ |
| dmaic-metrics.html | 390×844 | 10/10 ✅ | 10/10 ✅ |

**Totals:** BEFORE **56/60** checks → AFTER **60/60** checks.
Reproduction fixture: naive **24/30** (K9+K10 fail) → themed **30/30**.

> Note on K10 for the shipped pages: the original `metrics.html` legend was at the
> *top*, so it did not pre-overlap. The user's reported defect (bottom legend vs
> diagonal x-axis) is reproduced and measured on the dedicated fixture above; the
> shared-theme bottom-legend layout is what the shipped charts now use, verified at
> 0 px² overlap across all three viewports.

---

## 5. What changed

- **`docs/assets/abacus_chart_theme.js`** (new) — shared accessible Plotly theme:
  colour-blind-safe `light`/`dark` palettes (contrast-verified), `order()`,
  `layout(mode, overrides, {legend, tickangle})`, `deepMerge`, `config`.
- **`docs/metrics.html`** — loads the shared theme; replaced the inline palette
  and layout with the theme; version-lineage chart uses a non-overlapping bottom
  legend; added responsive table wrapper + grid fix.
- **`docs/dmaic-metrics.html`** — loads the shared theme (dark); rethemed all 4
  charts; conditional colours use contrast-safe green/amber/red (no red-vs-green).
- **`scripts/generate_metrics_charts.py`** — static SVG fallback palette aligned
  to the colour-blind-safe light palette; regenerated `docs/assets/charts/*.svg`.
- **`scripts/qa/dashboard_playwright_qa.py`** (new) — K1–K10 suite.
- **`docs/qa/fixtures/{naive,themed}_bottom_legend.html`** (new) — K10/K9
  regression fixtures.
- **`docs/qa/playwright/`** — before/after JSON results + 84 screenshots.

## 6. Follow-ups (not in this PR)

- `docs/cryo_dashboard_v0_3_0/index.html` uses **Chart.js**, not Plotly; the
  Plotly-specific K9/K10 DOM selectors do not apply. A Chart.js-aware pass (or a
  Chart.js adapter in the theme) is recommended as a separate change.
- `docs/qplant/monitoring_dashboard/index.html` renders static placeholders; it
  should either adopt real charts (then the shared theme) or be marked non-chart.

## 7. How to reproduce

```bash
# serve the docs dir (so dmaic's fetch() of api/dmaic_metrics.json works)
cd docs && python3 -m http.server 8082 &
# run the suite (system chromium)
python scripts/qa/dashboard_playwright_qa.py \
  --html http://localhost:8082/metrics.html http://localhost:8082/dmaic-metrics.html \
  --output-dir docs/qa/playwright --label after
```
