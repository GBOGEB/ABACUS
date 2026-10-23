# ABACUS session retirement handover, 22 October 2026

**Status at retirement:** `MERGE_ADMISSION = HOLD` · Formal engineering credit Δ = 0 · Stability 3/3 = UNVERIFIED

**Main:** `GBOGEB/ABACUS@44caccf716a7c20693a2911566289bfc75ea81d9` (superseded on 23 October by `0138ef51`, see §9), unchanged across all four observations (O1 to O4). Open PRs went from 26 (O1) to 31 (O3, O4).

**Source:** four read-only "CODE PURPLE" monitoring reports from the retired chat (O1 to O4), plus one independent unauthenticated GitHub REST readback on 22 October 2026 (V1, ledger row `S05`, §8). Every row lives in `telemetry/*.jsonl`. This file is the human summary of those rows.

---

## 1. Qualified outcomes (candidate-level only, none on main)

| PR | Wave | Exact HEAD | Outcome | Evidence |
|---|---|---|---|---|
| #2388 | W88 | `76531e5a` | Broad-CI matrix 0/9 → 9/9; canonical B0 11/13 → 13/13 | E12, E13 |
| #2388 | W88 | `76531e5a` | +828 covered statements vs `7e9564f9` baseline (33,580 → 34,408 / 46,942; 71.11% → 73.02% combined) | E13, C-W88 |
| #2367 | W76 | `301960e9` | Focused testflight 0/4 → 4/4; B0 11/13 → 13/13; scoped 233/233 stmts and 50/50 branches retained | E05, E11 |
| #2385 | W77-L | `95084b42` | B0 1 FAIL → 0 FAIL, 13/13 | E10 |
| #2375 | GOV | `a38dd42e` | Governance tests 348/349 → 350/350 (population changed) | E07 |
| #2376 | W76 (cbd) | `08bbbea4` | Broad CI FAILURE → SUCCESS (19/1 skipped); +2 covered statements | E14, E15 |

**Do not add these together.** C-W88, C-2376 and C-W76-scoped have overlapping test populations, and each one is a candidate delta against main.

## 2. Causal roots (deduplicated)

| Root | Class | Status | Note |
|---|---|---|---|
| R01 | W88 test harness: undefined `Phase8TODOManagement` / `TODOTracker` | displaced @ `09c0b44c` | 1 root behind the B0 failure, 9 unit cells and 2 × F821 |
| R02 | W88 duplicate TODO-ID assertion | displaced @ `76531e5a` | Failed on Linux/macOS, passed on Windows. Check that the fix did not weaken the assertion |
| R03 | W88 Bandit ratchet +20 (4 test files) | **open** | Still failing at `76531e5a`. Fix with scoped `# nosec` + justification, or rework the literals |
| R04 | W76 missing `mock` import | displaced @ `301960e9` | 1 root, not 4 platform closures |
| R05 | Governance test 348/349 | displaced @ `a38dd42e` | Population changed |
| R06 | W77-L single B0 failure | displaced @ `95084b42` | Test id not recorded |
| R07 | #2376 formatting | displaced @ `08bbbea4` | |
| R08 | Ruleset 24494381 not effective | **open** | No required checks, no last-push approval, no thread resolution, 6 always-bypass, no rejected RED canary |
| R09 | Coverage threshold apparently not enforced | **suspected** | See D3 |

"Displaced" means the first-red moved at a newer source revision. None of these is an *accepted closure*.

## 3. Discrepancies found while reconciling (resolve before relying on the rows)

