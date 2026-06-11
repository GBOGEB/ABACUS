# MINERVA / MYRRHA P&ID Symbol Library — Legend Analysis

**Authoritative symbol reference** for the ongoing MINERVA P&ID reconstruction
work, extracted from the client/company standard legend sheet.

| Field | Value |
|---|---|
| Source document | `AD_01.16  SUP - PID General Legend Sheet.pdf` |
| Drawing number | **106889-PID00** (P&IDs 106889-PID01, sheets 1–9) |
| Doc number | MYR100PTF-0521 |
| Owner | **SCK CEN** — MYRRHA / MINERVA project |
| Revision | **A** (Released), 16/11/2023 |
| Sheet size / count | A1 · 9 legend sheets (10 PDF pages incl. cover) |
| Drawn by / Verified / Approved | Leysen J. / Bergmans G. / Voorderhake S. |

## Standards basis

The legend explicitly subordinates itself to published standards — capture
these deviations exactly, because **this company legend is the authoritative
source** and takes precedence over generic ISA-5.1 where they differ:

- **ANSI/ISA-5.1-2022** — instrument letter codes (subordinate to *Table 4.1*)
  and instrument symbolic representation (subordinate to *Table 5.1.1*).
- **ISO 10628** — process diagram house style (piping / equipment layout).
- **IEC 60617 (publication 617)** — electrical symbols (Sheet 7). Symbols
  marked with an asterisk `*` are **non-standard** (house additions). Relay
  function numbers marked `**` follow **ANSI C37.2**.
- **Tag numbering** — Primary Systems Naming Convention & Terminology
  *SCK CEN/36557490*; deviceclass mnemonics *SCK CEN/36793249*.

## Deliverables (this folder)

| File | Purpose |
|---|---|
| `legend_symbols.json` | Structured catalogue: every symbol + metadata, naming conventions, ISA letter code, bubble matrix, colour/stroke spec, usage notes, and the list of drawn SVG ids. |
| `symbol_library.svg` | Reusable SVG `<defs>` of **159 `<symbol>` elements** (zero-size, position:absolute). Reference any symbol with `<use href="#<id>"/>`. |
| `symbol_library_preview.svg` / `.png` | Human-readable contact sheet of every drawn symbol with its id (visual QA). |
| `build_legend_library.py` | Pure-stdlib generator that (re)produces all of the above. Re-run with `python3 build_legend_library.py`. |

**159 symbols are drawn** (schematic, standards-based geometry — not a pixel
copy of the CAD source) covering the complete process-P&ID scope of sheets 1–5.
The facility-specific (RIB line, beam optics) and electrical/fire sheets (6–9)
are catalogued at reference level in `reference_only_sets` (77 listed items).

## How to use the SVG library

```html
<!-- 1. embed/link symbol_library.svg once (it is defs-only, renders nothing) -->
<!-- 2. place any symbol, scaling freely; each symbol has its own viewBox -->
<svg width="900" height="400">
  <use href="#valve-gate"        x="100" y="100" width="60" height="36"/>
  <use href="#inst-A1"           x="220" y="90"  width="48" height="48"/>
  <use href="#act-diaphragm"     x="320" y="70"  width="70" height="70"/>
  <use href="#line-primary"      x="420" y="110" width="120" height="24"/>
</svg>
```

All ids are stable, lower-case, hyphen-separated, and namespaced by category
prefix (`line-`, `inst-`, `flow-`, `valve-`, `act-`, `eq-`, `conn-`, `iface-`,
`scope-`, `misc-`, `hvac-`). See `svg_library.drawn_ids` in the JSON for the
full list.

---

## 1. Line types (Sheet 1)

Line weight is significant and must be honoured:

