# MINERVA CryoCell P&ID v3 — A3 Printing Guide

All v3 sheets are authored at true **A3 landscape — 420 × 297 mm** with a
`viewBox` of `0 0 1587.273 1122.430` user units (≈ 3.779 units/mm). The PDFs are
already A3; the SVGs declare `width="420mm" height="297mm"`.

### Recommended output

| Use | File | Notes |
|-----|------|-------|
| Colour review / plotting | `*_STANDARD.pdf` | Full colour, process emphasised |
| Control-room / signal review | `*_CONTROL-CENTRIC.pdf` | Process greyed back, signals emphasised |
| Black-and-white plotting | `*_STANDARD_MONO.pdf` / `*_CONTROL-CENTRIC_MONO.pdf` | Line-weight + dash differentiation only |

### Printer settings

* **Paper:** A3 (420 × 297 mm), **landscape**.
* **Scaling:** *100 % / Actual size* — do **not** "fit to page" (it rescales line
  weights and defeats the calibrated 0.25–1.0 mm hierarchy).
* **Margins:** borderless or ≤ 6 mm; the sheet already carries a 6 mm frame margin.
* **Colour:** use the `_MONO` files for B/W printers rather than letting the
  driver desaturate — the mono files are designed to read without colour.

### Text legibility (verified minimums @ A3)

| Element | Target | v3 setting |
|---------|--------|------------|
| Main equipment / line tags | ≥ 2.5 mm | 2.6 mm |
| Instrument bubble text | 2.0 mm | ~1.85–2.0 mm |
| Line / note callouts | 2.2 mm | 2.2 mm |
| Legend text | 1.8 mm | 1.8 mm |

### Line-weight hierarchy (at 100 %)

* Primary cryo trunk **1.0 mm** → branch **0.7 mm**.
* Secondary (DI water) **0.5 mm**.
* Out-of-scope services **0.35 mm** (dashed).
* All instrument signals **0.25 mm** (pneumatic dash+//, electric dotted,
  hydraulic dash-dot).

### Regenerating PDFs from SVG

```bash
cd pid_project
python3 -c "import glob,cairosvg; [cairosvg.svg2pdf(url=s, write_to=s[:-4]+'.pdf') for s in glob.glob('output_v3/*/*.svg')]"
```

`cairosvg` preserves the 420 × 297 mm page size (≈ 1190.55 × 841.89 pt).

### Tip — declutter before printing

Use a **default view** (see `DEFAULT_VIEWS_GUIDE.md`) to hide layers you do not
need, and turn the `16_Legend_TOGGLEABLE` layer **on** if the print is going to
someone unfamiliar with the symbol set.
