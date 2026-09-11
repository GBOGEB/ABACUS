# MIP Controlled Execution Register

Status date: 2026-09-11. Scope: this rollout; other sessions are not assumed synchronized.
Canonical source for this wave: ABACUS/MIP/EXECUTION.md. CODEX and DOCX link here.
This is an execution contract and backlog, not a claim that its scheduler or agents already run.

## Mission and acceptance

Modernize, Innovate, Perpetuate across ABACUS, CODEX, DOCX_RTM_Automation and
ABACUS/integration/codespace_jyperter. Separate CODESPACE/DOCX repo identities remain unconfirmed.
Three repositories, four surfaces; the nested surface is not a fourth repository.
Existing MIP README DoV remains binding: receipts at three distinct repo SHAs
and an executable self-heal or produce proof. Do not create empty commits to meet this gate.
Private reviewed evidence can support DoV; public receipt publication is not required.
Child/project disposition authority stays with main triage; this register cannot promote it.

## Ordered action queue

Status vocabulary: DONE, IN_PROGRESS, READY, BLOCKED, PLANNED, CONTROL.
Owner entries below are responsibility roles, not claims of spawned agents.

| ID | Priority | Action / location | Dependency | Owner / resource | State | Exit evidence |
| --- | --- | --- | --- | --- | --- | --- |
| M01 | P0 | Reconcile receipt branches in all 3 repos | none | Coordinator / GitHub reads | DONE | Branch policy files present; no existing receipt-policy PRs at reconciliation |
| M02 | P0 | Reconcile already-merged guards and clarify private evidence acceptance | M01 | Implementer / contents API, git | IN_PROGRESS | Existing main guards retained; DOCX bootstrap removal retained; clarification PRs open |
| M03 | P1 | Inspect newer main execution artifacts before rerunning the 4-surface census | Existing main guards; M01 | Repo maintainers / isolated worktrees, Python stdlib | READY | Private commit-bound receipts; actual tracked-file denominators |
| M04 | P1 | Execute real debug/LDAB and Docker/runner/MCP probes | M03 | Technical lead / existing probes and declared environments | PLANNED | Process executes >0 steps; exit code, environment and results bound to commit |
| M05 | P1 | Resolve first real failure or missing dependency; repeat | M04 | Implementer / smallest affected module | PLANNED | Targeted fix passes and independent checkout repeats |
| M06 | P1 | Prove one reusable capability, then implant in another repo | M03; selected capability passes M04 | Skill engineer / existing code, skill-creator | PLANNED | Callable package, dependencies, examples and second-repo execution |
| M07 | P2 | Add bounded health remediation | M04, M05 | Technical lead / health code and rollback | PLANNED | Detect -> proposed action -> bounded execution -> verify; rollback tested |
| M08 | P1 | Evaluate component CONTROL promotion | Relevant M03-M07 evidence | Reviewer / evidence ledger | PLANNED | Acceptance, repeatability, owner, cadence, drift and re-entry rules |
| M09 | P2 | Refresh measured priority and residual backlog | M03; each completed pulse | Analyst / DMAIC, BT; PCA only with adequate data | PLANNED | Ranked gaps with feature provenance and uncertainty |
| M10 | P2 | Federate summaries through existing DOW/KEB/child route | Verified payload and existing contract discovery | Integration lead / existing adapters | PLANNED | Consumer validates payload; child records ACCEPT/REJECT/DEFER |
| M11 | P3 | Expand repo coverage and agent orchestration | M08, M09; capacity available | Coordinator / verified identities and existing orchestration | PLANNED | New scope denominator, bounded workers and same acceptance gates |

## Work structure and resources

Shared functional sequence: index -> assess -> evidence -> decision -> bounded action -> verify -> report.
ABACUS owns this wave's coordination register and nested-surface roll-up.
CODEX is a candidate implementation home for debug/health capabilities; inspect before assigning code ownership.
DOCX uses existing document/RTM automation and representative fixtures.
codespace_jyperter requires its declared environment; a missing pytest installation is BLOCKED, not a code FAIL.
Use separate worktrees and environments. Keep generated private evidence outside tracked source by default.
Do not publish local path census, dirty-state details or environment diagnostics with these PRs.
Prefer existing scripts, modules and adapters; no new MCP service or agent framework is required by this plan.
Use skill-creator only when packaging a proven capability; document/PDF skills for rendered-output checks.
Agents, project managers and technical managers are planned roles until their callable paths are demonstrated.

