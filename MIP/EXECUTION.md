<!-- markdownlint-disable MD013 -->

# MIP Controlled Execution Register

Status date: 2026-09-12. Scope: this rollout; other sessions are not assumed synchronized.
Canonical source for this wave: ABACUS/MIP/EXECUTION.md. CODEX and DOCX link here.
This register separates the closed receipt/self-index tranche from broader MIP work that remains open.

## Mission and acceptance

Modernize, Innovate, Perpetuate across ABACUS, CODEX, DOCX_RTM_Automation and
ABACUS/integration/codespace_jyperter. Separate CODESPACE/DOCX repo identities remain unconfirmed.
Three repositories, four surfaces; the nested surface is not a fourth repository.
Private reviewed evidence can support DoV; public raw receipt publication is not required.
Child/project disposition authority stays with main triage; this register cannot promote it.

The fixed medium-term receipt-protection + exact-SHA self-index tranche is closed at 8/8 PASS.
Canonical sanitized acceptance: `MIP/N2_CROSS_REPO_ACCEPTANCE_20260912.json`.
This closes only that fixed tranche. Broader MIP/DOW/KEB/TRIAGE/global DoV remains WITHHELD.

## Ordered action queue

Status vocabulary: DONE, IN_PROGRESS, READY, BLOCKED, PLANNED, CONTROL.
Owner entries below are responsibility roles, not claims of spawned agents.

| ID | Priority | Action / location | Dependency | Owner / resource | State | Exit evidence |
| --- | --- | --- | --- | --- | --- | --- |
| M01 | P0 | Reconcile receipt branches in all 3 repos | none | Coordinator / GitHub reads | DONE | Receipt-policy state reconciled without losing newer main work |
| M02 | P0 | Reconcile guards and private evidence acceptance | M01 | Implementer / contents API, git | DONE | N1 protection merged in ABACUS #1125, CODEX #629, DOCX #47 |
| M03 | P1 | Execute exact-SHA self-index across 4 scoped surfaces | M02 | Repo maintainers / GitHub Actions, Python stdlib | CONTROL | Four scoped surfaces proved exact-SHA repeatability; fixed G1-G8 tranche = 8/8 PASS |
| M04 | P1 | Execute broader debug/LDAB and Docker/runner/MCP probes | M03 | Technical lead / existing probes and declared environments | PLANNED | Process executes >0 steps; exit code, environment and results bound to commit |
| M05 | P1 | Resolve first real failure or missing dependency; repeat | M04 | Implementer / smallest affected module | PLANNED | Targeted fix passes and independent checkout repeats |
| M06 | P1 | Prove one reusable capability, then implant in another repo | M03; selected capability passes M04 | Skill engineer / existing code, skill-creator | IN_PROGRESS | ABACUS shareable self-index skill proved; second-repo implantation remains separate scope |
| M07 | P2 | Add bounded health remediation | M04, M05 | Technical lead / health code and rollback | IN_PROGRESS | ABACUS controlled health/self-heal proof exists; wider implementation/rollback coverage remains separate scope |
| M08 | P1 | Evaluate further component CONTROL promotion | Relevant evidence | Reviewer / evidence ledger | READY | Promote only individually accepted components with owner, cadence, drift and re-entry rules |
| M09 | P2 | Refresh measured priority and residual backlog | each completed pulse | Analyst / DMAIC, BT; PCA only with adequate data | PLANNED | Ranked gaps with feature provenance and uncertainty |
| M10 | P2 | Federate summaries through existing DOW/KEB/child route | Verified payload and existing contract discovery | Integration lead / existing adapters | PLANNED | Consumer validates payload; child records ACCEPT/REJECT/DEFER |
| M11 | P3 | Expand repo coverage and agent orchestration | M08, M09; capacity available | Coordinator / verified identities and existing orchestration | PLANNED | New scope denominator, bounded workers and same acceptance gates |

M04-M11 are not retroactive gates on the closed 8/8 tranche. Any new denominator must be versioned explicitly.

## Fixed tranche closure

Closed scope: `mip_dov_v1_receipt_protection_and_self_index`.

