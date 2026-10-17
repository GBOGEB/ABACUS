<!-- markdownlint-disable MD013 MD060 -->
# G3A — Governed N→N+3 Advancement

Status: ABACUS-local implementation candidate. Global semantic authority stays
with CODEX [draft PR #1059](https://github.com/GBOGEB/CODEX/pull/1059).
No new federation SSOT, global scheduler, merge authority or engineering acceptance.

## Formal taxonomy

| Moniker | Long name | Purpose | Credit |
| --- | --- | --- | --- |
| **3W** | Three-Wave Delivery | Three bounded engineering tranches with source-owner leases, disjoint commits, fan-in and exact-head tests | A wave may fail or defer; it is not automatically N+1 |
| **3MP** | Three Measurement/Improvement Pulses | Three DMAIC/MIP observe → classify → act/defer → measure → Control loops | An observation or repeated test is not an accepted advance |
| **G3A** | Governed Three-Advance Mission | One kickoff, three source-bound A1/A2/A3 checkpoint gates, stop early on major blocker | N→N+3 only when three distinct scoped checkpoints are proven |
| **ADVANCE** | Accepted local checkpoint | Evidence-bound scoped engineering verification claim | Missing, skipped, stale or failing proof does not increment N |

The existing CODEX atomic action monikers remain `CLOSE`, `RED`, `RUNTIME`,
`SEM`, `SSOT`, `RECEIPT`, `ENABLE`, `HARDEN`, `CLEAN`, `MAINT`,
`READ`, `EXP` and `WATCH`. 3W/3MP/G3A are execution units,
not new action monikers or reserved W108 status keys. Existing 3PC, 3PR,
3P* and 3P3 retain their separate meanings.

**N** is the named accepted G3A checkpoint index, not an open-PR count,
failed-job count, pulse, wave, calendar day or GitHub merge.
Historical `MIP/EXECUTION.md` horizons (N+5, N+10) counted pulses.
Do not retroactively reinterpret them; use `g3a_n` or
`checkpoint_index` for this new namespace.

## Canonical single-kickoff prompt

> **G3A — Execute governed N→N+3.** Resolve the current evidence-qualified
> N, default branch, exact PR heads and effective GitHub gates. Choose the
> smallest source-owner action with greatest verified first-red/root leverage
> and matched test/coverage improvement. Across three checkpoint gates,
> execute without interim prompts when an execution session or explicitly
> dispatched runner exists. Each gate shall inspect → repair/build if
> authorized → test → measure → bind exact-source proof → accept the scoped
> checkpoint or stop. Use disjoint worker commits only when leases and
> capacity permit; integrate one exact-head testflight. Never rerun
> unchanged deterministic failures, merge or waive without authorization,
> fabricate review/security approval, or count queued jobs as successful.
> If blocked materially, return early. End with N→actual-N, before/after
> numerators/denominators, source SHA, run/job/attempt, linked artifacts,
> first-red and the next directly linked action.

## Required kickoff and returned evidence

Inputs: mission ID; source repository; current accepted N and objective;
authorized expected HEAD SHA; A1/A2/A3 objectives and gate-specific DoV;
bounded worker/time budgets and per-path ownership where mutation is
authorized; security/review/authority vetoes; and receipt destination.

Outputs: `mission_id`, `start_n`, `target_n`, `actual_n`,
`attempted`, `accepted_checkpoints`, exact SHA, each step's objective,
action moniker, test and metric numerator/denominator, time and proof digest,
first material blocker, next action, and explicit admission boundary.
For missing external data, report UNKNOWN, not synthetic 0 or PASS.

The shipped executable is a **local read-only checkpoint verifier**:
`scripts/g3a_bounded_mission.py` runs allowlisted `syntax`,
`file_sha256`, `metric_min` and bounded `unittest` actions.
It rejects mismatched checkout SHA and unapproved shell commands.
It does not commit code, dispatch remote workers, mutate GitHub settings,
grant owner attestation/independent approval or merge.
A full source-changing autonomous mission requires the existing authorized
ABACUS/CODEX scheduler and human approval at restricted gates.

## Three checkpoint defaults

| Checkpoint | DMAIC/MIP default | Action | Exit evidence |
| --- | --- | --- | --- |
| A1 / N+1 | Define + Measure / Modernize | Re-resolve baseline, causal first-red, constraints and owner | Source-bound verified diagnosis or readiness improvement |
| A2 / N+2 | Analyze + Improve / Innovate | Implement bounded owned repair or expand tests and coverage | New passing cases and matched numerator/denominator |
| A3 / N+3 | Control / Perpetuate | Qualify integrated source, negative controls, recurrence and recoverability | Final proof, rollback/drift plan and handover |

These are defaults, not a mandate for three artificial edits. One wave may
contain multiple pulses; several waves may serve one accepted checkpoint.

## SIPOC

| Supplier | Input | Process | Output | Customer |
| --- | --- | --- | --- | --- |
| Owner and repo | N, SHA, scope, safety/review controls | Preflight identity and authority | Eligible mission or early stop | Existing scheduler |
| Workers and CI | Source-owned changes, first-red, JUnit/coverage | Three bounded checkpoint evaluations | A1/A2/A3 proof | MIP/DMAIC |
| GitHub native API/reviewer | Runs, job attempts, review gates | External exact-head admission | HOLD or separately authorized merge eligibility | Owner |
| DOW + CODEX KEB | Immutable receipts and matched metrics | Lineage join, telemetry and causal analysis | N→actual-N, first-red, direct action | Operator/child consumers |

```
mermaid
flowchart LR
  S[One kickoff at N] --> P{Exact SHA and authority?}
  P -->|HOLD| X[Return actual N and blocker]
  P -->|PASS| A1[A1 N+1]
  A1 -->|PASS| A2[A2 N+2]
  A2 -->|PASS| A3[A3 N+3]
  A3 -->|PASS| R[Final ledger and Control]
  A1 -->|FAIL| X
  A2 -->|FAIL| X
  A3 -->|FAIL| X
```

## Runtime, status and acceptance

State path: `CREATED → PREFLIGHT → A1 → A2 → A3 →
COMPLETE_LOCAL_3_OF_3`. A first material failure returns
`BLOCKED_MAJOR` and the exact achieved ordinal. Stale source identity
fails preflight. Unexecuted CI remains queued/not-run and never counts
as a passed checkpoint. The verifier performs no infinite polling.

```
bash
HEAD_SHA="$(git rev-parse HEAD)"
python -m unittest discover -s tests -p test_g3a_bounded_mission.py -v
python scripts/g3a_bounded_mission.py \
  --spec docs/ci/G3A_EXAMPLE_MISSION.json \
  --repo-root . --expected-head "$HEAD_SHA" \
  --out test_reports/g3a/mission-receipt.json
```

The example mission accepts three distinct **local control-verification**
checkpoints (runner syntax, test-suite syntax, 25 real unit tests).
That local N=0→3 is not ABACUS PR/root closure or a merge.
Native GitHub proof workflow:
`.github/workflows/g3a-bounded-continuation-proof.yml`.
Global semantic sources remain
`GBOGEB/CODEX:federation/mesh/GLOBAL_GLOSSARY_v1.yaml` and
`GBOGEB/CODEX:federation/mesh/GLOBAL_ACTION_TAXONOMY_v1.yaml`;
ABACUS consumes them but does not replace them.
