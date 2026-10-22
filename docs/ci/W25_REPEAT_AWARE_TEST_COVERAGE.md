# CODE PURPLE W25 — repeat-aware N+i and scoped test coverage

**Status: isolated read-only source change; MERGE_ADMISSION=HOLD.**

## Why N23 appeared to have more tests

The N+i chart counted GitHub Actions **workflow runs**, not pytest test cases.
Exact-SHA push-run readback separates repetitions from distinct workflow IDs:

| Cohort | Runs | Distinct workflows | qps-canonicalization runs | Success/all |
| --- | ---: | ---: | ---: | ---: |
| N23 `e08c51232edb...` | 37 | 26 | 12 | 31/37 |
| N27 `01ea2e481346...` | 28 | 28 | 1 | 14/28 at frozen poll |

Twelve successful N23 runs were the same qps-canonicalization workflow ID
`350890474`: eleven extra green executions beyond one per family. Thus
cap-to-one-success-per-family gives **20/26**; excluding QPS entirely
gives **19/25**. These are separate diagnostic ratios, neither test coverage
nor proof of worker launches, repaired roots or superior code quality.

Actual broad pytest results changed from 4,163 pass / 1 fail / 2 skip
at N27 (run 39140449306, job 117713709333) to 4,168 pass / 0 fail / 2 skip
at main SHA `97a8b13faff577272a90edaf0dd4593035e10605`
(run 39142444027, job 117719440816). This provides no evidence for
a broad test-culling claim, but different source heads require separate
root and coverage qualification.

## Source-owned implementation

- `tools/mip2/workflow_family_metrics.py`: validated run-family cohort lens
- `tools/mip2/mip_nplus_observatory.py`: integrated family and repeat accounting
- `tests/test_workflow_family_metrics.py`: 23 adversarial unit test methods
- `tests/test_mip_nplus_observatory.py`: 5 additional integration methods
- `triage/rex/NPLUS_W25_N23_N27_RUN_FAMILY_CENSUS.json`: frozen native API
  run identity, workflow ID, attempt, exact SHA, event, state, conclusion and URL

Three noninterchangeable populations must be shown: (1) run conclusions
including nonterminal censoring, (2) workflow-family outcomes including
repeat amplification, and (3) native JUnit test-case outcomes. The last
remains UNKNOWN unless native receipts supply the exact cases and configuration.
Never treat cancelled, skipped or nonterminal as an engineering-root repair.

## Validation boundary

Local non-native execution: **23/23 PASS**, new helper **59/59 statements**
and **28/28 branches** covered (100%). The locally tested helper and
committed GitHub helper were verified byte-length/FNV32 identical.
The 5 integration methods are authored but their exact-head native CI is
not yet qualified. No broad-main or changed-line uplift is claimed.

Report-only active-source coverage previously stayed at 7,706/21,170
while the unrelated canonical admission population was 25,814/38,059.
Those denominators must never be combined or treated as matched improvements.

## Admission and next N+i sequence

Qualify exact-head native tests and source coverage, then B0 and Windows
with run/job/attempt/JUnit and immutable artifact receipts. Maintain source
owners for governance, dashboard 53-href recensus and canonical #1929 roots.
Effective ruleset 24494381 last required 0 approving reviews and no required
status-check rule; six bypass actors were configured. An authorized admin
must enforce independent approval and prove rejection of a RED canary.
No automatic mutation workers, merges, waivers or CODEX dispatch.

`MERGE_ADMISSION=HOLD`; `ROOT_OPEN/CLOSED=UNKNOWN/UNKNOWN`;
`MATCHED_MAIN/DIFF_UPLIFT=UNKNOWN`; `AUTHORITY_TRANSFER=false`.