- **D1 — Rerun attempts. RESOLVED by V1.** E05, E07, E10, E11, E14 and E15 are **attempt 2**. A same-SHA failure on attempt 1 would have made them rerun passes (a flake signal). V1 shows every attempt 1 concluded `action_required` with no jobs executed. Each attempt 2 was therefore the first real execution, and the displacements stand.
- **D2 — "W76" names two PRs. RESOLVED by V1.** #2367 ("CODE PURPLE W76", 10 modules) and #2376 ("cbd W76", 8 release/ICD sources) are two separate W76-lane PRs. Keep them as separate cohorts.
- **D3 — Threshold vs job status.** The broad threshold is 75%, yet the coverage jobs report SUCCESS at 73.02% (E13) and 71.54% (E14). Either the job doesn't enforce `fail_under`, or the 75% figure isn't a gate. Either way the threshold is configured but not effective (R09).
- **D4 — Missing attempts. RESOLVED by V1** for E09, E12 and E13 (attempt 1) and E14 and E15 (attempt 2). E06 (the queued observation) stays `null`.
- **D5 — Previous-run SHAs.** The earlier RED runs 39638604093 (W77-L) and 39741091210 (W76 B0) have no recorded source SHA, so their comparison with the newer heads isn't keyed on exact HEADs.
- **D6 — Checkout identity.** Broad CI checks out a synthetic merge commit (only `ad912b0c` was recorded, for E13). Broad-CI rows are PR-associated diagnostics, not literal-HEAD evidence.
- **D7 — Digests.** All eight artifact SHA256 values come from GitHub metadata. None was re-hashed from downloaded bytes.
- **D8 — Untriaged PRs.** 5 PRs appeared between O1 and O3 and were never characterised. Several other PR heads show `action_required` with no executed jobs, which counts as neither positive nor negative evidence.

## 4. Carried-forward actions

1. **R03:** clear W88 Bandit new debt, then re-run broad CI at the new exact HEAD.
2. **R08:** make ruleset 24494381 effective: add a required-status-check rule (canonical B0 + broad CI), require last-push approval, dismiss stale reviews, require thread resolution, cut always-bypass to the minimum, then prove it by having a deliberately RED canary PR **rejected**.
3. **R09:** confirm whether the coverage job enforces 75%. If it doesn't, decide whether it should.
4. **Bypass actors:** re-read ruleset 24494381 *authenticated*. The unauthenticated API hides `bypass_actors`, so V1 could not confirm the "6 always-bypass" figure.
5. **Approval gate:** six runs needed a manual `action_required` approval before executing. Note this as a governance-relevant step in admission evidence.
6. **R06/W77-L:** reconcile testcase identity (JUnit) between runs 39638604093 and 39769477515.
7. Get terminal broad-CI evidence for #2367 (it was queued) and #2385 (not qualified).
8. TODO registers: ABACUS #1860 is at **1/12**, CODEX #977 at **0/7**. Neither moved during this session.
9. Triage the 5 new PRs (D8).

## 5. Method lessons to keep (from the retired chat)

1. **Composite evidence key:** `repo + source SHA + workflow + run + attempt + job + artifact`. When the source changes, every measurement from the older source is stale. Track checkout SHA separately from PR HEAD.
2. **Causal-root DAG:** `root → tests → jobs → summaries`. Count roots, not red jobs.
3. **Two-dimensional coverage:** keep statement/branch coverage and zero-covered-module count as separate KPIs. Compare only fixed denominators, report losses as well as gains, and never sum overlapping cohorts.
4. **Qualified stability:** 3 transitions need 4 distinct, terminal, comparable, source-changing waves. Re-polling or re-running at the same SHA adds nothing (and see D1: a rerun pass is a flake signal).
5. **Effective enforcement:** a configured rule only counts once a RED canary is rejected.
6. **Separate observation, qualification, admission and credit.** A green run can be valid evidence and still be neither an admissible merge nor engineering credit.

**Notify rule:** notify only when (a) the exact-HEAD terminal first-red changes, (b) same-cohort coverage increases with qualification, (c) a TODO milestone changes, or (d) a correctly governed merge is verified. A new failed run of a known, unchanged root is not material.

## 6. Retirement checklist

