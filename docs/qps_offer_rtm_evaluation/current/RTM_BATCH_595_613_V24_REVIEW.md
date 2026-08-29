# QPS RTM governed item review — RTM-595..613

Status: **REVIEW / DERIVED EVIDENCE ONLY — NO REQUIREMENT CLOSURE**

## Governing source chain

1. SCK CEN/90508872 Addendum II PDF/DOCX — contractual authority.
2. `QPS_OFFER_Cluster_v3_3_Canonical_RTM_722.xlsx` — governed RTM-001..RTM-722 numbering, canonical text projection and OFFER crosswalk.
3. `QPS_OFFER_Evaluation_FULL_v24.xlsx` — bidder-independent technical-evaluation BT/PCA prioritisation only.
4. Exact v24 selector evidence — Actions run `33245164584`, artifact `9712597442`, artifact ZIP digest `sha256:fd02fa8b160c4804bdd7c246efb2cf198dda42b513eead6547c5c946da3f87ea`.

Exact FULL v24 binary provenance remains: frozen commit `0291d43990d73a45058ad19fe5ce6ed97e92e178`, Git blob SHA-1 `bccab3a8ccf539db7c4a9636f1f2abee86885494`, raw SHA-256 `3e84a3cab305b5b6b9bcf73367a47b3d49fef9f74077cff95e5cfe7e1b4a7118`, size `641318` bytes.

## Authority boundary

- Contract/Addendum II remains authoritative.
- RTM remains the governed numbered projection.
- OFFER links remain request/evidence interfaces only.
- No applicant reply, bidder evaluation, negotiation response or bidder score is assimilated into requirement wording.
- BT/PCA rank/tier controls review priority only; it does not alter applicability, compliance or closure.
- DOW/KEB/PCA/BT outputs remain derived/proposed evidence until governed promotion.

## Why this block is next

The exact v24 selector excluded the already-reviewed ranges `RTM-012..024`, `RTM-048..063`, `RTM-236..280` and `RTM-281..309`, then sorted all remaining RTMs by exact v24 Rank ascending without contiguous-range inference.

RTM-595..613 is the highest-density coherent remaining T0 block: all 19 items are **T0 Gate**, all lie within the top 34 remaining ranks, and the canonical requirement structure is one safety chain spanning:

- RTM-595..600 — Safety and Protection Requirements;
- RTM-601..608 — Personnel Safety;
- RTM-609..613 — Oxygen-Deficiency Hazard.

This grouping preserves engineering coherence while following the exact v24 priority model.

## Canonical batch register

| RTM | Page | Section | Controlled synopsis — canonical verbatim remains in Addendum II / 722-row workbook | OFFER interface | v24 priority |
|---|---:|---|---|---|---|
| RTM-595 | 116 | §5 | Contractor risk analysis (e.g. HAZOP/FMECA/equivalent) shall cover external interfaces, utility loss, MIS interlock failure, operation outside interface windows, operator error and internal QPS failures, with mitigation implemented and design reports updated. | None | R2 · T0 Gate |
| RTM-596 | 116 | §5 | Fail-safe hard-wired interlock circuits shall be designed, implemented and validated to prevent QPS damage and remain functional for relevant control-system and utility failures. | None | R12 · T0 Gate |
| RTM-597 | 116 | §5 | Internal QPS interlock processing shall not rely on MIS; MIS is used only for interlock connections outside QPS. | None | R13 · T0 Gate |
| RTM-598 | 116 | §5 | QPS:CIS shall expose QPS interlock status to the MCS control interface. | None | R14 · T0 Gate |
| RTM-599 | 116 | §5 | Hard-wired interlock sensor contacts shall use positive logic so signal/power/cable loss forces the affected component to a safe state. | None | R15 · T0 Gate |
| RTM-600 | 116 | §5 | Redundant measurement channels and stand-by heaters shall be provided for inaccessible components and components whose failure could jeopardise machine integrity. | None | R10 · T0 Gate |
| RTM-601 | 116 | §5.2 | Personnel-safety boundary conditions assign QCELL bursting-disc venting outside QPS scope and fire/access-control responsibilities to SCK CEN. | None | R29 · T0 Gate |
| RTM-602 | 116 | §5.2 | Safety treatment shall distinguish hazards, consequences and mitigation layers. | None | R30 · T0 Gate |
| RTM-603 | 116 | §5.2 | Contractor shall design, implement, supply and document safety measures, PPE and procedures for hazards including ODH/asphyxiation and cryogenic cold burn. | None | R22 · T0 Gate |
| RTM-604 | 117 | §5.2 | Hazard analysis, mitigation measures, detection/protection devices, PPE and associated procedures shall be documented. | None | R23 · T0 Gate |
| RTM-605 | 117 | §5.2 | Contractor is responsible for any required third-party inspection/certification, e.g. PED auditor. | None | R18 · T0 Gate |
| RTM-606 | 117 | §5.2 | Cold helium volumes shall be protected by safety devices in accordance with EN 17527, supplemented where applicable by API 520/521/580 for warm service. | None | R31 · T0 Gate |
| RTM-607 | 117 | §5.2 | Any isolatable cold volume and all insulation-vacuum volumes shall have dedicated safety devices. | None | R32 · T0 Gate |
| RTM-608 | 117 | §5.2 | A project-specific Safety File shall be accepted before site activities; it includes PIF/residual-risk inputs and the signed Safety Charter. | None | R5 · T0 Gate |
| RTM-609 | 117 | §5.2.1 | Contractor shall propose substantiated ODH monitor locations for all QPS rooms using SCK CEN installation, EN 50104:2019, SIL-2 and MINERVA site-alarm/access-control boundary conditions. | None | R24 · T0 Gate |
| RTM-610 | 117 | §5.2.1 | Contractor shall provide QPS technical inputs required for SCK CEN ODH-system certification. | None | R33 · T0 Gate |
| RTM-611 | 117 | §5.2.1 | ODH monitor signals shall be integrated into QPS:CIS to perform mitigating actions. | None | R34 · T0 Gate |
| RTM-612 | 117 | §5.2.1 | Contractor shall define where SCK CEN supplies ODH signals to QPS: at each monitor or at a central safety-interlock aggregator. | None | R16 · T0 Gate |
| RTM-613 | 117 | §5.2.1 | ODH integration shall be functionally tested during standalone commissioning and demonstrated during SAT, with evidence in Commissioning and Acceptance Test Files. | None | R8 · T0 Gate |

