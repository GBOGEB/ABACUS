# W80 / MC-2 — Drop-in restart

Continue from repository authority only. Do not rely on chat memory and do not repeat burned W79/W80 predicates.

## REFRESH FIRST

1. `GBOGEB/ABACUS main`
2. `GBOGEB/ABACUS#1270`
3. `GBOGEB/ABACUS#1164`
4. `GBOGEB/cryoplant-project#1063`

## READ NEXT, IN ORDER

1. `architecture/w79/W79_W78_INPUT.json`
2. `architecture/w80/W80_OBSERVED_VALIDATION_LEDGER.json`
3. `architecture/w80/W80_GITHUB_ACTIONS_RUN_RECEIPT.json`
4. `tools/w80_observed_outcome_validation.py`
5. `tests/test_w80_observed_outcome_validation.py`
6. `architecture/w80/W80_3PSTAR_MIP_CLOSEOUT_RECEIPT_v0.1.json`
7. `handover/mc2/W80_LOSSLESS_HANDOVER_20260918.md`
8. `handover/mc2/W80_CURRENT.json`

## CANONICAL DISPOSITION

- W80 is a controlled negative diagnostic, not a positive predictor.
- Outcome-state coverage = 11/15.
- PC1 range coverage = 0.276351, below promotion floor 0.70.
- Spearman rho = 0.019780; exact p = 0.974459.
- LOOCV R2 = -0.724876.
- Docs-failure AUC = 0.604167; exact p = 0.642424.
- PC1 predictive validation = false.
- Pairwise outcome accumulation = false.
- Pairwise events = empty.
- BT = withheld.
- More elapsed-time PCA is not the default path.
- QPS engineering/compliance/release/formal credit delta = 0.

## EXACT PROOF LINEAGE

- #1266 merge `a0de73a9a60071665f27bf2fecb6e17e24172a93` — observed outcome validator.
- #1269 merge `fd5e2f705fe4f5201c6c0986bc3508be6bc257bb` — range restriction + exact-run provenance.
- #1270 merge `5f530096c75715653b7d423cb3db2de759c212ca` — SHA-256 receipt pin.
- #1270 exact head `24d94ed2b5fc4f5186929f00025746f42e2a0f49`.
- ABACUS matrix run `35340909766`: Python 3.10/3.11/3.12 PASS with real runner steps.
- W80 Actions producer receipt SHA-256:
  `1412820d9ccfb3eda94ce5deddfe0f25d68d3f7ba032b11a870490a4a0ecfb01`.

## DO NOT REPAIR INSIDE W80

Broad `CI/CD Test Suite` debt is separate unless explicitly re-routed:
DMAIC report generation, Week3 8<10, missing `11_PREVIOUS_SESSIONS`, legacy Docker async/network assertions and `docker-compose` executable assumptions.

## NEXT EXECUTABLE TRANSITION

Use 3PR on new evidence. Prioritize:
1. authoritative comparable outcomes for missing low-PC1 states `s01..s04`; or
2. an exact-source independent repair/work outcome block.

Only after predictive validation passes may genuine observed pairwise outcomes be accumulated for BT. Never synthesize BT pairs from PC1 ordering.
