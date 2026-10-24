# CODE PURPLE session retirement checkpoint, 24 October 2026

**Authority:** none. This handover authorises no execution, merge, review approval or security waiver, and it infers no waiver or engineering-root closure.

**Verdict:** `READY_FOR_HANDOVER`, not `LOSSLESS_ARCHIVED`. It becomes archivable once this file is merged, its merge SHA is read back, and it is linked from `GBOGEB/ABACUS#1860` and `GBOGEB/CODEX#977`.

Extends [`ABACUS_20261022_RETIREMENT.md`](ABACUS_20261022_RETIREMENT.md) and [`ABACUS_20261022_RESTART_CONTRACT.yaml`](ABACUS_20261022_RESTART_CONTRACT.yaml). Where this file disagrees with live GitHub, live GitHub wins.

## 1. Live facts re-read on 24 October 2026

| Fact | Value | How read |
|---|---|---|
| ABACUS `origin/main` | `25940371d4750afa00be15f48c6b53963c9b534e` | `git fetch`, then `git log -1 origin/main` |
| ABACUS PR #2388 | **MERGED** 2026-10-23T08:09:06Z, merge commit `13a19d72bdb4aea7e2823198b91bc04e4f031f3c`, head `b44aaa7d4f35136e3d5bdaa9bf13e4b1a062ab51` | `gh pr view 2388` |
| ABACUS #1860, CODEX #977 | both OPEN | `gh issue view` |

## 2. Observations carried from the retiring session (not re-verified)

Everything here was reported by the retiring session on 22 October. Treat it as historical and re-read it before relying on it.

- **#2388 first-red regression:** head `23b06e26` → `41ba0ab4` took the unit matrix from 4/9 to 0/9. Cause: a 3-line change to `tests/coverage/test_phase8_todo_management_lane3.py` (blob `b91bc337` → `c6d70c51`) dropped the `Phase8TODOManagement, TODOTracker` import, giving 2 `NameError`s and 2 new F821 findings. This is root **R01** in the 22 October retirement doc. #2388 has since merged at a later head, so it is no longer a live blocker.
- **Unit-test denominators differed** (5,551 executed at `23b06e26`, 286 at `41ba0ab4`) because the later job stopped early. They are not matched success rates.
- **Main coverage:** 33,579 → 33,580 of 46,942 statements, branches unchanged at 9,830 of 14,102. The one-statement difference is unattributed and earns no credit.
- **Dashboard #1885:** 53 historical broken hrefs (50 MYRRHA, 2 reports, 1 dynamic expression). Six alert tickets were closed as duplicate or housekeeping, which is `HOUSEKEEPING_ONLY` and earns no engineering-root credit.
- **Formal TODOs on #1860:** 1/12 at last report. Engineering-root OPEN/CLOSED counts: UNKNOWN/UNKNOWN.
- **Authenticated CODEX-to-ABACUS mutation launch:** UNVERIFIED. CODEX #977 dispatch was `STAGED_NOT_LAUNCHED`. B0 runner receipts prove GitHub-hosted execution, not authenticated source mutation.

## 3. Lessons, and where each now lives

| Lesson | Permanent home |
|---|---|
| An observed GREEN is not an admissible GREEN | `admission_verdict()` in `scripts/code_purple_evidence.py`: fail-closed, requires exact head, enforced checks, a rejected RED canary, and review identity derived from the review list rather than a caller flag |
| A merge needs readback | `merge_verified()`: verdict recorded for the same head that merged, and the merge SHA read back from main |
| Issue closure ≠ root closure | `engineering_credit()`: keeps `issue_state`, `root_state` and credit apart; a closed issue alone is `HOUSEKEEPING_ONLY` |
| Repeated alerts for one blocker | `notifications()`: transitions only, identified by a content-hash `event_id`; the caller persists the seen set |
| Unknown is not zero | Every function returns `None`, `UNKNOWN` or `HOLD_UNKNOWN_*`, never a coerced default |
| Four independent KPIs: coverage, roots, runner activity, admission | `governed-ci-evidence-recovery` skill, section 9 |
| Matched-cohort coverage, deduplicated roots, zero-coverage frontier | **Not re-implemented here.** Existing owners on main: `cbd-matched-coverage.yml`, `tools/mip2/mip_wave_series.py`, `triage/ABACUS_BD_QUEUE_CURRENT.yaml`, `tools/everred_v3/` |

## 4. Not done, deliberately

- **Authenticated dispatch and REX evidence contract (CODEX #977):** needs the dispatch principal, nonce and run/job IDs from a real launch. It cannot be written from this session.
- **Disjoint worker path leases:** no existing owner was found on main by a quick grep. Check `gh pr list --state open` and `tools/mip2` before building one.
- **The proposed folder tree** (`ci/governance/`, `tools/recovery/`, `schemas/receipts/` and the rest) is a target layout, not a claim that those paths exist. Nothing was moved.
- **A separate `code-purple-evidence-auditor` skill:** not created. The existing `governed-ci-evidence-recovery` skill already owns this ground and now points at the executable contracts.

## 5. Next admissible actions

1. Merge this file through the normal governed path. Do not merge with any gate red.
2. Read back the merge SHA and record it in `GBOGEB/ABACUS#1860` and `GBOGEB/CODEX#977`.
3. Re-run the restart contract reads against live GitHub. Move `expected_state` forward to the new main SHA before claiming any KPI change.
4. Open a separate PR for the CODEX transport/REX contract once a real authenticated launch exists.