| # | Item | State |
|---|---|---|
| 1 | Evidence history and artifact references preserved | **Partial.** Captured in this pack (15 run rows, 4 repo snapshots, 9 roots, 5 cohorts); not yet committed to a repo |
| 2 | Unresolved governance/TODO actions carried forward | **Done in this pack** (§4) |
| 3 | Reusable method and negative tests incorporated | **Partial.** Method in §5 and the `governed-ci-evidence-recovery` skill draft; the negative tests are not implemented |
| 4 | Restart instructions independently verified | **Done (read-only), except bypass actors.** V1 ran the contract's reads and every expected value matched (§8) |

**Verdict:** you can retire the chat **once this pack is committed** (item 1). The chat holds nothing that isn't in these files. Item 3 is work for the repo, not a reason to keep the chat.

## 7. Restart

Follow `ABACUS_20261022_RESTART_CONTRACT.yaml`: re-read main, the five PR heads, the latest terminal runs per workflow, ruleset 24494381 and the two TODO issues. Then compare them with the `S04` and `E12`–`E15` rows. Any mismatch makes that row stale, not wrong. Then run `python -I ci/verify_handover.py .` and expect 0 errors.

## 8. Independent readback V1 (22 October 2026, unauthenticated REST, read-only)

| Check | Expected | Observed |
|---|---|---|
| main | `44caccf7…` | `44caccf7…` ✔ |
| Open PRs | 31 | 31 ✔ |
| PR heads #2388 / #2367 / #2376 / #2385 / #2375 | as in contract | all match; all open, none merged ✔ |
| Run conclusions E09–E15, E05, E07, E10, E11 | as in ledger | all match ✔ |
| Attempt 1 of every attempt-2 run | unknown | `action_required` and never executed (D1 resolved) |
| Ruleset 24494381 rules | no required checks | `deletion, pull_request, non_fast_forward, code_quality, copilot_code_review`. No `required_status_checks` ✔ |
| PR rule params | | 2 approvals, stale dismissal **on**, last-push approval **off**, thread resolution **off** ✔ |
| Bypass actors | 6 | **not visible** without auth |
| ABACUS #1860 / CODEX #977 | 1/12, 0/7 | 1/12, 0/7 (checkbox count) ✔ |

Not re-checked in V1: job-level metrics, coverage numbers, artifact digests (D7) and the coverage-threshold question (R09).

## 9. Addendum V2: main moved on 23 October 2026 (ledger `S06`, root `R10`)

Between 08:02:54Z and 08:10:40Z, main went from `44caccf7` to **`0138ef51`** through 25 first-parent PR merges. All five tracked PRs are now merged, which makes `expected_state` in the restart contract a historical snapshot.

| PR | Merged at | Merge head | Qualified head in this pack | APPROVED reviews | Red at merge head | No conclusion at read time |
|---|---|---|---|---:|---|---|
| #2367 | 08:02:54Z | `15dd7b73` | `301960e9` ✘ | 0 | Bandit Disjoint Census, CI Matrix, CI Workflow Governance | 4 runs |
| #2376 | 08:03:30Z | `08bbbea4` | `08bbbea4` ✔ | 0 | none | none |
| #2385 | 08:04:02Z | `95084b42` | `95084b42` ✔ | 0 | CI Matrix | none |
| #2375 | 08:06:07Z | `d99e70d2` | `a38dd42e` ✘ | 0 | Bandit Disjoint Census, CI Matrix, CI Workflow Governance | 4 runs |
| #2388 | 08:09:06Z | `b44aaa7d` | `76531e5a` ✘ | 0 | CI/CD Test Suite | none |

Ruleset 24494381 was updated at 07:57:58Z, five minutes before the first merge, and still has no `required_status_checks` rule. **V3 correction:** that update set `required_approving_review_count` to **0**, which is the owner's documented solo-developer waiver. So the merges complied with the ruleset. What makes them ungoverned is the missing enforced checks, not the approval count.

**Disposition (revised in V3):** these merges complied with the ruleset but were **not evidence-gated** under §5.5. Candidate evidence in §1 does not become main credit. For #2367, #2375 and #2388 it doesn't carry over at all, because the merged heads differ from the qualified heads. A new main baseline (coverage cohort, B0 at `0138ef51`) is the next qualifying measurement. R03 (W88 Bandit debt) has probably reached main and needs re-reading there.

