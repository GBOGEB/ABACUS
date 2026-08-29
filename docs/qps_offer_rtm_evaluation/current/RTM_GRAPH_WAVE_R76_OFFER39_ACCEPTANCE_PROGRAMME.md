# QPS Wave 2G — exact-v24 R76/R78 graph-expanded evidence harvest

Status: **EXACT-RANK ENTRY + CANONICAL/DERIVED FAMILY EXPANSION — NO REQUIREMENT CLOSURE**

## Ranked entries

- **RTM-493 = R76** — canonical OFFER-39 acceptance-programme family RTM-491..495.
- **RTM-186 = R77** — already individually governed by Wave 2F adjacency.
- **RTM-264 = R78** — External Helium Withdrawal and Recovery, §4.4.8; enters a previously evidence-poor RTM-197 graph neighbourhood and expands engineering review to RTM-263..267.

BT/PCA chooses entry points. Canonical OFFER↔RTM edges and explicit engineering dependencies expand review. Derived adjacency does not create contract authority or a new canonical OFFER edge.

## Owner acceptance matrix — OFFER-39 / RTM-491..495

| RTM | Owner requirement/function | Returned evidence | Owner disposition |
|---|---|---|---|
| RTM-491 | Contractor retains responsibility for planning/executing acceptance-test activities. | ALAT proposes SCK CEN support for site acceptance; LKT limits approval transfer. | **D_CL / RESPONSIBILITY BOUNDARY.** SCK CEN support does not transfer Contractor responsibility. Require RACI for preparation, execution, witnessing, approval, NCR/retest and evidence retention. |
| RTM-492 | Programme submitted to SCK CEN for approval before corresponding test. | ALAT bases programme on proposed SAT. LKT says comprehensive FAT programme will not be provided because of procurement variability. | **D_MATERIAL / APPROVAL-GATE ISSUE.** Preserve pre-test SCK CEN approval; procurement variability is handled by controlled revision, not deletion of the gate. |
| RTM-493 | Programme contains, **at minimum**, contractual general, safety, measurement, method, acceptance and reporting content. | ALAT proposes deleting `at minimum`; LKT says comprehensive programme will not be provided. | **D_CL_MATERIAL — exact-v24 R76.** Preserve minimum content floor and require clause-by-clause programme template. |
| RTM-494 | Programme defines execution/record/acceptance controls. | ALAT has no flagged row exception; LKT carries family deviations. | **PE_LKT_D / FAMILY-TO-ROW RECONCILIATION.** Bind positive evidence to actual template; require row-specific LKT mapping. |
| RTM-495 | Contractor provides/makes available contractually allocated test resources. | ALAT transfers utilities/consumables and invCOP electrical measurement to SCK CEN. | **D_MATERIAL / SUPPLY-BOUNDARY MATRIX.** Freeze contractual allocation; define provider, specification, calibration, date, interface and contingency. |

## R78 family — External Helium Withdrawal and Recovery / RTM-263..267

These five were part of the RTM-197 depth-2 graph's 11 evidence-recovery nodes. Direct comparison evidence is now sufficient for individual Owner disposition.

