<!-- markdownlint-disable MD013 MD060 -->
# GCA-3: governed three-wave advancement — execution taxonomy and glossary

**Status:** operational execution convention; subordinate to the existing MIP / 3P* methodology, repository ownership, CODE PURPLE #1860 evidence, and active GitHub rules. **Not a new federation SSOT.** This document does not reopen the historically closed MIP fixed tranche in `MIP/EXECUTION.md`.

## Canonical monikers

| Term / ID | Definition | What increments it | What it does **not** mean |
| --- | --- | --- | --- |
| **GCA-3** — Governed Convergence Advance ×3 | One **bounded, same-invocation** instruction to execute three consecutive governed delivery waves, N+1, N+2 and N+3, and return a complete evidence-based closeout | One accepted *wave*, sequentially; an attempted/held wave is separately recorded | Background execution, autonomous authority transfer, three commits, three merges, or three successful CI runs |
| **Wave** (`W[N+1]`) | An independently receipted engineering delivery increment with a fixed objective, path ownership, root/PR scope, tests, observed outcome, and control gate | Delivery/engineering DoV PASS on its declared scope; release DoV is independent | A single CI rerun or an arbitrary collection of observations |
| **Pulse** (`U1..Uk`) | A short local **observe → diagnose → change or deliberately no-change → verify** feedback loop nested inside a wave | One complete, timestamped observation/action/result receipt; k defaults to 1–3 per wave | An integration baseline increment, a new PR, or method stage P1/P2/P3 |
| **3-pulse** (`U×3`) | Three sequential feedback loops on one declared wave/cohort, with each comparing comparable evidence | Three documented pulse receipts | Three delivery waves |
| **3-wave** (`W×3`) | Three distinct N+1/N+2/N+3 wave attempts, with individual DoV and final mission reconciliation | Three wave receipts; only passing contiguous waves advance the accepted index | Necessarily nine loops or three main merges |
| **3P\*** (`P1/P2/P3`) | Existing governed method stages: **P1 discovery**, **P2 reverse-pressure**, **P3 governed information re-entry**; see `architecture/w64/GENERIC_3P_END_TO_END_PIPELINE.yaml` | Method-specific proof/DoV | The number of pulses, despite similar spelling |
| **DMAIC** | Define, Measure, Analyze, Improve, Control governing each pulse/wave according to the applicable artifact | Controlled evidence/actions, not a counter | A substitute for independent admission |
| **N (accepted index)** | Highest contiguous, previously accepted GCA wave baseline. Record SHA and evidence source separately | Only measured wave-level acceptance after its required engineering gates | PR count, commit count, or main-merge count |
| **N+3 attempted** | Three planned wave executions have been performed and individually receipted | Execution records for W[N+1..N+3] | All three were accepted |
| **N+3 accepted** | Every one of W[N+1], W[N+2], W[N+3] has a valid, source-bound wave PASS with no intervening HOLD | Three contiguous wave PASS receipts | Automatic permission to merge into main |
| **Owner lease** | Exact branch-head expectation and non-overlapping writable path scope for one source owner | Explicit compare-and-swap source update | A second independent human reviewer |
| **Major blocker** | Safety/security P0/P1 with no authorized path, authority or irreversible-action uncertainty, irreconcilable source collision, missing mandatory evidence that blocks all remaining independent work, or exhausted bounded budget | Stops unsafe lane or mission, with reason and evidence | A routine deterministic first-red that can be repaired safely |
| **BDQ** | Burndown queue of uniquely identified manifestations and independently diagnosed causal roots | Root/manifestation transitions on matching immutable source and run IDs | Raw PR count or `~260` observations automatically equal independent roots |
| **Engineering DoV / Release DoV** | Scope-bound delivery verification vs independent protected admission (security, A10, governance, reviewer, branch rules, exact-head CI) | Independent gate evidence | Green B0 alone permits merging |

## Hierarchy and naming

```text
GCA-3 mission (current accepted N -> goal N+3)
  W[N+1]  wave receipt (PASS / HOLD / STOP)
    U1   measurement + bounded action + verification
    U2   optional root-specific improvement
    U3   optional convergence/control check
    3P* stages P1/P2/P3 may be applied WITHIN these pulses
  W[N+2]  new wave and independent acceptance receipt
    U1..Uk
  W[N+3]  new wave and independent acceptance receipt
    U1..Uk
  closeout: attempted=3, accepted=0..3 contiguous, qualified BDQ and coverage deltas
```

The default budget is **three waves and up to three pulses per wave** (maximum nine pulses, not a requirement to use all nine). Reuse existing passing evidence only if SHA, workflow, test scope, config, producer job, and artifact lineage still match. One source-owned patch followed by one integrated exact-head testflight is preferred over repetitive CI storms.

## Input and execution protocol

