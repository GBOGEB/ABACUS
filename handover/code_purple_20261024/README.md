# CODE PURPLE 24 October 2026 snapshot

Dated, as-received snapshot of two analyst tables that accompanied the
[24 October repo-first handover](../../docs/handovers/CODE_PURPLE_20261024_REPO_FIRST.md).
Both files are kept as received, except that line endings are normalised
from CRLF to LF (both hashes are in `MANIFEST.json`). They are **not**
sources of truth:

- the live issue state is on GitHub;
- the coverage cohorts are owned by `telemetry/coverage_cohorts.jsonl`,
  with run rows in `telemetry/evidence_ledger.jsonl` (`obs: O24`, `E21` to
  `E28`).

## `issues_snapshot.csv`

52 rows: ABACUS 41 and CODEX 11 open issues. At the 24 October readback
(main `25940371`) this matched the live open set exactly, with no missing,
extra or duplicate issue. `title` and `family` are analyst paraphrases and
groupings, not GitHub titles or labels. Every `closure_class` is
`UNKNOWN_ENGINEERING_ROOT`: a GitHub issue state is not a root state.

## `coverage_waves.csv`

11 wave observations on the 429-file, 46942-statement, 14102-branch
population. Every percentage and combined figure recomputes exactly. Read
it with these corrections, which the JSONL ledger already carries:

- **Two baselines, two SHAs.** `N0` (`7e9564f9`) = 33579 and `N8`
  (`44caccf7`) = 33580, confirmed from the artifact bytes. There is a
  1-statement noise floor between them: no `.py` file changed.
- **Per-candidate bases.** Each PR row was measured on a synthetic merge.
  The checkout SHA is in the artifact name and its parents give the base:
  W75-A is on `7e9564f9`; W53-GG/ER/BD/RT, W77 and W88 are on `44caccf7`.
  So every row except W75-A should be compared with `N8`, not `N0`.
- **`merge_sha` on the W88 row** (`ad912b0c`) is the synthetic-merge
  checkout, not the GitHub merge. #2388 merged head `b44aaa7d` as
  `13a19d72`; the measured head was `76531e5a`.
- `N9` and `N10` have no measurement. They mean UNKNOWN, not 0.
- Candidate deltas overlap in test population and must not be summed.
