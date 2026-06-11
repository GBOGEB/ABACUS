# MINERVA CryoCell P&ID v3 — Layer Naming Standard

**Project:** MINERVA CryoCell — SCK CEN (MYRRHA / MINERVA Phase 1)
**Standards:** ANSI/ISA-5.1-2022 · ISO 10628 · IEC 60617 · SCK CEN **AD_01.16**

Every v3 SVG uses the same ordered, hierarchical, self-describing Inkscape
layer set. Layers are named `NN[_Sub]_Category_Detail` so they sort correctly
and read unambiguously in Inkscape, Illustrator and any SVG editor. Drawing
order is bottom (background) to top (annotations).

### Layer table

| # | Layer name | Purpose | Default colour | Line weight |
|---|------------|---------|----------------|-------------|
| 00 | `00_Background_TitleBlock` | Sheet frame, header strip, compact bottom title block | Black | 0.7–2.0 mm |
| 01 | `01_Scope_Boundaries` | AD_01.16 termination-point (TP) scope diamonds | Per category | 1.2 mm |
| 02 | `02_Structure_Reference` | Faded reference geometry from source | Grey | 0.5 mm |
| 03 | `03_Equipment_Vessels` | Cavities, couplers, HX, vessels, tuners, antennae | Black / brown | 0.5 mm |
| 04A | `04A_Piping_PRIMARY_40K` | 40 K shield **trunk** lines | Red `#e00000` | **1.0 mm** |
| 04B | `04B_Piping_BRANCHES_40K` | 40 K shield **branch** lines | Red `#e00000` | 0.7 mm |
| 05A | `05A_Piping_PRIMARY_4p5K` | 4.5 K supply **trunk** lines | Blue `#0033cc` | **1.0 mm** |
| 05B | `05B_Piping_BRANCHES_4p5K` | 4.5 K supply **branch** lines | Blue `#0033cc` | 0.7 mm |
| 06A | `06A_Piping_PRIMARY_2K` | 2 K return **trunk** lines | Cyan `#00a6bd` | **1.0 mm** |
| 06B | `06B_Piping_BRANCHES_2K` | 2 K return **branch** lines | Cyan `#00a6bd` | 0.7 mm |
| 07 | `07_Piping_SECONDARY_Water` | DI cooling-water secondary circuit | Green `#00a000` | 0.5 mm |
| 08 | `08_Piping_OUTSIDE_SCOPE` | 60 K guard / infrastructure / instrument air | Grey dashed | 0.35 mm |
| 09 | `09_Valves_Mechanical` | CV/HV/SV/RV/MV/PL valves + bellows | Black | 1.0 mm |
| 10 | `10_Signals_Pneumatic` | Pneumatic instrument signals | Purple `#7a00a0` | **0.25 mm** |
| 11 | `11_Signals_Electric` | Electric instrument signals | Blue `#00529b` | **0.25 mm** |
| 12 | `12_Signals_Hydraulic` | Hydraulic instrument signals | Amber `#a06a00` | **0.25 mm** |
| 13 | `13_Instruments_Sensors` | ISA instrument bubbles + heat-load markers | Per family | 0.3 mm |
| 14 | `14_Instruments_Control_DIS` | DIS interlock, tuner limit switches, Lemo connectors | Black / red | 0.3–1.6 mm |
| 15 | `15_Tags_Instruments` | All tag text | Black | — |
| 16 | `16_Legend_TOGGLEABLE` | Compact legend overlay (**off by default**) | Mixed | — |
| 17 | `17_Notes_TOGGLEABLE` | Buffer/scope notes and callouts | Green / red | — |

### Piping hierarchy — PRIMARY vs BRANCH

Within each cryogenic class (40 K, 4.5 K, 2 K) the source geometry is split into
two sub-layers:

* **PRIMARY** (`…A`) — the trunk/header runs, drawn at **1.0 mm**.
* **BRANCH** (`…B`) — the take-offs and short connections, drawn at **0.7 mm**.

The classifier ranks every line segment by its on-sheet length (CTM-resolved).
Segments at or above the 55th percentile of their class become PRIMARY; the rest
become BRANCH. Junction nodes and coloured fills travel with the PRIMARY layer.
Secondary (DI water) is a single 0.5 mm layer; out-of-scope services are a single
0.35 mm grey **dashed** layer.

### Signal-line differentiation (all 0.25 mm)

To stay legible on monochrome plots each signal type uses a distinct dash
pattern, following the intent of AD_01.16 Sheet 1/9:

| Layer | Type | Pattern |
|-------|------|---------|
| 10 | Pneumatic | long dash **+ // cross-tick** hatch marks |
| 11 | Electric | fine **dotted** |
| 12 | Hydraulic | **dash-dot** |

> **Note on AD_01.16 vs the brief.** AD_01.16 represents *electrical* as dashed,
> *pneumatic* with cross-ticks and *hydraulic* with an "L" mark. The brief asked
> for pneumatic = dashed, electric = dotted, hydraulic = dash-dot. v3 keeps all
> three **visually distinct** and leans on the AD_01.16 cross-tick for pneumatic
> while using dotted for electric (clearest on A3). The mapping is recorded here
> and in the on-sheet legend so there is no ambiguity.

### Monochrome (`_MONO`) variants

Each sheet is also issued as a pure black-and-white `_MONO` SVG/PDF:

* all piping is **black**, differentiated only by the weight hierarchy above;
* out-of-scope services stay **dashed**; signals keep their dash patterns;
* instrument bubbles are **white-filled with black outline**;
* arrowhead / junction markers are recoloured to black.

### Scope categories (AD_01.16)

Termination-point diamonds carry three compartments: `TP` / `<letter><number>` /
`<next system>`. Category letters:

`B` = Building · `C` = Civil · `E` = Electrical · `G` = Compressed gasses ·
`H` = HVAC · `L` = Liquid waste · `S` = Solid waste · `W` = Water