1. **Intake:** the operator supplies the **mission objective**, repository/scope, accepted N and reference/evidence, priority ordering, acceptance gates, excluded actions, resource limits, and a stopping policy. GCA-3 never infers owner permission or reviewer approval. Use `MIP/GCA3_REQUEST_TEMPLATE.json` and `scripts/gca3_contract.py` for request validation.
2. **Freeze baseline:** independently reread default branch, effective available protection/rules, open PR heads, run/job/attempt IDs, reviews, source owners, prior BDQ identifiers, and matched statement/branch denominators. Snapshot before changes. If a gate is inaccessible, report **UNKNOWN**, not PASS.
3. **Execute W[N+1]:** allocate read-only scouts as capacity permits, choose top disjoint source owner(s), apply bounded pulses (`U1..U3`) using DMAIC and 3P* as appropriate. Each source mutation requires exact-head lease; do not mutate multiple owners' paths in the same worker. Use one integrated exact-head testflight. Record negative cases, first-red and coverage proof.
4. **Control checkpoint:** accept the wave only if *declared engineering* DoV passes; record release/admission gates independently. If the wave is HOLD, its accepted index does **not** advance; continue only with independently safe, explicitly separated observation or work, never mislabel a later attempt as accepted N+2.
5. **Repeat up to three wave attempts:** recompute priorities from live evidence, record forecasts before running, compare predicted versus actual metrics, and prevent re-executing deterministic unchanged-SHA failures. Do not extend beyond time/call/PR/CI budgets without a new instruction.
6. **Close out during the same execution:** return all three wave states (or exact point of justified stop), attempted vs accepted index, PR/commit/file deltas, native SHA/run/job/attempt evidence, test and coverage numerators/denominators with comparable scopes, BDQ root vs manifestations, throughput/time and uncertainty, current major blockers, DAG/SIPOC changes, and direct next actions. Publish only authorized/sanitized receipts to the existing canonical #1860; never overwrite historical proof.

### Major-blocker semantics

- **STOP mission:** unresolvable authorization or restricted-content issue, an unsafe irreversible action, unreconciled exact-head lease for all lanes, unowned P0/P1 security exposure, or resource/time budget exhaustion that leaves no admissible action. Preserve evidence and report the achieved contiguous N+k; do not promise unattended background completion.
- **HOLD one lane / keep moving:** an independent CI first-red, a queue delay, a missing noncritical coverage artifact, or a source collision with an alternative disjoint owner. Preserve HOLD on affected wave and separate attempted from accepted increments.
- **Never autonomously:** weaken protections, grant approvals, waive P0/P1, merge main, invent users/workers, retry an unchanged deterministic failure, or claim a release DoV from engineering-only tests.

## Receipt/accounting vocabulary

Mandatory status dimensions are `attempted_waves`, `accepted_contiguous_waves`, `wave_status`, `pulse_status`, `commit_shas`, `before/after_scope`, `run_id`, `run_attempt`, `job_id`, `coverage_lines_covered/eligible`, `coverage_branches_covered/eligible`, `tests_pass/fail/skip`, `unique_root_ids`, `manifestations`, `duration_seconds`, `forecast_vs_actual`, `uncertainty`, and `release_admission` (normally HOLD until independent gates pass). `NOT_RUN`, `UNKNOWN`, `BLOCKED`, and `FAIL` are distinct. A PR creation is not a wave acceptance; a test PASS does not imply a root's full causal closure.

### Copy-ready invocation

> **Execute GCA-3 from accepted wave N=[index/ref] to target N+3.** Use the canonical CODE PURPLE/MIP/3P* and #1860 evidence, with priority **test coverage and first-red root burndown**, followed by execution telemetry and DAG/SIPOC integration. Freeze and re-resolve exact GitHub heads, rules, native job attempts, source ownership and acceptance gates. Execute up to three bounded wave increments with adaptive 1–3 pulses per wave; allocate only path-disjoint workers with CAS leases. Repair the largest attributable roots, add positive/negative/reverse tests, and require a single integrated exact-head testflight per changed head. Continue without intermediate prompts within this request unless a major blocker/authorization issue arises. Never auto-merge, waive security, approve for a human, or repeat unchanged deterministic CI. At the end, return an N→N+3 receipt: what changed, PR/commit links, matched before/after test and coverage numerators, unique BDQ roots/manifestations, time/efficiency, new DAG/SIPOC edges, independent gates, exact accepted N+k and remaining HOLDs. Distinguish attempted from accepted waves and mark missing evidence UNKNOWN. Do not claim background execution.

**Capability limitation:** GCA-3 is a bounded workflow *within one active ChatGPT execution*, not a persistent unattended agent. Later scheduled execution requires an explicit supported automation, and access to connected runners/approval identities must be verified independently.