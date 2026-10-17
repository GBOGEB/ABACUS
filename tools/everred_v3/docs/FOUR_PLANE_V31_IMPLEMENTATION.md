# EVERRED V3.1 — Four-plane controlled execution

Implementation: additive stacked work package for ABACUS PR #1933.
The source-control baseline shall be pinned when the stacked PR is created.

## Four cooperating planes

| Plane | Producer | Governed outcome |
| --- | --- | --- |
| Diagnostic | LLDB, LLDB-DAP and canonical LDAB | Session and candidate link |
| Runtime | Host OS, RHEL/UBI and Docker | Observed runtime identity |
| Orchestration | Strict YAML plans and Git leases | Bounded ready/HOLD plan |
| Evidence/admission | Exact-source join and review | Census and HOLD |

The new implementation **does not replace** `native_ingest.py`,
`ci/governance/workflow_policy.json`, the canonical BD/LDAB joiner,
or `.mesh/MESH_DOCK.yaml`.

## Typed separation

- Debugger: tool, session, build ID, steps, frames and optional container.
- LDAB: stable root/fingerprint hypothesis with unconfirmed causality.
- Runtime: OS, kernel, architecture, container, ports, log receipt.
- Federation: producer/consumer identity with independent disposition.
- Orchestration: DAG, paths, tasks, owner and bounded mode.

`Source` carries repository, source SHA, run, job and executed SHA.
A self-described SHA or artifact hash is not native authentication.
Native job/artifact reconciliation is still required.

## Local and native execution

Run from `tools/everred_v3`:

```bash
python -m pip install PyYAML jsonschema defusedxml
python -m unittest discover -s tests -q
python scripts/four_plane_preflight.py \
  --repo GBOGEB/ABACUS \
  --sha YOUR_REAL_SOURCE_SHA \
  --run-id YOUR_REAL_RUN_ID \
  --output data/four_plane_preflight.json
python scripts/build_four_plane_dashboard.py
```

`--probe-lldb` asks for an optional disposable C-debugger proof.
No production process is attached and no arbitrary user command is run.
If debugging fails, the receipt is unsuccessful and stays diagnostic.

The native V3 workflow runs the negative suite, validates the
canonical BD/LDAB adapter, checks source checkout identity,
executes the host/optional LLDB probe and uploads a read-only
JSON artifact. It never pushes back to the source branch.

## Validation and threat model

- YAML: duplicate keys, aliases/merges, unsafe paths and cycles rejected.
- Worker plans: overlapping write paths and mutation without review denied.
- Debugging: session requires build ID; steps are not remote proof by name.
- Containers: image digest and container ID must match as a pair.
- Ports: a temporary loopback probe is recorded **closed**.
- Logs: bounded redaction, raw digest and no continuous-listener claim.
- Federation: exact producer/executed SHA and digest; no self-ACCEPT.
- LDAB: source-bound canonical receipt; root labels remain hypotheses.
- Admission: all imported, local and replay evidence remains **HOLD**.

## Implementation limits / follow-on gates

1. Native job-ID and artifact-upload step corroboration still required.
2. Live RHEL8/9 and UBI tests require eligible registered runners.
3. Docker-daemon/session logs require scoped read-only runtime access.
4. LLDB-DAP native debug proof depends on installed debugger/symbols.
5. Cross-repo CODEX/ABACUS receipt acceptance needs independent review.
6. A10, Safety, branch rules, changed-line coverage and broad CI remain
   independently blocking if native checks do not clear them.

No team is credited for a registration without an authenticated
session receipt. No successful preflight authorizes a merge.

## CODE PURPLE / EVERRED CENSUS scaling contract

The existing four-plane plan is the Mission Control-compatible control surface.
It now separates one central joined CENSUS from three read-only disjoint CENSUS
lanes: CI, governance and security. Their outputs converge only through
RECENSUS, then KPI_PULSE. This is an adaptation of the existing EVERRED
single-root-owner/disjoint-path method, not a second orchestration system.

The sequence is:

1. GITHUB_RECEIPT, LDAB_CORRELATION and RUNTIME_HOST feed JOINED_CENSUS.
2. DISJOINT_CENSUS_CI, DISJOINT_CENSUS_GOVERNANCE and
   DISJOINT_CENSUS_SECURITY inspect independent evidence families without
   source mutation.
3. RECENSUS reconciles their exact-head observations. Missing evidence remains
   UNKNOWN; duplicated manifestations do not become new roots.
4. KPI_PULSE reports source-bound deltas and queue health.
5. CONTROLLED_MUTATION remains REVIEW_REQUIRED and cannot be dispatched by this
   plan. A worker identity, launch ID or REX return is credited only from an
   authenticated external receipt.

Mission Control assets remain the existing ABACUS #1860 / CODEX #977 and #975
authority references, EVERRED four-plane receipts, canonical BD/LDAB joins,
Git leases, and REX return contracts. The plan never converts a GitHub Actions
job into a Crew launch, never transfers authority, and never waives A10,
Safety/Bandit, governance, required checks or independent approval.
