# PR1 (combined) — W001–W005: Colour-line model, layer hierarchy, geometric tracing & XLSX register reconciliation

> Paste this as the GitHub PR description. **Do not auto-merge** — open for engineering review only.

**Branch:** `pr1-w001-w005` → **Base:** `main`
**Programme:** Mott MacDonald / SCK CEN — MYRRHA-MINERVA Phase 1 (QCELL / RFCELL P&ID)
**Toolchain:** Python stdlib + `cairosvg` (PDF) + `openpyxl` (Excel) + `PyYAML`

---

## What this PR delivers

A single consolidated foundation covering five waves:

- **W001** — source ingestion & style extraction (inline-style colour precedence).
- **W002** — colour-line decomposition into canonical process lines + validation.
- **W003** — 13 top-level layers (21 named sub-layers) hierarchy, per-element assignment.
- **W004** — geometric arrow/flow tracing, element pairing, component catalog (297), PEMO SSOT.
- **W005** — XLSX **tag & instrument register reconciliation**: cross-reference the 141 as-drawn
  catalog tags against the 97-tag design nomenclature register; per-TYPE coverage delta; ISA-class
  cross-validation; documented PPT re-allocations; merged canonical register (SSOT).

We deliberately do **not** open one PR per wave — the reviewer sees one coherent capability set.

## Reproducibility (read first)

Derived outputs (`data/model/`, `data/pemo/`, `data/excel/`, `output_v6/`, `publish/`,
`reports/*.xlsx`) are **git-ignored** — regenerable, not source. From a fresh clone:

```bash
./make.sh                                                   # regenerate ALL derived outputs
PYTHONPATH=src python3 tests/test_integration_pipeline.py   # source-only smoke test (no data needed)
PYTHONPATH=src python3 tests/test_colour_model.py           # W002 assertions (after make.sh)
PYTHONPATH=src python3 tests/test_w003_w004.py              # W003/W004 assertions (after make.sh)
PYTHONPATH=src python3 tests/test_w005_reconciliation.py    # W005 assertions (after make.sh)
```

**Verified:** fresh `make.sh` exit 0 → **31/31 tests pass** → headline numbers reproduce exactly
(297 components, 982→112 unmapped, pairing median 25.35 px; W005: 97 design tags vs 141 as-drawn).

Tracked source of record: `src/`, `segmentation/data/*.json`, `configs/`, `data/svg/`,
`extracted/` (source reference XLSX/SVG), `tests/`, `reports/*.md`, `reports/W005_coverage_statistics.json`,
`reports/wave_status.json`, `docs/`.

---

## W005 headline finding (honest, not a defect)

The official **design nomenclature register** and the **as-drawn component catalog** use
**orthogonal tag-numbering schemes**:

- **Design register** — circuit-sequential (`CV001–004`, `CV100/101`=40 K, `TT100–111`=Pt/40 K…).
- **As-drawn catalog** — SVG-instance numbering (`CV560`, `TT514`, `EH514`, `LS-021`, `HV503`…).

→ **Exact normalized tag overlap = 0 (0.0 %).** This is a genuine engineering finding — the two
registers were authored against different conventions — **not** a pipeline defect. No matches are
fabricated. Coverage is therefore measured **per instrument TYPE**, and the #1 recommended next
deliverable is a **design ↔ as-drawn cross-map**.

| W005 metric | Value |
| --- | --- |
| Design (Excel) tags / TYPES | 97 / 15 |
| As-drawn real tags / TYPES | 141 / 6 |
| As-drawn template placeholders (flagged non-reconcilable) | 24 (`TTxxx`, `EHx11`…) |
| Exact tag matches | 0 |
| TYPES present in both | CV, EH, HV, PT, TT |
| TYPES missing from catalog | FT, FV, HX, J, LE, LI, PV, RD, SV, V (10) |
| As-drawn-only TYPE | LS (25 limit switches) |
| Documented PPT re-allocations applied | 2 (TT535→PZ coldest, TT525→PZ warmest) |

W005 outputs: `reports/W005_XLSX_RECONCILIATION_REPORT.md`, `reports/W005_validation_report.md`
(✅ PASS), `reports/W005_coverage_statistics.json`, and (regenerable) `data/excel/*.json`,
`data/excel/canonical_register_v1.yaml` (238-entry merged SSOT), `reports/COMPONENT_CATALOG_v2.xlsx`.

---

## Capability Matrix (honest "Claim ≠ Complete" accounting)

### CAN — implemented and verified

| Capability | Evidence |
| --- | --- |
| Reduce unmapped elements via legend reclassification | 982 → 112 (88.6 %) |
| CTM-resolved geometry extraction (bbox/centroid/shape) | `geometry.py`; 7 shape classes |
| Pair text → components / dots / triangles / arrows → lines | 315 / 205 / 100 / 132 |
| Colour-classify text nodes | 533 nodes |
| Assign 13 top-level layers (21 named sub-layers) | `layer_assignment.json`; sum-check 2421 |
| Render layered SVG + PDF; interactive layer-toggle atlas | QCELL 1834/14, RFCELL 591/12 |
| Trace flow arrows + junctions | 132 arrows, 36 junctions |
| Catalog components to Excel + HTML | 297 components |
| Emit PEMO YAML 1.2 SSOT | 122 loops, 60 heat loads |
| **Reconcile as-drawn catalog vs design nomenclature XLSX (W005)** | 97 vs 141; per-TYPE delta |
| **Detect orthogonal tag schemes (reported honestly, not forced)** | 0 exact overlap |
| **Flag 10 design TYPES missing from catalog** | FT/FV/HX/J/LE/LI/PV/RD/SV/V |
| **Flag RFCELL template placeholders non-reconcilable** | 24 placeholders |
| **Apply documented PPT instrument re-allocations** | TT535→PZ, TT525→PZ |
| **Emit canonical merged instrument register (SSOT)** | `canonical_register_v1.yaml`, 238 entries |

### CANNOT — blocked by source data / toolchain

| Capability | Reason |
| --- | --- |
| Map the 112 residual magenta elements to a line | No legend swatch for that colour family |
| Confirm true 3-D pipe routing / elevations | Source is 2-D schematic; no z-data |

### DID NOT / DEFERRED — possible, deferred to a later wave

| Capability | Status / target wave |
| --- | --- |
| Design ↔ as-drawn tag cross-map (keyed on TYPE+circuit+position) | DEFERRED — W005 quantified the need |
| Extend as-drawn catalog to the 10 missing design TYPES | DEFERRED |
| Exhaustive parse of the 65 MB QSYS instrumentation PPT | DEFERRED — cost; 2 cited re-allocations encoded |
| Cross-drawing identity reconciliation (QCELL↔RFCELL) | DEFERRED — Wave W006 |
| CI / GitHub Actions workflow | DEFERRED — only PLANNED |

---

## Repo hygiene note

Auto-generated office-doc preview artifacts (`*_preview/` HTML renderings of `.docx`/`.pptx`)
were **removed from the entire git history** and added to `.gitignore`. They were derived
artifacts and one contained a base64 media blob that tripped GitHub secret-scanning push
protection (false positive — embedded PPTX media, not a live credential). History was rewritten
with `git filter-repo` prior to first push; commit SHAs differ from the local pre-push state.
