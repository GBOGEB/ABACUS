# W80 / MC-2 Drop-in Restart

Continue from repository authority only.

Do not rely on chat memory.

Do not repeat burned W79 or W80 predicates.

## Refresh first

1. `GBOGEB/ABACUS main`
2. `GBOGEB/ABACUS#1270`
3. `GBOGEB/ABACUS#1164`
4. `GBOGEB/cryoplant-project#1063`

## Read next

Read in this order:

1. `architecture/w79/W79_W78_INPUT.json`
2. `architecture/w80/W80_OBSERVED_VALIDATION_LEDGER.json`
3. `architecture/w80/W80_GITHUB_ACTIONS_RUN_RECEIPT.json`
4. `tools/w80_observed_outcome_validation.py`
5. `tests/test_w80_observed_outcome_validation.py`
6. `architecture/w80/W80_3PSTAR_MIP_CLOSEOUT_RECEIPT_v0.2.json`
7. `handover/mc2/W80_LOSSLESS_HANDOVER_20260918.md`
8. `handover/mc2/W80_CURRENT.json`

## Canonical disposition

- W80 is a controlled negative diagnostic.
- It is not a positive predictor.
- Outcome state coverage is 11 / 15.
- PC1 range coverage is 0.276351.
- Promotion range floor is 0.70.
- Spearman rho is 0.019780.
- Exact permutation p is 0.974459.
- LOOCV R2 is -0.724876.
- Docs-failure AUC is 0.604167.
- Exact AUC p is 0.642424.
- PC1 predictive validation is false.
- Pairwise outcome accumulation is false.
- Pairwise events are empty.
- BT is withheld.
- More elapsed-time PCA is not the default path.
- QPS formal credit delta is zero.

## Exact proof lineage

PR #1266 merge:

```text
a0de73a9a60071665f27bf2fecb6e17e24172a93
```

PR #1269 merge:

```text
fd5e2f705fe4f5201c6c0986bc3508be6bc257bb
```

PR #1270 merge:

```text
5f530096c75715653b7d423cb3db2de759c212ca
```

PR #1270 exact head:

```text
24d94ed2b5fc4f5186929f00025746f42e2a0f49
```

ABACUS matrix run:

```text
35340909766
```

Python 3.10, 3.11, and 3.12 passed with real runner steps.

W80 producer receipt SHA-256:

```text
1412820d9ccfb3eda94ce5deddfe0f25d68d3f7ba032b11a870490a4a0ecfb01
```

## Closeout control note

PR #1272 merged before its failing Markdown lint could block the merge.

Do not treat the #1272 0 / 0 post-merge summary as proof.

The closeout fix-forward must show a real docs job with more than zero
steps before W80 3PC Prove is PASS.

## Do not repair inside W80

Broad `CI/CD Test Suite` debt is separate unless re-routed.

It currently includes:

- DMAIC report generation;
- Week3 8 < 10;
- missing `11_PREVIOUS_SESSIONS`;
- legacy Docker asynchronous and network assertions;
- legacy `docker-compose` executable assumptions.

## Next executable transition

Use 3PR on new evidence.

Prioritize:

1. comparable outcomes for missing low-PC1 states `s01..s04`;
2. an exact-source independent repair or work outcome block.

Only after predictive validation passes may genuine observed pairwise
outcomes be accumulated for BT.

Never synthesize BT pairs from PC1 ordering.
