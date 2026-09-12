---
name: mip-repo-self-index
description: >-
  Prove and classify repository self-index state with exact-SHA lineage,
  sanitized producer and consumer receipts, and branch-causality separation.
  Use for MIP, QPS TRIAGE, or similar repository convergence work when
  ChatGPT must bind evidence to a GitHub commit, inspect self-index or
  diagnostic CI, classify branch-caused versus inherited reds, validate
  downstream artifact consumption, or promote a repository capability from
  RED or AMBER toward GREEN or CONTROL without claiming broader project DoV.
---

# MIP Repo Self Index

## Core contract

Treat exact commit identity as the evidence anchor. Preserve repository
architecture while proving runtime behavior.

Never infer PASS from the absence of a red check. Require an executed
predicate with evidence. Never repair an inherited failure inside a local
proof pulse merely to make the matrix green.

## Execution workflow

1. **Freeze the evaluated identity**
   - Read the PR head SHA and base SHA from GitHub.
   - If the branch moves, discard stale proof and restart from the new head.
   - Record repo, PR, head/base SHAs, run/job IDs, and artifact IDs.

2. **Run or inspect the producer**
   - Require checkout of the exact evaluated head, not an implicit branch tip.
   - Run the self-index twice when repeatability is part of the gate.
   - Normalize only volatile fields such as timestamps and local paths.
   - Require declared receipt SHA to equal runtime `git rev-parse HEAD`.
   - Keep raw receipts transient unless authority permits persistence.

3. **Require a real consumer**
   - Upload only sanitized producer evidence.
   - In a downstream job, download that exact artifact.
   - Validate repo, SHA, schema/program, PASS, repeatability, and retention.
   - Emit a separate sanitized consumer receipt on the same exact SHA.

4. **Classify every red before editing**
   - `BRANCH_CAUSED`: branch introduced the failing predicate.
     Repair only that narrow defect.
   - `PRE_EXISTING`: equivalent predicate was already red on the base.
     Do not repair it in this pulse.
   - `METADATA_OR_GOVERNANCE`: PR metadata, inventory, or policy failure.
     Keep it separate from runtime code repair.
   - `EXTERNAL`: runner, service, permission, or external dependency.
   - `UNKNOWN`: evidence is insufficient. Do not guess.

5. **Use base/head causality when logs are incomplete**
   - Compare the identical predicate on the base SHA when needed.
   - A red on both base and head supports inheritance only when the branch
     did not alter the predicate's governing files.
   - Do not use this proof if workflow inputs or environment changed.

6. **Repair locally and re-prove**
   - Change only files needed for the first branch-caused red.
   - Re-run the exact-head producer and consumer.
   - Re-run formatting, schema, and governance gates touched by the change.
   - Preserve unrelated reds as separately classified debt.

7. **Repeat on a later SHA**
   - Prove the same invariant contract on another distinct SHA before
     promoting repeatability toward CONTROL.
   - Compare invariant fields, not artifact byte identity.

8. **Report scoped DoV**
   - State the narrow predicate that passed.
   - Report `unclassified_red_count` explicitly.
   - Keep global/project DoV WITHHELD unless its gate is satisfied.

## Self-assessment lanes

Use these canonical lanes when present:

- `repo_self_assess_debug_ldab`: executable diagnostic evidence on exact SHA.
- `repo_self_assess_runners_mcp`: executable runner/orchestration evidence.
- `repo_self_assess_codz_health_selfheal`: observed health/self-heal behavior.
- `repo_self_produce`: reusable skill, agent, parser, or orchestrator.

A filename is a discovery signal, never sufficient proof of GREEN by itself.
Bind GREEN promotion to executable evidence or a downstream consumer.

## Sanitized receipt requirements

Use the contract in `references/receipt-contract.md`.

When local JSON receipts are available, run:

```bash
python scripts/validate_receipt.py producer.json \
  --consumer consumer.json --expected-sha <sha>
```

Validator success is structural evidence only. CI execution and GitHub
exact-head lineage remain authoritative.

## GitHub connector discipline

Prefer GitHub repo, PR, run, job-log, artifact, and commit evidence over
public web sources.

For each failure:

1. fetch PR/head/base metadata;
2. fetch exact-head workflow runs;
3. fetch failing job steps;
4. fetch logs only to the first meaningful error;
5. compare with base/parent if causality is ambiguous;
6. patch only after classification.

Do not repeatedly retry an unavailable log endpoint. Switch to base/head
evidence or preserved artifacts instead.

## Stop conditions

Stop local repair and report the boundary when:

- only proven inherited or external reds remain;
- the requested gate passes but global/project DoV does not;
- repair would alter architecture, topology authority, or unrelated policy;
- evidence cannot support a safe classification.
