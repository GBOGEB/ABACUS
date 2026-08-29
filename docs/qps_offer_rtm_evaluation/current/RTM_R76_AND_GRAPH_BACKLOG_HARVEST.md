# QPS Wave 2G — exact-v24 R76 + RTM-197 graph backlog harvest

Status: **OWNER DISPOSITION / EVIDENCE RECOVERY — NO REQUIREMENT CLOSURE**

## 1. Exact-v24 frontier — RTM-493 / R76

RTM-493 is the acceptance-test-programme control requirement under §4.13.1. It requires each acceptance test programme to contain, at minimum, the test purpose/list, participants and logistics, equipment/tools/instrumentation/computing devices, environmental conditions, consumables/utilities, personnel qualifications, safety/permits/emergency/stop/hazard controls, measured parameters with targets and limits, instrument accuracy, measurement/calculation methodology, test setups/methods, and reporting/transmittal requirements.

ALAT returns broad `Compliant` evidence for the detailed programme content but proposes changing `Each acceptance test programme shall, at minimum, contain:` to `shall contain:`.

Owner state: **D_CL / PE — R76 INDIVIDUALLY GOVERNED.**

Owner disposition:
- preserve `at minimum` as the contractual floor; deletion is not accepted by wording substitution;
- bind every FAT/SAT programme to a requirement→test→parameter→instrument→accuracy→method→acceptance-limit→record crosswalk;
- require explicit abnormal/stop criteria and safety arrangements;
- calculations may replace direct measurement only where the programme identifies the method, assumptions, uncertainty and acceptance basis;
- returned `Compliant` statements remain positive evidence, not test acceptance or requirement closure.

Dependency multiplication: RTM-493 is the acceptance-control parent for the quantitative and verification gaps already identified in the WCS cleanliness chain (including RTM-151/166/167/172/174/176/178/186/188/192) and other FAT/SAT-governed requirements. This is a derived verification dependency, not a new contractual edge.

Contiguous exact-v24 frontier therefore advances **R75 → R76**. RTM-186 at R77 has already been individually governed by Wave 2F, so the next selector reconciliation should test whether R78 is now the first unresolved exact-v24 row; do not assume it without exact metadata.

## 2. RTM-197 graph backlog — cheap evidence harvest

The 11 previously evidence-recovery nodes were:

- RTM-236..238;
- RTM-249..251;
- RTM-263..267.

Current comparison evidence is sufficient to triage all 11 without inventing compliance.

### 2.1 WSH configuration — RTM-236..238

| RTM | Returned evidence | Owner state / disposition |
|---|---|---|
| RTM-236 | ALAT provides information/positive evidence for the WSH configuration requirement; LKT exception-only row is silent. | **PE.** Bind selected WSH configuration and scope boundary to controlled design/BOM; LKT silence is not compliance. |
| RTM-237 | ALAT states compliance with FixedScope→FullScope extensibility by adding helium storage vessels only; LKT silent. | **PE.** Require expansion interface/capacity/layout evidence showing no other plant modification is needed. |
| RTM-238 | ALAT states compliance with FixedScope obligations; LKT separately records an explicit deviation against RTM-238: no vessel inner-surface treatment, citing outgassing/helium-contamination concerns with named treatments. | **D_CL / EQ_REQUIRED.** Separate the broad ALAT positive evidence from LKT's row-specific material deviation. Owner baseline remains authoritative; require material/surface-condition, corrosion/cleanliness/outgassing and helium-purity equivalence evidence before accepting omission/substitution. |

### 2.2 Conditional LN2 storage — RTM-249..251

ALAT marks all three requirements `Not applicable` because the QSN obligation is conditional on implementation of LN2 precooling. LKT exception-only evidence is silent.

