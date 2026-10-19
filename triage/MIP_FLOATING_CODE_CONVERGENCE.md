# CODE PURPLE / MIP V3: evolutionary floating-code convergence

Date: 2026-10-19. Status: advisory, no admission authority.

Owner: ABACUS source governance. Companion process:
[Canonical MIP SIPOC-DAG](../docs/ci/MIP_SIPOC_DAG.md).

Historical W46: 9,430 / 28,014 covered; 18,584 missing.
The W46 measured scope has 114 of 223 zero-covered paths.
These are historical observations, NOT V3 functional gain.
W104 path hints do not prove semantic orphanhood.

## 0. First RED: admission and provenance

GitHub PRs #2320 and #2321 were observed merged on 2026-10-19.
Their prior descriptions declared MERGE_ADMISSION = HOLD.
On #2321, the changed-document validation workflow was red
with 17 MD013 line-length findings. The previous description
did not establish actual protected admission.

A merge event is not an admission receipt. Trace effective rules,
required status contexts, security, independent eligible review,
last-push review, unresolved threads, and negative RED canary.
Only an authorized administrator can repair policy.
Keep current and historical SHA evidence separate.

## 1. Define, Measure and resource-bound MIP charter

Goal: increase verified exercised capability on retained code.
Co-goals: resolve unknown source ownership; remove real bottlenecks;
reduce runner-hours and wall time; preserve user-facing behavior.
Optimize real improvement per constrained resource, not job volume.

Measure on an identical eligible opportunity population:
covered statement count, eligible statements, covered branches,
eligible branches, CI instrumentation and source cohort fingerprint.
A changed population or source deletion is a STRUCTURAL DELTA,
never an automatically earned functional coverage gain.

Freeze on each native observation: repository, exact source SHA,
run ID, attempt, job ID, artifact ID and raw SHA256, OS, Python,
dependency lock, test selection, UTC timestamps and source owner.
Unknown fields must remain null; never infer a zero from absence.

## 2. Classify each discovered path (F01-F07 plus UNKNOWN)

- F01: active and uncovered; prioritize behavior and fault tests.
- F02: floating valuable capability; bridge to a real consumer.
- F03: dormant subsystem; prove an intended orchestrator path.
- F04: cross-repo utility; test and register federation contracts.
- F05: possible duplicate; differential and side-effect comparison.
- F06: obsolete candidate; removal only after search and approval.
- F07: unsafe or unstable; isolate and sandbox.
- UNKNOWN: absent semantic evidence; do not silently call orphan.

Evidence ladder: M0 path hint; M1 static graph;
M2 safe executed smoke; M3 real consumer/differential result;
M4 approved reversible disposition; M5 independently verified.
File-name or directory similarities never prove dead code.
An absent static import does not exclude a dynamic or external user.

## 3. Directed relationships, SIPOC and reverse pressure

Reuse the canonical SIPOC in docs/ci/MIP_SIPOC_DAG.md.
Graph node types: file, symbol, caller, registry, CI/CLI entry,
workflow, dependency, producer, artifact, consumer, contract,
test, owner, source SHA and receipt.

Edge types:
- HARD_PRECEDES (verified blocker -> dependent)
- DECLARED_LINK (not proof of execution)
- STATIC_IMPORT, DYNAMIC_OBSERVED, ARTIFACT_CONSUMER
- CONTRACT_REQUIRES, CROSS_REPO_CONSUMER
- INFERRED_HYPOTHESIS (never silently promoted to hard)
- NEGATIVE_SEARCH (bounded evidence, not proof of absence)

Record direction explicitly. A -> B means B cannot be completed
before A if the edge is HARD_PRECEDES. Requirements and their
dependent outputs are reverse-traced from release gates to roots.
Graph cycles, dangling nodes and contradictory authorities are RED.

A controlling release gate exerts reverse pressure on its verified
upstream prerequisites. Distinguish:
- Immediate unlock: action is the last missing prerequisite.
- Partial unlock: action removes one of several blockers.
- Downstream leverage: action benefits more than one distinct gate.
Do not double-count a shared gate under multiple ancestors.
Never let a soft hypothesis override a hard dependency.

## 4. Invest in discriminating experiments, not maximum testing

Incubator order:
S0 provenance and environment isolation;
S1 no-side-effect import/smoke;
S2 valid/invalid contract tests;
S3 negative, reverse, metamorphic and fault tests;
S4 differential behavior for F05 overlap;
S5 executable consumer/producer integration;
S6 owner-reviewed disposition and rollback proof.

Stop early if direct action is unsafe, redundant or lower-value
than closing an evidenced root. Do not require expensive stress
tests for simple data-only assets without a justified failure mode.
PRUNE requires owner approval, negative-dependency searches,
isolated removal test and cross-repo consumer check.
SNIP extracts unique capability before retiring an obsolete shell.
No deletion is rewarded as testing improvement.

## 5. Choose a direction: blocker, BT, or experiment

FIRST filter by evidence, safety, authority, hard dependencies,
disjoint file leases and bounded runner capacity.
Only independent ready tasks enter any discretionary ranking.

Next evaluate counterfactual gate closure on each candidate:
How many distinct required sinks become satisfiable if this task
passes? Use a reverse dependency pass for immediate closure and
for partial unlocks. Verify scope and estimated time to proof.

