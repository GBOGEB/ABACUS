---
name: governed-ci-evidence-recovery
description: Read-only monitoring of a governed GitHub repository's CI evidence — classify runs by exact source identity, deduplicate failures into causal roots, qualify coverage and stability claims, assess merge admission, and emit a machine-readable handover. Use when asked to check CI/PR/coverage status for credit or admission, to compare waves, or to retire a monitoring session.
---

# Governed CI evidence recovery

Read-only. Never merge, approve, waive, rerun, dispatch or change secrets/rulesets. Report outcomes; do not perform them.

## 1. Admit evidence only by composite key

Every observation is a row keyed by
`repo, source_sha, checkout_kind, checkout_sha, workflow, run, attempt, job, artifact(+sha256, digest_source)`.

- Unknown fields are `null`/`"UNKNOWN"`, never assumed (an absent attempt is not attempt 1).
- `checkout_kind`: `exact_head` | `synthetic_merge` | `main`. Synthetic-merge runs are PR-associated diagnostics, not literal-HEAD proof.
- Only `status=completed` rows count. `queued`, `in_progress`, `action_required` with no jobs → no credit either way.
- When a source SHA moves, all rows at the old SHA become `stale`.
- For `attempt > 1`, read attempt 1. Same SHA failed→passed is a **rerun pass** (flake signal), not a displacement.
- Artifact digests from API metadata are tagged `github_metadata`; only re-hashed bytes are `verified`.

## 2. Count causal roots, not red jobs

Build `root → tests → jobs → summaries`. One harness defect failing N cells is one root.
Root states: `open` → `displaced` (first-red moved at a newer source SHA) → `accepted_closure` (only via a governed merge and explicit acceptance). Record `production_defect` separately from test-harness/scanner/formatting roots.

## 3. Qualify coverage

- Compare only identical instrumented denominators (statements and branches) and a source population whose production files are unchanged; prove the latter with a diff of the two source SHAs.
- Keep statement/branch coverage and zero-covered-module count as separate KPIs; report losses with gains.
- Candidate deltas are against main and **never summed** across overlapping test populations.
- A coverage job reporting SUCCESS below its stated threshold is a governance finding (threshold not enforced).

## 4. Qualify stability

Three qualifying transitions require four distinct, terminal, comparable, **source-changing** waves with unchanged outcome class. Re-polls and same-SHA reruns add zero.

## 5. Admission requires effective governance

Configured ≠ effective. Verify: required status checks naming the canonical producers; stale-review dismissal; minimal bypass actors; and a deliberately RED canary that was **rejected**. Any gap → `MERGE_ADMISSION = HOLD`.

Independent approval, last-push approval and thread resolution depend on the repository's **CODE PURPLE MACH level** (`docs/governance/CODE_PURPLE_MACH_LADDER.md`, evaluator `scripts/code_purple_mach_admission.py`):

- **MACH-I** (team): all three required.
- **MACH-II** (solo owner, the current ABACUS mode): the approval count is waived by recorded policy. A 0-approval merge is *not* a finding on its own. It is admissible only when checks are platform-enforced, the required lanes are green at the exact head, and an automated review is present at that head.
- **MACH-III**: one owner PR in a ≤60-minute exception window with P2/P3 deferral records. P0/P1/UNKNOWN still block.
- **MACH-IV** (merge train): each step re-qualified on the main left by the previous merge, at most `max_steps`, then a green post-train main baseline.

Report the level-specific `HOLD_*` reason, not only HOLD.

## 6. Notify only on material change

```
notify = exact_head_terminal_first_red_changed
      or qualified_same_cohort_coverage_increased
      or qualified_todo_milestone_changed
      or correctly_governed_merge_verified
```

A new failure of a known, unchanged root is not material.

## 7. Output

Each check ends with:
1. A short report: what changed, table of `previous → current` per KPI with evidence links, explicit disposition line
   `MERGE_ADMISSION = … · Formal engineering credit Δ = … · Stability n/3 = …`.
2. Appended rows to `telemetry/evidence_ledger.jsonl`, `causal_roots.jsonl`, `coverage_cohorts.jsonl`.
3. A discrepancy list: anything inconsistent across observations (label collisions, missing attempts, unrecorded prior SHAs).

## 8. Session retirement

Retire only after: ledger/roots/cohorts committed; open actions carried into the durable TODO register; method lessons in repo; a restart contract (`ABACUS_20261022_RESTART_CONTRACT.yaml`) whose reads were executed once by a fresh session and matched. Run `ci/verify_handover.py` to check pack integrity.
