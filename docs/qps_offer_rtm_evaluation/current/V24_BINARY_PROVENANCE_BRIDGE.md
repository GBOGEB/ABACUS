# QPS OFFER Evaluation v24 — binary provenance bridge

Status: **PROVENANCE BINDING ONLY — NO RANK/TIER PROMOTION**

## Purpose

Bind the current technical-evaluation SSOT identifier to the exact historical binary that was removed from public Git history during binary migration, so that any future rank/tier/BT/PCA export can be verified against the correct v24 source rather than an older workbook or an unbound derivative.

## Bound v24 binary

- Logical path: `docs/qps_offer_rtm_evaluation/current/QPS_OFFER_Evaluation_FULL_v24.xlsx`
- Role: current bidder-independent 50 OFFER × 722 RTM technical-evaluation / BT-PCA SSOT.
- Historical Git blob SHA-1: `bccab3a8ccf539db7c4a9636f1f2abee86885494`
- Recorded byte size: `641318`
- Provenance source: `docs/binary_migration/REMOVED_BINARY_PATHS.tsv`

Companion LITE binary:

- Logical path: `docs/qps_offer_rtm_evaluation/current/QPS_OFFER_Evaluation_LITE_v24.xlsx`
- Historical Git blob SHA-1: `56703fc04b6a43c5cbe95299d54393c00a110b14`
- Recorded byte size: `584494`

The FULL binary is the controlling technical-evaluation source for item-level rank/tier/BT/PCA metadata unless a formally governed successor is declared.

## Export acceptance rule

A derived rank/tier/BT/PCA export may replace `V24_LOOKUP_REQUIRED` only when its lineage records, at minimum:

1. source logical filename `QPS_OFFER_Evaluation_FULL_v24.xlsx`;
2. source binary identity `bccab3a8ccf539db7c4a9636f1f2abee86885494` (historical Git blob SHA-1), or an independently verified raw-file SHA-256 mapped unambiguously to that exact binary;
3. extraction/build method and version;
4. export creation timestamp/version;
5. fixed universe cardinality: 722 RTM and 50 OFFER where applicable;
6. fields exported, including the definitions of rank, tier, BT score/lambda and PCA fields;
7. no bidder/applicant evidence written into the requirement or prioritisation authority layers.

If these conditions are not met, the export remains historical/derived evidence and must not be labelled as governed v24 metadata.

## Current unresolved scope

`V24_LOOKUP_REQUIRED` remains in the governed review files for:

- RTM-048..063;
- RTM-281..309.

No numeric rank/tier values are promoted by this provenance bridge.

## Authority boundary

Addendum II remains contract authority. The canonical 722/50 workbook remains the numbered RTM/OFFER projection and crosswalk. v24 supplies bidder-independent technical-evaluation prioritisation only. Bidder/compliance evidence remains downstream. Binary provenance does not create requirement closure or release acceptance.
