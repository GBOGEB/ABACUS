# MINERVA P&ID v4 - QA Report (Phase 6)

- High-resolution PNG renders: **16** (at 3000px wide / approx. 215 DPI on A3).
- Colour-vs-mono comparison strips: **8**.
- v3-vs-v4 grid: 1.
- Alignment overlays (thirds grid + 3% safe margin): **2**.

## Checks performed

1. **Frame containment** - all content stays inside the 3% safe-margin box; title block and border are intact on every variant.
2. **Colour/mono parity** - mono variants carry identical geometry; legibility maintained through inline line NAMES and white-boxed tags.
3. **Tag overlap** - instrument and valve tags render in opaque white boxes on the front-most layer (no pipe show-through).
4. **Edge terminal points** - TP assemblies anchor to the left (FROM) and right (TO) page edges per AD_01.10.

All 16 SVG variants validated as well-formed XML and exported to A3 PDF (1190.55 x 841.89 pt).