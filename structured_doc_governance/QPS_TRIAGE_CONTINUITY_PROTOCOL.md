# QPS / TRIAGE Chat-to-Repository Continuity Protocol

Version: v1.0.0
Status: Controlled Working Method

## Purpose

Convert each QPS/TRIAGE chat or work session into a governed execution pulse across:

- GBOGEB/cryoplant-project
- GBOGEB/CODEX
- GBOGEB/ABACUS

The protocol preserves evidence, decisions, implementation state, open gates, PCA/BT/MIP context, and exact repository lineage while preventing duplicate PRs, framework drift, and repeated analysis.

## Repository roles

- cryoplant-project: project/engineering child implementation, governed QPS outputs and acceptance/disposition evidence.
- CODEX: executable implementation, parsers, schemas, functions, blocks, agents, runtime probes and generators.
- ABACUS: KEB/governance, orchestration, triage census, cross-repo evidence, DMAIC/PCA/BT/MIP and release/disposition control.

## Standard pulse sequence

### P0 - Re-entry / census

Prompt:

`Perform a QPS TRIAGE re-entry census. Inspect the current active PRs/branches in cryoplant-project, CODEX and ABACUS. Identify today's existing work first and do not duplicate it. Report exact PR numbers, head SHAs, merge state, CI state, unresolved review feedback, current wave/pulse and the narrowest victory condition.`

Checks:
- existing same-purpose PR found?
- branch/head SHA exact?
- merged/closed/open/draft distinguished?
- CI observed rather than assumed?
- child/parent/cross-repo dependencies explicit?

Output:
- TRIAGE_CENSUS
- active 3PR map
- current blockers
- next narrow victory condition

### P1 - Harvest chat knowledge

Prompt:

`Treat this chat/session as QPS engineering and coding evidence. Extract only reusable knowledge. Classify every useful item as immutable input, source-supported evidence, derived calculation, postulate/assumption, requirement, ADR/decision, OCD/scenario, risk, issue, task, artifact, function/block/agent, test/receipt, or governance rule. Preserve source and confidence. Do not promote unsupported claims.`

Checks:
- evidence class assigned?
- source locator available?
- contradiction with SSOT?
- stale/newer evidence?
- should this be immutable, provisional, or superseded?

Output:
- FEATURE_ROWS / evidence rows
- candidate SSOT updates
- ADR/OCD/requirement deltas
- implementation candidates

### P2 - Prune vs bridge

Prompt:

`Perform granular prune-or-bridge classification for the harvested items. PRUNE conversational duplication, obsolete plans and superseded wording. BRIDGE reusable deltas into the correct existing canonical object, file, function, skill, agent, SSOT row, RTM row, DMAIC register, PCA feature row, BT driver or MIP backlog item. Create a new object only when no canonical target exists.`

Checks:
- canonical target searched first?
- duplicate object avoided?
- lineage parent recorded?
- supersedes/derived_from/used_by recorded?
- same concept represented once in SSOT?

Disposition values:
- ACCEPT
- MERGE_INTO_EXISTING
- DEFER
- REJECT
- SUPERSEDE
- PRUNE

### P3 - Prioritize

Prompt:

`Rank the accepted QPS/TRIAGE deltas using factual completion dependency first, then priority. Use FIFO for already-started gates, but pull low-hanging enabling work forward when it reduces blockers. Distinguish observed completion score from PCA/criticality priority. Do not use manual weights as if PCA-derived.`

Priority features may include:
- closure leverage
- blocker removal
- downstream fan-out
- evidence maturity
- uncertainty reduction
- runtime executability
- cross-repo reuse
- safety/compliance relevance
- effort
- reversibility

Output:
- execution queue
- observed completion %
- PCA/priority score where measured
- Top drivers and reverse loadings

### P4 - Execute 3PR / 3PC

Prompt:

`Execute the highest-value non-duplicate QPS TRIAGE pulse as a 3PR/3PC across ABACUS, CODEX and cryoplant-project where the work genuinely crosses all three. Reuse existing branches/PRs when possible. Implement code/docs/tests, run or inspect CI, and bind exact-head receipts. Recurse on the first red gate: diagnose -> repair -> rerun -> record result. Do not claim PASS for unexecuted or deferred checks.`

