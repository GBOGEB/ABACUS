# CODE PURPLE — 24 October 2026 repo-first handover

**Status:** READ-ONLY OBSERVATION / MERGE_ADMISSION=HOLD / no engineering-root closure credit / no inferred launch, approval or waiver.

This is the durable, reviewable entrypoint for the 24 October readback. It supplements, rather than replaces, the canonical historical ledgers under `telemetry/` and the existing [22 October retirement handover](../../docs/handovers/ABACUS_20261022_RETIREMENT.md). No ZIP is a release dependency. Create ZIP archives **only on explicit owner request**.

## Exact identities (24 October readback)
- ABACUS main: `25940371d4750afa00be15f48c6b53963c9b534e`.
- CODEX main: `58ee1520b0ed90265e4134be82f5580d60a30139`.
- gg_MATH main observed: `952d62ea1f98099fc7bc514340d3304e9dd165d1`.
- ABACUS #1860 checkbox state: 1/12; CODEX #977: 0/7.
- GitHub repository-count snapshot: ABACUS 41 open issues / 3 open PR; CODEX 11 open issues / 0 open PR. **These are not engineering-root counts.**
- CODEX PR #975 was merged historically, merge SHA `c51b3debd784558c6ccb9b85d091eb1decb38605`. It is not an authenticated ABACUS worker dispatch.

