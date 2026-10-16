# MIP CI Temporal Pulse: N, N+1 and N+2

This is a **read-only companion** to ABACUS #2033 `mip_ci_wave_telemetry.v2`
and its native-source collector. No separate authority or CI workflow is
created. The source observations shall be acquired as complete,
exact-run/attempt native GitHub responses and verified externally before
statistical credit. The comparator itself does not acquire or authenticate
GitHub data.

Run:

```bash
python -m unittest -v tests.test_mip_ci_temporal_rollup
python -m tools.mip_ci_temporal_rollup --input ci_temporal_input.json --out ci_temporal_rollup.json
```

Input schema: `abacus.mip.ci-temporal-input.v1`. Required
`repository=GBOGEB/ABACUS`; `cohort` hashes of the declared workflow selection,
test selection and runner matrix; one or more ordered `observations` with
consecutive wave IDs, monotone UTC observed-at, exact source SHA, explicit
distinct `[run_id,attempt]` identities, a full source-bound #2033 v2 telemetry
projection, and optional coverage measurement from the same source SHA.
Coverage evidence includes exact eligible/covered line and branch counts,
Coverage.py version, configuration digest, instrumented scope digest and source
artifact SHA-256. A digest field on input is **not proof of its byte
authentication**.

## DMAIC and temporal qualification

- **Define**: workflow-run manifestations are not causal engineering roots;
  different PRs are different cohorts until scope matched.
- **Measure**: terminal-vs-queued workflow outcomes and job queue p95 remain
  separate; absent samples are null, never zero. Exact `run_id:attempt`
  identities are required.
- **Analyze**: success-rate comparison requires both terminal cohorts with
  equal workflow-run count; queue p95 comparison also requires at least 20
  measured jobs in each cohort, the same declared timing definition, and a
  reconciled `queue_source_counts` for each observation. The fallback clock
  (`workflow_run.created_at -> job.started_at`) is longer than the native
  job-queue clock and changes the quantity measured. A mixed/fallback timing
  population therefore **cannot earn a cross-wave p95 delta**, even when its
  aggregate `queue_basis` label and nominal sample size match. The original
  p95 remains visible, with the native/fallback numerator and denominator.
  Even fully native job samples are correlated, and their delta is
  **descriptive, not inferential**.
- **Improve**: line/branch gains are computed only for equal coverage file-set
  digest, configuration, tool version and denominators; resulting numbers are
  candidate source-reported, not accepted main coverage improvement.
- **Control**: negative tests cover identity duplication, stale SHA, mixed
  cohorts, reclassified pending jobs, invalid coverage, backdated forecasts and
  fake admission. A10, Safety, Bandit, reviewer eligibility and all required
  checks remain independent HOLD gates.

A forecast is never invented retrospectively: the program proposes a
persistence-only estimate for N+1/N+2 after N is observed, **unissued** until
the caller durably stores a timestamped forecast before the target observation.
Later observations score its absolute prediction error, without altering the
earlier forecast. Prediction histories need external immutability and trusted
timestamping before any audit credit.

## First-red step recurrence is not causal root closure

The canonical `mip_ci_wave_telemetry.v2` producer now exposes
`first_red_manifestations` and `first_red_signatures` per exact source SHA.
A signature is SHA-256 over native workflow path, job name, failing step name,
and numeric step ordinal. Each occurrence retains run ID, attempt and job ID.
Only terminal red jobs with complete native step numbers and workflow/job
identities are attributable; missing or ambiguous step detail increases
`red_jobs_without_attributed_first_step` instead of implying a clean run.

Counts of repeated signatures are **correlated job manifestations**, not
independent trials and not causal BD/LDAB roots. The projection retains
`first_red_causal_roots_verified=null`; a canonical root owner must independently
inspect source, runner log, configuration, recurrence and repaired-head proof.
No scanner finding, first-red signature or synthetic replay grants A10, Safety,
review, QPS acceptance or release authority.

## Statistical provider and immutable inputs

The canonical mathematical reference implementation resides in
`GBOGEB/gg_MATH` (PCA, PCA alignment, Bradley-Terry and uncertainty kernels).
Before PCA or temporal model admission, the consumer shall bind a matched
workflow set, test selection, runner matrix, source/config digests, independently
sampled waves and the provider's exact source SHA. Native artifact bytes and
library/runtime binary identities remain separate evidence fields; absent
identity or sample independence remains UNKNOWN, not zero or a fitted PC1.

PCA requires independent, comparable, sufficiently populated observations
across distinct metric families. Runs/jobs/steps and a few consecutive waves do
not prove independence or process stability. M2/M3 process/PCA maturity remains
HOLD here; canonical statistical ownership is ABACUS #1989 and gg_MATH.
`authority_transfer=false`, `merge_authorized=false`,
`accepted_bd_root_closures=null`, `native_artifact_bytes_authenticated=null`.

Canonical sources and authorities:

- [ABACUS #2033](https://github.com/GBOGEB/ABACUS/pull/2033): CI telemetry.
- [ABACUS #1998](https://github.com/GBOGEB/ABACUS/pull/1998): wave series.
- [ABACUS #1989](https://github.com/GBOGEB/ABACUS/pull/1989): statistics.
- [BD-LDAB #1929](https://github.com/GBOGEB/ABACUS/issues/1929): roots.
- [CODEX #977](https://github.com/GBOGEB/CODEX/issues/977): Crew authority.
