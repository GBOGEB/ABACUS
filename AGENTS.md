# AGENTS.md — MINERVA QCELL P&ID (Colour-Line-First Pipeline)

## Mission
Decompose the **real** QCELL / RFCELL P&ID SVG drawings into **colour-defined
process lines**, preserving each line's sequence and scope/boundary context, so
the lines can be isolated, reviewed, and reassembled into the full P&ID without
losing engineering meaning. The success metric is *"can we isolate each
colour/process line and roll it back into the full P&ID"* — **not** tag count.

## Colour-first pipeline (the only supported flow)
1. **Ingest** — copy real sources into `data/svg/` (STOP if < 2 SVGs). PDF →
   `data/pdf/`, PPTX → `data/ppt/`.
2. **Extract** — `parser.extract_elements()` walks every drawable element and
   reads colour/style with **inline-style precedence**:
   `style.get(key) or elem.attrib.get(key)` (inline style wins). The effective
   process colour is the stroke if present, else the fill.
3. **Cluster** — `parser.classify_colour()` assigns each colour to the nearest
   canonical anchor by RGB distance (not exact hex):

   | Colour | Code | Meaning |
   |---|---|---|
   | BLUE / NAVY | A / A′ | 4.5 K main line + internal branch |
   | CYAN / TEAL | B / B′ | 2 K internal line |
   | GREEN | W | coupler (splits from BLUE A inside QM) |
   | OLIVE | S | warm S line |
   | GREY | V | vent line (per module, to outside) |
   | RED / ORANGE | D / E | warm/cold manifold |
   | BLACK | structure | boundary / symbols / unknown |
   | other | unknown | unresolved (flagged, e.g. magenta) |

4. **Model** — emit `colour_inventory.json`, `line_model.json`, and the seven
   per-colour files in `data/model/lines/`.
5. **Validate** — `reports/W002_colour_line_validation.md` + `navigation.json`.
6. **Publish** — `publish/colour_line_collage.html`: full drawing + one isolated
   view per colour line (A3 landscape, monochrome-safe labels).

## Run
```bash
python3 src/abacus_svg_pid/cli.py            # build the colour line model
python3 src/abacus_svg_pid/render_collage.py # build the collage
python3 tests/test_colour_model.py           # assertions
```

## Hard rules
- **Preserve sequence** — never geometrically re-order a line's components
  unless arrow / left-to-right evidence exists (that evidence is **W004**).
- **Claim ≠ Complete** — do not claim a colour is semantically correct unless it
  maps to the canonical table *or* it is explicitly listed as unresolved.
- Do **not** start UI, PPT, CI, package-rename, or the W003/W004 layer &
  geometry engine. Do not open a PR until success criteria 1–5 are non-zero.

## Wave roadmap
See `configs/wave_registry.json` (W001–W009) and `reports/navigation.json`
(current/next wave, status, SVGs found, blocking items). Current wave: **W002**.
