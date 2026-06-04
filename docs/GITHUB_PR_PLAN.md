# GitHub PR Plan — MINERVA QCELL/RFCELL Colour-Line Model

Branch & PR strategy. **Consolidated** — we do NOT open one PR per wave. Completed
waves are bundled into a single reviewable PR so the reviewer sees a coherent
capability set, not a trickle of partial commits. **PRs are never auto-merged.**

---

## PR1 — W001 + W002 + W003 + W004: Colour-line model, layer hierarchy & geometric tracing  *(THIS PR — ready for review)*

**Branch:** `wave/w001-w004-colour-line-layer-geometry`
**Base:** `main`

This single PR consolidates the entire foundation: source ingestion + style
extraction (W001), colour-line decomposition (W002), the 13-top-level /
21-named-sub-layer hierarchy (W003), and geometric arrow/flow tracing (W004).

### Reproducibility (read first)
Derived outputs (`data/model/`, `data/pemo/`, `output_v6/`, `publish/`,
`reports/*.xlsx`) are **git-ignored** — they are regenerable, not source. To
reproduce every number quoted below from a fresh clone:

```bash
./make.sh                                  # regenerate all derived outputs
PYTHONPATH=src python3 tests/test_integration_pipeline.py   # source-only smoke test
PYTHONPATH=src python3 tests/test_colour_model.py           # W002 assertions (after make.sh)
PYTHONPATH=src python3 tests/test_w003_w004.py              # W003/W004 assertions (after make.sh)
```

Tracked source of record: `src/`, `segmentation/data/*.json`, `configs/`,
`data/svg/`, `tests/`, `reports/*.md`, `docs/`.

### PR description — Capability Matrix

Honest "Claim ≠ Complete" accounting. Every row is **CAN** (implemented &
verified by runtime counts), **CANNOT** (not possible with current source /
toolchain), or **DID NOT / DEFERRED** (possible but intentionally not done).

#### CAN — implemented and verified

| Capability | Evidence |
| --- | --- |
| Ingest both real source SVGs with inline-style colour precedence | QCELL + RFCELL, 1888 drawable elements |
| Reduce unmapped elements via legend reclassification | 982 → 112 (88.6 %) |
| CTM-resolved geometry extraction (bbox/centroid/shape) | `geometry.py`; 7 shape classes |
| Pair text → components | 315 pairs |
| Colour-classify text nodes | 533 nodes |
| Pair dots / heat-load triangles / arrows → lines | 205 / 100 / 132 |
| Pairing-distance quality recorded | median 25.35 / p90 355.4 / max 1040.2 px (>p90 flagged low-confidence) |
| Standardize text to Consolas + 4 mm tiers | 533 nodes tiered |
| Assign 13 top-level layers (21 named sub-layers) per element | `layer_assignment.json` |
| Layer sum-check balances exactly | 1888 drawable + 533 text = 2421, no drops |
| Render layered SVG + PDF | QCELL 1834/14, RFCELL 591/12 |
| Build interactive layer-toggle atlas | `layered_atlas_v6.html` |
| Trace flow arrows + junctions | 132 arrows, 36 junctions |
| Parse vertical-letter nomenclature into tree | 33 segments, 8 parents |
| Catalog components to Excel + HTML | 297 components |
| Catalog spec-change dots by line | S 40, V 10, B 2, uncol. 153 |
| Detect scope boundaries | 5/5 (QM/QVB/vac/Jumper/QINFRA) |
| Detect handover diamonds (TP#NNN) | 22 |
| Emit PEMO YAML 1.2 SSOT | 122 loops, 60 heat loads |

#### CANNOT — blocked by source data / toolchain

| Capability | Reason |
| --- | --- |
| Map the 112 residual magenta elements to a line | No legend swatch for that colour family in the source SVG |
| Confirm true 3-D pipe routing / elevations | Source is 2-D schematic; no z-data |
| Resolve the degenerate-transform coordinate outlier to a real position | Source transform is mathematically degenerate; mitigated via viewBox bounds |

#### DID NOT / DEFERRED — possible, deferred to a later wave

| Capability | Status / target wave |
| --- | --- |
| XLSX tag/instrument register reconciliation + coverage delta | **W005 (next, PR2)** |
| Recover the U line (top-left, currently black) | DEFERRED — colour re-attribution pass |
| Bind the 77 floating arrows to source lines | DEFERRED — nearest-line heuristic |
| Populate 04G_E_RED / manifold header layers | DEFERRED — reserved placeholders |
| Interactive layered viewer (beyond static atlas) | DEFERRED — W006, PR3 |
| Cross-drawing reconciliation, temperature/pressure annotation | DEFERRED — later waves |
| CI / GitHub Actions workflow | DEFERRED — W007, PR3 |

### Review checklist
- [ ] `./make.sh` reproduces all derived outputs from a clean clone.
- [ ] Integration smoke test passes (`tests/test_integration_pipeline.py`).
- [ ] Confirm 13-top-level / 21-named-sub-layer assignment matches engineering intent.
- [ ] Sanity-check the 297-component catalog against the drawing.
- [ ] Confirm handover-diamond list (22) and 5 scope boundaries.
- [ ] Accept the documented deferrals (U line, 112 magenta, 77 floating arrows).

### Not merged automatically
Opened for review only. Merge after sign-off.

---

## PR2 — W005: Tag & Instrument Register Reconciliation (XLSX coverage delta)  *(planned — next)*

**This is the #1 next priority** — it is the question an engineering reviewer
asks first. Reconcile the 297 auto-catalogued components against the official
tag/instrument register (XLSX) and report the **coverage delta**:
- which catalogued components appear in the official register (matched),
- which are **false positives** (catalogued but not in register),
- which register tags are **missing** from our catalog,
- nomenclature reconciliation (our segment labels vs official tag naming).

Cross-validates colour-derived line identity against ISA tag class
(`configs/isa_classes.json`) per the governance principle in `AGENTS.md`.

## PR3 — W006 + W007: Interactive layered viewer + CI  *(planned)*

- **W006** — interactive layered viewer (beyond the static atlas HTML): toggle
  layers, isolate colour lines, click-through component inspection.
- **W007** — CI / GitHub Actions workflow running `./make.sh` + the test suite
  on every push.

## PR4 — W008 + W009: Round-trip reassembly + publication & sign-off  *(planned)*

- **W008** — recompose isolated colour lines back into the full P&ID without
  loss of meaning (the round-trip success metric).
- **W009** — engineering-reviewed colour-line atlas + sign-off record.

---

### Conventions
- One consolidated feature branch per PR bundle; never commit directly to `main`.
- Commit identity: `Abacus Agent <agent@abacus.ai>`.
- Squash-merge with the wave ids in the title.
- Derived outputs are git-ignored and regenerated by `./make.sh` (see `.gitignore`).