| RTM | Owner state / disposition |
|---|---|
| RTM-249 | **APPLICABILITY_CONDITIONAL.** If LN2 precooling is implemented, Contractor supply of QSN activates. Record the governed design decision; `N/A` is valid only while the trigger remains false. |
| RTM-250 | **APPLICABILITY_CONDITIONAL.** QSN sizing and §4.2.5 storage capacity activate with LN2 precooling. Preserve sizing evidence requirement if triggered. |
| RTM-251 | **APPLICABILITY_CONDITIONAL.** Minimum QSN equipment floor—tank(s), vaporizers/heaters where required, process lines/valves, I&C, safety/pressure protection, filling interfaces, supports/ancillaries—activates with LN2 precooling. |

No closure is claimed: these are governed conditional-applicability states, not proof that the project will never use LN2 precooling.

### 2.3 External helium withdrawal/recovery — RTM-263..267

| RTM | Returned evidence | Owner state / disposition |
|---|---|---|
| RTM-263 | ALAT generally compliant but refers supplied elements to technical proposal. LKT asks for WGR-MAC clarification and allocates offgas purification to Owner scope while warm-up remains Contractor scope. | **CL / INTERFACE_BINDING.** Require itemised Dewar Filling Station/WGR-MAC scope and GHe return boundary; resolve acronym/scope without deleting Contractor warm-up/interface obligations. |
| RTM-264 | ALAT states compliance with serving External Dewar Users from installed §4.2.4 capacity. LKT repeats WGR-MAC scope clarification. | **PE_CL.** Bind dewar-user duty to controlled cooling-capacity/load cases and interface scope. |
| RTM-265 | ALAT will provide no equipment beyond its proposal and no overdesign for undefined external disturbances; later HAZOP additions are proposed as changes. LKT repeats interface clarification. | **D_MATERIAL.** Preserve QPS integrity/stability/purity protection objective. Require disturbance envelope, protection functions and HAZOP-driven design basis; lack of bid-stage definition does not transfer all protection risk to Owner/change order. |
| RTM-266 | ALAT compliant with Dewar Filling Station/G20 location in Coldbox Room. LKT repeats WGR-MAC clarification. | **PE_CL.** Bind physical location plus warm-return/purification interface routing. |
| RTM-267 | ALAT deletes `at minimum`, limits filling-capacity substantiation to two cases, refuses one required calculation as not understood, declines availability/operational-stability RAMI calculation for cost reasons, and excludes mobile-dewar impurity. LKT provides interface clarification only. | **D_MATERIAL / MULTI-GAP.** Preserve full Engineering File substantiation floor. Require all contractually relevant operating/transient cases, helium-demand/load calculation, availability/stability/RAMI effect, impurity/disturbance basis and explicit clarification of the misunderstood requirement. Cost is not equivalence. |

## 3. Backlog multiplication result

The previous **11 `DEPENDENCY_COVERED_PENDING_EVIDENCE_RECOVERY` nodes are now 11/11 individually triaged** from available evidence:

- positive evidence: RTM-236, 237;
- material/clarification/equivalence: RTM-238;
- conditional applicability: RTM-249..251;
- external-user interface/evidence/deviation: RTM-263..267.

This removes the original RTM-197 depth-2 evidence-recovery backlog as a generic queue. Any remaining work is now explicit evidence/action per row rather than `evidence recovery unknown`.

## 4. Immediate next

1. Exact-v24 selector reconciliation after R76, recognising R77/RTM-186 is already governed; identify the first unresolved exact row at or after R78.
2. Graph-expand that seed bidirectionally.
3. Convert RTM-493 into the common FAT/SAT acceptance-evidence matrix so every material requirement gap has a test/measurement/record route.
4. Reconcile live JSON/HTML to include Waves 2D–2G and remove stale embedded counters.

## Control

Contract/Addendum II and canonical 722/50 RTM/OFFER projection remain authoritative. Returned bidder status is evidence only. `N/A` is conditional applicability, not deletion. Family/interface clarification cannot rewrite a requirement. Derived verification dependencies are labelled as derived. No requirement closure is claimed. Accepted-release HOLD remains unchanged and independent.
