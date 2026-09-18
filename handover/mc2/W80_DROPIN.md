# W80 / MC-2 Drop-in Restart

Continue from repository authority only.

Do not rely on chat memory.

Do not repeat burned W79 or W80 predicates.

## Refresh first

1. `GBOGEB/ABACUS main`
2. `GBOGEB/ABACUS#1274`
3. `GBOGEB/ABACUS#1164`
4. `GBOGEB/cryoplant-project#1063`

## Read next

Read in this order:

1. `architecture/w79/W79_W78_INPUT.json`
2. `architecture/w80/W80_OBSERVED_VALIDATION_LEDGER.json`
3. `architecture/w80/W80_GITHUB_ACTIONS_RUN_RECEIPT.json`
4. `tools/w80_observed_outcome_validation.py`
5. `tests/test_w80_observed_outcome_validation.py`
6. `architecture/w80/W80_3PSTAR_MIP_CLOSEOUT_RECEIPT_v0.3.json`
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

## 3P* and MIP state

- 3PR Refresh, Probe, and Rank are PASS.
- 3PC Prepare, Prove, and Commit are PASS.
- MIP Modernize is PASS.
- MIP Innovate is PASS_DIAGNOSTIC_ONLY.
- MIP Perpetuate is PASS_REPOSITORY_NATIVE.

## Final closeout proof

PR #1274 final head:

```text
7d9802aab65b3fead4c1a99719b839485d55f8a2
```

PR #1274 merge:

```text
b4094dbabf1bc2d750fdc0803d4ccc25ca5cf524
```

Changed-docs proof:

```text
run 35350555778
job 105617410488
PASS_GT_ZERO_STEPS
```

Final-head matrix proof:

```text
run 35350555821
Python 3.10 PASS
Python 3.11 PASS
Python 3.12 PASS
```

W80 producer receipt SHA-256:

```text
1412820d9ccfb3eda94ce5deddfe0f25d68d3f7ba032b11a870490a4a0ecfb01
```

Receipt v0.3 closes the v0.2 chronology finding.

## Separate non-compensating reds

Broad `CI/CD Test Suite` debt remains outside W80.

It currently includes:

- DMAIC report generation;
- Week3 8 < 10;
- missing `11_PREVIOUS_SESSIONS`;
- legacy Docker asynchronous and network assertions;
- legacy `docker-compose` executable assumptions.

Two #1274 merge-push failures are also outside W80:

- Pandoc and TeX package installation failed;
- QPLANT presentation test collection lacked `requests`.

Do not convert these into W80 outcome or authority credit.

## Next executable transition

Use 3PR only on new evidence.

Prioritize:

1. comparable outcomes for missing low-PC1 states `s01..s04`;
2. an exact-source independent repair or work outcome block.

Only after predictive validation passes may genuine observed pairwise
outcomes be accumulated for BT.

Never synthesize BT pairs from PC1 ordering.
