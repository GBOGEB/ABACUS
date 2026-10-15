# Mission Control measured waves: telemetry, roll-up and federation

Status: **candidate implementation on PR #1999**. Native exact-head tests,
workflow execution, artifact authenticity and merge admission are separate
decisions. Do not assert coverage, root closure, independent review or CI
acceleration from a synthetic test fixture.

## Reuse instead of reinvention

| Source | Observation |
| --- | --- |
| PR #1990 wave pulse | MIP roots and cohort-matched coverage |
| PR #1990 backlog delta | Repeated failure fingerprints |
| Main BD/LDAB join | Read-only Bandit/LLDB joins |
| Main CI gate roll-up | Dashboard-only CI states |
| MIP B0 | Native JUnit and coverage receipts |
| CODEX REX | Accepted, signed returns only |
| 3P* SIPOC-DAG | 3PR/3PC qualification stages |
| Solo AMBER | Per-check carryover requests, not bypasses |

The current telemetry producer provides **GitHub API read-only run and job
timestamps**, categorized by *workflow name hint*. Workflow names cannot
prove actual MIP, DMAIC, PCA/BT, 3P, LDAB, LLDB or REX completion.

## Native read-only telemetry

```bash
export GITHUB_TOKEN="$(gh auth token)"
python ci/governance/mission_ci_telemetry.py \
  --target "GBOGEB/ABACUS@$(git rev-parse HEAD)" \
  --output-dir test_reports/mission-control
```

Emits `mission_ci_snapshot.json`, `mission_ci_snapshot.sha256` and
`mission_ci_summary.md`. The hash is an integrity checksum, not a signed
third-party attestation. This is an **operator-executed collector**: a
repository-wide workflow has deliberately NOT been added because the canonical
workflow-policy inventory requires separate governance reconciliation.

For federation, repeat `--target GBOGEB/CODEX@<exact-40hex>` or another
explicit GBOGEB repo/SHA. The GitHub token needs `actions:read` on each
target; unauthorized or unavailable federation targets produce UNKNOWN
rather than a zero count. Never store the token in repository artifacts.

Run-status census is one page (max 100). A partial page is flagged. Only up to
15 completed runs are sampled for job timings by default (bound: 0..40); do
not interpret partial job samples as full-repo runtime. Queue time is
`job.started_at-job.created_at`; runtime is
`job.completed_at-job.started_at`. Missing timestamps remain null. Parallel
job times are **not** summed as elapsed wall time. p50/p95 require >=5
terminal observations. Dependency download, install, test body and upload
require native step telemetry before attribution.

## Wave-by-wave federation history

The history input is `mission.wave.history.input.v1`:

```json
{
  "schema": "mission.wave.history.input.v1",
  "waves": [
    {
      "wave_id": "W1",
      "observations": ["REPLACE_WITH_ACTUAL_CI_SNAPSHOT_JSON_OBJECT"],
      "mip_pulses": [],
      "solo_decisions": []
    }
  ]
}
```

The string in the example **must be replaced with the object** from the
actual native collector, never used as evidence. Subsequent waves carry unique
IDs and snapshots bound to exact source SHAs.

```bash
python ci/governance/mission_wave_history.py \
  --input test_reports/mission-control/wave-history-input.json \
  --output test_reports/mission-control/wave-history.json
```

The command emits both JSON and Markdown next to the chosen output path.
No synthetic numbers are assigned to missing fields.

**Comparison policy:** A matched-workflow set may compare terminal PASS/red
counts, with caveat that dependencies, runners, configurations and changed
source still require separate binding. Pending jobs, missing page coverage
or changed workflow sets withhold progression credit. Producer-declared MIP
source-cohort coverage deltas are displayed per repo but not independently
reauthenticated, and never summed across different denominators.

## Metrics after every pulse and wave

| Axis | Observation | Withhold when |
| --- | --- | --- |
| Depth | Evidence dimensions | Not method maturity |
| Breadth | Repositories with API snapshots | API unavailable |
| Fan-out | Sampled job concurrency | Sample incomplete |
| Root BD | Exact-main native closure proof | Proof missing |
| Coverage | Matched line/branch delta pp | Cohort changed |
| CI throughput | Matched terminal check results | Pending/different |
| Latency | Per-repo queue/runtime p50/p95 | Fewer than 5 |
| Recovery | AMBER request plus issue/expiry | Not authorized |
| 3PR/3PC | Repeatability qualification | No native trials |
| PCA/BT | M1-M3 and observed pairwise outcomes | Insufficient data |
| REX | Signed accepted return | Missing authority |

## Scaling gates

1. **Depth 1 / two disjoint workers:** bounded formatter/correctness repair and
   separate observational diagnosis; no shared-file writes.
2. **Depth 2 / four disjoint workers:** only after completed native receipts,
   collision audit and matched coverage deltas.
3. **Breadth 2 / ABACUS+CODEX:** consume independently authorized receipts,
   with one writer per owned root; one repo's green does not excuse another's
   red.
4. **Federation 4+ / up to eight workers:** only when measured root
   closures/worker-hour improve without CI cost/queue regression. No blanket
   privilege or cross-repo merge rights.
5. **DMAIC control loop:** DEFINE root and stop criteria, MEASURE telemetry,
   ANALYZE cost and repeated manifestations, IMPROVE bounded source repairs,
   CONTROL via recovery issues and expiry.

## Unblocking and governance

The currently active ABACUS ruleset is #24494381. It requires one approval
and has no bypass actors. The GitHub connector cannot mutate rulesets here.
A self-issued review is **not** independent human approval, nor does an
AMBER_REQUESTED JSON receipt bypass GitHub protection.

Manual owner refinement shall keep complete decision audit, concrete
carryovers, explicit issue references and expiration. Security, confidentiality,
data-integrity and provenance failures remain RED_HOLD in the ledger.

No full CI PASS, accepted REX, capacity score or merge is claimed by this file.
