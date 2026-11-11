# A10 F2+F3 phase B - lossless handover (20261022)

Cut `A10-F3B-20261022-v1` · method
`handover/mip/LOSSLESS_RESTART_PROTOCOL_V1.md` · state
`SC_20261109_A10_F3B_STATE_V2.json` (new bounded continuation; live PR and
ruleset evidence still outranks it).

> **Correction recorded 2026-11-09:** the previously named 2026-10-22 V1
> JSON state file was not present in the reviewed PR. No missing original
> state has been reconstructed or backdated. The new
> `SC_20261109_A10_F3B_STATE_V2.json` is a separately dated, bounded
> **observation at its parent head**, with unknowns explicitly retained; it
> is not proof of a private-source move, security acceptance or current-head
> native CI. Re-read GitHub after any commit.

## What changed

- ABACUS `fix/a10-f3-phase-b-20261022` from main `44caccf716`: 13 files with
  offer figures or a restricted deck's identity removed; deck identity in
  `qps_slide_reviewer/lib/analytics.ts` moved to env vars; W05 evaluation
  workflow renamed; supplier/vendor codes that returned since phase A
  (#2075) re-aliased; 15 data/lineage files point at the private copies;
  catalog entry `qps-gate-yaml` is now `controlled_input`; 4 allow-list keys
  of removed versions dropped (guard stricter).
- cryoplant-project `tender/a10-f3-phase-b-20261022` from main `3689ad0c41`:
  byte copies under `tender_library/abacus_phase_b_20261022/` with
  `MANIFEST.csv` (sha256, ABACUS commit).

## Evidence (local, before → after)

| Check | Before | After | Class |
| --- | --- | --- | --- |
| A10 guard --diff base | - | PASS | LOCAL_HASH_ONLY |
| A10 guard --head | FAIL | PASS | LOCAL_HASH_ONLY |
| governance --check | FAIL | FAIL | LOCAL_HASH_ONLY |
| governance unit tests | FAIL | FAIL | LOCAL_HASH_ONLY |
| affected pytest (4 files) | FAIL | FAIL | LOCAL_HASH_ONLY |
| native CI on PR head | - | UNKNOWN | - |

Governance failures marked FAIL before and after are pre-existing on main
(unclassified workflows), not caused here.

## Task status

| Task | Status |
| --- | --- |
| `A10.F3.B.move` | done |
| `A10.F3.B.redact_deck_identity` | done |
| `A10.F3.B.rename_w05` | done |
| `A10.F3.B.alias_regressions` | done |
| `A10.F3.B.guard_diff` | verified |
| `A10.F3.B.guard_head` | verified |
| `A10.F3.B.affected_tests` | unknown |
| `A10.F3.B.native_ci` | unknown |
| `A10.F3.C.history_rewrite` | deferred |
| `A10.6.github_support_and_metadata` | deferred |
| `issue_1996_recheck` | deferred |

## Open, bounded

1. Merge cryoplant PR first, then ABACUS; re-read native CI on the exact
   ABACUS PR head.
2. Re-check agent PRs blocked by issue #1996 after merge; agents must not
   regenerate dumps from private-repo titles.
3. Phase C (history rewrite of the codes, typed GO) then A10.6 GitHub Support
   request; closed-PR titles/bodies that still carry codes are GitHub
   metadata and are handled there.
4. Residual tooling files in `analytics/qps_cost_estimate_roundtrip/` carry
   no codes or figures; disposition with A10.9.

`authority_transfer=false` · `merge_admission=HOLD_until_live_proven` ·
`security_waiver=false`
