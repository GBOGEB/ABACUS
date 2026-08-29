# QPS RTM governed top-gate review — RTM-700 / 327 / 514 / 075 / 002

Status: **REVIEW / DERIVED EVIDENCE ONLY — NO REQUIREMENT CLOSURE**

## Governing source chain

1. SCK CEN/90508872 Addendum II PDF/DOCX — contractual authority.
2. `QPS_OFFER_Cluster_v3_3_Canonical_RTM_722.xlsx` — governed RTM-001..RTM-722 numbering, canonical text projection and OFFER crosswalk.
3. `QPS_OFFER_Evaluation_FULL_v24.xlsx` — bidder-independent technical-evaluation BT/PCA prioritisation only.
4. Exact v24 selector evidence — Actions run `33245164584`, artifact `9712597442`, artifact ZIP digest `sha256:fd02fa8b160c4804bdd7c246efb2cf198dda42b513eead6547c5c946da3f87ea`.

Exact FULL v24 provenance: frozen commit `0291d43990d73a45058ad19fe5ce6ed97e92e178`, Git blob SHA-1 `bccab3a8ccf539db7c4a9636f1f2abee86885494`, raw SHA-256 `3e84a3cab305b5b6b9bcf73367a47b3d49fef9f74077cff95e5cfe7e1b4a7118`, size `641318` bytes.

## Selection rule

Following merged reviews through RTM-595..613 and RTM-686..696, the exact-v24 unresolved queue was re-filtered. The five highest-ranked unresolved **T0 Gate** requirements are selected directly, irrespective of contiguity:

| order | RTM | v24 Rank | Tier | Gate | Weighted S | BT Win % | BT λ index | Primary dimension |
|---:|---|---:|---|---|---:|---:|---:|---|
| 1 | RTM-700 | 4 | T0 Gate | Yes | 54.666667 | 99.5839 | 94.7716 | Safety / Legal |
| 2 | RTM-327 | 6 | T0 Gate | Yes | 48 | 99.1678 | 89.9568 | Safety / Legal |
| 3 | RTM-514 | 7 | T0 Gate | Yes | 48 | 99.1678 | 89.9568 | Safety / Legal |
| 4 | RTM-075 | 9 | T0 Gate | Yes | 43 | 98.8904 | 86.9537 | Safety / Legal / Performance |
| 5 | RTM-002 | 11 | T0 Gate | Yes | 36 | 98.2663 | 80.7342 | Safety / Legal |

This intentionally avoids manufacturing a contiguous engineering block that would displace higher-priority unresolved gates.

## Authority boundary

- Contract/Addendum II remains authoritative.
- RTM remains the governed numbered projection.
- OFFER links remain request/evidence interfaces only.
- No applicant reply, bidder evaluation, negotiation response or bidder score is assimilated into requirement wording.
- BT/PCA rank/tier controls review priority only; it does not alter applicability, compliance or closure.
- Range allocation does not establish individual requirement closure.

## Canonical item register and review focus

### RTM-700 — EMC implementation and verification

**Canonical anchor:** PDF p130, §9.3 Electromagnetic interference.

The solution shall comply with relevant EN 61000-6-2 immunity and EN 61000-6-4 emission provisions, or an SCK CEN-approved equivalent. Verification includes at least an EMI design dossier/layout and shielding evidence, site wiring/installation inspection checklist, and where applicable EMC type tests/certificates for sensitive components.

**OFFER boundary:** OFFER-49 supporting/contextual only; not a primary compliance anchor.

**Review focus:**
- controlled EMC/EMI design dossier and zoning/segregation/shielding/earthing rationale;
- site inspection evidence linked to as-built configuration;
- type-test/certificate applicability for PLCs, sensors, analysers and other sensitive elements;
- explicit treatment of equivalent standards requiring SCK CEN approval;
- traceable SAT/commissioning evidence that installation did not invalidate component-level EMC assumptions.

### RTM-327 — Cyber Resilience Act products with digital elements

**Canonical anchor:** PDF p75, §4.6.4.5 Security.

The Contractor shall identify all products with digital elements under the EU Cyber Resilience Act. COTS products require valid CE marking; custom-built products require technical documentation and Declaration of Conformity demonstrating CRA compliance. Documentation is provided to SCK CEN for review/approval before SAT.

**OFFER boundary:** OFFER-25 direct — exact contract section. OFFER evidence remains partial evaluation evidence and does not replace RTM compliance.

