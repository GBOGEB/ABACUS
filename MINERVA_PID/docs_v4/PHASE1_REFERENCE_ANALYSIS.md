# Phase 1 — Reference P&ID Analysis (AD_01.10 / 11 / 14 / 17)

Extracted best-practice conventions from the SCK CEN / Mott MacDonald example
drawings to drive the v4 refinement.

## Source drawings reviewed
| Drawing | Content | Size |
|---|---|---|
| AD_01.10 P&ID PCW (TP2=PS01.PAB12) | Process Cooling Water P&ID (2 sheets: notes + diagram) | A4/A3 |
| AD_01.11 P&ID Instrument Air (TP2=PS01.QFB10) | Instrument-air P&ID (3 sheets) | A4/A3 |
| AD_01.14 Piping Layout - Instrument Air (PS05.QFB10) | Piping GA / layout | A3 |
| AD_01.17 Instrument Air - Piping Routing & Layout | Routing layout | A0 |

## 1. Terminal-point (TP) placement — KEY FINDING
Terminal points sit **at the left and right page edges** (and occasionally
top/bottom for vertical flows). Each TP is a small *assembly*, not a bare diamond:

```
   ┌───────────────────────────┐  ← scalloped "cloud" callout
   │        WATER GLYCOL        │     · system / medium name (top line)
   │  ◁ =NP.PS01_PFB503 │ 7884 │     · arrow box: destination DWG ref + line no.
   │   FROM MAC (WEST GALLERY) │     · TO/FROM <area> annotation (bottom line)
   └───────────────────────────┘
              ◇ TP.PS01.4002          ← TP diamond w/ TP code + category flag (△B) + NOTE ref
              │
        ──────┘ (pipe continues into / out of the drawing)
```

* **Arrow direction encodes flow**: left-pointing arrow = incoming (`FROM`),
  right-pointing = outgoing (`TO`).
* The pipe **runs to the frame border** with a short connection stub.
* "FROM SHEET 2 / TO SHEET 2" clouds appear at the **bottom edge** for
  inter-sheet continuation.
* Each TP carries a **category triangle** (△B etc.) and a **NOTE n** reference.

## 2. Line naming strategy
Lines are labelled **inline, sitting on the pipe** in a small white gap:
`BR0021-4"-PAC1-BA` = *line-number – size – fluid/spec-class – insulation/route code*.
Labels repeat along long runs and at every branch. This is the mechanism the
reference uses to keep a **monochrome** drawing readable — the **name on the
line**, not colour, is the primary identifier.

## 3. White boxes for tags
Every instrument / valve tag (e.g. `AA0019`, `AA3001 / MOV-03`) sits in a small
**white rectangle** so it never collides with piping behind it. Tag boxes are
opaque white with a hairline border and live on the topmost layer.

## 4. Valve orientation
* Valves are drawn **in-line** with the pipe (gate-valve bow-tie), white-filled
  with a black outline so they read clearly where they cross a coloured/black line.
* Actuated valves (`MOV`, control) add the actuator glyph above the body.
* Tags are placed in white boxes directly **below** the valve.

## 5. Other conventions adopted
* Scalloped "cloud" callouts for off-sheet/area references.
* Category triangles (△B/C/E/…) used as note + scope flags.
* Reference-drawings list and a "Key to symbols" cell in the title strip.
* Branch take-offs carry their own line number.

## How v4 applies these
| Reference convention | v4 implementation |
|---|---|
| TP at L/R edges with cloud + diamond + arrow | `terminal_point_edge()` on layer `02_TerminalPoints_EDGE`; stacked along frame edges |
| Inline line names (mono legibility) | new layer `04C_Piping_LINENAMES` + `line_label()` |
| White tag boxes | `tag_with_box()`; instrument/valve tags on `12_Tags_Instruments` (front) |
| In-line + control-view valves | primary in-line valves + `08B_Valves_HORIZONTAL_OVERLAY` tracked-asset row |
| Flow-direction arrows | arrow heads in TP assemblies (TO/FROM) |
