# QPS Wave 2H — clear final RTM-197 graph evidence backlog

Status: **BACKLOG EVIDENCE RECOVERY + OWNER TRIAGE — NO REQUIREMENT CLOSURE**

## Scope

This wave clears the final six nodes left from the RTM-197 depth-2 graph expansion:

- RTM-236..238 — WSH configuration;
- RTM-249..251 — conditional LN2 storage (QSN).

These are not selected by new scalar BT rank. They are deliberately harvested now because keeping old evidence-recovery nodes open after adjacent families are governed would leave an artificial backlog.

## Owner dispositions

| RTM | Canonical Owner baseline | Returned evidence | Owner state / disposition |
|---|---|---|---|
| RTM-236 | Contractor supplies WSH in one of the contractually permitted configurations. | ALAT returns positive/information evidence across the configuration choices. LKT exception-only summary has no matching canonical row exception. | **PE / CONFIGURATION DECISION BINDING.** Require the selected WSH configuration to be explicitly frozen in the controlled design basis, with scope, vessel count, interfaces and expansion path. Positive offer evidence is not closure. |
| RTM-237 | WSH_FixedScope, if selected, remains extendable to WSH_FullScope by adding helium storage vessels only. | ALAT compliant; LKT exception-only lane silent. | **PE / FUTURE-EXPANSION EVIDENCE.** Bind spare connection provisions, isolation, structural/layout allowance, control/instrumentation scalability and capacity model showing vessel-only extension achieves FullScope. |
| RTM-238 | If WSH_FixedScope is selected, Contractor satisfies the listed FixedScope implementation obligations. | ALAT compliant. A separate LKT technical-compliance row is labelled `RTM-238` but describes **inner-surface treatment of a vessel**, which does not match the canonical RTM-238 WSH-FixedScope requirement text. | **SOURCE_IDENTITY_MISMATCH / DO NOT ASSIMILATE.** Do not map the LKT surface-treatment deviation onto canonical RTM-238 until source numbering/requirement identity is reconciled. Keep canonical RTM-238 positive-evidence review open and create a separate orphan-evidence reconciliation item for the LKT row. |
| RTM-249 | **If LN2 Precooling is implemented**, Contractor supplies QSN. | ALAT marks N/A. LKT exception-only lane silent. | **CONDITIONAL_APPLICABILITY_GATE.** Bidder `N/A` cannot decide applicability. The Owner design decision on LN2 precooling governs. If LN2 is selected, RTM-249 becomes mandatory; if formally excluded by governed design decision, record the applicability rationale and evidence. |
| RTM-250 | Contractor sizes QSN; capacity complies with the LN2 precooling requirement. | ALAT marks N/A. LKT silent. | **CONDITIONAL_APPLICABILITY_GATE / DESIGN EVIDENCE.** If LN2 is selected, require storage sizing basis, duty cycle, refill logistics, vaporisation demand, margin and interface conditions. `N/A` is not closure without the governing design decision. |
| RTM-251 | QSN includes, **at minimum**, the listed tanks, vaporizers/heaters where required, process lines/valves, instrumentation/control, safety/pressure protection, filling interfaces, supports and ancillary equipment. | ALAT marks all listed elements N/A. LKT silent. | **CONDITIONAL_APPLICABILITY_GATE / MINIMUM-SCOPE FLOOR.** If LN2 is selected, preserve every applicable minimum element and require a QSN P&ID/BOM/interface matrix. The conditional parent decision may deactivate the family; a Contractor cannot selectively delete the minimum content while claiming applicability. |

## Source-identity control discovered

The LKT exception register contains a row tagged `RTM-238` whose text concerns vessel inner-surface treatment and contamination/outgassing. The canonical RTM-238 in the governed 722-RTM projection concerns WSH_FixedScope implementation.

Therefore:

1. the LKT row is retained as **orphan/misaligned returned evidence**;
2. it is not used to score or disposition canonical RTM-238;
3. its true canonical target must be recovered from section/text matching before promotion;
4. this mismatch becomes a QA check for all future bidder-row imports: **ID match + section match + semantic text match** before assimilation.

This is a useful control improvement from backlog harvesting: the process now catches false-positive requirement linkage rather than merely importing bidder IDs.

## LN2 applicability control

RTM-249..251 demonstrate a second generic rule:

> `Not applicable` is a Contractor position, not an applicability authority.

For conditional requirements, the live state shall distinguish:

- `CONDITION_NOT_YET_DECIDED`;
- `APPLICABLE_OPEN`;
- `NOT_APPLICABLE_BY_GOVERNED_OWNER_DECISION`;
- `APPLICABLE_EVIDENCE_COMPLETE`;
- `CLOSED`.

Only the governed Owner/system design decision may move the requirement between applicable and not-applicable branches.

## Multiplication result

The original RTM-197 graph reached 49 unique RTMs. Its evidence-poor subset was 11. Wave 2G recovered RTM-263..267 (5), and this wave triages RTM-236..238 and RTM-249..251 (6).

**Evidence-recovery backlog: 11 -> 5 -> 0.**

The graph neighbourhood is therefore no longer carrying generic `pending evidence recovery` nodes. Items remain open where positive evidence, applicability decision, equivalence or closure evidence is still required, but each now has an explicit governed state.

## Next ranked action

After merge, return to the exact-v24 priority frontier after R78 and identify **R79** from the authoritative v24 selector. Use R79 only as the next graph entry point; expand through canonical OFFER links, already-returned bidder evidence and derived engineering dependencies exactly as in Waves 2G/2H.

## Control

Contract/Addendum II and canonical RTM remain authoritative. Bidder IDs are not trusted without section/text identity confirmation. Contractor `N/A` cannot exercise applicability authority. OFFER evidence remains downstream evidence only. No requirement is closed by this file. Accepted-release HOLD remains unchanged and independent.
