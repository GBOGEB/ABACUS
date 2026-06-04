# Capability Matrix — v6.0 (W003 + W004)

Honest "Claim ≠ Complete" accounting. Every row is one of:
**CAN** (implemented & verified by runtime counts) ·
**CANNOT** (not possible with current source data / toolchain) ·
**DID NOT / DEFERRED** (possible but intentionally not done this wave).

---

## CAN — implemented and verified

| Capability | Evidence |
| --- | --- |
| Reduce unmapped elements via legend reclassification | 982 → 112 (88.6 %) |
| CTM-resolved geometry extraction (bbox/centroid/shape) | `geometry.py`; 7 shape classes |
| Pair text → components | 315 pairs |
| Colour-classify text nodes | 533 nodes |
| Pair dots / heat-load triangles / arrows → lines | 205 / 100 / 132 |
| Pairing distance quality (honest caveat) | 752 pairs, median 25px. 10% above 355px flagged low-confidence; max 1040px (known outlier, deferred to W005 review) |
| Standardize text to Consolas + 4 mm tiers | 533 nodes tiered |
| Assign 13 top-level layers (21 named sub-layers) per element | `layer_assignment.json` |
| Render layered SVG + PDF | QCELL 1834/14, RFCELL 591/12 |
| Build interactive layer-toggle atlas | `layered_atlas_v6.html` |
| Trace flow arrows + junctions | 132 arrows, 36 junctions |
| Parse vertical-letter nomenclature into tree | 33 segments, 8 parents |
| Catalog components to Excel + HTML | 297 components |
| Catalog spec-change dots by line | S 40, V 10, B 2, uncol. 153 |
| Detect scope boundaries | 5/5 (QM/QVB/vac/Jumper/QINFRA) |
| Detect handover diamonds (TP#NNN) | 22 |
| Emit PEMO YAML 1.2 SSOT | 122 loops, 60 heat loads |

## CANNOT — blocked by source data / toolchain

| Capability | Reason |
| --- | --- |
| Map the 112 residual magenta elements to a line | No legend swatch exists for that colour family in the source SVG |
| Confirm true 3-D pipe routing / elevations | Source is 2-D schematic; no z-data |
| Resolve the single degenerate-transform coordinate outlier to a real position | Source transform is mathematically degenerate; mitigated by using viewBox bounds |

## DID NOT / DEFERRED — possible, deferred to a later wave

| Capability | Status / target wave |
| --- | --- |
| Recover the U line (top-left, currently black) | DEFERRED — needs colour re-attribution pass |
| Bind the 77 floating arrows to source lines | DEFERRED — needs nearest-line heuristic |
| Populate 04G_E_RED line layer (geometry) | DEFERRED — RED currently text-only |
| Populate manifold COLD/WARM header layers (03A/03B) | DEFERRED — reserved placeholders |
| Cross-drawing identity reconciliation (QCELL↔RFCELL) | DEFERRED — Wave W006 |
| Temperature/pressure annotation per segment | DEFERRED — Wave W007 |
| CI / GitHub Actions workflow | DEFERRED — only PLANNED in `GITHUB_PR_PLAN.md` |
| UI framework / web app | DEFERRED — static HTML only this wave |
