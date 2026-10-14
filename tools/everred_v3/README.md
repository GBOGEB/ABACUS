# ABACUS EVERRED V3

Governed causal recovery, typed telemetry, disjoint work and fail-closed
admission. This is an engineering prototype, not an approved release.

## Start locally

```bash
cd tools/everred_v3
python3 -m unittest discover -s tests -q
python3 src/everred.py verify
python3 src/everred.py snapshot
python3 src/control.py
python3 scripts/build_joined_census.py
python3 scripts/build_dashboard.py
```

Open `dashboard/index.html` to explore the self-contained dashboard.
Its data are a historical ledger snapshot, not a live GitHub poll.
Manual browser imports are always classified as untrusted.

## New native evidence collectors

`src/native_ingest.py` binds GitHub runs and jobs to their exact source
SHA. It supports scanner and runtime artifacts only where the bytes,
manifest and SHA-256 identity match. GitHub metadata and provenance
are distinct from security acceptance and causal confirmation.

Supply `GITHUB_TOKEN` with read-only Actions permission and run:

```bash
python3 scripts/collect_native.py \
  --repo GBOGEB/ABACUS \
  --sha "$PR_HEAD_SHA" \
  --run-id "$NATIVE_RUN_ID" \
  --output native-event-batch.json
```

The default is read-only collection to a separate JSON file. The
`--apply-ledger` flag appends events locally. An explicit JSON artifact
plan is required for Bandit, Cobertura, JUnit and runtime artifacts.
Unsafe ZIP paths, source mismatches, invalid denominators, absent scan
configuration digests, and unknown storage redirect hosts fail closed.

The native collector does not scan GitHub without a named source run.
It does not silently infer an uploader job from artifact metadata.

## Historical BD/LDAB adapter

The existing ABACUS producer has schema `bd.ldab.joined.census.v1`.
It remains canonical. EVERRED consumes its output without assigning
confirmed root causes to scanner-fingerprint groups:

```bash
python3 scripts/ingest_bd_ldab_join.py --input join-output.json
```

Native events are reconciled by `src/joined_census.py`, using the tuple
(repository, exact SHA, run ID, job ID). Cross-run and cross-repository
associations require separate accepted evidence.

## Atomic worker coordination

`src/coordination.py` uses an isolated lease-registry Git ref and
`git push --force-with-lease` as the remote compare-and-swap primitive.
A stale expected ref cannot overwrite a competing claim. This does
not authorize a worker to change source or override repository policy.
The dedicated ref must have explicit repository-level access controls.

Claims require root identity, expected source SHA, permitted file paths,
principal, idempotency key and an auditable authority reference. The
reference is **not** independently authenticated by this module.
Expiry does not silently transfer file ownership.

## Immutable replay

`src/replay.py` builds a source-bound integration tree using Git
`merge-tree`. It can run a constrained test profile in an isolated
worktree on an explicitly authorized, trusted runner.

Results are always **integration previews**, not native PASS results
on the consumer's unchanged PR SHA. Conflicts fail closed.

## KPI history and recurrence

`src/control.py` appends hash-chained KPI pulses with precise scope and
numerators/denominators. Source gaps remain `null` or `UNKNOWN`.
Recurrence sentinels emit local review-required alert artifacts; no
external notification delivery is claimed without an actual receipt.

## Independent admission evaluation

`src/admission.py` evaluates native exact-head checks, coverage, security,
workflow policy, effective main-branch rules and independent reviews.
Untrusted input can never become an authenticated admission receipt.
Even a passing authenticated evaluation yields *eligible for an
independently authorized merge*, never an automated `ADMIT` or merge.

## Layout

- `src/`: ledger, native ingest, join, coordination, replay and control.
- `scripts/`: read-only collection, BD/LDAB bridge and build tools.
- `tests/`: negative, unit and temporary-Git integration tests.
- `data/`: historical ledger, snapshots, KPI pulses and alert exports.
- `dashboard/`: editable HTML source and standalone generated HTML.
- `diagrams/`: Mermaid, DOT and publication SVG architecture exports.
- `docs/`: implementation register and native evidence contract.

## Current evidence boundary

The initial dashboard refers to PR #1914 at exact head
`e9f34b22967064c779891a4d2ac40541f370e812`. Its broad coverage,
focused coverage and raw Bandit observations have different scopes.
They are not current-main or matched security-burndown evidence.

The existing producer evidence, root ledger and lease coordinator
cannot restore branch protection or supply independent code reviews.
P0 governance and native exact-head verification remain mandatory.

See the governed recovery register at ABACUS issue #1860 and the
BD/LDAB join register at issue #1929.