| Symbol id | Name | Line weight | Style |
|---|---|---|---|
| `line-primary` | Primary line segment | **1 mm** | solid + arrow |
| `line-secondary` | Secondary line segment | **0.5 mm** | solid + arrow |
| `line-primary-future` | Primary, future extension | 1 mm | dash-dot + arrow |
| `line-secondary-future` | Secondary, future extension | 0.5 mm | dash-dot + arrow |
| `line-electrical-signal` | Electrical signal | 0.25 mm | dashed |
| `line-pneumatic-signal` | Pneumatic signal | 0.25 mm | double cross-hatch ticks |
| `line-hydraulic-signal` | Hydraulic signal | 0.25 mm | periodic L-marks |
| `line-software-signal` | Software / data signal | 0.25 mm | ring markers |
| `line-em-sonic-signal` | Guided EM / sonic signal | — | wave marker |
| `line-capillary` | Capillary tube | 0.25 mm | x cross marks |
| `line-hose` | Hose | — | continuous wavy |
| `line-pipe-insulated` | Pipe, insulated | — | hatch band |
| `line-tracer` | Tracer (heating/cooling) | — | parallel dashed trace |
| `line-jacketed` | Jacketed pipeline | — | outer jacket box |
| `line-heated-insulated` | Heated/cooled + insulated | — | hatch + trace |
| `line-hvac-supply` | HVAC air supply | 1 mm | solid |
| `line-hvac-return` | HVAC air return | 1 mm | dash-dot |
| `conn-connected-lines` | Connected lines | — | junction bridge |
| `conn-non-connected-lines` | Non-connected lines | — | hop / gap |

## 2. Instrumentation (Sheet 2 — ISA-5.1 matrix; Sheet 3 — flow elements)

### Bubble matrix (type × location) — `inst-<TYPE><ROW>`

The legend reproduces ISA-5.1 *Table 5.1.1* as a 4-column × 5-row matrix. Type
is the **enclosure shape**; location is the **line through the bubble**.

**Type columns**

| Col | Meaning | Shape |
|---|---|---|
| **A** | Shared display/control — Basic Process Control System (BPCS) | square enclosing a circle |
| **B** | Shared display/control — Safety Instrumented System (SIS) | square + circle + **diagonals** |
| **C** | Computer systems and software | **hexagon** |
| **D** | Discrete visualisation of instruments | plain **circle** (stadium/oval = two instruments → `inst-discrete-oval`) |

**Location rows** (accessibility line across the bubble)

| Row | Location | Line |
|---|---|---|
| **1** | Field-mounted; operator accessible | none |
| **2** | Front of central/main panel or console | single solid |
| **3** | Rear of central panel / cabinet behind panel | single dashed |
| **4** | Front of secondary/local panel | double solid |
| **5** | Rear of secondary/local panel / field cabinet | double dashed |

So e.g. `inst-A1` = field BPCS bubble, `inst-B2` = main-panel SIS,
`inst-C3` = behind-panel software, `inst-D5` = field-cabinet discrete.

### Instrument tag composition (Sheet 1)

Instrument tags are **not drawn explicitly**; they are composed:
1. take the **first line** of the tag of the element the instrument is attached to;
2. append the **top + bottom** parts shown inside the bubble, joined by `-`.

> Example: an `LS` bubble (LS / 1001) on valve `THSITS-GSRSEL:PNE-VALVE-1002`
> → instrument tag `THSITS-GSRSEL:PNE-LS-1001`.
> A `TT` bubble (TT / 202) on `THSITS-GSRSEL:PNE-PIPE-111`
> → `THSITS-GSRSEL:PNE-TT-202`.

### ISA letter code (Sheet 2, subordinate to ISA-5.1 Table 4.1)

First letter = measured/initiating variable (+ optional modifier); succeeding
letters = readout/passive, output/active, function modifier. The full table is
in `legend_symbols.json → categories.instrumentation.letter_code`. Highlights:
`F` flow, `L` level, `P` pressure, `T` temperature, `A` analysis,
`S` speed/safety, `Z` position/SIS; succeeding `T` transmit, `I` indicate,
`C` control, `R` record, `S` switch, `V` valve/damper, `E` sensor/element.

### In-line flow / primary elements (Sheet 3 — INSTRUMENT SYMBOLS)