## Exact v24 metadata

| RTM | Rank | Weighted S | BT Win % | BT λ index | Primary dimension |
|---|---:|---:|---:|---:|---|
| RTM-595 | 2 | 58.666667 | 99.8613 | 98.2081 | Safety / Legal |
| RTM-596 | 12 | 36 | 98.2663 | 80.7342 | Safety / Legal |
| RTM-597 | 13 | 36 | 98.2663 | 80.7342 | Safety / Legal |
| RTM-598 | 14 | 36 | 98.2663 | 80.7342 | Safety / Legal |
| RTM-599 | 15 | 36 | 98.2663 | 80.7342 | Safety / Legal |
| RTM-600 | 10 | 42 | 98.7517 | 85.5097 | Reliability |
| RTM-601 | 29 | 20 | 95.4230 | 59.4010 | Safety / Legal |
| RTM-602 | 30 | 20 | 95.4230 | 59.4010 | Safety / Legal |
| RTM-603 | 22 | 30.666667 | 97.0180 | 70.1584 | Safety / Legal |
| RTM-604 | 23 | 30.666667 | 97.0180 | 70.1584 | Safety / Legal |
| RTM-605 | 18 | 32 | 97.4341 | 73.4396 | Safety / Legal |
| RTM-606 | 31 | 20 | 95.4230 | 59.4010 | Safety / Legal |
| RTM-607 | 32 | 20 | 95.4230 | 59.4010 | Safety / Legal |
| RTM-608 | 5 | 48.666667 | 99.4452 | 93.1231 | Safety / Legal |
| RTM-609 | 24 | 27.333333 | 96.8100 | 68.5993 | Safety / Legal |
| RTM-610 | 33 | 20 | 95.4230 | 59.4010 | Safety / Legal |
| RTM-611 | 34 | 20 | 95.4230 | 59.4010 | Safety / Legal |
| RTM-612 | 16 | 36 | 98.2663 | 80.7342 | Safety / Legal |
| RTM-613 | 8 | 48 | 99.1678 | 89.9568 | Safety / Legal |

## Canonical OFFER boundary

The canonical 722/50 workbook records **No OFFER link expected** for every item RTM-595..613. No OFFER relationship is inferred or back-filled in this review.

Bidder comments or compliance statements seen in downstream evaluation workbooks remain bidder/evidence-layer material and are not assimilated here.

## Item-level review questions

### RTM-595..600 — risk and interlocks

- Is there one controlled HAZOP/FMECA-equivalent risk register covering all contractual hazard classes and interfaces?
- Does every required mitigation trace to a fail-safe interlock, engineered safeguard, procedural control or accepted residual risk?
- Are positive-logic hard-wired trips demonstrably independent from ordinary CIS/MIS failure modes where required?
- Is redundancy/stand-by heating allocated from consequence rather than convenience, with failure-state evidence?

### RTM-601..608 — personnel safety and pressure protection

- Are SCK CEN / Contractor safety boundaries explicit and interface-owned?
- Are hazard, consequence and mitigation concepts separated in the safety analysis and verification records?
- Do relief/safety-device calculations cover every isolatable cold and insulation-vacuum volume and reference the correct EN/API basis?
- Are third-party/PED responsibilities, Safety File acceptance, PIF/residual-risk inputs and Safety Charter gating traceable to phase entry criteria?

### RTM-609..613 — ODH chain

- Does the ODH location proposal derive from credible helium-release cases, room geometry/ventilation and detector coverage rather than generic placement?
- Are EN 50104:2019 / SIL-2 assumptions and SCK CEN installation/site-alarm responsibilities preserved at the interface?
- Is the ODH signal path into QPS:CIS defined end-to-end, including physical signal handoff and mitigating actions?
- Are standalone commissioning, SAT demonstration and acceptance-file evidence explicit and testable?

## Promotion controls

No item leaves `REVIEW / DERIVED EVIDENCE ONLY` unless canonical text/source anchor is preserved, source ownership is explicit, verification evidence is identified, bidder/evaluation material remains outside requirement wording, and governed review approves promotion.

## Next-order rule

After RTM-595..613, continue from the exact v24 `next_50` queue, preserving engineering coherence while never allowing a lower-ranked convenience range to displace a materially higher-ranked unresolved T0/T1 item without a documented reason.
