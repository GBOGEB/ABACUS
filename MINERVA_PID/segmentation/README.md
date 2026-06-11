# MINERVA P&ID — Segmentation Package

Structured segmentation of the two MINERVA CryoCell P&ID SVGs into all requested
process-logic categories. Everything here is regenerated from the source SVGs in
`../svg_source/` by two pure-stdlib Python scripts.

## How to regenerate

```bash
cd segmentation
python3 segment_pid.py     # parse SVGs -> data/ JSON + CSV
python3 make_report.py     # data/ -> reports/ markdown + layer manifest
```

## Folder layout

```
segmentation/
├── segment_pid.py            # SVG parser + segmentation engine (transforms, tags, colors)
├── make_report.py            # report / layer-breakdown generator
├── data/                     # structured outputs (JSON + CSV) per sheet
│   ├── _summary.json             # headline counts for both sheets
│   ├── _all_segmentation.json    # full combined segmentation tree
│   ├── <SHEET>_segmentation.json # full per-sheet segmentation
│   ├── <SHEET>_instruments.csv       # ISA 5.1 tags (tag, prefix, variable, role, x, y, layer)
│   ├── <SHEET>_equipment.csv         # vessels / couplers / cavities / valves / terminal pts
│   ├── <SHEET>_process_lines.csv     # line segments by color class (A/B/D/E/WATER)
│   ├── <SHEET>_temperature_points.csv# TT/LT tags + annotated K values
│   ├── <SHEET>_pressure_points.csv   # PT/PZ/PL tags + annotated bar/mbar values
│   ├── <SHEET>_safety_devices.csv    # SV / RV / RD / PL / PZ
│   ├── <SHEET>_vacuum_barriers.csv   # barrier labels + dashed boundaries
│   ├── <SHEET>_color_groups.csv      # stroke-color histogram + meaning
│   └── <SHEET>_color_palette_full.csv# full fill+stroke color palette + meaning
└── reports/
    ├── process_logic_report.md   # human-readable segmentation report (all categories)
    ├── layer_breakdown.md        # layer-by-layer breakdown grouped by role
    └── layer_breakdown.json      # machine-readable layer manifest for reconstruction
```

`<SHEET>` is `QCELL-LB` or `RFCELL`.

## Segmentation categories produced

| # | Category | Where |
|---|----------|-------|
| 1 | Process lines by color class A/B/D/E (+ WATER) with T/P specs | `*_process_lines.csv`, report §2 |
| 2 | Equipment / components (cavities, couplers, vessels, tuners, terminal points …) | `*_equipment.csv`, report §3 |
| 3 | Instrumentation — ISA 5.1 tags by prefix / variable / role | `*_instruments.csv`, report §4 |
| 4 | Temperature & pressure measurement points (tagged + annotated values) | `*_temperature_points.csv`, `*_pressure_points.csv`, report §5 |
| 5 | Vacuum barriers + safety devices & interlocks | `*_vacuum_barriers.csv`, `*_safety_devices.csv`, report §6 |
| 6 | Color-to-meaning mapping + color groups | `*_color_groups.csv`, report §7 |
| 7 | Layer-by-layer breakdown for reconstruction | `reports/layer_breakdown.*` |

## Method notes

* **Coordinates** — every element coordinate is resolved to absolute SVG user space
  by accumulating the full CTM (matrix/translate/scale/rotate) down the group tree.
  The shared sheet space is `viewBox 0 0 1527.2727 1080` (ISO A3 landscape).
* **Tags** — parsed at the `<tspan>` token level (not just `<text>`), because the
  source stores co-located tags such as `EH514` + `TT514` as separate tspans inside
  one `<text>`. This recovers the full tag set (QCELL-LB: 221 unique, RFCELL: 45 unique).
* **Line classes** — bound to stroke color per the drawing legend
  (A 4.5 K/3 bar blue · B 3.5 K/27 mbar cyan · D 40 K/14 bar red · E 60 K/13 bar olive;
  green = coupler/DI-water utility). Confidence levels are recorded in the color tables.
* **ISA 5.1** — prefix dictionary maps each 2-letter prefix to measured variable +
  function (e.g. `TT` = temperature transmitter, `CV` = control valve, `SV` = safety valve).
  `HL` (heat load) and `CF` (CF-flange callout) are retained but flagged as annotations.