`flow-sonic`, `flow-variable-area`, `flow-coriolis`, `flow-magnetic`,
`flow-vortex`, `flow-radiation`, `flow-orifice-generic`, `flow-nozzle`,
`flow-venturi`, `flow-positive-displacement`, `flow-turbine`.

## 3. Valves & actuators (Sheet 3)

The base body is the ISA two-triangle **bow-tie**. Lock/fail state codes are
written above the body:

| Code | Meaning | Code | Meaning |
|---|---|---|---|
| LC | Locked closed | NO | Open in normal operation |
| LO | Locked open | FC | Fail to closed (`act-fail-closed`) |
| NC | Closed in normal operation | FO | Fail to open (`act-fail-open`) |
| | | FA | Fail as it is (`act-fail-as-is`) |

**Valve bodies:** `valve-generic`, `valve-gate`, `valve-globe`, `valve-ball`,
`valve-needle`, `valve-butterfly`, `valve-angle`, `valve-three-way`,
`valve-check`, `valve-swing-check`, `valve-ball-check`, `valve-globe-check`,
`valve-tilting-disk-check`, `valve-piston-lift-check`,
`valve-y-piston-lift-check`, `valve-butterfly-check`, `valve-y-globe`,
`valve-safety`, `valve-safety-spring-angle`, `valve-pressure-reducing`,
`valve-balancing`, `valve-differential-pressure`.

**Actuating elements:** `act-diaphragm` (pneumatic), `act-piston`,
`act-hydraulic`, `act-solenoid`, `act-manual`, `act-motor-electric`,
`act-motor-dc`, `act-motor-pos-transmit`, `act-self-fcv/pcv/tcv/lcv`
(self-acting control valves), `act-fixed-spring`, `act-float`, `act-weight`,
`act-high-speed`, `act-fail-closed/open/as-is`.

## 4. Additional symbols

### Equipment (Sheet 4)
Pumps (`eq-pump-liquid`, `-centrifugal`, `-cavity`), compressors/vacuum
(`eq-compressor-vacuum`, `eq-turbo-compressor`), `eq-blower-fan`, heat
exchangers (`eq-heat-exchanger-general/-u-tube/-plate`), `eq-electric-heater`,
`eq-steam-generator`, `eq-chiller`, filters (`eq-gas-filter`, `-hepa`,
`eq-liquid-filter`, `eq-mixed-bed-filter`, `eq-ion-exchanger`,
`eq-charcoal-filter`), tanks (`eq-horizontal-tank`, `-vertical-tank`,
`-conical-tank`, `eq-hopper`), `eq-rupture-disc`, `eq-steam-trap`,
`eq-viewing-glass`, `eq-orifice-plate-line`.

### Connection / end types (Sheet 3)
`conn-threaded`, `conn-flanged-ends`, `conn-wafer`, `conn-welded-ends`,
`conn-quick-coupling`, `conn-hose`, `conn-flanged-connection`,
`conn-isolating-flange`, `conn-blind-flange`, `conn-screw-cap`,
`conn-welded-cap`, `conn-reducer`.

### Interfaces & scope boundaries (Sheet 1)
- `iface-termination-point` — diamond `TPXYYYY / ZZZ`. **X** = interface
  category: **B** building, **C** civil, **E** electrical, **G** compressed
  gasses, **H** HVAC, **L** liquid waste, **S** solid waste, **W** water;
  YYYY = unique number; ZZZ = next system/process.
- `iface-offpage-connector` — `XXXXX | 123456-PID01 | WWWWW`
  (unique name | interconnecting P&ID number | from/to process; ZZZZZ = medium).
- `iface-system-nfs` — interface between (non-primary) systems, e.g. `PBS1`.
- `scope-design-limit` — system & design-conditions limit (valve + diamond).
- `scope-code-jurisdiction` — piping **code jurisdiction break**
  (e.g. ASME VIII ↔ ASME B31.3); `*` denotes the supplier side. Design
  conditions per code letter are tabulated in boxes on each drawing.