**Review focus:**
- complete inventory of products with digital elements, including embedded/third-party components;
- COTS CE evidence and applicability traceability;
- custom-product CRA technical documentation and Declaration of Conformity;
- configuration/version identity between assessed product and SAT installation;
- pre-SAT review/approval gate and ownership of updates after software/firmware changes.

### RTM-514 — SAT demonstration of safety-related functions

**Canonical anchor:** PDF p99, §4.13.3.1 Demonstration of functional behaviour and operability.

The Contractor shall demonstrate correct operational behaviour of safety-related functions during SAT, including where applicable functional tests supporting verification of specified safety-integrity requirements.

**OFFER boundary:** OFFER-39 supporting/contextual FAT/SAT evidence only.

**Review focus:**
- complete safety-function register linked to hazards/interlocks/SIL or equivalent integrity requirements;
- test preconditions, initiators, expected safe state, timing and pass/fail criteria;
- independence between safety function and normal control where required;
- controlled evidence for both positive function and credible failure modes;
- traceability from SAT result to requirement, hazard and acceptance record.

### RTM-075 — LN2 equivalent electrical contribution to invCOP

**Canonical anchor:** PDF p41, §4.3.4.1 Inverse Coefficient of Performance.

If LN2 precooling is implemented, LN2 consumption including boil-off shall be converted to equivalent electrical power using `W_LN2_eq = (m_LN2 × c_LN2) / (Δt × c_elec)`, with contract reference prices `c_LN2 = 160 EUR/ton` including delivery and `c_elec = 180 EUR/MWh`.

**OFFER boundary:** OFFER-12 supporting — invCOP child section.

**Review focus:**
- units and conversion consistency, particularly kg vs ton and MWh vs h/W;
- defined operating period and total LN2 mass including boil-off;
- no substitution of live commercial prices for the contract reference prices in the contractual invCOP metric;
- clear separation between contractual efficiency metric and separate OPEX/scenario analysis;
- uncertainty propagation into the reported invCOP where applicable.

### RTM-002 — Contractor responsibility for complete definition and execution

**Canonical anchor:** PDF p24, §4.1 General Requirements.

The Contractor is responsible for correct definition and execution of all activities necessary to perform the Contract and ensure every supply/work item meets imposed requirements. Where SCK CEN has not specified activity-level requirements, the Contractor shall define appropriate requirements from function, performance, operating circumstances and its expertise; once defined and accepted, changes require prior written SCK CEN approval.

**OFFER boundary:** OFFER-03 direct primary anchor; OFFER-01 and OFFER-02 supporting/shared-section links.

**Review focus:**
- requirement-completeness method for contractor-defined lower-level requirements;
- traceability from functional/performance needs to derived requirements and verification;
- explicit assumptions and missing-information management without converting them into unapproved deviations;
- configuration/change control for contractor-defined requirements after acceptance;
- interface between OFFER-01/02/03 evidence and the continuing contractual responsibility after award.

## Cross-item engineering deductions

These five gates expose five different failure modes that should not be collapsed into one compliance score:

1. **RTM-700:** installation-level electromagnetic compatibility can fail despite compliant individual components.
2. **RTM-327:** digital-product conformity can drift when firmware/software/configuration changes after initial documentation.
3. **RTM-514:** a declared safety architecture is insufficient without end-to-end SAT demonstration against defined integrity requirements.
4. **RTM-075:** an apparently small unit/conversion or accounting-boundary error can materially distort contractual invCOP comparison.
5. **RTM-002:** incomplete contractor-derived requirements can create systemic gaps even when individually enumerated SCK CEN requirements appear satisfied.

The common evidence principle is therefore **configuration-bound demonstration**, not document presence alone.

## Promotion controls

No item leaves `REVIEW / DERIVED EVIDENCE ONLY` unless canonical text/source anchor is preserved, OFFER classification matches the governed 722/50 crosswalk, evidence ownership and verification route are explicit, bidder/evaluation material remains outside requirement wording, and governed review approves promotion.

## Next exact-v24 unresolved gates after this set

The next unresolved T0 entries in the extracted queue are RTM-001 (R25), RTM-003 (R26), RTM-004 (R27), RTM-594 (R28), and RTM-702..705 (R40..43). Their grouping should again follow exact priority first and engineering coherence second.
