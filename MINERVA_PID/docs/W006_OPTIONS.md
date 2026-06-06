# Wave W006 — Two-Path Decision

**Project:** MINERVA QCELL/RFCELL P&ID · **Status of prior waves:** W001–W005 complete (PR #546 merged, PR #547 open)
**Pick one path below; W006 executes the selected option end-to-end.**

---

## Context (why this decision exists)

W005 reconciled the **design nomenclature register** (Excel, 97 tags) against the **as-drawn catalog**
(SVG-instance, 141 real tags) and found **0 % exact tag overlap** — the two registers use *orthogonal*
numbering schemes:

| | Design register (Excel) | As-drawn catalog (SVG) |
| --- | --- | --- |
| Numbering | Circuit-sequential (`CV001`, `TT100`) | SVG-instance (`CV560`, `TT514`) |
| Has location? | Free-text only (`"40K circuit to pumping line"`) | X/Y coordinates + colour-class line (A/B/D/S/V/W) + layer |
| Has circuit/temp? | Embedded in location text (40 K / 4.5 K / 2 K) | Encoded via colour class + legend |

The W005 report's **#1 recommendation** was to build a **Design ↔ As-Drawn Cross-Map**.

---

## Option A — Design ↔ As-Drawn Cross-Map ⭐ RECOMMENDED

### What it solves
Turns the 0 % exact-overlap finding into a **functional bidirectional mapping** (`CV001 ↔ CV560`),
enabling traceability from design intent → physical implementation. Foundation for commissioning,
maintenance, and any future digital-twin work.

### Approach (grounded in the actual W005 data)
1. **Feature extraction** per tag: ISA TYPE, circuit/temperature (parsed from Excel location text vs.
   catalog colour-class→legend), line assignment, and — catalog side only — X/Y + layer.
2. **Type-partitioned candidate matching** with **confidence scoring**:
   - TYPE match (mandatory gate)
   - Circuit/temperature-band agreement (40 K / 4.5 K / 2 K ↔ colour class)
   - Sequence-order heuristic within a type+circuit group (design N-th ↔ as-drawn N-th)
   - Manual validation seed (e.g. the PPT-confirmed `TT535`/`TT525` → PZ allocations)
3. **Confidence tiers:** HIGH (type+circuit+order), MEDIUM (type+circuit), LOW (type only — flagged for review).

### Honest limitation (will be stated in the report, not hidden)
The design register has **no coordinates**, so a *true* spatial position match is impossible. Matching
relies on TYPE + circuit-band + within-group ordering. Expect a meaningful share of MEDIUM/LOW pairs
that need engineering sign-off — we will **not** fabricate HIGH-confidence matches.

### Deliverables
- `data/crossmap/design_to_asdrawn.json` (bidirectional mapping + reverse index)
- `data/crossmap/crossmap_confidence.json` (per-pair score + reasons)
- `reports/W006_CROSSMAP_REPORT.md` (validation report: tiered tables + unmapped list + recommendations)
- `reports/W006_crossmap_statistics.json` (coverage summary)
- `data/excel/canonical_register_v2.yaml` (canonical register + cross-references)
- `src/abacus_svg_pid/build_w006_crossmap.py` (reproducible engine, wired into `make.sh`)
- `tests/test_w006_crossmap.py` (bidirectional lookup, confidence bounds, golden seeds)
- Governance updates (`wave_status.json`, `CAPABILITY_MATRIX.md`, `wave_registry.json`)

### Effort / impact
1 wave · **HIGH** engineering value · **blocks** future waves (W007–W009 traceability builds on this).

---

## Option B — Interactive UI Viewer (originally planned W006)

### What it provides
A standalone, browser-based P&ID navigator over the existing layered model.

### Approach
1. **Layer toggle controls** — the 21-layer hierarchy with checkboxes (heat loads, spec dots, signals…).
2. **Pan / zoom / search** — SVG viewport manipulation; search by tag (`CV001` → highlight + zoom).
3. **Metadata popups** — click an element → show catalog/reconciliation details.
4. **Comparison views** — side-by-side QCELL vs RFCELL; colour-class isolation.

### Deliverables
- `publish/interactive_viewer.html` (standalone, no server required)
- JavaScript layer-toggle + search/filter engine
- Metadata popups (instrument details from the catalog/canonical register)
- Per-layer / per-view PNG-PDF export controls
- `tests/test_w006_viewer.py` (data-binding + asset-integrity checks)

### Effort / impact
1 wave · **MEDIUM** value · **blocks nothing** (nice-to-have; can be deferred to W007/W008).

---

## Comparison

| Criterion | A: Cross-Map | B: Interactive UI |
| --- | --- | --- |
| Engineering priority | ⭐⭐⭐ HIGH (W005 #1 rec) | ⭐⭐ MEDIUM |
| Depends on | W005 canonical register | W003/W004 layer hierarchy |
| Complexity | Medium (heuristics + validation) | Medium (UI/UX + SVG manipulation) |
| Deliverable type | Data model + report | Interactive application |
| Stakeholders | Engineers, commissioning | All stakeholders, demos |
| Blocks future work? | **Yes** (W007–W009) | No |
| Can defer? | No (critical gap) | Yes |

---

## Recommendation

**Execute Option A (Cross-Map) first** — it closes the critical traceability gap identified in W005 and
is a prerequisite for the later waves. Option B can follow in a subsequent wave.

### User choice
- [ ] **Option A** — Design ↔ As-Drawn Cross-Map (recommended)
- [ ] **Option B** — Interactive UI Viewer
- [ ] **Both** (sequential; longer)
- [ ] **Other** (tell me)
