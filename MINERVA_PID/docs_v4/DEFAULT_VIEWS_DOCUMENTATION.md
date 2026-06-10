# MINERVA CryoCell P&ID — Default Views Documentation (v4)

**Project:** MINERVA CryoCell — SCK CEN (MYRRHA/MINERVA Phase 1)
**Consultant:** Mott MacDonald, Bristol UK — MMD 411066
**Standard:** SCK CEN AD_01.16 · Status: S2 — FOR ACCEPTANCE · RESTRICTED

---

## 1. Purpose

The v4 P&ID set is **layered**. Each SVG contains 24 named layers (groups), and the
drawing ships with five pre-defined **default views** — curated layer combinations for
different audiences and tasks. The view definitions are embedded in each SVG's
`<metadata>` block and mirrored in the interactive viewer (`js/pid-viewer.js → VIEWS`),
so the same presets are available whether you open the SVG directly or use the HTML
viewer.

---

## 2. The 24 Layers (draw order, bottom → top)

Layers draw in list order — the first entry is the bottom of the stack. Tag layer
`12_Tags` and overlays are placed late so they render on top of pipes and equipment.

Grouped by function:

- **Frame / title:** `00_Frame`, `01_TitleBlock`
- **Process pipes (by class):** `02_Pipe_D`, `02B_Pipe_E`, `03_Pipe_A`, `04_Pipe_B`,
  `04C_Pipe_WATER`, `05_Pipe_AIR`
- **Equipment:** `06_Equipment`, `07_Vessels`, `08_Valves`
- **Overlays:** `08B_Valves_HORIZONTAL_OVERLAY` *(hidden by default)*
- **Instruments / signals:** `09_Instruments`, `10_Signals`, `11_Controls`
- **Annotation:** `12_Tags`, `13_LineNames`, `14_TerminalPoints`, `15_Dimensions`
- **Reference:** `16_Legend`, `16_Legend_INTERACTIVE` *(hidden)*,
  `17_Notes_TOGGLEABLE` *(hidden)*, plus revision/notes layers.

Three layers are **hidden by default**:
`08B_Valves_HORIZONTAL_OVERLAY`, `16_Legend_INTERACTIVE`, `17_Notes_TOGGLEABLE`.

---

## 3. The Five Default Views

| View          | Audience / use case                              | Shows                                                                 |
|---------------|--------------------------------------------------|-----------------------------------------------------------------------|
| **FULL**      | Complete reference / acceptance review           | All visible layers (everything except the 3 hidden-by-default).       |
| **PROCESS**   | Process engineers — focus on fluid path          | Frame, title, all process-pipe classes, equipment, vessels, valves, line names, terminal points, legend. Hides most instrument/signal detail. |
| **CONTROL**   | C&I engineers — focus on instrumentation         | Frame, title, equipment outlines, instruments, signals, controls, tags, legend. Pipes shown light for context. |
| **MAIN**      | General overview / drawing issue                 | Frame, title, primary process pipes, equipment, vessels, valves, tags, line names, terminal points, legend. |
| **PRINT_MONO**| Black-and-white plotting / AD_01.16 mono check   | All process content in monochrome with inline line names and weight/dash differentiation; colour suppressed. |

### View details

- **FULL** — `vis = layer not in HIDDEN_BY_DEFAULT`. The horizontal-valve overlay,
  interactive legend and toggleable notes remain off until explicitly enabled.
- **PROCESS** — emphasises `02*–05*` pipe classes, `06/07/08` equipment & valves,
  `13_LineNames`, `14_TerminalPoints`. Instrument layers (`09/10/11`) are off.
- **CONTROL** — emphasises `09_Instruments`, `10_Signals`, `11_Controls`, `12_Tags`;
  process pipes kept visible but visually subordinate for context.
- **MAIN** — the "issue" view: primary headers + equipment + valves + tags + names.
- **PRINT_MONO** — drives the mono rendering path so a colour-free A3 plot still
  conveys every class via names, weights and dash patterns (see Colour & Legend Guide).

---

## 4. Using the Views

- **In the SVG:** the `<metadata id="minerva-frontmatter">` block lists each view and
  its layer visibility map (machine-readable, inside a CDATA section so the YAML `---`
  fences don't break XML parsers).
- **In the HTML viewer:** select a preset from the **Views** control; the layer panel
  updates to reflect which layers each preset enables. You can then fine-tune
  individual layers on top of any preset.

See `INTERACTIVE_VIEWER_MANUAL.md` for step-by-step viewer instructions.
