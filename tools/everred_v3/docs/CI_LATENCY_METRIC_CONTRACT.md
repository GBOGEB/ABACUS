# CI latency and statistical telemetry — MIP execution contract

This producer is additive to the canonical EVERRED native-ingest and the
pending coverage/LDAB spine. It does not alter admission or canonical
BD/LDAB root disposition.

## Timing identities

Use GitHub Actions **native** run, job, step timestamps on an exact source SHA.
Do not infer runner queue solely from workflow total minus job runtime.

- Workflow wall: `run.updated_at - run.created_at`. The end timestamp is
  a GitHub metadata observation, not an independent billing receipt.
- Job queue: `job.started_at - job.created_at`, per native job, when both exist.
- Runner runtime: `job.completed_at - job.started_at`.
- Pre-first-job delay: first job start minus workflow creation.
- Post-last-job tail: workflow metadata update minus last timed job completion.
- Aggregate runner-seconds: **sum** across jobs; measures occupied runner time.
- Active union: **union of job intervals**; concurrency prevents double counting.
- Stage attribution: timestamped job steps, not an additive substitute for wall.
- Cache and wheel reuse: UNKNOWN unless separate cache-action/log evidence exists.

Native example: Bandit run 38539036478 => 503s workflow wall; its one
job was created one second later, queued 460s and ran for 42s.
MIP Wave run 38698921915 => 14s wall, 3s queue and 11s job time.

These are different workflows and source SHAs; **never pool their quantiles**
as one statistical population.

## Statistics and gg_MATH

Per population use the exact tuple (repository, source SHA, workflow, event)
and native run/attempt observations. Report n, median, p5, p95 and p99 via
Type-7 linear sample interpolation. Outputs are descriptive.

- p95 tail qualification requires at least 20 sample observations.
- p99 tail qualification requires at least 100 sample observations.
- PCA is not executed by this producer. At 30+ comparable observations,
  submit a separately verified contract to gg_MATH; verify independence,
  feature scaling, variance, missingness and effective sample rank.

No median, tail metric, PCA loading or speedup is a merge admission signal.

## Metric tree / future priority

- Source: active heads, denominator/source evolution, reproducible receipts
- Coverage: covered/eligible statements/branches, old-debt closure (separate)
- CI: per-job queue/run, workflow wall, stage costs, runner union, P5/P95/P99
- Cache: wheel provenance and warm/cold experiment (future native evidence)
- Test: JUnit native count, stress/negative controls and mutation detection
- Security/BD: fingerprint lineage, root closure, recurrence, disjoint ownership
- Runtime/LDAB: source discoveries distinct from authenticated debug sessions
- Federation: gg_MATH → KEB → DOW → QPS source/native/owner distinctions

## BD / DoV

P1 latency distribution: collect >=20 same-workflow comparable independent
observations with all job timestamps; until then quantiles are descriptive.
P1 cache: conduct cold/warm paired job setup experiments on unchanged exact
source and configuration; record cache receipt rather than claim speedup.
P1 PCA: implement through authoritative gg_MATH four-hop evidence, not local
unvalidated approximation.

Negative controls include duplicate jobs, cross-head/run/attempt bindings,
missing timestamps, negative intervals, mixed populations, nonterminal
runs and malformed sample values. UNKNOWN is never zero.
