# W83-NG1 LOSSLESS DROP-IN

Continue MC-2 measured-outcome work from repository authority.

## Read first

1. `handover/mc2/W83_CURRENT.json`
2. `architecture/w83/W83_NG1_CONTROL_v0.1.json`
3. `architecture/w83/W83_NG1_NON_GOVERNANCE_OUTCOME_LEDGER_v0.1.json`
4. `architecture/w83/W83_NG1_NON_GOVERNANCE_OUTCOME_DIAGNOSTIC_v0.1.json`

## Controlled result

NG1 reuses already-executed W83 exact-source receipts for the 11 W80 states
with independent observed validation outcomes.

Geometry:

- 11 states;
- 8 docs failures / 3 passes;
- 2 semantic-composition vectors;
- 6 consumer-graph vectors;
- 16 varying non-governance features;
- all 165 label assignments enumerated.

Exact AUC permutation tests plus Holm FWER found no surviving signal.

Strongest raw feature:
`consumer_graph_distribution.consumer_entities_exactly_one_file`

- AUC: `0.770833`
- exact p: `0.151515`
- Holm p: `1.0`

Therefore W83-NG1 is a controlled measured negative.

No PCA was fit. Timing PCA remains closed. PC1 predictive validation remains
false. No pairwise events are admitted and BT remains withheld. There is no
allocation, engineering, compliance, release, or formal-credit authority.

## Next admissible frontier

Acquire broader independent exact-source outcomes and/or deterministic
change-delta features. Prefer evidence that increases outcome and topology
diversity rather than more near-identical governance heads.

Do not compensate `cryoplant-project#923`.
