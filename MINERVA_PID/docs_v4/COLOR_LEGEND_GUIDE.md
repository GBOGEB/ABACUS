# MINERVA CryoCell P&ID — Colour & Legend Guide (v4)

**Project:** MINERVA CryoCell — SCK CEN (MYRRHA/MINERVA Phase 1)
**Consultant:** Mott MacDonald, Bristol UK — MMD 411066
**Client:** SCK CEN, Boeretang 200, 2400 Mol, Belgium
**Standard:** SCK CEN AD_01.16 (P&ID conventions)
**Status:** S2 — FOR ACCEPTANCE · RESTRICTED

---

## 1. Purpose

This guide explains the colour coding, line-weight conventions and legend tables used
across the v4 MINERVA CryoCell P&ID set. It applies to all four sheets
(QCELL `=NA.PS01_PFB712` and RFCELL `=NA.PS01_PFB713`, process + utilities).

The drawing set is designed to be read in **two complementary modes**:

- **Colour (STD) mode** — fluid/service class is identified primarily by line colour.
- **Mono mode** — for black-and-white printing, class is identified by **inline pipe
  names** printed directly on the run, plus differentiated line weights and dash
  patterns. No information is lost when colour is removed.

---

## 2. Fluid / Service Class Colours

Each process class has a dedicated colour, design temperature and design pressure.
These are summarised in the on-sheet **Class Legend** table (layer `16_Legend`).

| Class | Service                | Colour          | Hex      | Design Temp | Design Press |
|-------|------------------------|-----------------|----------|-------------|--------------|
| D     | 40 K helium supply     | Red             | #e00000  | 40 K        | 14 bar       |
| A     | 4.5 K helium           | Blue            | #0033cc  | 4.5 K       | 3 bar        |
| B     | 2 K helium             | Cyan            | #00a6bd  | 2 K         | 27 mbar      |
| WATER | Cooling water (CW)     | Green           | #00a000  | Ambient     | 4 bar        |
| E     | 60 K helium shield     | Olive           | #8a8a00  | 60 K        | 13 bar       |
| AIR   | Instrument / plant air | Magenta         | #c000c0  | Ambient     | 6 bar (g)    |

> The colour swatches in the interactive HTML viewer's layer panel match these hex
> values exactly, so on-screen toggling reflects the printed legend.

---

## 3. Mono-Mode Line Weights & Names

When colour is suppressed (mono toggle / black-and-white printing), classes are
distinguished by:

1. **Inline pipe names** — the line identifier is printed *on* the pipe run at regular
   intervals so the reader never has to trace a line back to a colour key. Examples:
   - `40K PRIMARY` (Class D supply header)
   - `2K0-4"-PAC1-BA` (Class B, 4-inch, line tag PAC1-BA)
2. **Line weight** — primary process headers are drawn heavier than branch/utility runs.
3. **Dash pattern** — signal and pneumatic lines use distinct dashed/dotted patterns
   (see Signal Legend below).

This guarantees AD_01.16 legibility on a monochrome A3 plot.

---

## 4. Signal / Connection Legend

The **Signal Legend** table (also on layer `16_Legend`) documents instrument and
connection line styles:

| Line style            | Meaning                                  |
|-----------------------|------------------------------------------|
| Solid heavy           | Major process pipe                        |
| Solid light           | Minor process / branch pipe               |
| Long dash             | Electrical signal                         |
| Dash-dot              | Software / data link                      |
| Fine dotted           | Pneumatic / capillary                     |
| Double slash break    | Pipe class / spec break                    |

---

## 5. ISA Instrument Bubbles & Tag Boxes

- Instrument bubbles follow ISA-5.1: circle (field), circle-in-square (DCS/shared),
  hexagon (computer/PLC), with a horizontal bar for panel-mounted devices.
- Every valve and instrument tag is rendered inside a **white tag box** so the text
  stays legible where it overlaps pipes, equipment or hatching — in both colour and
  mono modes.

---

## 6. Edge Terminal Points

Off-sheet connections terminate at the **drawing frame edge** with a cloud-style
terminal point carrying the continuation reference (AD_01.10 style). Terminal points
are colour-classed in STD mode and labelled with the line name in mono mode.

---

## 7. Toggling Colour in the Interactive Viewer

In `HTML_INTERACTIVE/index.html`:

- **Mono toggle** — switches the whole set between colour and monochrome rendering.
- **Style toggle** — switches between the filled/coloured presentation and a
  line-weight-only presentation.
- **Layer panel** — each class layer has a colour swatch matching the table in §2;
  toggle individual classes on/off.

See `INTERACTIVE_VIEWER_MANUAL.md` for full viewer instructions.
