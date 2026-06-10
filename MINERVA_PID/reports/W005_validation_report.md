# W005 — Validation Report

**Governance:** Claim ≠ Complete. A claim passes only when (1) the output files exist, (2) this validation record exists, (3) runtime counts are recorded, and (4) known gaps are listed.

## 1. Output files produced

| File | Exists | Bytes |
| --- | --- | --- |
| `data/excel/excel_register.json` | ✅ | 43752 |
| `data/excel/catalog_register.json` | ✅ | 73339 |
| `data/excel/reconciliation_results.json` | ✅ | 43027 |
| `reports/W005_coverage_statistics.json` | ✅ | 2926 |
| `reports/W005_XLSX_RECONCILIATION_REPORT.md` | ✅ | 9766 |
| `data/excel/canonical_register_v1.yaml` | ✅ | 72025 |
| `reports/COMPONENT_CATALOG_v2.xlsx` | ✅ | 19392 |

## 2. Runtime counts (regenerable via ./make.sh)

| Quantity | Value |
| --- | --- |
| Design (Excel) instrument tags | 97 |
| As-drawn real instrument tags | 141 |
| As-drawn template placeholders | 24 |
| Exact normalized tag matches | 0 |
| Exact tag coverage % | 0.0 |
| Missing in catalog | 97 |
| Extra in catalog | 141 |
| Design TYPES / As-drawn TYPES | 15 / 6 |
| Re-allocations applied | 2 |

## 3. Invariants checked

| Invariant | Result |
| --- | --- |
| excel + catalog tag counts are non-zero | ✅ PASS |
| matched ⊆ both registers (matched = |excel ∩ catalog|) | ✅ PASS |
| missing + matched == excel total | ✅ PASS |
| extra + matched == catalog real total | ✅ PASS |
| every reallocation tag resolved against both registers | ✅ PASS |

## 4. Known gaps

- **Zero exact tag overlap is real, not a bug:** design (circuit-sequential) and as-drawn (SVG-instance) schemes are orthogonal. A design↔as-drawn cross-map is required for tag-level reconciliation (Recommendation 1).
- **Full PPT deck not exhaustively parsed:** the 65 MB QSYS instrumentation deck was not machine-parsed (cost); only the two explicitly documented re-allocations (TT535, TT525) are encoded with citations.
- **10 design instrument TYPES not catalogued** (FT, FV, HX, J, LE, LI, PV, RD, SV, V): the W003/W004 category sheets covered only CV/EH/HV/LS/PT/TT.
- **24 RFCELL template placeholders** are flagged non-reconcilable rather than matched.
- **Catalog duplicates** were de-duplicated by normalized tag before reconciliation (see `catalog_register.json` `duplicate_norm_tags`).

## Overall: ✅ PASS