- G1-G8: PASS, 8/8.
- Repositories: ABACUS, CODEX, DOCX_RTM_Automation.
- Surfaces: 4/4, including ABACUS/integration/codespace_jyperter.
- ABACUS fresh producer + downstream consumer proof: run `34712556105`, exact proof head `e836930229ebeb95f028c066e287b4ba6775ea80`.
- CODEX repaired self-index proof: run `34712316007`, proof head `215f367bba12022d4dd19bcf2345a08a8c34c8c8`, repair #662 merged.
- DOCX repaired self-index proof: run `34712361991`, proof head `de8a62af406ec72d0883ce41fc4b988f51587e8c`, repair #52 merged.
- Cross-repo sanitized acceptance: ABACUS #1158, merge `700505790ee0cfff8a7f62f5ad7285e96cf3072d`.
- Raw receipt retention: transient runner only.
- Broader/global DoV: WITHHELD.

Control rule: retain regression monitoring and re-enter IMPROVE only after an observed regression,
contract drift, changed requirement or material new opportunity. Do not extend G1-G8 after closure.

## Work structure and resources

Shared functional sequence: index -> assess -> evidence -> decision -> bounded action -> verify -> report.
ABACUS owns this wave's coordination register and nested-surface roll-up.
CODEX is a candidate implementation home for broader debug/health capabilities.
DOCX uses existing document/RTM automation and representative fixtures.
Use separate worktrees/environments and keep generated private evidence outside tracked source by default.
Do not publish local path census, dirty-state details or environment diagnostics.
Prefer existing scripts, modules and adapters; no new MCP service or agent framework is required merely to preserve the closed tranche.

## Controlled acceleration

Default WIP cap remains 2 execution lanes plus 1 verification lane for broader scope.
Blocked work releases execution capacity but retains its ID, reason, unblock condition and owner.
Reconcile heads before each mutation and serialize writes to the same branch.
Each pulse must retire a blocker, add verified capability, reduce uncertainty, or explicitly park a low-value item.
Increase capacity only after repeated accepted pulses and available reviewer/runner capacity.

## Horizons

| Gate | Outcome | Current disposition |
| --- | --- | --- |
| N+1 | Protection/policy baseline | DONE |
| Fixed medium-term G1-G8 | Exact-SHA four-surface proof + sanitized acceptance | CONTROL, 8/8 PASS |
| N+5 | Broader runtime/debug probes and first additional CONTROL candidate | Separate next scope |
| N+10 | Second-repo implantation, bounded remediation, validated federation | Separate next scope |
| N+50 | Desired control coverage with only justified residual improvement | Expand only against measured unmet need |

Horizons count bounded pulses, not dates or promised completions. New work must not silently alter the closed denominator.


### G3A notation clarification (17 October 2026; candidate)

The historical N+1/N+5/N+10 horizons above retain their original
**bounded-pulse** interpretation; they are not rewritten or retrospectively
claimed as three accepted source changes.

For new requests that explicitly require one uninterrupted N→N+3 mission,
use **G3A (Governed Three-Advance Mission)** with a separate `g3a_n`
accepted-checkpoint index. `3W` means three implementation waves,
`3MP` means three DMAIC/MIP feedback pulses, and neither automatically
increments `g3a_n`. The repository-local control method, exact-head input
manifest, early-stop rule, source-bound receipts and SIPOC/DAG are defined in
[`docs/ci/G3A_GOVERNED_THREE_ADVANCE.md`](../docs/ci/G3A_GOVERNED_THREE_ADVANCE.md).
Global meaning remains CODEX-owned, proposed in CODEX draft PR #1059.
Existing source-owner, safety, review, admission and child-domain gates remain
unchanged.


## IMPROVE to CONTROL

Promote individual components, never the whole mesh by inference.
Required: defined acceptance tests pass; representative repeatability; no unresolved critical defect;
recovery/rollback evidence where applicable; named owner, monitoring cadence and re-entry trigger.
A plateau is not proof of MAX or Six Sigma capability. Investigate measurement limits and constraints.
CONTROL still runs regression monitoring and periodic audits; it is not abandonment.

## Metrics and priority

For the closed tranche:

