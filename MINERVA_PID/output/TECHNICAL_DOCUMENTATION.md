# MINERVA CryoCell P&ID — Reproduction & Standardisation Report

**Project:** MINERVA CryoCell (SCK CEN / 84836013)
**Deliverable:** Reproduced & improved Piping & Instrumentation Diagrams
**Standards applied:** ISO 10628 (flow diagrams) · ANSI/ISA-5.1 (instrumentation symbols & identification)
**Sheet format:** ISO A3 landscape — 420 mm × 297 mm
**Version:** v2.0 (rebuilt)

---

## 1. Scope

Two source P&ID sheets were reproduced and improved:

| Key | Source file | Title |
|-----|-------------|-------|
| QCELL-LB | `PFD-PID MINERVA QCELL-LB.svg` | QCELL / LB cryogenic flow scheme (full) |
| RFCELL | `PFD-PID MINERVA RFCELL seen by ACR.svg` | RFCELL DI-water / coupler module |

The rebuild is **data-driven**: it re-uses the validated segmentation produced
in the previous project stage (`segmentation/data/*.json`) for all instrument,
equipment, safety and vacuum elements, and re-extracts the original process-line
geometry with fully resolved transforms so the pipe network is preserved exactly
while being recoloured and re-weighted to standard.

### Output files (`output/`)

| File | Description |
|------|-------------|
| `PID_QCELL-LB_improved.svg` / `.pdf` | Improved QCELL-LB sheet (A3) |
| `PID_RFCELL_improved.svg` / `.pdf` | Improved RFCELL sheet (A3) |
| `TECHNICAL_DOCUMENTATION.md` | This report |
| `LAYER_STRUCTURE.md` | Layer hierarchy reference |
| `previews/*.png` | Raster previews |

---

## 2. How the diagrams were rebuilt

The generator lives in `generator/`:

| Module | Role |
|--------|------|
| `svg_extract.py` | Walks the source SVG, accumulates the full CTM for every node, captures every graphic primitive with resolved transform, stroke/fill colour, width, dash and owning layer, and **bins** it (process line by class, structure, instrument-bubble candidate, dashed boundary, coloured fill/node). |
| `symbols.py` | ISA-5.1 / ISO-10628 symbol primitives: instrument bubbles, valves (manual / control / solenoid / relief), vessels, cavity/coupler bodies, heat exchangers, terminal points, heat-load callouts, junction nodes. |
| `build_pid.py` | Composes the A3 sheet: frame + title block, equipment, colour-segmented process lines, vacuum barriers, fresh ISA instrument bubbles, ISA tags and the full legend. Emits SVG and feeds the PDF conversion. |

Re-run with:

```bash
cd generator && python3 build_pid.py
```

---

## 3. Improvements made

### 3.1 Sheet, border & title block
- Re-laid out on a **true ISO A3 landscape** canvas (420 × 297 mm,
  `viewBox 0 0 1587.273 1122.430`, ratio 1.41414).
- Added a **double-line drawing border** and a structured **title block**
  (project, title, drawing number, standard, revision).
- The original drawing content is mapped uniformly into a reserved content
  region so the border, the right-hand legend column and the bottom class-legend
  band never overlap the schematic.

### 3.2 Layer hierarchy (ISO logical structure)
The drawing is organised into the requested 7-level Inkscape layer hierarchy with
process lines split into colour/class sub-layers — see `LAYER_STRUCTURE.md`.

### 3.3 ISA-5.1 instrumentation
- Every field instrument is redrawn as a **standard circular bubble** with a
  **two-line tag** (measured-variable + function letters over loop number),
  e.g. `TT / 514`.
- **Tag grammar** follows ISA-5.1: first letter = measured variable, succeeding
  letters = function:
  - `T` Temperature, `P` Pressure, `L` Level, `F` Flow, `E` Electrical,
    `A` Analysis, `S` Speed/Safety, `R` Radiation …
  - `T` Transmitter, `I` Indicator, `S` Switch, `V` Valve, `E` Element …
  - Examples present: `TT` temperature transmitter, `PT` pressure transmitter,
    `LT` level transmitter, `FT` flow transmitter, `LS` level switch,
    `EH` electric heater, `PZ/FZ` safety variants, `AP` analysis/antenna probe.