| RTM | Owner baseline | Returned evidence | Owner disposition |
|---|---|---|---|
| RTM-263 | QPS includes Dewar Filling Station for sporadic external LHe withdrawal and warm GHe return, including necessary withdrawal infrastructure and G20 recovery interfaces. | ALAT refers to its technical proposal for supplied elements. LKT asks for WGR-MAC clarification and assumes WGR-MAC/customer purification scope while warm-up of dewar offgas is Contractor scope. | **D_CL / INTERFACE-SCOPE RECONCILIATION.** Produce complete supply/interface matrix for dewar filling, warm return/G20 and WGR-MAC boundary. Clarification cannot remove necessary QPS infrastructure. |
| RTM-264 | QPS serves External Dewar Users using installed cooling capacity specified by §4.2.4. | ALAT marks row compliant. LKT's section clarification concerns WGR-MAC/customer scope rather than rejecting installed-capacity use. | **PE_LKT_CL — exact-v24 R78.** Retain installed-capacity boundary; require operating-envelope evidence showing when dewar service is permissible without degrading higher-priority QPS states. No closure from positive status alone. |
| RTM-265 | QPS protects integrity, operational stability and helium purity against disturbances from External LHe User systems. | ALAT states no additional equipment/overdesign, HAZOP-discovered operational components would be change, and no protection/analysis for dirty mobile-dewar helium. LKT carries WGR-MAC boundary clarification. | **D_MATERIAL / PROTECTION-AND-PURITY ISSUE.** Baseline requires protection, not merely allocation of responsibility to operator. Require disturbance envelope, contamination barriers/monitoring, isolation/interlock philosophy and HAZOP-to-design closure. |
| RTM-266 | Dewar Filling Station and G20 interface located in Coldbox Room. | ALAT compliant; LKT section clarification does not provide row-specific rejection. | **PE_LKT_CL / LOCATION-INTERFACE EVIDENCE.** Bind to controlled layout, P&ID/tags, access/maintainability and G20 interface definition. |
| RTM-267 | Contractor substantiates Dewar Filling Station design in Engineering File; **at minimum** includes required capacity, balances, consumption, QPS availability/stability, acceptance criteria, inventory and purity effects. | ALAT proposes deleting `at minimum`, limits capacity substantiation to two cases, declines LHe-consumption calculation because requirement was not understood, declines availability/stability analysis for cost reasons, and excludes mobile-dewar impurity. LKT carries section-level WGR-MAC clarification. | **D_MATERIAL / MULTI-AXIS SUBSTANTIATION GAP.** Preserve full minimum evidence floor. Require mass/energy balances across governing modes/transients, net and parasitic helium consumption, 2K-OP availability/stability impact, pressure/inventory/purity acceptance criteria and contamination assumptions. Cost or misunderstanding does not waive substantiation. |

## Multiplication and dependencies

The OFFER-39 family remains the acceptance-control envelope over detailed FAT/SAT evidence: approved programme, measurement chain, resources, execution, witnessing and records.

RTM-263..267 now create a second high-value dependency chain:

1. **RTM-264 → RTM-267:** installed-capacity service must be substantiated quantitatively, not only declared.
2. **RTM-265 → RTM-267:** disturbance/purity protection assumptions become explicit Engineering File acceptance cases.
3. **RTM-263/266 → RTM-267:** physical G20/WGR-MAC and Dewar Station interfaces become controlled model/P&ID/layout inputs.
4. **RTM-267 → RAMI + 2K-OP verification:** dewar filling impact on availability/stability must propagate to the reliability and acceptance-test evidence chain.
5. **RTM-267 → RTM-269..271:** downstream Dewar Filling Station capacity, helium-demand and no-adverse-impact requirements are a derived engineering continuation and should be harvested next if not already individually governed.

## Rank frontier

RTM-493 R76 is governed here; RTM-186 R77 was already governed; RTM-264 R78 is now individually governed. The contiguous exact-v24 reviewed frontier therefore advances through **R78**. No later rank is claimed without exact-v24 evidence.

## Evidence-recovery backlog

The RTM-197 graph evidence-recovery backlog shrinks from **11 to 6** because RTM-263..267 are now individually dispositioned.

Remaining:

- RTM-236..238;
- RTM-249..251.

These six remain evidence-recovery work, not compliance or closure.

## Control

Contract/Addendum II and canonical RTM remain authoritative. OFFER and bidder positions are evidence interfaces only. `Compliant`, `nothing on file`, clarification, cost, procurement variability, subvendor responsibility or Owner support do not modify the requirement. Derived dependencies are explicitly non-authoritative. No requirement is closed by this file. Accepted-release HOLD remains unchanged and independent.