- fixed DoV: 8/8 PASS;
- exact-SHA scoped surface coverage: 4/4;
- open MIP PRs across ABACUS/CODEX/DOCX at final cleanup: 0;
- remaining ABACUS `mip/*` refs: deletion-only pointers recorded in `MIP/FINAL_CLEANUP_20260912.json`;
- broader/global DoV: WITHHELD;
- CONTROL promotion: receipt-protection + exact-SHA self-index tranche only.

For broader work, publish numerator, denominator, commit/time scope and evidence freshness for every metric.
Use transparent BT-style risk/impact/dependency/cost ranking first; record manual weights as manual.
Formal PCA requires a standardized measured matrix, sample adequacy and interpretable loadings.
PC1 captures variance, not automatically value; do not label expert guesses as telemetry.

## Pulse event protocol

Record append-only events with pulse_id, task_id, repo, component, observed_at, source_commit,
prior_state, next_state, check, outcome, evidence_reference, blocker, next_action and reviewer.
Keep detailed receipts private; public events contain only reviewed summaries.
A failed check is FAIL; a missing prerequisite is BLOCKED/DEFER; an unexecuted check is NOT_RUN.
A PR opening is implementation progress, not merged acceptance or runtime DoV.

## Final reconciliation event

The fixed tranche is complete and moved to CONTROL. No open MIP PR remains in ABACUS, CODEX or DOCX.
CODEX and DOCX have no remaining `mip/*` branch refs from this work.
ABACUS retains three historical `mip/*` refs because the available connector cannot delete Git refs:

1. `mip/n2-sanitize-external-output-20260912` — proof-only marker, closed #1157, SAFE_DELETE.
2. `mip/n2-shareable-self-index-skill-20260912` — closed #1156 as SUPERSEDED_WITH_CONTENT_PRESERVED, SAFE_DELETE.
3. `mip/w105-modernize-cicd-runtime` — 0 commits ahead of main at final comparison, SAFE_DELETE.

Do not merge or revive these branches. Delete the refs when a branch-delete-capable interface is available.
No implementation or evidence is lost by their deletion; canonical accepted state is on `main` and in merged PR/run history.

## G3A N15 mathematical consumer (2026-10-17; candidate)

**M09/ANALYZE implementation:** Versioned source-bound input at
[`MIP/receipts/g3a_n14_gg_math_convergence_input.json`](receipts/g3a_n14_gg_math_convergence_input.json)
binds N13=115/446 and N14=200/446, same production source blobs,
Python 3.12/coverage.py 7.16.2 and native run/attempt identities to the
merged gg_MATH math provider source `961eadf43f19b6bc0ef11fdd640c30ab59f74f41`.
[`MIP/statistics/gg_math_g3a_consumer.py`](statistics/gg_math_g3a_consumer.py)
performs strict structural/source checks. Pinned provider execution is optional
and **not claimed** until an exact local provider checkout and receipt exist.

**Do not confuse qualifications:** N13→N14 is +85 distinct reached arcs
and 0 lost on 446; it is not a stability demonstration. PCA has n=2,p=4,
insufficient for an interpretable temporal fit; BT has zero observed pair
outcomes; Six Sigma has no representative field CTQ/opportunity sample.
Unchanged Phase 8 and orchestrator under N14 were **not targeted**.
N15 Phase8 test flight [#2145](https://github.com/GBOGEB/ABACUS/pull/2145)
is source-frozen and **PENDING NATIVE** on its first attempt; no fabricated N15 metric.
Governance first-red repair [#2144](https://github.com/GBOGEB/ABACUS/pull/2144)
must itself obtain terminal first-red clearance; not a waiver.
A review-only Plotly candidate lives at `docs/ci/g3a-control/index.html`;
the full offline HTML and its browser QA remain in the lossless session artifact,
not implicitly a GitHub Pages deployment.

**Authority:** gg_MATH = mathematical method provider, ABACUS = local native
evidence/quality owner, CODEX/KEB = semantic consumer authority,
QPS/Mission Control = separate operational consumers. No automatic federation
promotion, admission, root closure, CI waiver or source-owner transfer.
Do not modify the historical closed MIP 8/8 denominator; this is a distinct
candidate scope. Re-enter MIP/CONTROL assessment only after required
comparable native temporal samples, dedicated owner review and no blocker.
