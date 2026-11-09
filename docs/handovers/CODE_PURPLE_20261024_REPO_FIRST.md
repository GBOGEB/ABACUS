# CODE PURPLE — 24 October 2026 repo-first handover

**Status:** READ-ONLY OBSERVATION / MERGE_ADMISSION=HOLD / no
engineering-root closure credit / no inferred launch, approval or waiver.

This is the durable, reviewable entrypoint for the 24 October readback. It
supplements, rather than replaces, the canonical historical ledgers under
`telemetry/` and the existing [22 October retirement
handover](ABACUS_20261022_RETIREMENT.md). No ZIP is a release dependency.
Create ZIP archives **only on explicit owner request**.

The dated snapshot of the issue register and the wave observations is in
[`handover/code_purple_20261024/`](../../handover/code_purple_20261024/README.md).
Corrections made after the first cut (`f7659f26`) are listed at the end
under "Corrections log".

## Exact identities (24 October readback)

- ABACUS main: `25940371d4750afa00be15f48c6b53963c9b534e`.
- CODEX main: `58ee1520b0ed90265e4134be82f5580d60a30139`.
- gg_MATH main observed: `952d62ea1f98099fc7bc514340d3304e9dd165d1`.
- ABACUS #1860 checkbox state: 1/12; CODEX #977: 0/7.
- GitHub repository-count snapshot: ABACUS 41 open issues / 3 open PR;
  CODEX 11 open issues / 2 open draft PR (#1162, #1163; 0 at the first
  cut). **These are not engineering-root counts.**
- CODEX PR #975 was merged historically, merge SHA
  `c51b3debd784558c6ccb9b85d091eb1decb38605`. It is not an authenticated
  ABACUS worker dispatch.

## P0 admission

[ABACUS ruleset 24494381][ruleset] is active but has **no
required_status_checks rule**. It has 0 required approving reviews under
the documented solo-owner policy (`solo_owner_waiver` in
`config/governance/code_purple_mach_policy.json`, whose `mode` is still
`CODE_PURPLE_MACH_LADDER_PROPOSED`). Last-push approval is false,
thread resolution is false, and six integrations can always bypass.
`copilot_code_review.review_on_push` is false, so the automated review is
not refreshed at a new head.

A correctly governed first-main merge under the evidence-gated policy is
**not verified**. It needs an owner decision, effective platform status
checks and a server-rejected RED canary. Keep independently required
security evidence noncompensating. No backdated admission for the
October 23 merge burst.

Before `CI/CD Test Suite` becomes a required check, note that
`.github/workflows/ci-cd-tests.yml` has `paths:` filters on
`pull_request`. A docs-only PR would wait on it forever.

