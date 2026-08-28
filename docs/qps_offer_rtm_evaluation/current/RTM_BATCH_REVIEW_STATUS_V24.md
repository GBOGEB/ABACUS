# QPS RTM governed batch review status — v24

Status: **ITEM-LEVEL REVIEW COVERAGE COMPLETE FOR PLANNED PRIORITY BATCHES — NO REQUIREMENT CLOSURE**

## Controlling source roles

1. **Addendum II PDF/DOCX** — contract authority.
2. **`QPS_OFFER_Cluster_v3_3_Canonical_RTM_722.xlsx`** — governed 722 RTM / 50 OFFER numbered projection and canonical crosswalk.
3. **`QPS_OFFER_Evaluation_FULL_v24.xlsx`** — bidder-independent BT/PCA technical-evaluation SSOT for prioritisation only.
4. **`03_DATA_SSOT/offer_evidence_full.json` and `03_DATA_SSOT/rtm_evidence_full.json`** — downstream bidder evidence/compliance only.

No lower layer may redefine a higher-authority layer. The superseded 735-row extraction is not an accepted input or fallback.

## Planned priority review coverage

| Sequence | Governed range | File | Coverage status | Requirement closure |
|---:|---|---|---|---|
| 1 | RTM-012..024 | `RTM_BATCH_012_024_CANONICAL_722_50.md` | Complete item-level review synopsis | No |
| 2 | RTM-048..063 | `RTM_BATCH_048_063_V24_REVIEW.md` | Complete item-level review synopsis | No |
| 3 | RTM-281..309 | `RTM_BATCH_281_309_V24_REVIEW.md` | Complete item-level review synopsis | No |
| 4 | RTM-236..280 | `RTM_BATCH_236_280_V24_GOVERNED_REVIEW.md` | Complete item-level review synopsis | No |

The tables in these files are review synopses unless explicitly stated otherwise. Canonical verbatim requirement text remains in Addendum II and the canonical 722-row workbook.

## Remaining v24 reconciliation

The only current `V24_LOOKUP_REQUIRED` placeholders in these planned batch files are in:

- `RTM_BATCH_048_063_V24_REVIEW.md`
- `RTM_BATCH_281_309_V24_REVIEW.md`

These placeholders shall be replaced only when exact rank/tier/BT/PCA values are read from `QPS_OFFER_Evaluation_FULL_v24.xlsx` or from an explicitly governed v24-derived export. Older workbook values shall not be promoted as v24 values.

The exact historical FULL v24 binary is now provenance-bound in `V24_BINARY_PROVENANCE_BRIDGE.md` to Git blob SHA-1 `bccab3a8ccf539db7c4a9636f1f2abee86885494` with recorded size `641318` bytes, using `docs/binary_migration/REMOVED_BINARY_PATHS.tsv` as the migration record. Any future v24-derived rank/tier export must bind to that binary identity (or an unambiguous independently verified raw-file SHA-256 mapping to it) before replacing lookup placeholders.

Repository-side historical/recompute ranking material may be used only after its lineage to v24 is explicitly established. Presence of ranking values in a log or navigator is not, by itself, proof that the values are governed v24 outputs.

### Reconciliation finding RF-V24-001 — rank/tier export lineage not established

A Library and repository sweep located v24 pointers plus ranking-bearing HTML, patch, navigator and recompute artifacts, but no export whose own metadata explicitly binds its RTM rank/tier values to the provenance-bound FULL v24 binary above. Therefore no repository or Library ranking artifact is promoted as a v24 substitute in the current review state.

`RF-V24-001` may be closed only by one of the following governed evidence routes:

1. direct read/materialisation of `QPS_OFFER_Evaluation_FULL_v24.xlsx`; or
2. an explicitly governed v24-derived export that records, at minimum:
   - source workbook `QPS_OFFER_Evaluation_FULL_v24.xlsx`;
   - lineage to Git blob SHA-1 `bccab3a8ccf539db7c4a9636f1f2abee86885494` or an independently verified raw-file SHA-256 mapping to that exact binary;
   - export generation date/tool or reproducible generator reference;
   - RTM ID;
   - v24 rank;
   - v24 tier;
   - any BT/PCA score fields promoted into the review;
   - an explicit statement that bidder evidence/compliance did not participate in the rank/tier derivation.

Until that evidence exists, `V24_LOOKUP_REQUIRED` is the correct governed value. This is a metadata reconciliation HOLD only; it does not reopen the completed item-level requirement review ranges and does not affect the canonical requirement/OFFER crosswalk.

## OFFER boundary summary

- RTM-012..024: direct canonical OFFER interface only for RTM-019..022 → OFFER-04.
- RTM-048..063: direct canonical OFFER interface only for RTM-057..063 → OFFER-11.
- RTM-281..309: no canonical OFFER interface.
- RTM-236..280: canonical relationships include contextual OFFER-13 plus direct/supporting OFFER-19, OFFER-20, OFFER-21, OFFER-22, OFFER-23 and OFFER-24 relationships as recorded in the governed batch file.

OFFER responses remain tender-stage evidence/request interfaces and do not replace RTM compliance or close requirements.

## Promotion gate

Completion of these four review ranges means the planned **item-level review pass** is complete. It does **not** mean:

- the requirements are closed;
- bidder evidence has been accepted;
- BT/PCA values have contractual authority;
- a range allocation proves individual compliance;
- the QPS accepted-release gate has advanced.

Any subsequent promotion must preserve authority/evidence separation and be supported by governed source evidence.
