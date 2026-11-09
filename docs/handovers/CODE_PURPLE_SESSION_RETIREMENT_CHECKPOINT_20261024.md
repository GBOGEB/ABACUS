# CODE PURPLE session retirement checkpoint, 24 October 2026

**Authority:** none. This handover authorises no execution, merge, review
approval or security waiver, and it infers no waiver or engineering-root
closure.

**Verdict:** `READY_FOR_HANDOVER`, not `LOSSLESS_ARCHIVED`. It becomes
archivable once this file is merged, its merge SHA is read back, and it is
linked from `GBOGEB/ABACUS#1860` and `GBOGEB/CODEX#977`.

## Scope: lessons and code only

State, identities, first-reds, coverage cohorts and the execution order live in
[`CODE_PURPLE_20261024_REPO_FIRST.md`](CODE_PURPLE_20261024_REPO_FIRST.md)
(#2422), the single owner of 24 October state. Earlier state lives in
[`ABACUS_20261022_RETIREMENT.md`](ABACUS_20261022_RETIREMENT.md) and
[`ABACUS_20261022_RESTART_CONTRACT.yaml`](ABACUS_20261022_RESTART_CONTRACT.yaml).
This file does not repeat their numbers. Where any handover disagrees with live
GitHub, live GitHub wins.

## 1. One reconciliation

The retiring session's "new blocking first-red" for PR #2388 is **historical**.
The head moved from `23b06e26` to `41ba0ab4`, the unit matrix went from 4/9 to
0/9, and a dropped `Phase8TODOManagement, TODOTracker` import produced two
`NameError`s and two F821 findings. That is root **R01** in the 22 October
retirement doc. PR #2388 merged on 2026-10-23 at
`13a19d72bdb4aea7e2823198b91bc04e4f031f3c` (read with `gh pr view 2388` on
24 October). It is not a live blocker and must not be re-notified. The unit-test
denominators differed (5,551 against 286, because of early termination), so
they are not matched success rates.

## 2. Lessons, and where each now lives

Code is in `scripts/code_purple_evidence.py`.

- **An observed GREEN is not an admissible GREEN.** `admission_verdict()` is
  fail-closed. It needs the exact head, enforced checks and a rejected RED
  canary. Review assertions are derived from the review list, never taken from
  a caller flag, at every level including each MACH-IV train step. A human
  approval needs a `User` actor with a known login and a known, different PR
  author. An automated review needs a positively identified `Bot` or
  `Organization`. MACH-I also needs zero unresolved threads, green lanes and
  mergeability.
- **A merge needs readback.** `merge_verified()` requires a verdict recorded
  for the same head that merged, and the merge SHA read back from main.
- **Issue closure is not root closure.** `engineering_credit()` keeps issue
  state, root state and credit apart. A closed issue alone is
  `HOUSEKEEPING_ONLY`.
- **Repeated alerts for one blocker.** `notifications()` and
  `python scripts/code_purple_evidence.py notify PREV CUR --seen FILE` alert on
  transitions only, with a content-hash `event_id` and a persisted seen set. A
  second verified merge with a new merge SHA alerts again.
- **Unknown is not zero.** Every function returns `None`, `UNKNOWN` or
  `HOLD_UNKNOWN_*`, never a coerced default. Non-numeric coverage deltas are
  ignored, not compared.
- **Four independent KPIs** (coverage, roots, runner activity, admission):
  the `governed-ci-evidence-recovery` skill, section 9. The user-level skill
  carries it. The repo snapshot under `docs/handovers/skills/` is left as on
  main, because editing it makes the docs linter check the whole file.
- **Matched-cohort coverage, deduplicated roots, zero-coverage frontier.**
  Not re-implemented. The owners are listed under "Reuse instead of rebuild"
  in #2422.

Run `python scripts/code_purple_evidence.py admission II evidence.json` and
`python -I tests/test_code_purple_evidence.py`.

## 3. Not done, deliberately

- **Authenticated dispatch and REX contract (CODEX #977).** #2422 step 6
  already lists what the executor owner must decide: exact SHA, principal, path
  leases, idempotency, replay guard, signed receipt and
  `mutation_enabled=false`. It cannot be written from a read-only session.
- **Disjoint worker path leases.** No owner was found on main by a quick grep.
  Run `gh pr list --state open` and check `tools/mip2` before building one.
- **The proposed folder tree** (`ci/governance/`, `tools/recovery/`,
  `schemas/receipts/` and the rest) is a target layout, not a claim that those
  paths exist. Nothing was moved.
- **A separate `code-purple-evidence-auditor` skill** was not created.
  `governed-ci-evidence-recovery` already owns this ground.
- **Composite-key completeness and A to B to A or stale-JUnit scheduler
  tests** (the temporal contract in #2422) belong with
  `tools/mip_ci_wave_telemetry.py`, not here.
- **Lane results and mergeability** stay caller-supplied observations. Only
  review and head assertions are derived.

## 4. Next admissible actions

1. Merge this branch through the normal governed path, with CI green on the
   declared runtime. Local verification here was Python 3.12 only.
2. Read back the merge SHA and record it in `GBOGEB/ABACUS#1860` and
   `GBOGEB/CODEX#977`.
3. Re-run the restart contract reads against live GitHub and move
   `expected_state` forward before claiming any KPI change.
