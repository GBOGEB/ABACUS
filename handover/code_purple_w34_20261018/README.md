# CODE PURPLE W34 — GitHub-first governed lossless operational packet

**Status: MERGE_ADMISSION=HOLD.** This is an unmerged source-staging branch, not a properly admitted main change. It preserves tested source and a dated GitHub-first continuation packet; it does not seal/replay the canonical LOSSLESS_HANDOVER_V2 archive or contain a verbatim chat export.

## Read order

1. [STATE.json](STATE.json) — five-repository SHA crosswalk, exact B0, source slices, gate vector, UNKNOWNs.
2. [HANDOVER.md](HANDOVER.md) — full N-1/N/N+1 operational record, three source-owner lanes and guarded action sequence.
3. [DROPIN.md](DROPIN.md) — copy-ready CP.RESUME receiver.
4. [HISTORY.json](HISTORY.json) — immutable earlier heads, native run/job identities and root manifestations.
5. [EVIDENCE_GRAPH.json](EVIDENCE_GRAPH.json) / [DAG.mmd](DAG.mmd) — evidence DAG and source/consumer relationships.
6. [FORECAST.json](FORECAST.json) — immutable conditional N+1/N+2/N+3 predictions (actuals unknown).
7. [TEMPLATE.md](TEMPLATE.md) — field overlay to the pre-existing published handover template.
8. [QA_REPORT.json](QA_REPORT.json) and [MANIFEST.json](MANIFEST.json) — local/adversarial proof and GitHub blob-index receipts, not a V2 replay seal.

## Three independently staged branches

- [W34-A matrix](https://github.com/GBOGEB/ABACUS/tree/code-purple/w34-matrix-networkx-sourceowner-20261018): interpreter-scoped NetworkX in broad requirements-test.txt, five test-contract methods.
- [W34-B proof/handover](https://github.com/GBOGEB/ABACUS/tree/code-purple/w34-proof-verified-handover-20261018): repair false source-reported evidence promotion; ZIP/JUnit/branch-coverage byte verifier; 18/18 **local synthetic** tests passed and source/test Git blobs matched locally.
- [W34-C G3CS](https://github.com/GBOGEB/ABACUS/tree/code-purple/w34-g3cs-single-source-missing-marker-20261018): single governed optional archive marker + source-missing reason; protects all original negative parser tests.

Latest canonical B0 source observation: [main run 39159906022](https://github.com/GBOGEB/ABACUS/actions/runs/39159906022) attempt 1, head 994ad6e73c748923841d92b12651e92d41b2d4ff, 11/13 jobs success, canonical 3,854 PASS / 3 FAIL / 1 SKIP. GitHub-native qualification of these new branches remains UNKNOWN. No PR was opened, no CI rerun dispatched and no merge performed by this W34 wave.

Canonical authority remains [issue #1860](https://github.com/GBOGEB/ABACUS/issues/1860#issuecomment-6214640143), [ruleset #24494381](https://github.com/GBOGEB/ABACUS/rules/24494381), the published [handover template](../HANDOVER_MESSAGE_TEMPLATE.md), and [V2 process specification](../../tools/handover_v2/process_spec.json).
