# QPS Wave 2G — exact-v24 R76 / OFFER-39 acceptance-programme family

Status: **EXACT-RANK ENTRY + CANONICAL FAMILY EXPANSION — NO REQUIREMENT CLOSURE**

## Ranked entry

- exact-v24 unresolved seed: **RTM-493 = R76**;
- canonical family: **OFFER-39 — FAT/SAT Testing Strategy & Procedures, §4.13.1**;
- direct family: **RTM-491..RTM-495**;
- selection rule: BT/PCA chooses RTM-493 as entry point; canonical OFFER↔RTM linkage expands the review to the complete acceptance-programme family.

OFFER-39 is a canonical edge. The downstream links from this family into detailed FAT/SAT requirements are derived engineering/verification dependencies and do not alter contract authority.

## Owner acceptance matrix

| RTM | Owner requirement/function | Returned evidence | Owner disposition |
|---|---|---|---|
| RTM-491 | Contractor retains responsibility for planning/executing acceptance-test activities under the contractual acceptance framework. | ALAT proposes SCK CEN support when needed for site acceptance. LKT family position says FAT detail will be outlined later and limits transfer of approval responsibility. | **D_CL / RESPONSIBILITY BOUNDARY.** SCK CEN support does not transfer Contractor responsibility. Require RACI for preparation, execution, witnessing, approval, NCR/retest and evidence retention. |
| RTM-492 | Each acceptance-test programme is submitted to SCK CEN for approval before the corresponding test. | ALAT says programme will be based on proposed SAT. LKT says comprehensive FAT programme will not be provided because of procurement variability and states only client acceptance is granted while test responsibility remains with Linde/subvendors. | **D_MATERIAL / APPROVAL-GATE ISSUE.** Preserve pre-test SCK CEN approval. Procurement variability may be handled by controlled programme revision, not deletion of the approval gate. Contractor/subvendor responsibility does not remove Owner approval rights. |
| RTM-493 | Each acceptance-test programme contains, **at minimum**, the contractual general, safety, measurement, test-method, acceptance and reporting content. | ALAT proposes deleting `at minimum` but otherwise marks the detailed content compliant. LKT family evidence says a comprehensive programme will not be provided and limits approval transfer. | **D_CL_MATERIAL — exact-v24 R76.** Preserve minimum content floor. Require a clause-by-clause acceptance-programme template covering purpose, test list, participants/logistics, equipment/utilities, personnel qualifications, safety/hazards, measured parameters, targets/limits, instrument accuracy, methodology/calculations, setups, sequence, acceptance/rejection, records and reporting. |
| RTM-494 | Acceptance programme defines the required execution/record/acceptance control content of §4.13.1. | ALAT has no flagged exception on this row. LKT carries the same family deviations concerning comprehensive programme and approval responsibility. | **PE_LKT_D / FAMILY-TO-ROW RECONCILIATION.** Bind ALAT positive evidence to the actual programme template. Require LKT to map its family deviation against each RTM-494 obligation rather than using one section-level exception as blanket disposition. |
| RTM-495 | Contractor provides/makes available testing equipment, tools, instrumentation, consumables/utilities and additional test equipment as contractually allocated. | ALAT transfers utilities/consumables and invCOP electrical measurement to SCK CEN. LKT family retains acceptance-programme deviations. | **D_MATERIAL / SUPPLY-BOUNDARY MATRIX.** Freeze contractual allocation, then create test-resource matrix: item, provider, specification/range/accuracy, calibration, availability date, interface and contingency. Any Owner-provided utility must be an explicit agreed interface, not silent scope transfer. |

## Verification multiplication

The acceptance-programme family is the control envelope over the already-reviewed detailed test evidence:

1. **RTM-492 → all FAT/SAT execution:** no governed acceptance test should begin without the required approved programme.
2. **RTM-493 → RTM-151/166/167/172/174/176:** oil-content claims require programme-defined sampling points, instruments, uncertainty, methods and acceptance limits.
3. **RTM-493 → RTM-178/179/180:** abnormal-event, guard-stage and shutdown logic require explicit test setup, expected response and acceptance evidence.
4. **RTM-493 → RTM-186/188:** dryer availability/redundancy/regeneration deviations require measurable RAM/performance acceptance cases.
5. **RTM-495 → invCOP and utility-dependent performance tests:** resource ownership cannot invalidate the measurement chain; electrical/utility measurement boundaries must be agreed and calibrated.
6. **RTM-491..495 → FAT/SAT RTM-496 onward:** these five requirements govern how the detailed FAT/SAT rows are prepared, approved, executed, witnessed, recorded and accepted.

## Rank frontier

RTM-493 R76 is now individually governed. RTM-186 R77 was already individually governed by engineering adjacency in Wave 2F. Therefore, subject to exact-v24 sequence confirmation that no other unresolved row occupies R77, the contiguous reviewed frontier can advance through **R77**. This file does not invent any rank beyond exact-v24 evidence.

## Backlog relation

This wave is evidence-rich and therefore does not consume the separate 11-node evidence-recovery backlog from the RTM-197 graph. Those remain:

- RTM-236..238;
- RTM-249..251;
- RTM-263..267.

Next execution should first confirm the exact-v24 R78 seed, then graph-expand it. In parallel, recover any of the 11 nodes where canonical/Contractor evidence can be obtained cheaply without interrupting the ranked evidence flow.

## Control

Contract/Addendum II and canonical RTM remain authoritative. OFFER-39 is a request/evidence interface, not requirement authority. Bidder `Compliant` is evidence, not closure. Procurement variability, cost, subvendor responsibility or Owner support do not silently modify acceptance obligations. No requirement is closed by this file. Accepted-release HOLD remains unchanged and independent.
