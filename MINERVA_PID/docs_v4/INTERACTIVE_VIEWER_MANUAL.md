# MINERVA CryoCell P&ID — Interactive Viewer Manual (v4)

**Project:** MINERVA CryoCell — SCK CEN (MYRRHA/MINERVA Phase 1)
**Consultant:** Mott MacDonald, Bristol UK — MMD 411066
**Standard:** SCK CEN AD_01.16 · Status: S2 — FOR ACCEPTANCE · RESTRICTED

---

## 1. What it is

`HTML_INTERACTIVE/` is a self-contained, browser-based viewer for the four MINERVA
CryoCell P&ID sheets. It lets a reviewer explore the layered SVGs without any CAD
software: toggle layers, apply default views, search tags, switch colour/mono, zoom,
pan and export PNGs.

```
HTML_INTERACTIVE/
├── index.html              ← landing page (sheet gallery)
├── <sheet>.html  (×4)      ← per-sheet interactive viewer
├── css/viewer.css
├── js/pid-viewer.js        ← layer control, views, zoom/pan, export
├── js/search.js            ← tag search & highlight
└── assets/
    ├── *_v4.svg  (×16)     ← the drawing layers
    └── thumbs/*.png (×4)   ← gallery thumbnails
```

---

## 2. Launching the viewer

Because the viewer loads SVG assets via `fetch()`, it must be served over HTTP — opening
`index.html` directly with a `file://` path will be blocked by the browser's
same-origin policy.

From inside the `HTML_INTERACTIVE/` directory run a simple static server, e.g.:

```bash
cd HTML_INTERACTIVE
python3 -m http.server 8137
```

Then open `http://localhost:8137/` in your browser.

> **Note on localhost:** When this viewer is launched on the Abacus AI Agent machine,
> *that* localhost refers to localhost of the Abacus AI Agent computer running the
> application, **not your local machine**. To run it yourself, download all files using
> the **Files** icon at the top right, navigate inside the downloaded folder, and serve
> the `HTML_INTERACTIVE` directory locally as shown above.

---

## 3. Landing page

The landing page (`index.html`) shows a gallery of the four sheets with thumbnails and
metadata (drawing number, title, revision). Click any sheet to open its interactive
view.

---

## 4. Controls (per-sheet view)

### 4.1 Layer panel
- Each of the 24 layers has a checkbox; class layers show a **colour swatch** matching
  the printed legend (see Colour & Legend Guide §2).
- Layers are grouped (frame/title, process pipes, equipment, instruments, annotation,
  reference) for quick navigation.
- Toggling a layer immediately shows/hides it in the drawing.

### 4.2 Default views (presets)
- The **Views** selector applies one of the five presets: FULL, PROCESS, CONTROL,
  MAIN, PRINT_MONO (documented in `DEFAULT_VIEWS_DOCUMENTATION.md`).
- Selecting a preset updates the layer checkboxes; you can then fine-tune individual
  layers on top of the preset.

### 4.3 Tag search
- Type a tag (e.g. `CV500`) in the **Search** box.
- Matching tags are highlighted and the view **pans/zooms to the first match**.
- Use the next/prev controls (or repeated Enter) to cycle through multiple matches.

### 4.4 Mono toggle
- Switches the drawing between **colour** and **monochrome** rendering. In mono mode,
  classes remain identifiable via inline line names and line-weight/dash differences.

### 4.5 Style toggle
- Switches between the filled/coloured presentation and a line-weight-only
  presentation.

### 4.6 Zoom & pan
- **Scroll wheel** (or zoom buttons) to zoom; **click-drag** to pan.
- A reset/fit control returns to the full-sheet view.

### 4.7 Valve overlay
- Enabling the `08B_Valves_HORIZONTAL_OVERLAY` layer shows the alternative horizontal
  valve representation on top of the standard symbols (off by default).

### 4.8 PNG export
- The **Export PNG** button rasterises the current view (with the current layer
  visibility, mono/style state and zoom) and downloads it as a PNG.

---

## 5. Tips

- Start from a **default view**, then toggle individual layers for a focused review.
- Use **PRINT_MONO** + **Export PNG** to verify how a sheet will look on a
  black-and-white A3 plot before issuing.
- Tag search is the fastest way to locate a specific valve or instrument across a busy
  sheet.

---

## 6. Relationship to the SVG/PDF set

The viewer renders the same `*_v4.svg` files delivered in `output_v4/`. The PDF set
(A3 landscape, 420 × 297 mm) is the formal issue format; the HTML viewer is a review
aid. Layer names, default views and class colours are identical across all formats.
