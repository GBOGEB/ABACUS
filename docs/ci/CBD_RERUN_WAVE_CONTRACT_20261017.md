# CBD rerun sequencing and partial-census contract

This implementation is a read-only, source-bound planning stage; no auto-dispatch, merge, security waiver, acceptance or authenticated REX.

## SIPOC and DAG
Suppliers: GitHub exact-head PRs, workflow run/attempt/job evidence, ABACUS source owners, canonical BD/LDAB issue #1929.
Inputs: immutable base/head SHAs; native run and job IDs; verified first-red classifications; queued/in-progress counts; test/coverage numerators and denominators only when measured.
Process: read exact head -> ingest terminal attempt -> classify first-red -> deduplicate shared roots -> path-disjoint canary -> enforce capacity budget -> choose retry only if justified -> observe next attempt -> compare N/N+1 -> publish new immutable shard only on real change -> dependent recheck.
Outputs: deterministic input digest, candidate actions, immutable partial transition events, UNKNOWN for unverified BD closure, coverage, admission and REX.

## Retry policy
- Queued/in-progress/stale-head: WAIT; do not rerun.
- Deterministic, A10, security, governance: repair source, do not retry to hunt for green.
- Rate-limit: wait for verified capacity/API recovery.
- Transient runner: one failed-jobs retry on stable head when queue budget permits; preserve successful jobs.
- Isolated flaky job: retry that one native job once.
- Full rerun: owner-reviewed recertification, typically after real dependency/workflow changes or invalidated proof. Not performed by this planner or authorized by green checks alone.
- Retry count cap 2, candidate rerun budget 2; current provisional backpressure caps queued 40, in-progress 12. These are conservative scheduling policies, not experimentally optimized limits.

## Partial push contract
Census shards belong on a dedicated non-main evidence branch with expected-head CAS. Emit a new shard only on NEW_OBSERVATION, TERMINAL_TRANSITION, NEW_ATTEMPT or FIRST_RED_UPDATED; identical status/input shall not create a commit. A partial shard can trigger RECHECK_ONLY of a dependent root, never an automatic runner, merge or cross-repo authority transfer. Full census/BD reconciliation remains separately authoritative (#1929, #1860, #1991; CODEX #977 for authenticated dispatch).
Freeze N+1 receipts with run/attempt/job IDs and test denominators. Compare main and PR coverage on matched scopes; UNKNOWN is not zero.

Queue snapshot recorded 323 queued and 7 in-progress: no new reruns are currently admitted by this planner. Avoid opening a new PR while capacity is saturated; review source on this evidence branch and gate PR launch separately.