**MERGE_ADMISSION = N/A (merged) · Formal engineering credit Δ = 0 · Stability 3/3 = UNVERIFIED**

## 10. V3: read-only main baseline at `0138ef51` (23 October 2026)

Ledger `S07`, `E16`–`E20`; cohort `C-MAIN-0138ef51`; roots R08/R10 revised, plus new roots R11 and R12.

| Item | Result | Evidence |
|---|---|---|
| Push runs at main | **9 of 37 failed** (plus 1 cancelled): Validate Docs, Session Tuple CI/CD, export-docs, CI Workflow Governance, TestPilot Pre-GitHub Parity, DOW + Recursive DMAIC, DMAIC Metrics, **CI/CD Test Suite**, **CI Matrix** | S07 |
| MIP B0 | **13/13 success** (producer 120316240659, admission census 120329072380). Canonical artifact 12489263924 `6605eb67…` (GitHub metadata) | E16 |
| CI/CD Test Suite | **failure.** Unit cells 6/9: **all three Python 3.10 cells fail** (exit 2), 3.11/3.12 pass. Security Scanning, Code Quality and Full Red Summary fail. Integration and Docker integration pass. Code Coverage job **skipped** | E17 |
| CI Matrix | **failure.** py3.10 fails, py3.11/3.12 pass; the proof-completeness and compatibility gates fail | E18 |
| CI Workflow Governance | **failure** (`policy-and-inventory`). Detail unreadable without admin auth | E19 |
| **Coverage** | **UNKNOWN.** The CI/CD coverage job is skipped on push. B0's numbers are inside its artifact, and both artifact downloads and job logs need authentication (HTTP 403). No main-coverage figure is claimed | C-MAIN-0138ef51 |
| **Bandit** (local reproduction of the push-mode command, bandit 1.9.1) | **10,916 findings**: 8 HIGH, 95 MEDIUM, 10,813 LOW (10,182 are B101 `assert`). The repo's own `red_root_delta.py` reports NO_PR_CONTEXT, which changes no verdict | E20 |
| **Ruleset 24494381** | Active on `~DEFAULT_BRANCH`. **`required_approving_review_count: 0`** (solo waiver); stale-review dismissal on; last-push approval off; thread resolution off; extra approval for unattributed changes on; `code_quality` severity `errors`; Copilot review on drafts, not on push. **No `required_status_checks`.** Bypass actors not visible without auth | S07 |

**New roots**
- **R11, structurally red security lane.** On push, `Enforce security red roots` fails whenever `bandit -r .` exits non-zero, which happens with any whole-repo finding. Main can't show a green CI/CD Test Suite until push mode uses a baseline ratchet, or `-lll` plus excluding B101 under `tests/`.
- **R12, Python 3.10 (suspected).** `tools/triage/config_surface_audit.py` (#2390) imports `tomllib` unconditionally, and `tests/test_config_surface_audit.py` imports that module. `pyproject.toml` says `requires-python >=3.11`. Either drop the 3.10 cells or guard the import.

**Method change:** the solo-developer approval waiver is now explicit policy. Admission is judged by the **CODE PURPLE MACH ladder** (`docs/governance/CODE_PURPLE_MACH_LADDER.md`), where MACH-II's compensating control is *platform-enforced required checks*. Replayed through the evaluator, the 23 October burst holds at step 1 (`HOLD_CHECKS_NOT_ENFORCED`). With checks enforced it would hold on red or pending lanes, and from step 2 on a stale base.

**To close the coverage gap:** with an authenticated `gh`, run `gh run download 39922825831 -R GBOGEB/ABACUS -n b0-canonical-0138ef5193b20ef8a64132267444299074cd8beb -D <empty dir>`, then record its totals as `C-MAIN-0138ef51`.

**MERGE_ADMISSION = HOLD (MACH-II prerequisite unmet) · Formal engineering credit Δ = 0 · Stability 3/3 = UNVERIFIED**