## Controlled acceleration

Initial proposed work-in-progress cap: 2 execution lanes plus 1 verification lane.
Lane A closes the highest-priority blocker; lane B prepares an independent downstream capability.
Blocked work releases execution capacity but retains its ID, reason, unblock condition and owner.
Reconcile heads before each mutation; serialize writes to the same branch.
Each pulse must retire a blocker, add verified capability, reduce uncertainty, or explicitly park a low-value item.
Increase the cap by one only after two consecutive pulses meet acceptance without new critical regression
and reviewer/runner capacity is available. Reduce it when failures or review queues accumulate.
This is a scheduling policy for execution, not a background automation deployment.

## Horizons

| Gate | Target outcome | Expansion condition |
| --- | --- | --- |
| N+1 | M01-M02 reviewable; baseline path ready | Publication guards accepted before new evidence generation |
| N+5 | M03-M05 executable across scoped surfaces; first M06 pilot | Working runtime path and first CONTROL candidate |
| N+10 | Second-repo implantation, bounded remediation, validated federation | Repeatability and maintenance ownership established |
| N+50 | Desired control coverage with only justified residual improvement | Expand only against measured unmet need; stop low-value growth |

Horizons count bounded pulses, not dates or promised completions. Replan after each evidence review.

## IMPROVE to CONTROL

Promote individual components, never the whole mesh by inference.
Required: defined acceptance tests pass; representative repeatability; no unresolved critical defect;
recovery/rollback evidence where applicable; named owner, monitoring cadence and re-entry trigger.
Proposed plateau review: three comparable observations with marginal benefit below a component-specific
threshold. Record the metric, threshold and observation conditions before using this criterion.
A plateau is not proof of MAX or Six Sigma capability. Investigate measurement limits and constraints.
Re-enter IMPROVE after regression, dependency drift, changed requirements or a material new opportunity.
CONTROL still runs regression monitoring and periodic audits; it is not abandonment.

## Metrics and priority

Publish numerator, denominator, commit/time scope and evidence freshness for every metric.
Track verified/scoped components, CONTROL/eligible components, executed/planned probes,
open blockers by severity and age, escaped regressions, recovery time, cycle time and benefit per pulse.
This reconciliation observed policy source on 3/3 branches, explicit receipt ignore rules on 0/3,
and receipt-policy PRs on 0/3 before implementation. These are starting counts, not live dashboard values.
Seed coverage is inherited session evidence (3 repos / 4 surfaces), not fresh runtime verification.
Current global DoV: WITHHELD. CONTROL promotions in this wave: 0 evidenced.
No overall completion percentage is defined until component denominators are accepted.

Use transparent BT-style risk/impact/dependency/cost ranking first; record manual weights as manual.
Formal PCA needs a standardized measured matrix, sample adequacy and interpretable loadings.
PC1 captures variance, not automatically value. After stabilizing its actionable drivers,
rerank remaining loss and recompute PCA where justified; PC2 may become the new PC1.
Do not generate PCA percentages from expert guesses and label them telemetry.

## Pulse event protocol

Record append-only events with pulse_id, task_id, repo, component, observed_at, source_commit,
prior_state, next_state, check, outcome, evidence_reference, blocker, next_action and reviewer.
Keep detailed receipts private; public events contain only reviewed summaries.
A failed check is FAIL; a missing prerequisite is BLOCKED/DEFER; an unexecuted check is NOT_RUN.
A PR opening is implementation progress, not merged acceptance or runtime DoV.
Next event: verify M02 diffs and ignore behavior, open the three PRs, then recheck acceptance.

## Reconciliation event: current main supersedes stale branches

Main now contains receipt guards on 3/3 repos and 4/4 scoped paths. DOCX bootstrap is already removed;
preserve that removal. The earlier starting counts apply only to stale receipt-policy branches.
Current main commits inspected: ABACUS 36d636090e90a806056baed71615318cf21986e9;
CODEX cfd687d67596cab791da4c11fe263653451e78ec;
DOCX 6531500e87cd684491c18ad511bd2cd022bbad29.
PRs: ABACUS #1127, CODEX #631, DOCX #49. These clarify policy and consolidate execution;
they do not earn duplicate credit for already-merged guards. Preserve all newer main work.
Next action: inspect newer MIP manifests, acceptance summaries and runtime receipts before selecting
M03-M11 work. Their current execution maturity has not been assessed in this pulse.
