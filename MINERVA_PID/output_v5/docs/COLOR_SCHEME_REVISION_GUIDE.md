# MINERVA CryoCell P&ID — Colour Scheme Revision Guide (v5)

**Project:** MINERVA CryoCell — SCK CEN · MYRRHA / MINERVA Phase 1
**Consultant:** Mott MacDonald (Bristol, UK) · **MMD** 411066
**Status:** S2 — FOR ACCEPTANCE · **RESTRICTED**
**Standards:** SCK CEN AD_01.16 · ISO 10628 · ANSI/ISA-5.1-2022 · IEC 60617

---

## 1. Purpose of the revision

The v5 revision replaces the legacy colour assignment (which used red for the
40 K shield and treated all helium circuits with broadly similar emphasis) with
a **cryogenic-focus palette**. The guiding principle is that **colour now encodes
temperature**: the coldest lines read coolest (deep blue / cyan), the thermal
shield reads warm (orange / red) and the warm piping system reads green / olive.
This makes the thermal hierarchy of the cryomodule legible at a glance, on A3
and after monochrome plotting.

## 2. New palette

Lines are grouped into three temperature zones. Each **primary** (main) line has
a saturated hue; its **branch** lines (designator with a prime, e.g. `A′`) use a
darker or lighter shade of the same hue.

### Cold header (top of sheet)

| Line | Designator | Colour | Hex | Service | Temp | Pressure | Flow | DN | MOC |
|------|-----------|--------|-----|---------|------|----------|------|----|-----|
| A  | A  | Blue        | `#0000FF` | 4.5 K primary helium | 4.5 K | 3 bar | ~50 g/s | DN50 | SS316L |
| A′ | A′ | Navy        | `#000080` | 4.5 K branches | 4.5 K | 3 bar | varies | DN25 | SS316L |
| B  | B  | Cyan        | `#00FFFF` | 2 K primary helium | 2 K | 27 mbar | ~47.5 g/s | DN40 | SS316L |
| B′ | B′ | Teal        | `#008B8B` | 2 K branches | 2 K | 27 mbar | varies | DN25 | SS316L |

### Thermal shield

| Line | Designator | Colour | Hex | Service | Temp | Pressure | Flow | DN | MOC |
|------|-----------|--------|-----|---------|------|----------|------|----|-----|
| D  | D  | Orange       | `#FF8000` | 40 K shield inlet | 40 K | 14 bar | TBD | DN32 | Cu |
| D′ | D′ | Light orange | `#FFB366` | 40 K branches | 40 K | 14 bar | varies | DN20 | Cu |
| E  | E  | Red          | `#FF0000` | 60 K shield outlet | 60 K | 13 bar | TBD | DN32 | Cu |
| E′ | E′ | Dark red     | `#CC0000` | 60 K branches | 60 K | 13 bar | varies | DN20 | Cu |

### Warm piping system (WPS) — bottom of sheet

| Line | Designator | Colour | Hex | Service | Temp | Pressure | Flow | DN | MOC |
|------|-----------|--------|-----|---------|------|----------|------|----|-----|
| W | W | Green | `#00FF00` | WPS warm return | 4.5 K → 300 K | 6 bar | ~2.5 g/s | DN20 | SS304 |
| S | S | Lime  | `#BFFF00` | WPS service / safety | 2 → 292 K | 1.05 bar | TBD | DN15 | SS304 |
| U | U | Olive | `#808000` | WPS GHe supply inlet | 292 K | 14 bar | TBD | DN15 | SS304 |

### Reference

| Item | Colour | Hex | Notes |
|------|--------|-----|-------|
| Outside scope | Grey (dashed) | `#808080` | Services beyond the hand-over boundary |
| Secondary / DI-water | Green-blue | per sheet | Cooling water utility |

## 3. Old → new mapping

| Element | v4 (old) | v5 (new) | Rationale |
|---------|----------|----------|-----------|
| 4.5 K primary (A) | blue `#0000FF` | **blue `#0000FF`** | retained — coldest reads coolest |
| 2 K primary (B) | cyan `#00FFFF` | **cyan `#00FFFF`** | retained |
| 40 K shield in (D) | red `#FF0000` | **orange `#FF8000`** | red re-assigned to the *outlet*; 40 K reads warm-orange |
| 60 K shield out (E) | (grouped / olive) | **red `#FF0000`** | hottest cryo line gets the hottest hue |
| Warm return (W) | green `#00FF00` | **green `#00FF00`** | retained, now anchors the WPS zone |
| Service / safety (S) | — | **lime `#BFFF00`** | new explicit WPS line |
| GHe supply (U) | olive `#808000` | **olive `#808000`** | retained |

The key behavioural change: **red moved from the 40 K inlet to the 60 K outlet**,
and the 40 K inlet became orange — so the shield pair D→E now reads as a clear
warm-up (orange → red) instead of two reds.

## 4. Branch (prime) shading rule

* Cold lines (A, B): branch = **darker** shade (`A′` navy, `B′` teal).
* Thermal lines (D, E): branch = **lighter / darker** shade of the same hue
  (`D′` light orange, `E′` dark red).
* A run is classified **primary** vs **branch** automatically using the
  55th-percentile run-length threshold per class; primaries live on the main
  piping layers (04/05/06) and branches on the `_BRANCHES` layers (04B/05B/06B).

## 5. Where the scheme is applied

* **Production sheets** — all 16 (QCELL + RFCELL × 2 sheets × STANDARD /
  CONTROL-CENTRIC × colour / mono).
* **Zone bands** (layer `02C_Zone_Bands`) tint the sheet into cold-header,
  thermal-shield, equipment and warm-WPS reading zones.
* **Line labels** (layer `04D_Piping_LINE_LABELS`) carry `[LINE]-[SIZE]-[MOC]`.
* **Flow arrows** (layer `04G_Flow_Arrows`) are coloured per line.
* **Legend** — the on-sheet legend now contains the full **line specification
  table** (colour swatch, temperature, pressure, DN, MOC).
* **MAIN-LINES-ONLY** schematic and the `VIEW_MAINLINES_ONLY` preset.

## 6. Monochrome behaviour

When colour is removed, the class hierarchy is carried by **line weight + dash
pattern** instead of hue:

| Zone | Mono weight | Dash |
|------|-------------|------|
| Cold header (A/B) | 1.0 mm primary / 0.6 mm branch | solid |
| Thermal shield (D/E) | 0.8 mm primary / 0.6 mm branch | solid |
| Warm WPS (W/S/U) | 0.5 mm | dashed (8,3) |

This guarantees the drawing survives black-and-white plotting and photocopying
without loss of meaning.

## 7. Accessibility / plotting notes

* Blue↔cyan and orange↔red pairs were chosen to remain distinguishable by
  position (zone bands) even for colour-vision-deficient readers; the mono
  weight/dash system is the formal fallback.
* All hex values above are the controlled source-of-truth and match
  `generator/line_spec_data.py` and `LINE_SPECIFICATION_MASTER.xlsx`.
