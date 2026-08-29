# QPS RTM governed batch review status — v24

Status: **ITEM-LEVEL REVIEW COVERAGE COMPLETE; PLANNED V24 RANK/TIER RECONCILIATION COMPLETE — NO REQUIREMENT CLOSURE**

## Controlling source roles

1. **Addendum II PDF/DOCX** — contract authority.
2. **`QPS_OFFER_Cluster_v3_3_Canonical_RTM_722.xlsx`** — governed 722 RTM / 50 OFFER numbered projection and canonical crosswalk.
3. **`QPS_OFFER_Evaluation_FULL_v24.xlsx`** — bidder-independent BT/PCA technical-evaluation SSOT for prioritisation only.
4. **Exact-source v24 `RTM_RANKING` extraction** — governed metadata evidence for the reconciled target ranges only.
5. **`03_DATA_SSOT/offer_evidence_full.json` and `03_DATA_SSOT/rtm_evidence_full.json`** — downstream bidder evidence/compliance only.

No lower layer may redefine a higher-authority layer. The superseded 735-row extraction is not an accepted input or fallback.

## Planned priority review coverage

| Sequence | Governed range | File | Coverage status | Requirement closure |
|---:|---|---|---|---|
| 1 | RTM-012..024 | `RTM_BATCH_012_024_CANONICAL_722_50.md` | Complete item-level review synopsis | No |
| 2 | RTM-048..063 | `RTM_BATCH_048_063_V24_REVIEW.md` | Complete; exact v24 rank/tier reconciled | No |
| 3 | RTM-281..309 | `RTM_BATCH_281_309_V24_REVIEW.md` | Complete; exact v24 rank/tier reconciled | No |
| 4 | RTM-236..280 | `RTM_BATCH_236_280_V24_GOVERNED_REVIEW.md` | Complete item-level review synopsis | No |

The tables in these files are review synopses unless explicitly stated otherwise. Canonical verbatim requirement text remains in Addendum II and the canonical 722-row workbook.

## v24 reconciliation evidence

The exact historical FULL v24 binary was recovered at frozen commit `0291d43990d73a45058ad19fe5ce6ed97e92e178` and independently checked in the extraction run against all bound identities:

- logical source: `docs/qps_offer_rtm_evaluation/current/QPS_OFFER_Evaluation_FULL_v24.xlsx`;
- Git blob SHA-1: `bccab3a8ccf539db7c4a9636f1f2abee86885494`;
- raw SHA-256: `3e84a3cab305b5b6b9bcf73367a47b3d49fef9f74077cff95e5cfe7e1b4a7118`;
- byte size: `641318`;
- extraction sheet: `RTM_RANKING`, header row 5, RTM ID column B;
- extraction tool: openpyxl 3.1.5 / GitHub Actions;
- target scope: RTM-048..063 and RTM-281..309;
- bidder evidence used in derivation: **false**.

GitHub Actions run `33244181179` completed successfully. Its exact-row extractor rejected duplicate/missing target IDs and found one governed `RTM_RANKING` row for every target. Artifact `9712296635` (`qps-v24-exact-metadata`) has ZIP digest `sha256:173d2fc70857d05fea47b7e1e5d7e51672832ab0f39b3913a04d95f598efa2e4` and records Rank, RTM ID, Gate, Tier, Weighted S, BT Win %, BT λ index and Primary dimension.

No v23/static-v3.4/recompute-log value was used to fill the planned placeholders.

### Reconciliation finding RF-V24-001 — CLOSED by exact-source extraction

**Disposition: CLOSED for the planned target scope RTM-048..063 and RTM-281..309.**

The closure route is direct materialisation/read of the provenance-bound `QPS_OFFER_Evaluation_FULL_v24.xlsx`, with source filename, frozen commit, Git blob SHA-1, raw SHA-256, size, extraction method/timestamp, RTM identity, v24 rank/tier and additional BT fields recorded in the exact-source artifact. Bidder evidence/compliance explicitly did not participate in derivation.

Accordingly, the `V24_LOOKUP_REQUIRED` placeholders in the two governed target batch files have been replaced with exact v24 rank/tier metadata. This closes only the metadata-lineage finding; it does not create requirement closure, bidder acceptance or contractual authority for BT/PCA.

## OFFER boundary summary

- RTM-012..024: direct canonical OFFER interface only for RTM-019..022 → OFFER-04.
- RTM-048..063: direct canonical OFFER interface only for RTM-057..063 → OFFER-11.
- RTM-281..309: no canonical OFFER interface.
- RTM-236..280: canonical relationships include contextual OFFER-13 plus direct/supporting OFFER-19, OFFER-20, OFFER-21, OFFER-22, OFFER-23 and OFFER-24 relationships as recorded in the governed batch file.

OFFER responses remain tender-stage evidence/request interfaces and do not replace RTM compliance or close requirements.

## Promotion gate

Completion of these four review ranges plus the planned v24 rank/tier reconciliation means the planned **item-level review and prioritisation-metadata pass** is complete. It does **not** mean:

- the requirements are closed;
- bidder evidence has been accepted;
- BT/PCA values have contractual authority;
- a range allocation proves individual compliance;
- the QPS accepted-release gate has advanced.

Further work is evidence acquisition/reconciliation against the governed RTM items, not a fifth generic RTM batch. The accepted-release HOLD remains independent and requires its own controlled PC/OneDrive receipt and raw-SHA parity evidence.