Bradley-Terry ranks observed pairwise preference/outcome only.
It does NOT learn task priority from topological precedence.
No native connected pairwise network => BT_NOT_IDENTIFIABLE.
Use frozen prior observations and a declared outcome metric,
e.g. accepted root closures per bounded engineer/runner hour.
Do not manufacture wins from heuristic weights or projected gain.
Complete separation, disconnected graph, confounding and
uncontrolled context block unqualified BT comparisons.
Prefer the existing gg_MATH provider for mature inference.

Use bounded exploration only where the expected information
can alter a downstream disposition or priority decision.
A high missing-line count is an opportunity CAP, not expected gain.
An unknown cost is not free; do not divide by an invented hour.
Preserve nondominated alternatives rather than overfit one score.

## 6. Telemetry: three clocks and an immutable N+2 ledger

Track separately:
- State clock: ordered pulse N, N+1 and N+2.
- Wall clock: queue, execution, review and elapsed seconds.
- Version clock: exact source HEAD, test tree and receipt identity.

A pulse is an attempted source/evidence change with a new receipt.
Repeated polling is an observation of the same pulse, not N+1.
Attempted waves and accepted engineering waves are separate clocks.
An independent governed release decision is a third boundary.

Before observing N+1, seal forecasts for N+1 and N+2:
prediction issue time, model revision, input exact head,
expected outcome and credible uncertainty class.
When actual N+1 arrives, score errors on like-for-like units;
do NOT retroactively edit the N+1 forecast.
Then predict N+2 and N+3 from a versioned updated estimator.

Priority metrics:
- Covered / eligible on matched source and instrumentation.
- New executed behavioral opportunities; branch/statement split.
- Incubator dispositions and unresolved candidate cohort.
- Verified consumer edge penetration and first-red roots resolved.
- Runner p50/p95 queue, runtime, overhead and receipt yield.
- Wall-clock critical path, source-owner contention and idle time.
- Forecast MAE, interval hit rate and priority ranking accuracy.
- Denominator inflation/deflation and source removal separately.

Temporal caveat: a few dependent workflows are not independent
replicates. p95 of tiny samples is descriptive, not stable tail
performance. Validate assumptions before PCA or BT fitting.

## 7. Disjoint workers, DAG scheduler and admission firewall

Reuse, do not replace:
- scripts/cbd_recurse_fanout_w48.py (bounded DAG, path leases)
- MIP/EVIDENCE_TO_ADMISSION_OBSERVATORY/elastic_wave_governor.py
- runtime/execution/dependency_spine_readonly_selector.py
- tools/triage/mip_pulse_rollup.py (legacy descriptive telemetry)

V3 workers are disjoint source-owner BRANCHES, not concurrent
writers on main. Separate jobs for governance first-red,
graph census, duplicated agents, focused coverage, federation,
telemetry and learned scheduling. Keep overlapping fixtures with
the designated owner and require a negotiated dependency edge.

Do not dispatch runners or merge from advisory ranking.
Admission requires fresh exact-head native CI, security and
A10 checks, effective protection, eligible independent review,
all required status contexts and thread resolution.
Merely observing a merge never makes these gates PASS.

## 8. Stop, pivot and recursive convergence

Run bounded source-changing pulses and observe terminal receipts.
Three consecutive zero-gain transitions require FOUR independent,
terminal, comparable pulses. A repeated SHA or rerun alone is
not a source-changing pulse.

- FAILURE: negative covered delta, security RED or gate regression.
- REBASELINE: source population / instrumentation / tool drift.
- BLOCKED: no actionable ready task; seek the controlling root.
- LOCAL_TARGET: proven source-specific target with tests complete.
- LOCAL_PLATEAU: comparable no-gain pulses; pivot source family.
- CONTINUE: at least one high-value ready evidence-backed action.
- GLOBAL_DONE: separately established engineering AND governance.

Never call a plateau global convergence. Stop a marginal
experiment when its expected bounded benefit does not justify
its measurement, compute, review and opportunity costs.
Do not continue on the same failed exact SHA without source repair.

## 9. Resource budget and falsifiable N+2 contract

Per wave reserve bounded capacity for:
P0 security/governance, P1 dependency-first RED roots,
P2 highest-yield behavioral tests, P3 exploration/BT calibration.
Use capacity only when workers, queues and independent owner
availability are measured. Excess demand remains queued.

For each candidate, store:
unique task ID, source-owner lease, hard prerequisites,
expected gain interval or UNKNOWN, runner-hour interval,
reverse sink IDs, first-red fingerprint, test hypothesis,
rollback, verification criteria and projected unlock class.

To compare policies, freeze a candidate cohort and record which
would be selected by dependency-first, BT, reverse pressure and
simple coverage-size ranking before observing outcomes.
Score realised closures per cost and error retrospectively;
do not claim one policy superior from synthetic examples.

Expected next waves:
- N+1: repair Markdown first RED; mature evidence joins.
- N+2: compare graph/consumer findings, exercise focused tests.
- N+3: evaluate disjoint returns and prioritize actual bottleneck.
These are forecasts, NOT observed passes or authorizations.

## 10. Release and evidence boundary

The 12-gate JADE/B&B point-release readiness assessment is
separate from ABACUS MIP local tests. A partial MIP success may
supply evidence to a gate but never substitutes for all gates.

MERGE_ADMISSION = HOLD; authority_transfer = false;
formal_coverage_credit = false until independently qualified.