Checks per repo:
- implementation exists > documentation-only where executable work is expected
- tests/probe execute >0 steps
- exact head SHA captured
- receipt/artifact bound to same SHA
- DOW/KEB/child contract observed
- ACCEPT/REJECT/DEFER recorded

### P5 - MIP pass

Prompt:

`Apply MIP to the changed surfaces only. Modernize stale or failing code/workflows; Innovate by adding useful connections, hierarchy, analogues or reusable functions/agents; Perpetuate through tests, runners, Docker/MCP/CI, metrics and recursive DMAIC. Keep MIP subordinate to the current Definition of Done.`

Checks:
- Modernize: repaired/upgraded?
- Innovate: materially new capability, not decoration?
- Perpetuate: repeatable execution and measurement?

### P6 - Validate DoD / DoV

Prompt:

`Evaluate the pulse against QPS/TRIAGE Definition of Done and Definition of Victory. Report factual gate counts and evidence. Separate engineering closure, numerical/source closure, negotiation closure and governance/runtime closure. No score promotion without the required receipt/evidence.`

Minimum terminal proof:
- source/SSOT bound
- schema/contract valid
- executable path works
- generated artifact exists where required
- cross-repo parity/receipt bound
- fresh-checkout/repeat where required
- unresolved DEFERs explicitly listed

### P7 - Session handover to GitHub

Prompt:

`Create the QPS TRIAGE session handover and commit it to the appropriate governance location. Include user-prompt/agent-output pairs in summarized structured form; artifacts created; files/branches/PRs/SHAs; tests and receipts; decisions; pruned items; bridged items; observed completion; PCA/BT/MIP changes; blockers; next three moves; full remaining major waves; and the exact next-chat re-entry prompt.`

Required handover objects:
- SESSION_MANIFEST.md
- EXECUTION_STATUS.md
- ARTIFACT_REGISTER.md
- LINEAGE/FEATURE_ROW update
- optional conversation.jsonl pointer or summary

## QPS/Triage Definition of Done

The protocol itself is done when a new chat can reconstruct the execution state from GitHub without relying on conversational memory and can identify one unambiguous next action.

For a QPS work package, terminal DoD requires as applicable:
- canonical SSOT updated or explicitly unchanged
- evidence classification preserved
- RTM/OFFER/EVAL/agenda crosswalk updated where affected
- generated canonical outputs regenerated where affected
- schema/contract validation passes
- executable code/tests/probes pass >0 steps
- exact-SHA lineage/receipts recorded
- 3-repo handoffs agree on disposition
- no unsupported compliance or engineering credit
- remaining negotiation/RFI dependencies remain explicit
- session handover committed

## Anti-drift rules

1. Search active PRs before creating a PR.
2. Extend canonical work before creating parallel frameworks.
3. Finish the oldest active blocker first unless a low-effort dependency unlocks it.
4. No dashboard or new abstraction may displace an incomplete executable gate.
5. PCA priority and observed completion are different measures.
6. DEFER is a valid result; it is not PASS.
7. Exact-SHA evidence outranks narrative status.
8. Every new artifact must state parent/source/derived_from/supersedes where applicable.
9. Every session closes with a next-chat re-entry prompt.

## Compact reusable master prompt

`Run one QPS/TRIAGE continuity pulse: (1) census current ABACUS/CODEX/cryoplant-project PRs and avoid duplicates; (2) harvest this chat into typed evidence/requirements/ADR/OCD/tasks; (3) prune duplicates and bridge accepted deltas to canonical SSOT/code/RTM/PCA/BT/MIP objects; (4) prioritize FIFO plus low-hanging blocker removal; (5) execute the smallest meaningful 3PR/3PC and recurse on first red; (6) apply MIP only to touched surfaces; (7) report DoD/DoV with exact SHA receipts and DEFERs; (8) commit a session manifest and give the exact next-chat prompt.`
