# Coverage obligations: source identity and genuine old-debt reduction

This additive producer is **not** another coverage percentage scoreboard.
It can consume two Coverage.py JSON outputs, each accompanied by a
source identity manifest with exact Git blobs for every file.

## Population contract

One observation has repository, exact SHA, run, job, coverage JSON SHA-256,
instrumentor version, configuration digest, test selection, exclusions,
branch instrumentation and file-to-Git-blob IDs.

The runner/consumer shall independently corroborate source blob IDs,
run/job and artifact origin before promoting provenance beyond
`SELF_DECLARED_UNVERIFIED`. A matching SHA-256 of supplied local bytes
proves byte integrity **only**, not GitHub or test-run origin.

Statements are source line IDs; branches are Coverage.py directed arcs
`[from_line, to_line]`, including exit arcs with negative endpoints.
Every line and arc must be in exactly one covered/uncovered set.
Counters are checked against native per-file summary denominators.

## Two different truth levels

- *Descriptive source evolution:* eligible counts, covered counts, net
  denominators, changed/added/retired blobs and coverage rates.
- *Verified stable-blob transition:* formerly uncovered branch/statement
  now covered (or formerly covered now missing) on exactly unchanged file
  Git blob, the same instrumentor/config/selection and exact arc/line ID.

No old-debt credit is assigned for a changed file blob without a separately
audited source-obligation semantic mapping. Added fully covered files may
raise the percentage while old-debt gain remains zero. The strict
regression counter remains visible despite overall coverage improvement.

## Negative controls and federation

- Fake denominators, duplicate arcs, overlapping executed/missing arcs
- Forged/wrong Git file blobs, source scopes and cross-repository identity
- Test profile drift, Windows/absolute/traversal paths, stale local artifacts
- Structural source modifications without an accepted semantic correspondence
- Bounded deterministic 600-module/1200-branch stress test

Future integration shall join this producer into #1994's exact-head
spine, preserving its LDAB census and receipt evidence levels.
The four-hop gg_MATH → CODEX/KEB → ABACUS/DOW → QPS acceptance chain
remains independent: **coverage gain is not an owner disposition**.

## BD / Done when verified

B1: authenticate raw artifact ZIP digest, internal coverage.json bytes and
Git file-blob identity from native GitHub API before claiming native
old-debt closure. B2: add source-safe semantic mapping for modified code
when a validated mapping protocol exists. B3: measure branch-census
penetration and negative-control failure-mode inventory across federation.
No exemptions, merge decision or QPS authority transfer.
