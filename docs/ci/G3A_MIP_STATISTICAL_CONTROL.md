# G3A MIP.CTRL.V1 — DMAIC / MIP statistical-control decision

**Evidence date: 2026-10-17. Governance state: HOLD.**
Parent lineage: N13 [#2133](https://github.com/GBOGEB/ABACUS/pull/2133), then native N14 [#2139](https://github.com/GBOGEB/ABACUS/pull/2139). This additive statistical note changes no production source or CI policy. It is advisory and cannot admit a merge.

## Verified, independently rejoined N13/N14 arcs

The same four Git production blobs and coverage.py **7.16.2** were instrumented in N13 run **39040416656** and N14 run **39046868554**, job **117437224320**, artifact **12106560662**. N14 completed **98/98 tests**. Actual executed-branch arc pairs were compared, not merely the percentages.

| Frozen source | N13 | N14 | Distinct new arcs | Lost arcs | Motion | Stability |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| `DMAIC_V3/debug_pipeline.py` | 17/116 | 94/116 | +77 | 0 | IMPROVING | NOT DEMONSTRATED (n=2) |
| `DMAIC_V3/phases/phase4_improve.py` | 45/134 | 53/134 | +8 | 0 | IMPROVING | NOT DEMONSTRATED (n=2) |
| `DMAIC_V3/phases/phase8_todo_management.py` | 30/118 | 30/118 | 0 | 0 | NOT TARGETED IN N14 | NOT ASSESSED |
| `cicd_github_orchestrator.py` | 23/78 | 23/78 | 0 | 0 | NOT TARGETED IN N14 | NOT ASSESSED |
| **Same-scope total** | **115/446** | **200/446** | **+85** | **0** | **IMPROVING** | **INSUFFICIENT INDEPENDENT SERIES** |

44.84% N14 coverage versus 25.78% N13 is **+19.06 percentage points** and reduces frozen four-module uncovered arcs from **331 to 246**. Twenty-two new N14 test methods correspond to **3.86 additional covered arcs per new method** descriptively, without causal attribution.

The separate CI governance **39046868436** FAILED `test_repository_workflows_are_classified_once` (`policy-and-inventory`). Therefore **MERGE_ADMISSION=HOLD**. It is an operational blocker, NOT evidence that four-module coverage plateaued.

## DMAIC / MIP / SIPOC

**DEFINE:** identify source blobs, denominator/eligible arc identity, time/pulse, exact SHA and test intent. **MEASURE:** bind native job/run/attempt, branch-arc union, test count, queue vs execution clocks, missingness and coverage version. **ANALYZE:** stratify targeted vs untargeted cohorts, first-red causal-owner hypotheses, actual gained/lost arcs, uncertainty and comparability. **IMPROVE:** smallest bounded source-owner cohort, negative/reverse/fault fixtures, first-red repair, repeat verified native evidence. **CONTROL:** promote elements only with repeated representative observations, owner, regression/re-entry control, governance and rollback proof.

MIP = **Modernize / Innovate / Perpetuate**. Its existing `MIP/EXECUTION.md` M09 controls measured priority and residual backlog; M08 governs component-level CONTROL. The historical fixed 8/8 MIP closure must not be widened or revoked by this independent four-module test opportunity. Federation into CODEX/QPS/DOW/KEB is **not** verified by this PR.

SIPOC: GitHub Actions/source owners (suppliers) -> exact SHA/blob and test receipts (inputs) -> scope/arc checks plus statistical readiness (process) -> typed decision ledger and owner blocker (outputs) -> MIP, DMAIC, Mission Control, safety/governance reviewers (consumers).

## Mathematics and state vector

For fixed, independently verified eligible arc universe `U` and executed arc sets `B_N`:
- Coverage `C_N = |B_N| / |U|`; residual `R_N = |U \\ B_N|`.
- True gain `G=|B_new \\ B_old|`; loss `L=|B_old \\ B_new|`; net `Δk=G-L`.
- Pulse velocity `v_N=(C_N-C_previous)/ΔN` only for same denominator/instrumentation and meaningful comparable pulse spacing.
- Weighted roll-up `Σcovered / Σeligible`, but only over **disjoint** scopes. Never average module percentages unweighted or confuse branch coverage with operational defects.
- Multiple reruns of an identical source/test cohort contribute **repeatability**, not independent improvement interventions. Missing/unobserved is NULL or NOT_MEASURED, not zero.

Typed status is NOT one green/red boolean:
1. `MOTION` = NO_TELEMETRY, BASELINED, OBSERVED_IMPROVEMENT, OBSERVED_REGRESSION, UNCHANGED_TARGETED, UNCHANGED_NOT_TARGETED.
2. `CONTROL` = NOT_ESTIMABLE, INSUFFICIENT_SERIES, CONTROL_CANDIDATE, NOT_DEMONSTRATED.
3. `GATE` = BLOCKED, UNBLOCKED_WITH_VERIFIED_RECEIPTS, UNKNOWN; `MERGE_ADMISSION` is independently HOLD until all required checks pass.
4. `PLATEAU` = NOT_ASSESSED, CENSORED_BY_BLOCKER, PRACTICAL_PLATEAU_CANDIDATE. `MAX` = NOT_ESTABLISHED until formal reachable-opportunity census, accepted constraints, and validated ceiling model.
5. `SIX_SIGMA` = NOT_ASSESSED_FROM_COVERAGE; field defect opportunities and stable representative process must be defined first.

Conservative readiness minimum for considering stability: **at least 6 independent comparable observations**, at least **4 targeted interventions**, at least **2 independent repeatability receipts**, no red blocker, and a 95% slope confidence interval wholly inside a *predeclared* practical equivalence band (proposed `±0.5 percentage points per pulse`), plus rolling MAD ≤0.5 pp. These are preliminary engineering thresholds requiring owner review, not Six Sigma certificates. OLS assumptions (independence, errors, autocorrelation, fixed population) must be checked.

A *practical plateau candidate* additionally needs last three **targeted** interventions showing negligible marginal benefit, measured effort, absence of blockers, and demonstrably considered residual opportunities. **An asymptotic maximum is not proved by a flat line:** model `C(N)=C∞-A exp(-k N)` only with enough independent interventions, held-out evidence, reachability constraints and predeclared cost/value. A failed governance gate makes observations potentially censored, NOT saturated.

## PCA / BT are conditional, not display decorations

**PCA** with N13 and N14 across four module metrics has `n=2`, `p=4` and centered covariance rank ≤1, so a claimed PC1 = 100% would be meaningless. Minimum exploratory readiness: `n >= max(10, 3p)` independent comparable observations, ≥2 standardized non-collinear measured features, variance and missingness audited, loadings published. Prior W79 PC1 does **not** describe this N13/N14 population.

**BT (Bradley–Terry)** pairwise priority model: `P(i>j)=exp(theta_i)/(exp(theta_i)+exp(theta_j))`. Zero native pairwise comparison receipts exist for this four-module cohort; therefore `BT_NOT_ESTIMABLE`. Require at least 12 provenance-bound independent pair judgments, strongly connected directed win graph and uncertainty review before any BT ranking. Until then report a **manual** risk/impact/dependency/cost score as such, not a fitted BT model.

## Six Sigma capability is not 44.84% branch coverage

A field defect opportunity is not a Python branch arc. A meaningful `DPMO=1,000,000*defects/opportunities` requires independent/representative exposure and process control; the commonly quoted shifted long-term Six Sigma convention is 3.4 DPMO. Even with zero defects, the one-sided Poisson 95% upper limit is approximately `-1,000,000*ln(0.05)/n`, requiring **at least 881,098 independently relevant zero-defect opportunities** for the upper bound to fall below 3.4 DPMO, before review of assumptions. It is not automatic certification, nor something inferred from 200/446 branches.

## Next governed wave and stop condition

**W15/P1:** repair `#2139` first-red governance classification + generated policy/inventory via the correct owner, preserving checks, then obtain a fresh exact-head CI receipt. **W15/P2:** test-only targeted Phase 8 branch cohort with explicit intervention flag. **W16/P3:** disjoint targeted CI/CD cohort, only if P2 succeeds and owner/reviewer/runner capacity permits. No federation fanout, waiver, auto-merge or global acceptance is credited.

Evidence handover remains **G3A-REPEAT/N14-WAVE1-PR2139@1446d78a6e93** with additive `MIP.CTRL.V1`; local executable analyzer and 22 static controls supplied in the self-contained session release ZIP.