- **Bubble fill encodes the instrument family** (per the source legend):
  white = LB cryo instrument, salmon = RFCELL instrument, light-blue =
  LBI-specific instrument.
- **Protection / safety instruments** (`SV`, `RV`, `PL`, `PZ`, `FZ` …) use a
  **dashed bubble outline** — the ISA convention for interlock/safety functions.
- **Valves** are drawn with correct bodies and actuators:
  hand valve (hand-wheel), control valve (diaphragm), solenoid valve (`S` box),
  relief valve (angle/spring) — replacing generic bubbles for `HV/CV/SV/RV`.

### 3.4 Colour segmentation of process lines
The original used inconsistent / very light screen colours. Lines are now
recoloured to a **consistent, print-legible palette**, one Inkscape sub-layer per
class, with standard weights and line styles:

| Class | Service | Colour | Line style |
|-------|---------|--------|-----------|
| A | 4.5 K / 3 bar — LHe supply | blue `#0033cc` | solid, heavy |
| B | 3.5 K / 27 mbar — 2 K LP return | teal `#00a6bd` | solid, heavy |
| D | 40 K / 14 bar — thermal shield | red `#e00000` | solid, heavy |
| E | 60 K / 13 bar — return / He-guard | olive `#8a8a00` | solid, heavy |
| Water | DI cooling water (coupler / FREIA) | green `#00a000` | solid, medium |
| QINFRA | infrastructure scope division | dark green `#006400` | dashed |
| Inst. air | pneumatic 6 (5–7) bar(g) | magenta `#c000c0` | dash-dot |

Bulky solid colour blocks in the source were converted to **translucent service
zones** (22 % fill) so they read as highlighting rather than obscuring the
schematic; pipe junctions are drawn as small solid nodes in the class colour.

### 3.5 Vacuum barriers & boundaries
Dashed structural boundaries (vacuum vessel / scope divisions) are collected into
a dedicated **L4 — Vacuum Barriers & Boundaries** layer with a standard dashed
style, plus the explicit *“vacuum barrier”* annotation.

### 3.6 Legend enhancement
A comprehensive two-part legend was added:
- **Right column:** instrument-bubble key (families + safety), tag-grammar note,
  valve & equipment symbols, heat-load callout, terminal/scope point, vacuum
  boundary.
- **Bottom band:** process-line class legend mapping each colour to its
  temperature/pressure service and description.

### 3.7 Quality
- Standardised line weights and rounded joins/caps.
- Minimum on-sheet text sizes kept legible (≈ 6 pt and up).
- Suppressed the messy/overlapping original bubble circles and redrew clean ones.
- Markers (arrowheads) and gradient/def references from the source are carried
  over so flow-direction arrows are preserved.

---

## 4. Element inventory (from segmentation)

| Metric | QCELL-LB | RFCELL |
|--------|----------|--------|
| Instrument tags | 230 (221 unique) | 67 (45 unique) |
| Equipment items | 42 | 2 |
| Safety devices | 13 | 6 |
| Vacuum barriers | 5 | 0 |
| Temperature points | 77 | 23 |
| Pressure points | 28 | 11 |
| Process-line classes | A,B,D,E,Water,QINFRA,Air | A,B,D,E,Water,QINFRA,Air |

Instrument prefixes encountered (ISA-5.1):
`TT, TE, PT, PI, PZ, LT, LS, LI, FT, FI, FZ, EH, SM, RS, AP, AA, AD, ED,
CV, HV, SV, RV, PL, KW, AK, MV, HL, HX, CF`.

---

## 5. Limitations & notes
- The source sheets are intentionally **very dense**; the rebuild preserves the
  real topology and instrument positions rather than re-routing pipes, so
  localised crowding inherent to the originals remains.
- Colour-to-class mapping is taken from the drawing legend; a few low-confidence
  source colours (grey shading, near-black) are treated as structure.
- Geometry fidelity is exact (transforms are baked); symbology and styling are
  the standardised improvement layer.
