# CODE PURPLE session retirement checkpoint, 24 October 2026

**Authority:** none. This handover authorises no execution, merge, review approval or security waiver, and it infers no waiver or engineering-root closure.

**Verdict:** `READY_FOR_HANDOVER`, not `LOSSLESS_ARCHIVED`. It becomes archivable once this file is merged, its merge SHA is read back, and it is linked from `GBOGEB/ABACUS#1860` and `GBOGEB/CODEX#977`.

## Scope: lessons and code only

State, identities, first-reds, coverage cohorts and the execution order live in [`CODE_PURPLE_20261024_REPO_FIRST.md`](CODE_PURPLE_20261024_REPO_FIRST.md) (#2422), the single owner of 24 October state. Earlier state lives in [`ABACUS_20261022_RETIREMENT.md`](ABACUS_20261022_RETIREMENT.md) and [`ABACUS_20261022_RESTART_CONTRACT.yaml`](ABACUS_20261022_RESTART_CONTRACT.yaml). This file does not repeat their numbers. Where any handover disagrees with live GitHub, live GitHub wins.

## 1. One reconciliation

The retiring session's "new blocking first-red" for PR #2388 (head `23b06e26` → `41ba0ab4`, 4/9 → 0/9 unit cells, two `NameError`s and two F821 findings from a dropped `Phase8TODOManagement, TODOTracker` import) is **historical**. It is root **R01** in the 22 October retirement doc, and #2388 merged on 2026-10-23 at `13a19d72bdb4aea7e2823198b91bc04e4f031f3c` (read with `gh pr view 2388` on 24 October). It is not a live blocker and must not be re-notified. The unit-test denominators differed (5,551 vs 286, early termination), so they are not matched success rates.

## 2. Lessons, and where each now lives

| Lesson | Permanent home |
|---|---|
| An observed GREEN is not an admissible GREEN | `admission_verdict()` in `scripts/code_purple_evidence.py`: fail-closed, requires exact head, enforced checks, a rejected RED canary, and review identity derived from the review list rather than a caller flag. MACH-I also requires green lanes and mergeability |
| A merge needs readback | `merge_verified()`: verdict recorded for the same head that merged, and the merge SHA read back from main |
| Issue closure ≠ root closure | `engineering_credit()`: keeps `issue_state`, `root_state` and credit apart; a closed issue alone is `HOUSEKEEPING_ONLY` |
| Repeated alerts for one blocker | `notifications()` / `python scripts/code_purple_evidence.py notify PREV CUR --seen FILE`: transitions only, content-hash `event_id`, persisted seen set |
| Unknown is not zero | Every function returns `None`, `UNKNOWN` or `HOLD_UNKNOWN_*`, never a coerced default; non-numeric coverage deltas are ignored, not compared |
| Four independent KPIs: coverage, roots, runner activity, admission | `governed-ci-evidence-recovery` skill, section 9 |
| Matched-cohort coverage, deduplicated roots, zero-coverage frontier | **Not re-implemented.** Owners are listed under "Reuse instead of rebuild" in #2422 |

Run: `python scripts/code_purple_evidence.py admission II evidence.json` and `python -I tests/test_code_purple_evidence.py`.

## 3. Not done, deliberately

- **Authenticated dispatch and REX contract (CODEX #977):** #2422 step 6 already lists what the executor owner must decide (exact SHA, principal, path leases, idempotency, replay guard, signed receipt, `mutation_enabled=false`). It cannot be written from a read-only session.
- **Disjoint worker path leases:** no owner found on main by a quick grep. Run `gh pr list --state open` and check `tools/mip2` before building one.
- **The proposed folder tree** (`ci/governance/`, `tools/recovery/`, `schemas/receipts/` and the rest) is a target layout, not a claim that those paths exist. Nothing was moved.
- **A separate `code-purple-evidence-auditor` skill:** not created. `governed-ci-evidence-recovery` already owns this ground and now points at the executable contracts.
- **Composite-key completeness and A→B→A / stale-JUnit scheduler tests** (the temporal contract in #2422): belong with `tools/mip_ci_wave_telemetry.py`, not here.

## 4. Next admissible actions

1. Merge this branch through the normal governed path, with CI green on the declared runtime. Local verification here was Python 3.12 only.
2. Read back the merge SHA and record it in `GBOGEB/ABACUS#1860` and `GBOGEB/CODEX#977`.
3. Re-run the restart contract reads against live GitHub and move `expected_state` forward before claiming any KPI change.
