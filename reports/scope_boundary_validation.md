# Scope Boundary Validation — Wave W004 Phase 8

**Project:** MINERVA CryoCell / QCELL & RFCELL P&ID
**Wave:** W004 (Geometric Tracing), Phase 8

---

## 1. Summary

| Metric | Count |
| --- | ---: |
| Scope boundaries detected | **5 / 5** |
| Handover diamonds (TP#NNN) | **22** |
| W-line bottom-right elements isolated | **19** |
| Ambiguities | 0 |

All five expected scope boundaries were located by text-matching against the title
block and annotation layer. Handover points use the `TP#NNN` pattern (TP#101 … TP#604)
rather than the generic `TPXYYYY` placeholder; the parser regex
`\bTP[#A-Z]?\d{2,5}\b` matches both.

## 2. Boundaries detected

| Boundary | Evidence (sample) |
| --- | --- |
| **QM** (Cryomodule) | "Cryomodule (QM)", "QCELL-QM", "scope QM" |
| **QVB** | "scope QVB", "scope QVB (AUB)", "QVB INVAC connection CF40", "vacuum barrier" |
| **vacuum_barrier** | "vacuum barrier" |
| **Jumper** | "Jumper" |
| **QINFRA** | "QINFRA - Implementation by NFS", "scope QINFRA" |

## 3. Handover diamonds (22)

Matched on the `TP#NNN` pattern. Each carries sheet + text + resolved (x, y) in
viewBox coordinates. Series observed:

- **1xx series:** TP#101, TP#102, TP#103, TP#104, TP#105
- **4xx series:** TP#401, TP#402, … (QCELL lower band)
- **6xx series:** up to TP#604

Full list with coordinates in
`data/model/scope_boundary_validation.json → handover_diamonds_TPXYYYY`.

## 4. W-line bottom-right zone

19 elements belonging to the W (coupler, GREEN) line were isolated in the bottom-right
quadrant of the drawing for visual review (atlas layer `04C_Lines_W_GREEN`). Quadrant
math uses the parsed **viewBox bounds** (default `[0,0,1527.27,1080]`) — not raw
min/max of coordinates — to avoid a known degenerate-transform coordinate outlier.

## 5. Continuity flags

1. W line bottom-right zone isolated for visual review (see atlas layer 04C).
2. Handover diamonds matched on TPXYYYY pattern; verify category prefix per AD_01.16.

## 6. Provenance

- Engine: `src/abacus_svg_pid/build_w003_w004.py` (Phase 8)
- Machine-readable output: `data/model/scope_boundary_validation.json`