[ABACUS #1860][i1860] | [CODEX #977][i977] |
[ABACUS MACH-II–IV ladder (proposed)](../governance/CODE_PURPLE_MACH_LADDER.md)

## Exact-main first-reds

- **ABACUS Pages**: [run 40092398089][r-pages], job 120867593397.
  Detect package manager fails: `Unable to determine package manager`;
  deploy skipped.
- **ABACUS DOW/CD**: [run 40092397997][r-dow], job 120867592752.
  Pre-commit modifies files and TestPilot preflight fails; downstream
  skipped.
- **ABACUS EVERRED** (schedule event): [run 40094315794][r-er],
  job 120873270178. Black/isort gate; no-push patch proposal
  [artifact 12559279700][a-er] with eight paths. Possibly the same
  formatting root as the DOW pre-commit mutation (suspected, not proven).
- **CODEX OSV**: [run 39983531098][r-osv], job 120516695586. `certifi`
  2026.7.22 critical PYSEC-2026-4320, fixed version reported 2026.10.19.
  `certifi` is not pinned in `requirements.txt`; it is transitive.
- **CODEX Metrics** (per-commit tracking): [run 39983531344][r-cxm],
  step "Commit metrics artefacts" fails. Not classified yet.
- **ABACUS main CI**: [run 40092398057][r-main] SUCCESS. Not a
  replacement for missing mandatory/enforced lanes.
- **ABACUS CodeQL**: [run 40092398054][r-cql] SUCCESS. Not a waiver.

## Coverage: immutable and non-additive

- Committed historical records: `telemetry/causal_roots.jsonl` (14
  records), `telemetry/evidence_ledger.jsonl` and
  `telemetry/coverage_cohorts.jsonl`.
- **Two baseline observations, two SHAs.** Read back from the artifacts:
  `7e9564f9` (run 39532414479) = `33579/46942`; `44caccf7`
  (run 39710801966, attempt 2) = `33580/46942`. Both have 9830/14102
  branches and 71/429 zero-covered files. The earlier ledger row `C-BASE`
  bound 33580 to `7e9564f9`; that binding is wrong and is superseded by
  `C-BASE-7e9564f9` and `C-MAIN-44caccf7`.
- **Noise floor.** `7e9564f9..44caccf7` changes no `.py` file, yet
  `core/execution_backbone/backbone.py` covered lines moved 140 → 141. A
  whole-repo uplift smaller than 1 statement is not distinguishable from
  noise.
- **Each candidate is measured against its own synthetic-merge base.** The
  W88 checkout `ad912b0c` merges `76531e5a` into `44caccf7`, so W88 is
  `34408/46942` = **+828** against `C-MAIN-44caccf7`. The +829 figure is a
  cross-base comparison with `7e9564f9`. Keep both observations; credit
  neither as main. W75-A is based on `7e9564f9` (+233); W53-GG/ER/BD/RT and
  W77 are based on `44caccf7` (+337, +240, +203, +353, +708).
- W88 left zero-covered files at 71, unchanged from the baseline. This is
  a non-gain on that KPI.
- W76 scoped `233/233` statements and `50/50` branches is a separate,
  overlapping candidate cohort.
- Current ABACUS main broad/diff/zero-covered-file **coverage UNKNOWN**,
  not 0. Reproduce same-source and same-file-population native coverage
  before any uplift claim.
- Quality pilot #2359 totals 6173 → 231 omit Bandit, CodeQL, Semgrep and
  Trivy on the later run; scanner visibility changed. Do not infer debt
  closure.

## Dashboard link-health

[Issue #1885][i1885] original [run 38357570263][r-links]: 53 broken href
occurrences = 50 MYRRHA + 2 reports + 1 dynamic expression. Historical
source-tree snapshots showed 53 → 5 → 0 across *different* SHAs, and
dynamic JS was skipped in the final static scan. Six duplicate alert
tickets were closed as **HOUSEKEEPING_ONLY**, not six technical root
closures. Current deployed Pages SHA, dynamic link and HTTP/browser
coverage require new evidence; retain #1885 OPEN.

## Canonical owners and next execution order

1. **Owner/admin:** enforce named checks (at least canonical CI/security),
   review/waiver decision, last-push/stale/thread policy, restrict bypass;
   prove RED canary rejection.
2. **ABACUS source owners:** repair Pages package manager,
   pre-commit/TestPilot, EVERRED formatting via disjoint source paths.
   Preserve original failure logs.
3. **CODEX security owner:** remediate OSV `certifi` with
   lock/compatibility regression, independently verify full head.
4. **ABACUS #1929 root-census owner:** native, source-bound
   Bandit/Flake8/CI/LDAB join; distinguish occurrence, fingerprint, causal
   root, accepted closure, housekeeping. Unknown is not zero.
5. **ABACUS #1991 coverage owner:** run fixed-source statement, branch,
   changed-line and zero-covered-module census with current main+diff
   same-scope pairs.
6. **CODEX #977 executor owner:** decide independently authenticated
   ABACUS-local dispatcher, with exact SHA, principal, path leases,
   idempotency, replay guard and signed receipt; CODEX remains
   orchestration/read-only and `mutation_enabled=false`.
7. **Portal owner:** project validated JSON into existing CODEX
   W32/W36/MissionControl UI and Method Atlas; no duplicate source of
   truth. Recheck deployed Bytes/Pages, not merely static HTML.

## Temporal and scaling contract

Use N-1/N/N+1 waves with composite key `repo, source_sha, checkout_sha,
base_sha, merge_sha, workflow, run_id, attempt, job_id, artifact_id,
scan_config, source_blob_set`.

Track per lane: passed/eligible, skipped/cancelled/unknown, first-red
signature, root owner, statements/branches, zero-file count,
queue/idle/run/wall clocks, artifact bytes/digest, source-set
comparability, reviewer/required-check status.

These tests must fail red without claiming engineering root failures:
A→B→A, reversed DAG dependencies, out-of-order scheduler, stale JUnit,
missing scanner cohort, stale SHA, nested Windows-casefold path lease and
malformed ZIP.

PCA/gg_MATH scores are *diagnostic*; security and governance are
independent vetoes. Four distinct, terminal, comparable source transitions
are needed to demonstrate three stability transitions.

## Reuse instead of rebuild

- `tools/mip_ci_wave_telemetry.py`, `tools/mip_ci_temporal_rollup.py`,
  `tools/mip_testflight_plan.py`
- `scripts/bd_ldab_join_census.py`, `scripts/code_purple_mach_admission.py`
- `tools/w79_deterministic_work_pca.py`, `tools/triage/root_depth_census.py`
- `ci/verify_handover.py` (ledger integrity)
- `docs/ci/g3a-control/index.html`; CODEX `docs/index.html`,
  `docs/code_purple_convergence.html`, `docs/code-purple-dov.html`

## PR-first handover policy

Durable source, tests, sanitized evidence records, manifests and
human-readable navigation belong in narrow draft PRs, **not unversioned
chat ZIPs**. Never auto-merge this handover. Do not publish raw
private/local receipts or screenshots to public GitHub without explicit
review. A ZIP is produced only if the user explicitly requests one.

## Admission and notification

`MERGE_ADMISSION=HOLD`; `first_correctly_admitted_main_merge=NOT_VERIFIED`;
`authenticated_ABACUS_worker_launch=NOT_PROVEN`;
`current_main_coverage=UNKNOWN`; `root_accepted_closure_delta=0` in the
historical handover; the current joined open/closed total is UNKNOWN.

Notify only on governed merge, matched coverage gain, material TODO
completion or changed attributable first-red.

## Corrections log

Changes against the first cut `f7659f26`:

- Reflowed for markdownlint (MD013, MD022, MD032); the first-reds table
  became a list so each line fits.
- CODEX open PRs: 0 → 2 drafts (#1162, #1163) at the later readback.
- The MACH ladder link was labelled "CODEX"; it is the ABACUS ladder.
- "Frozen baseline: `33580/46942`" bound the number to the wrong SHA. It
  is now two observations (`7e9564f9` = 33579, `44caccf7` = 33580), and the
  ledger keeps the superseded row.
- Added the CODEX Metrics first-red, the transitive `certifi` note, the
  EVERRED event type, the `review_on_push` gap and the path-filter trap.

[ruleset]: https://github.com/GBOGEB/ABACUS/rules/24494381
[i1860]: https://github.com/GBOGEB/ABACUS/issues/1860
[i977]: https://github.com/GBOGEB/CODEX/issues/977
[i1885]: https://github.com/GBOGEB/ABACUS/issues/1885
[r-pages]: https://github.com/GBOGEB/ABACUS/actions/runs/40092398089
[r-dow]: https://github.com/GBOGEB/ABACUS/actions/runs/40092397997
[r-er]: https://github.com/GBOGEB/ABACUS/actions/runs/40094315794
[a-er]: https://github.com/GBOGEB/ABACUS/actions/runs/40094315794/artifacts/12559279700
[r-osv]: https://github.com/GBOGEB/CODEX/actions/runs/39983531098
[r-cxm]: https://github.com/GBOGEB/CODEX/actions/runs/39983531344
[r-main]: https://github.com/GBOGEB/ABACUS/actions/runs/40092398057
[r-cql]: https://github.com/GBOGEB/ABACUS/actions/runs/40092398054
[r-links]: https://github.com/GBOGEB/ABACUS/actions/runs/38357570263
