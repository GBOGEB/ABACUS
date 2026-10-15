# MIP regression recovery — pulse ledger (2026-10-15)

Authority: observational and candidate repair only. No merge admission,
waiver, security signoff, dispatched worker, accepted REX, or formal BD root
closure.

## Scope and lineage

- ABACUS reference recovery: [source][a]
- CODEX dispatch: [source][b] ; reference PR [source][c]
- Repair candidate: [source][d] (draft)
- Observed candidate base/main: `54da377cf82a358ac97903ecde0270c975b8fcc1`
- First candidate exact head: `03da7ffe2f565ad2403d5f76680fdaa0609aa177`
- Previous exact head for PR #1990:
  `01d99b1bda4ec828d6ffbe6f3fa6a911cd89ffcd`
- Introducing dependency merge #2012:
  `5bbc09ab72cda4bbc74ddc054f899c76252743b7`

## Pulse 0 — before

- Regression: Python 3.10 pip resolution FAIL because matplotlib>=3.11.2
  applied unconditionally.
- Earlier Python 3.10/3.11/3.12 matrix: 3/3 PASS [source][e]
- Regressed matrix: 2/3 PASS; Python 3.10 FAIL; run [source][f] ; failed job
  [source][g]
- Measured Python matrix pass fraction: 100% -> 66.67%, delta -33.33
  percentage points.
- Actual comparable new-main coverage: UNKNOWN. Earlier measured main
  21,391/39,139 = 54.653926% at `85dad8fbdab530d40e6ccf2f664c455f89454aad`.
- Historical baseline: 2026-10-11 main 36.85%; 2026-10-12 PR 36.92% broad,
  51% diff. Source scope comparability not established.
- PR #1990 broad prior: 21,971/39,721 = 55.313310%. Whole-PR changed-line
  coverage: UNKNOWN.
- Distinct BD roots open / closed: UNKNOWN / UNKNOWN. GitHub issue counts
  must not substitute for root counts.
- #1860 TODOs: 0/12 checked; #977 execution TODOs: 0/7 checked (at fresh
  read).
- Authenticated ABACUS-local mission dispatch ID: UNKNOWN; accepted REX
  return: UNKNOWN.
- P0 admission: HOLD; first correctly admitted merge: NOT VERIFIED.

## Pulse 1 — repair candidate, NOT native-qualified

- Updated `DMAIC_V3/requirements.txt` to use 3.10.x matplotlib for Python
  <3.11 and >=3.11.2 on Python >=3.11; no security waiver. Follow-up security
  policy compatibility is separately necessary.
- Added static regression boundary and negative control in
  `tests/test_matplotlib_requirement_compatibility.py`.
- PR #2026 opened in DRAFT. Source repair committed; native impact UNKNOWN
  pending terminal same-head jobs.
- Matrix native candidate: [source][h] (initial observed QUEUED).
- Full CI native candidate: [source][i] (initial observed QUEUED).
- A10 native candidate: [source][j] (initial observed QUEUED).
- Net coverage change (main and PR, comparable): UNKNOWN; diff coverage:
  UNKNOWN.
- Formal accepted closures: UNKNOWN. No assumed increment.
- Native first-red after repair: UNKNOWN until terminal logs are inspected.

## Observed native pulse before final QA repair

- Python 3.10 full-CI unit tests passed, including 3 new regression tests.
- DMAIC Python 3.10 installed matplotlib 3.10.9; 229 tests passed.
- Dedicated 3.10/3.11/3.12 matrix still awaited terminal proof.
- A10, OSV, dependency review and Ruff: PASS at observed head.
- Full-CI security: FAIL (Bandit 6607 outside touched files; Safety exit 64).
- Changed-code formatting: one Black and one isort new-debt finding.
- Handover Markdown: 44 attributable lint findings.
- None of these observations counts as merge admission or BD-root closure.

## Pulse 2 — next admissible verification

1. Re-read PR #2026 head and main exact SHAs; do not reuse this snapshot as
   present authority.
2. Consume terminal Python matrix and pip install logs on exact head. Require
   Python 3.10, 3.11 and 3.12 success; inspect source errors if not.
3. Run/inspect static regression tests natively. Repair only attributable
   first-reds in disjoint commits; update exact SHA every time.
4. Compare measured main and PR coverage with matched source/denominator
   cohort; report UNKNOWN when not available.
5. Confirm required branch checks, independently eligible approval, A10 and
   security, never waive.
6. Confirm actual authenticated worker execution via run/job/actor ID and REX
   artifact before counting any dispatch.
7. Record root fingerprint identity, source receipts, before/after
   open/closed root counts; proposal jobs are not formal root closures.
8. On eligible merge, record terminal CI URLs, source head SHA, merge commit
   SHA, exact main readback and postmerge coverage.
9. No chat deletion certification until a durable GitHub checkpoint holds
   terminal outcomes, live admission authority and enough state to resume
   without this chat.

## MIP telemetry contract (next improvement)

Each pulse must emit `wave_id`, `source_sha`, `base_sha`, `workflow_run_id`,
`job_ids`, `runner_actor`, `test_pass/test_fail`, `coverage_scope`, `covered`,
`total`, `changed_covered`, `changed_total`, `first_red_signature`, `root_id`,
`root_state`, `evidence_url`, `admission_state` and `rex_receipt`. Unknown
values must be the literal UNKNOWN, never fabricated zero. Separate observed
stage/workflow execution from approved mutation launch.

Classification: candidate source fix + traceable staged MIP pulse ledger, not
regression closure.

[a]: https://github.com/GBOGEB/ABACUS/issues/1860
[b]: https://github.com/GBOGEB/CODEX/issues/977
[c]: https://github.com/GBOGEB/CODEX/pull/975
[d]: https://github.com/GBOGEB/ABACUS/pull/2026
[e]: https://github.com/GBOGEB/ABACUS/actions/runs/38743473914
[f]: https://github.com/GBOGEB/ABACUS/actions/runs/38749352738
[g]: https://github.com/GBOGEB/ABACUS/actions/runs/38749352738/job/116473333563
[h]: https://github.com/GBOGEB/ABACUS/actions/runs/38771416057
[i]: https://github.com/GBOGEB/ABACUS/actions/runs/38771415939
[j]: https://github.com/GBOGEB/ABACUS/actions/runs/38771416003