### Miscellaneous / specialty (Sheet 5)
`misc-reducer`, `misc-vfd`, `misc-flame-arrestor`, `misc-dielectric-joint`,
strainers (`misc-strainer-y/-t/-cone`), `misc-sampling-point`,
`misc-atmospheric-vent`, `misc-spray-nozzle`, `misc-agitator`,
`misc-compensator`, `misc-funnel`, `misc-special-joint`.

### HVAC (Sheet 5)
`hvac-shutoff-damper`, `hvac-parallel-damper`, `hvac-opposed-damper`,
`hvac-fan-general`, `hvac-radiator`, `hvac-heating-coil`, `hvac-cooling-coil`,
`hvac-filter`, `hvac-supply-terminal`, `hvac-exhaust-terminal`.

## Reference-only sets (Sheets 6–9, not redrawn)

These belong to facility-specific and electrical/fire single-line drawings,
outside the core process-P&ID symbol scope. They are listed in
`legend_symbols.json → reference_only_sets`:

- **MINERVA RIB line specific elements** (Sheet 6) — pillow seal, clamped/thin/
  cooled windows, collimator, Hall sensor, magnet, target, bellows, etc.
- **MINERVA beam optics** (Sheet 6) — beam position/halo/profile/tail monitors,
  quadrupole, wire scanner, steering plates, Faraday cup, electrostatic bender,
  mirrors, slits, beam shutter/dump, optical diagnostics, laser/ABU/FCU, etc.
- **Electrical symbols** (Sheet 7) — IEC 60617; transformers, CTs, breakers,
  relays, contacts, meters, sounders, etc. (`*` = non-standard, `**` = ANSI C37.2).
- **Fire detection / extinguishing / safety** (Sheets 8–9) — detectors,
  sounders, extinguishing controls, fire separations E30/EI30/EI60/EI120,
  emergency / life-safety pictograms.

---

## Reconciliation with `generator/symbols.py`

The hand-built ISA-5.1 primitives in `pid_project/generator/symbols.py` remain
valid but are **superseded by this authoritative legend** where they differ.
Recommended adoption path for the reconstruction:

| `symbols.py` primitive | Authoritative legend equivalent | Note |
|---|---|---|
| `bubble()` (plain circle) | `inst-D1` (discrete, field) | field discrete instrument |
| `bubble_square()` | `inst-A1` (square + circle) | BPCS shared display |
| dashed bubble (`is_safety`) | `inst-B*` (SIS, square+circle+diagonals) | **legend uses diagonals for SIS, not a dashed outline** — align to `inst-B*` |
| `valve(kind="gate")` | `valve-gate` | bow-tie body matches |
| `valve(kind="control")` | `act-diaphragm` | diaphragm-actuated control valve |
| `valve(kind="solenoid")` | `act-solenoid` | matches |
| `valve(kind="relief")` | `valve-safety` / `valve-safety-spring-angle` | use angle type for spring-loaded relief |
| `vessel()` | `eq-vertical-tank` / `eq-horizontal-tank` | dished-end vessels |
| `heat_exchanger()` | `eq-heat-exchanger-general` | circle + zig-zag |
| `terminal_point()` | `iface-termination-point` | **legend uses a diamond `TPXYYYY/ZZZ`, not a crossed circle** — switch to diamond |

**Key deviations to apply going forward**

1. **SIS instruments** use a square+circle with **diagonal lines** (`inst-B*`),
   not a dashed outline.
2. **Termination points** are **diamonds** carrying `TPXYYYY / ZZZ`, with the
   category letter set drawn from {B,C,E,G,H,L,S,W}.
3. **Line weights are normative**: primary = 1 mm, secondary = 0.5 mm, all
   signal lines = 0.25 mm. Future/proposed lines use dash-dot.
4. **Off-page continuation** uses the arrow-box connector with the
   interconnecting P&ID number (`123456-PID01`) and medium.
5. **Code jurisdiction breaks** are explicit symbols (valve + diamond + code
   letters) and must be placed wherever the piping code changes.

> Regenerate everything with: `python3 standards/build_legend_library.py`
