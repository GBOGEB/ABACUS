# P&ID Layer Structure Documentation

Both improved sheets use an identical, strict **7-level Inkscape layer
hierarchy**. Layers are authored bottom-to-top so that later layers draw above
earlier ones. Each layer carries an `inkscape:groupmode="layer"` attribute and a
human-readable `inkscape:label`, so the file opens with named, toggleable layers
in Inkscape / Illustrator.

```
SVG (A3 landscape, viewBox 0 0 1587.273 1122.430)
│
├── <defs>                          markers / gradients carried from source
│
├── L1  Border / Title block        id = layer-frame
│        • white sheet background
│        • double drawing border
│        • structured title block (project / title / dwg no / standard / rev)
│        • sheet header strip
│
├── L2  Equipment & Vessels         id = layer-equipment
│        • re-emitted structural geometry (vessel/tank/coupler outlines, frames)
│        • standard equipment glyphs (vessels, cavities, couplers, HX,
│          terminal points, pickup antennae, nodes) placed from segmentation
│
├── L3  Process Lines               id = layer-process
│        ├── L3.A      id = layer-line-A      Class A  4.5 K / 3 bar   (blue)
│        ├── L3.B      id = layer-line-B      Class B  3.5 K / 27 mbar (teal)
│        ├── L3.D      id = layer-line-D      Class D  40 K / 14 bar   (red)
│        ├── L3.E      id = layer-line-E      Class E  60 K / 13 bar   (olive)
│        ├── L3.WATER  id = layer-line-WATER  DI cooling water         (green)
│        ├── L3.QINFRA id = layer-line-QINFRA scope division     (dk green dash)
│        └── L3.AIR    id = layer-line-AIR    instrument air     (magenta d-dot)
│        (within each class: fills → junction nodes → lines, drawn in that order)
│
├── L4  Vacuum Barriers & Boundaries id = layer-vacuum
│        • dashed vacuum-vessel / scope-division boundaries
│        • "vacuum barrier" annotations
│
├── L5  Instrumentation Symbols     id = layer-instruments
│        • ISA-5.1 instrument bubbles (circle; dashed = protection/safety)
│        • valve bodies (hand / control / solenoid / relief)
│        • family fill: white=LB, salmon=RFCELL, light-blue=LBI
│
├── L6  ISA 5.1 Tags & Labels       id = layer-tags
│        • two-line bubble tags  ([variable][function] over [loop])
│        • valve tag labels
│
└── L7  Legend & Annotations        id = layer-legend
         • right column: instrument / valve / equipment symbol key + tag grammar
         • bottom band: process-line class legend (colour → T/P service)
```

## Layer purpose summary

| Layer | id | Purpose | Source of content |
|-------|----|---------|-------------------|
| L1 | `layer-frame` | Sheet, border, title block | Generated |
| L2 | `layer-equipment` | Vessels / equipment & structure | Re-emitted structure + segmentation equipment |
| L3 | `layer-process` (+ 7 class sub-layers) | Colour-segmented process piping | Re-extracted source geometry, recoloured |
| L4 | `layer-vacuum` | Vacuum / scope boundaries | Re-extracted dashed boundaries + segmentation |
| L5 | `layer-instruments` | ISA bubbles & valves | Segmentation instrument/safety coordinates |
| L6 | `layer-tags` | ISA-5.1 tags & labels | Segmentation tags |
| L7 | `layer-legend` | Legend & annotations | Generated |

## Process-line class → layer mapping

| Sub-layer id | Class | Service | Colour | Style |
|--------------|-------|---------|--------|-------|
| `layer-line-A` | A | 4.5 K / 3 bar — LHe supply | `#0033cc` | solid |
| `layer-line-B` | B | 3.5 K / 27 mbar — 2 K LP return | `#00a6bd` | solid |
| `layer-line-D` | D | 40 K / 14 bar — thermal shield | `#e00000` | solid |
| `layer-line-E` | E | 60 K / 13 bar — return / guard | `#8a8a00` | solid |
| `layer-line-WATER` | Water | DI cooling water | `#00a000` | solid |
| `layer-line-QINFRA` | QINFRA | scope division / infrastructure | `#006400` | dashed |
| `layer-line-AIR` | Inst. air | pneumatic 6 (5–7) bar(g) | `#c000c0` | dash-dot |

> Toggle any class sub-layer in Inkscape to isolate a single cryogenic service.
