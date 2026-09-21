# W81 LOSSLESS DROP-IN

Continue MC-2 measured outcome work from repository authority.

## Read first

1. `handover/mc2/W80_CURRENT.json`
2. `architecture/w81/W81_REPAIR_PAIR_DIAGNOSTIC_v0.1.json`
3. `handover/mc2/W81_CURRENT.json`

## Current state

- W80 remains `CONTROLLED_NEGATIVE_DIAGNOSTIC_FINAL`.
- The W81 primary low-PC1 census found zero Actions runs for all four
  missing W80 states `s01..s04`. Missing remains missing, never zero.
- W81 measured two exact red-to-green repair pairs with four real hosted
  exact-source work receipts.
- All four repair states have the same semantic-work vector.
- Frozen W79 semantic PC1 is identical: `2.3131321337`.
- Full-work PC1 changes are tiny:
  W77 `+0.0002570950`; W80 `+0.0040909488`.
- All four projected states are above the W79 in-sample PC1 maximum.
  Treat them as extrapolative high-tail diagnostics.
- No PCA refit.
- `PC1_PREDICTIVE_VALIDATION=false`.
- Pairwise accumulation remains false; `BT=WITHHELD`.
- No allocation, engineering, compliance, release, or formal-credit
  authority is granted.

## Next admissible frontier

Seek exact-source outcomes that are **semantically diverse**, not more
instances of the same semantic vector
`[74,15,18,11,18,26,29]`.

Preferred evidence:

- a distinct semantic-work vector;
- an independently observed machine outcome;
- exact source SHA and a greater-than-zero-step receipt;
- enough support diversity to avoid the present high-PC1 extrapolation
  region.

Do not create BT pairs from repair order, PR chronology, or PC1 score
alone.

## REX

PR #1290 was intended to be disposable, but repository automation
auto-merged it. The corrective transaction removes only the temporary
W81 job from the W78 workflow and retains the measured receipts.

Future disposable probes require an explicit merge-prevention mechanism
stronger than PR prose.
