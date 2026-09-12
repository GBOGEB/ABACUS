---
name: mip-repo-self-index
description: Prove and classify repository self-index state with exact-SHA lineage, sanitized producer/consumer receipts, and branch-causality separation. Use for MIP/QPS TRIAGE or similar repository convergence work when ChatGPT must bind evidence to a GitHub commit, run or inspect self-index/diagnostic CI, compare a failing PR head with its base, classify reds as branch-caused versus inherited/governance/external, validate downstream artifact consumption, or decide whether a repo capability is ready to move from RED/AMBER toward GREEN/CONTROL without claiming broader project DoV.
---

# MIP Repo Self Index

## Core contract

Treat exact commit identity as the evidence anchor. Preserve repo architecture while proving runtime behavior.

Never infer PASS from absence of a red check. Require an executed predicate with evidence. Never repair an inherited failure inside a local proof pulse merely to make the matrix green.

## Execution workflow

1. **Freeze the evaluated identity**
   - Read the PR head SHA and base SHA from GitHub.
   - If the branch moves, discard stale proof and restart from the new exact head.
   - Record the repo, PR, head SHA, base SHA, workflow/run/job IDs, and artifact IDs used as evidence.

2. **Run or inspect the producer**
   - Require checkout of the exact evaluated head, not an implicit branch tip.
   - Run the self-index at least twice when repeatability is part of the gate.
   - Normalize only volatile fields such as timestamps and environment-local paths.
   - Require declared receipt SHA to equal runtime `git rev-parse HEAD`.
   - Keep raw receipts transient unless the governing contract explicitly allows persistence.

3. **Require a real consumer**
   - Upload only sanitized producer evidence.
   - In a distinct downstream job or consumer, download that exact artifact.
   - Validate repository, exact SHA, schema/program identity, producer PASS, repeatability invariants, and retention policy.
   - Emit a separate sanitized consumer receipt bound to the same exact SHA.

4. **Classify every red before editing**
   - `BRANCH_CAUSED`: first failing assertion is introduced by the branch. Repair only that narrow defect.
   - `PRE_EXISTING`: the same predicate was already red on the PR base or equivalent parent state. Do not repair it in this pulse.
   - `METADATA_OR_GOVERNANCE`: failure is PR metadata, inventory, policy registration, or another non-product-code gate. Keep it separate from runtime repair.
   - `EXTERNAL`: runner/service/permission/dependency condition outside branch code.
   - `UNKNOWN`: evidence is insufficient. Do not guess; obtain the first authoritative failing assertion or leave the gate withheld.

5. **Use base/head causality when logs are incomplete**
   - If exact failing assertion detail is unavailable, compare the identical workflow/predicate on the base SHA.
   - A red on both base and head is evidence of inheritance when the branch did not alter that predicate's governing files.
   - Do not treat this as proof if the workflow, inputs, or environment materially changed between base and head.

6. **Repair locally and re-prove**
   - Change only files needed for the first branch-caused red.
   - Re-run the exact-head producer and consumer.
   - Re-run formatting/schema/governance gates touched by the changed file type.
   - Preserve unrelated reds as separately classified debt.

7. **Repeat on a later SHA**
   - Demonstrate the same invariant contract on at least one later distinct SHA before promoting repeatability toward CONTROL.
   - Compare invariant fields and classification outcomes, not artifact byte identity.

8. **Report scoped DoV**
   - State the narrow predicate that passed.
   - Report `unclassified_red_count` explicitly.
   - Keep global/project DoV WITHHELD unless the broader project gate is independently satisfied.

## Self-assessment lanes

Use these canonical lanes when present:

- `repo_self_assess_debug_ldab`: executable diagnostic/debug evidence bound to exact SHA.
- `repo_self_assess_runners_mcp`: executable runners, workflows, federation, or orchestration evidence.
- `repo_self_assess_codz_health_selfheal`: observed health/self-heal behavior, not filename presence alone.
- `repo_self_produce`: a reusable skill, agent, parser, or orchestrator that another surface can consume.

A filename can be a discovery signal, never sufficient proof of GREEN by itself. Bind GREEN promotion to executable evidence or a downstream consumer.

## Sanitized receipt requirements

For producer/consumer receipts, require the contract in `references/receipt-contract.md`.

When local JSON receipts are available, run:

```bash
python scripts/validate_receipt.py producer.json --consumer consumer.json --expected-sha <sha>
```

Treat validator success as structural evidence only; CI execution and GitHub exact-head lineage remain authoritative.

## GitHub connector discipline

Prefer GitHub repository, PR, workflow-run, job-log, artifact, and commit evidence over public web sources.

For each failure:

1. fetch PR/head/base metadata;
2. fetch exact-head workflow runs;
3. fetch the failing job steps;
4. fetch the job log only as far as needed to identify the first meaningful error;
5. compare with base/parent when causality remains ambiguous;
6. patch only after classification.

Do not repeatedly retry an unavailable log endpoint. Switch to base/head evidence or preserved artifacts instead.

## Stop conditions

Stop local repair and report the boundary when:

- the only remaining reds are proven inherited/external;
- the requested gate is satisfied but global/project DoV is not;
- fixing a red would require changing architecture, topology authority, or unrelated governance;
- evidence cannot support a safe classification.
