<!--
  MASTER slides source. Each slide separated by `---`.
  Front-matter per slide:
    id:      unique id (e.g. hierarchy)
    title:   slide title
    subtitle: optional subtitle
    layout:  text-only | text-table | text-graph | 4-quadrants
    caption: optional figure/table caption
    notes:   slide notes (review/action/TODO)
-->

---
id: cover
title: MYRRHA QPLANT — Engineering Handover
subtitle: v0.4 — SCK CEN × Kaeser
layout: text-only
notes: |
  TODO: confirm version stamp before final export.
---
# MYRRHA QPLANT
**Engineering Handover** — *v0.4*

Baseline: **350 g/s @ 14 barG** (see B1)

---
id: exec-summary
title: Executive Summary
subtitle: Key design points (B1–B5)
layout: text-only
notes: |
  REVIEW: cross-check B2/B3 against latest test bench data.
---
- **B1** Baseline: 350 g/s @ 14 barG
- **B2** ALaT: 2 FSD · SFC 575 · 72 Hz → ~220 g/s
- **B3** LKT: 3 FSD · SFC 475 · ~57 Hz → 264 g/s nominal
- **B4** RCW: 85 °C max · 30 °C inlet · ΔT = 25 °C
- **B5** LCC/PVPS: 50 g/s · 2×5 units (N+1)

---
id: hierarchy
title: MYRRHA QPLANT System Hierarchy
subtitle: Canonical decomposition (Slide #3)
layout: text-only
caption: F1 — System decomposition tree
notes: |
  ACTION: validate skid IDs (HP1..HP4) with Kaeser nameplates.
  TODO: add LCC unit numbering scheme on next iteration.
---
```
QPLANT
├── QRB (cold side & coldbox)
└── WCS (warm side & warm compressor station)
    ├── HCC (LP→HP total, black box with utilities)
    │   ├── HP1 (Kaeser SKID 1)
    │   ├── HP2 (Kaeser SKID 2)
    │   ├── HP3 (Kaeser SKID 3)
    │   └── HP4 (Kaeser SKID 4)
    └── LCC (PVPS - 50 g/s target)
        └── 2×5 units (10 total, N+1 config)
```

Cross-refs: see **T1** (tables.html) and **G1** (graphs.html).

---
id: baseline
title: Baseline Operating Point — B1
layout: text-table
notes: |
  Anchor for all sizing calcs.
---
The reference point **B1 = 350 g/s @ 14 barG** anchors HCC + LCC delivery.

---
id: roadmap
title: Roadmap & Next Steps
layout: text-only
notes: |
  TODO: schedule v0.5 review with full team.
---
1. Validate B2/B3 on test bench
2. Finalize LCC unit-level P&IDs
3. Lock RCW heat-exchanger sizing
