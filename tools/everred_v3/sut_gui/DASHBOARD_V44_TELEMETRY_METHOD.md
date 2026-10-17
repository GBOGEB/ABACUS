# CODE PURPLE Dashboard V4.4 — telemetry leaves and measurement DAG

**Status:** additive, source-bound user-facing measurement view. It does not grant
merge, security, review, Crew, REX, engineering or statistical acceptance.

## Purpose

V4.4 makes the existing telemetry hierarchy visible without flattening nested
execution evidence into a fake statistical sample size.

The dashboard now exposes three complementary views:

1. **Summary cards** — fast operational readback for execution hierarchy, test
   penetration, coverage measurement breadth and queue/runtime scaling.
2. **Measurement leaves** — CI reliability, tests, coverage, DAB/static
   clusters, PCA, 3P* capacity, burndown and M1–M3 maturity.
3. **Method DAG** — the governed data path from exact SHA to runs, jobs, steps,
   JUnit, test-to-source contexts and coverage, plus the separate root, scaling
   and PCA lanes.

## Canonical ownership

| View / measurement | Canonical producer or owner | Dashboard role |
| --- | --- | --- |
| Runs → jobs → steps, queue/runtime/concurrency | ABACUS PR #2033 | Structural consumer |
| Root IDs, fingerprints, wave transitions, matched coverage | ABACUS PR #1998 | Wave/burndown consumer |
| Comparable cycle-level M1/M2/M3 statistics | ABACUS PR #1989 | Maturity consumer |
| Capacity / evidence yield | W64 / 3P* | Experimental summary |
| Work-state diversity | W78 | Descriptive state geometry |
| PA95 PCA / loading structure | W79 | Diagnostic multivariate summary |

The dashboard is not a replacement SSOT for any producer.

## Reference data contract

`telemetry_reference_v5.json` is a controlled, labeled reference snapshot. It
is not live state. The file requires:

- `authority_transfer=false`
- `merge_authorized=false`
- `security_waiver=false`
- `independent_process_observations=null`

Current reference cohorts are deliberately source-bound:

- #1989 exact head `79672200a0fb37b7538b996b03a1e82dceb83a2f`
- #2033 prior B0 head `42447d279cda0cf1a667e529e9deaf35f214bb31`
- current structural producer schema `abacus.mip.ci-wave-telemetry.v2`

The current #2033 producer head is recorded only as a qualification pointer; it
does not retrospectively change the historical reference metrics.

## Interpretation rules

### Hierarchy is not independence

`31 workflows → 121 jobs → 1,065 steps` describes execution width and depth.
It is **not** `1,217` independent process observations.

Nested jobs, steps, test cases, deterministic replays and coverage contexts can
explain a cycle, localize a first-red and measure penetration. M2 stability and
M3 capability require separately sampled comparable cycles.

### Coverage has two different questions

1. **How much code is covered?**
2. **How much code is being measured at all?**

The prior #2033 exact head expanded statement denominator from 21,007 to
30,153 while measured ratio moved from 31.38% to 56.6013%. Because the
denominator changed, V4.4 labels this as **measurement penetration**, not a
matched +25.22 percentage-point coverage improvement.

Matched coverage improvement still requires the same scope, configuration and
eligible denominator across the before/after SHAs.

### DAB/static debt is clustered

The reference snapshot shows 3,719 measured findings across 34 families and
1,102 read-only proposals. The top five families account for 75.80%. V4.4
therefore shows concentration as well as count so large style families do not
hide smaller security or behavioral roots.

### PCA remains diagnostic

W79 retains one PA95 component on both semantic and all-work panels. The
dashboard exposes the descriptive variance structure and small-sample warning;
it does not convert PCA into causal, admission or autonomous allocation
authority. Bradley–Terry remains withheld without real pairwise outcome data.

### 3P* is an experimental capacity view

W64 R01 is a read-only sample. Evidence yield, AHT and worker counts are useful
baseline telemetry, but `stability_class=INSUFFICIENT_EVIDENCE` remains the
governing interpretation until repeatable compatible runs exist.

## Updating the dashboard

The V4.4 flow is:

1. Produce a new exact-SHA receipt in its canonical producer.
2. Preserve repository, source SHA, run ID, attempt and job IDs.
3. Update the controlled reference only when the cohort is explicitly chosen
   for historical comparison.
4. Load `abacus.mip.ci-wave-telemetry.v2` receipts through the existing evidence
   file control for structural live/near-live views.
5. Never overwrite a historical reference with an incomparable live cohort.
6. Re-run the CODE PURPLE dashboard contract workflow.

## Method DAG

Canonical Mermaid source:

`tools/everred_v3/sut_gui/TELEMETRY_MEASUREMENT_DAG_V5.mmd`

The HTML also contains the same user-facing forward method path and a copyable
Mermaid version. Root/burndown, scaling and PCA remain separate lanes before
fan-in at #1989.

## Admission boundary

The telemetry view remains read-only with:

- no inferred Crew dispatch;
- no inferred REX acceptance;
- no inferred formal root closure;
- no security waiver;
- no inferred review approval;
- no merge authorization.

`UNKNOWN` remains UNKNOWN and is never normalized to zero.
