# W190 DOW Final-Head Repair

This DOW repair corrects the W190 exact-SHA chain after cryoplant #1178 was
finalized/merged with a different final PR head than the first DOW consumer used.

## Final Child Binding

- Child PR: [cryoplant #1178](https://github.com/GBOGEB/cryoplant-project/pull/1178)
- Final child PR head: `c283eb1f7d19eaa22b31a888a51c798c36107df5`
- Child execution receipt path:
  `federation/w190/W190_3PC_MIP_EXECUTION_RECEIPT.json`
- Execution receipt declared head:
  `37623d581df7d91c6ad9ee4e732d3666b44c3569`
- Execution receipt state: `WITHHELD_INFRA_PREEXECUTION`
- Runner evidence: `runner_id=0, steps=0, INFRA_PREEXECUTION`

## DOW Disposition

- Final-head repair: **ACCEPT**
- Global DoV: **DEFER**

The receipt is a valid handover/control record, but not a runtime promotion.
