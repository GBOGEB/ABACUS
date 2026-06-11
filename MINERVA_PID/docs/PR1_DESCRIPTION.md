# PR1 — W001 + W002 + W003 + W004: Colour-line model, layer hierarchy & geometric tracing

> Paste this as the GitHub PR description. **Do not auto-merge** — open for engineering review only.

**Branch:** `wave/w001-w004-colour-line-layer-geometry` → **Base:** `main`
**Programme:** Mott MacDonald / SCK CEN — MYRRHA-MINERVA Phase 1 (QCELL / RFCELL P&ID)
**Toolchain:** Python stdlib + `cairosvg` (PDF) + `openpyxl` (Excel)

---

## What this PR delivers

A single consolidated foundation covering four waves:

- **W001** — source ingestion & style extraction (inline-style colour precedence).
- **W002** — colour-line decomposition into canonical process lines + validation.
- **W003** — 13 top-level layers (21 named sub-layers) hierarchy, per-element assignment.
- **W004** — geometric arrow/flow tracing, element pairing, component catalog, PEMO SSOT.

We deliberately do **not** open one PR per wave — the reviewer sees one coherent capability set.

## Reproducibility (read first)

Derived outputs (`data/model/`, `data/pemo/`, `output_v6/`, `publish/`, `reports/*.xlsx`)
are **git-ignored** — regenerable, not source. From a fresh clone:

```bash
./make.sh                                                  # regenerate ALL derived outputs
PYTHONPATH=src python3 tests/test_integration_pipeline.py  # source-only smoke test (no data needed)
PYTHONPATH=src python3 tests/test_colour_model.py          # W002 assertions (after make.sh)
PYTHONPATH=src python3 tests/test_w003_w004.py             # W003/W004 assertions (after make.sh)
```

**Verified:** fresh clone → `make.sh` exit 0 → 20/20 tests pass → headline numbers reproduce
exactly (297 components, 982→112 unmapped, pairing median 25.35px, layer sum 1888+533=2421).

Tracked source of record: `src/`, `segmentation/data/*.json`, `configs/`, `data/svg/`,
`extracted/` (source reference XLSX/SVG), `tests/`, `reports/*.md`, `docs/`.

---

## Capability Matrix (honest "Claim ≠ Complete" accounting)

### CAN — implemented and verified

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

### CANNOT — blocked by source data / toolchain

| Capability | Reason |
| --- | --- |
| Map the 112 residual magenta elements to a line | No legend swatch for that colour family in the source SVG |
| Confirm true 3-D pipe routing / elevations | Source is 2-D schematic; no z-data |
| Resolve the degenerate-transform coordinate outlier to a real position | Source transform is mathematically degenerate; mitigated via viewBox bounds |

### DID NOT / DEFERRED — possible, deferred to a later wave

| Capability | Status / target wave |
| --- | --- |
| XLSX tag/instrument register reconciliation + coverage delta | **W005 (next, PR2)** |
| Recover the U line (top-left, currently black) | DEFERRED — colour re-attribution pass |
| Bind the 77 floating arrows to source lines | DEFERRED — nearest-line heuristic |
| Populate 04G_E_RED / manifold header layers | DEFERRED — reserved placeholders |
| Interactive layered viewer (beyond static atlas) | DEFERRED — W006, PR3 |
| Cross-drawing reconciliation, temperature/pressure annotation | DEFERRED — later waves |
| CI / GitHub Actions workflow | DEFERRED — W007, PR3 |

---

## Review checklist

- [ ] `./make.sh` reproduces all derived outputs from a clean clone.
- [ ] Integration smoke test passes (`tests/test_integration_pipeline.py`).
- [ ] 13-top-level / 21-named-sub-layer assignment matches engineering intent.
- [ ] 297-component catalog sanity-checks against the drawing.
- [ ] Handover-diamond list (22) and 5 scope boundaries confirmed.
- [ ] Pairing low-confidence caveat (>355px, max 1040px) understood and accepted.
- [ ] Documented deferrals accepted (U line, 112 magenta, 77 floating arrows).

## Not merged automatically
Opened for review only. Merge after sign-off. **Next:** PR2 = W005 XLSX register reconciliation.
