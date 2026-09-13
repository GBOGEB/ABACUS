# W76 — intrinsic/source-sensitive runtime redesign

W76 follows W75's finding that the frozen runtime PC1 is not repeatable enough
for allocation. It asks a narrower question: can intrinsic probe cost, normalized
by deterministic source work, produce a stable runtime-sensitive feature set?

## Evidence

The panel contains 15 real runner-backed W74/W75 probe observations:

- five exact historical ABACUS source SHAs;
- three independent workflow runs per SHA;
- exact `FEATURE_ROW` hashes;
- exact probe artifact IDs and digests;
- deterministic W73 topology work counters.

The panel is bound by SHA-256
`4947fc598744fc114335437d0719f3188f77555c168f0ff4e8f166fcb8a8ee0f`.

## Gate

A runtime-sensitive candidate must satisfy both:

- one-way single-measure ICC >= 0.75;
- median pairwise repeat Spearman rho >= 0.80.

Static source counters cannot pass the runtime gate by themselves. A PCA fit is
permitted only after at least two runtime-sensitive candidates pass this gate.

## Result

No candidate passes. The strongest candidate is
`log_seconds_per_consumer_edge`:

- ICC: 0.500378;
- median repeat Spearman rho: 0.60.

Therefore W76 does not fit or retain a new PCA axis. The disposition is
`INTRINSIC_RUNTIME_AXIS_WITHHELD` and global allocation authority remains false.

## Next instrumentation contract

The next bounded step is phase-level instrumentation of
`w72_semantic_census_exact_source_state` with deterministic work counters.
Required timers include manifest/index/gap/reference parsing, consumer scanning,
graph construction, and receipt emission. Required counters include scanned text
files and bytes, entity count, candidate checks, consumer hits, and graph nodes
and edges.

Candidate W77 features should be source-work-normalized timings such as consumer
scan seconds per text MiB or per candidate check, and graph-build seconds per
edge. They must repeat on real runner-backed executions before any PCA/PA95 step.

BT, child engineering promotion, compliance/release credit, and global resource
allocation remain withheld. W76 cannot compensate MC-1 #923, G6 release
identity, or source/PED/cost gates.
