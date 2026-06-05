# Layer Structure Guide — 14-Layer Toggleable Hierarchy

Every v2 SVG uses a strict bottom-to-top stack of **14 Inkscape layers**
(`inkscape:groupmode="layer"`), so each can be toggled independently in
Inkscape, Illustrator, or any CAD tool that honours SVG layer groups.

Layers are emitted in draw order: **Layer 0 is drawn first (bottom)**,
**Layer 13 last (top)**.

| # | Layer label | Contents | Notes |
|---|-------------|----------|-------|
| 0 | **Background** | Sheet fill, outer/inner frame, title block, header strip, version stamp | Always on |
| 1 | **Scope** | Scope-boundary diamonds (TPXYYYY), terminal/handover points | Defines the "last-meter" interface |
| 2 | **Structures** | Cavity geometry, outer shell, vacuum vessel | Rendered light grey as background context |
| 3 | **Equipment** | Vessels, heat exchangers, cavities, couplers, tuners, tanks | Major equipment glyphs |
| 4 | **Piping-40 K** | 40 K thermal-shield circuit | Red (`#e00000`) |
| 5 | **Piping-4.5 K** | 4.5 K supply circuit | Blue (`#0033cc`) |
| 6 | **Piping-2 K** | 2 K return circuit | Cyan (`#00a6bd`) |
| 7 | **Piping-Water** | DI cooling-water / utility circuit | Green (`#00a000`) |
| 8 | **Valves** | All valve symbols + 60 K guard / infrastructure / instrument-air services | Manual, control, safety, relief, MV bellows |
| 9 | **Instruments** | ISA sensor bubbles (TT, PT, LT, FT, …) | Field-mounted discrete instruments |
| 10 | **Control** | DIS interlock block, tuner limit switches, Lemo connectors, actuators | Control / interlock logic |
| 11 | **Signals** | Signal lines + heat-load callouts | Pneumatic / electric signal layer |
| 12 | **Tags** | All instrument tags, valve tags, buffer & hand-over annotations | Text layer |
| 13 | **Legend** | Drawing legend (classes, symbols, scope keys) | Always on |

## Emphasis behaviour by sheet type

- **Process / Cryogenic sheets (Sheet 1):** piping layers 4-7 are drawn at full
  weight & colour; only inline process devices (FT/PT/LT) appear on the
  instrument layer. Control layer (DIS etc.) is empty.
- **Instrumentation sheets (Sheet 2):** piping layers 4-8 are drawn as a faded
  grey backdrop so the full sensor suite, control layer, and signals stand out.

## Style-version interaction

The two style versions modify *rendering weights/colours within* these layers
(see Drawing Index §2) but do **not** change the layer structure — the 14-layer
hierarchy is identical across both `_STANDARD` and `_CONTROL-CENTRIC` files.