## P0 admission
[ABACUS ruleset 24494381](https://github.com/GBOGEB/ABACUS/rules/24494381) active but has **no required_status_checks rule**, 0 required approving reviews under the documented solo-owner policy, last-push approval false, thread-resolution false, and six always-bypass integrations. A correctly governed first-main merge under the evidence-gated policy is **not verified**. Owner decision plus effective platform status checks and server-rejected RED canary are required. Keep independently required security evidence noncompensating. No backdated admission for the October 23 merge burst.

[ABACUS #1860](https://github.com/GBOGEB/ABACUS/issues/1860) | [CODEX #977](https://github.com/GBOGEB/CODEX/issues/977) | [CODEX MACH-II–IV candidate policy](../../docs/governance/CODE_PURPLE_MACH_LADDER.md)

## Exact-main first-reds
| Source | Run / job | Evidence |
| --- | --- | --- |
| ABACUS Pages | [40092398089](https://github.com/GBOGEB/ABACUS/actions/runs/40092398089), job 120867593397 | Detect package manager fails: `Unable to determine package manager`; deploy skipped |
| ABACUS DOW/CD | [40092397997](https://github.com/GBOGEB/ABACUS/actions/runs/40092397997), job 120867592752 | Pre-commit modifies files and TestPilot preflight fails, downstream skipped |
| ABACUS EVERRED | [40094315794](https://github.com/GBOGEB/ABACUS/actions/runs/40094315794), job 120873270178 | Black/isort gate; no-push patch proposal [artifact 12559279700](https://github.com/GBOGEB/ABACUS/actions/runs/40094315794/artifacts/12559279700) with eight paths |
| CODEX OSV | [39983531098](https://github.com/GBOGEB/CODEX/actions/runs/39983531098), job 120516695586 | `certifi` 2026.7.22 critical PYSEC-2026-4320, fixed version reported 2026.10.19 |
| ABACUS main CI | [40092398057](https://github.com/GBOGEB/ABACUS/actions/runs/40092398057) | SUCCESS, not a replacement for missing mandatory/enforced lanes |
| ABACUS CodeQL | [40092398054](https://github.com/GBOGEB/ABACUS/actions/runs/40092398054) | SUCCESS, not a waiver |

## Coverage: immutable and non-additive
- Committed historical records: `telemetry/causal_roots.jsonl` (14 records), `telemetry/evidence_ledger.jsonl` (27 records), `telemetry/coverage_cohorts.jsonl` (six cohorts plus one non-accumulation rule).
- Frozen baseline: `33580/46942` covered statements; W88 candidate `34408/46942` (+828), checkout was synthetic merge and not present-main qualification.
- Another historical baseline used `33579/46942` (+829): **do not collapse the different baseline observations**.
- W76 scoped `233/233` statements and `50/50` branches is a separate, overlapping candidate cohort.
- Current ABACUS main broad/diff/zero-covered-file **coverage UNKNOWN**, not 0. Reproduce same-source and same-file-population native coverage before any uplift claim.
- Quality pilot #2359 totals 6173 -> 231 omit Bandit, CodeQL, Semgrep and Trivy on the later run; scanner visibility changed. Do not infer debt closure.

## Dashboard link-health
[Issue #1885](https://github.com/GBOGEB/ABACUS/issues/1885) original [38357570263](https://github.com/GBOGEB/ABACUS/actions/runs/38357570263): 53 broken href occurrences = 50 MYRRHA + 2 reports + 1 dynamic expression. Historical source-tree snapshots showed 53 -> 5 -> 0 across *different* SHAs, and dynamic JS was skipped in the final static scan. Six duplicate alert tickets were closed as **HOUSEKEEPING_ONLY**, not six technical root closures. Current deployed Pages SHA, dynamic link and HTTP/browser coverage require new evidence; retain #1885 OPEN.

## Canonical owners and next execution order
1. **Owner/admin:** enforce named checks (at least canonical CI/security), review/waiver decision, last-push/stale/thread policy, restrict bypass; prove RED canary rejection.
2. **ABACUS source owners:** repair Pages package manager, pre-commit/TestPilot, EVERRED formatting via disjoint source paths. Preserve original failure logs.
3. **CODEX security owner:** remediate OSV `certifi` with lock/compatibility regression, independently verify full head.
4. **ABACUS #1929 root-census owner:** native, source-bound Bandit/Flake8/CI/LDAB join; distinguish occurrence, fingerprint, causal root, accepted closure, housekeeping. Unknown is not zero.
5. **ABACUS #1991 coverage owner:** run fixed-source statement, branch, changed-line and zero-covered-module census with current main+diff same-scope pairs.
6. **CODEX #977 executor owner:** decide independently authenticated ABACUS-local dispatcher, with exact SHA, principal, path leases, idempotency, replay guard and signed receipt; CODEX remains orchestration/read-only and `mutation_enabled=false`.
7. **Portal owner:** project validated JSON into existing CODEX W32/W36/MissionControl UI and Method Atlas; no duplicate source of truth. Recheck deployed Bytes/Pages, not merely static HTML.

## Temporal and scaling contract
Use N-1/N/N+1 waves with composite key `repo, source_sha, checkout_sha, base_sha, merge_sha, workflow, run_id, attempt, job_id, artifact_id, scan_config, source_blob_set`.
Track per lane: passed/eligible, skipped/cancelled/unknown, first-red signature, root owner, statements/branches, zero-file count, queue/idle/run/wall clocks, artifact bytes/digest, source-set comparability, reviewer/required-check status. A->B->A, reversed DAG dependencies, out-of-order scheduler, stale JUnit, missing scanner cohort, stale SHA, nested Windows-casefold path lease and malformed ZIP tests must fail red without claiming engineering root failures.
PCA/gg_MATH scores are *diagnostic*; security and governance are independent vetoes. Four distinct, terminal, comparable source transitions are needed to demonstrate three stability transitions.

## Reuse instead of rebuild
- `tools/mip_ci_wave_telemetry.py`, `tools/mip_ci_temporal_rollup.py`, `tools/mip_testflight_plan.py`
- `scripts/bd_ldab_join_census.py`, `scripts/code_purple_mach_admission.py`
- `tools/w79_deterministic_work_pca.py`, `tools/triage/root_depth_census.py`
- `docs/ci/g3a-control/index.html`; CODEX `docs/index.html`, `docs/code_purple_convergence.html`, `docs/code-purple-dov.html`

## PR-first handover policy
Durable source, tests, sanitized evidence records, manifests and human-readable navigation belong in narrow draft PRs, **not unversioned chat ZIPs**. Never auto-merge this handover; do not publish raw private/local receipts or screenshots to public GitHub without explicit review. A ZIP is produced only if the user explicitly requests one.

## Admission and notification
`MERGE_ADMISSION=HOLD`; `first_correctly_admitted_main_merge=NOT_VERIFIED`; `authenticated_ABACUS_worker_launch=NOT_PROVEN`; `current_main_coverage=UNKNOWN`; `root_accepted_closure_delta=0` in historical handover, current joined open/closed total UNKNOWN. Notify only on governed merge, matched coverage gain, material TODO completion or changed attributable first-red.
