# QPS RTM governed item review — RTM-048..063

Status: **REVIEW / DERIVED EVIDENCE ONLY — NO REQUIREMENT CLOSURE**

## Governing source chain

1. SCK CEN/90508872 Addendum II PDF/DOCX — contractual authority.
2. Canonical 722/50 RTM/OFFER projection — authoritative numbering/crosswalk layer.
3. `QPS_OFFER_Evaluation_FULL_v24.xlsx` — current technical-evaluation SSOT for bidder-independent BT/PCA prioritisation.
4. Bidder/compliance evidence datasets — downstream evidence only; never requirement authority.

No 735-row source or fallback is permitted.

## v24 handling rule

The v24 workbook is the governing technical-evaluation SSOT. In this runtime the exact v24 binary is verified upstream but not materialised, so this review does **not** copy or infer per-item v24 rank/tier values from v23 or other older workbooks. Where v24 item-level priority is not directly evidenced, the priority field remains `V24_LOOKUP_REQUIRED` rather than being guessed.

## Authority boundary

- Contract/Addendum II remains authoritative.
- RTM remains the governed numbered projection.
- OFFER links are request/evidence interfaces only.
- Applicant replies, bidder evaluation, negotiation responses and scoring outcomes are not assimilated into requirement wording.
- Range allocation does not imply requirement closure.
- DOW/KEB/PCA/BT outputs remain derived/proposed evidence until governed promotion.

## Canonical batch register

| RTM | Page | Section | Canonical requirement anchor | Canonical OFFER interface | v24 priority | Review focus |
|---|---:|---|---|---|---|---|
| RTM-048 | 36 | §4.2.6 | QPS design shall withstand abnormal events without compromising system integrity or personnel safety. | None | V24_LOOKUP_REQUIRED | Abnormal-event design basis and system integrity. |
| RTM-049 | 36 | §4.2.6 | Contractor shall identify, define and implement all abnormal events applicable to the QPS. | None | V24_LOOKUP_REQUIRED | Completeness of abnormal-event register. |
| RTM-050 | 36 | §4.2.6 | For each abnormal event, the Contractor shall provide the required engineering definition/substantiation. | None | V24_LOOKUP_REQUIRED | Engineering File traceability, consequence/recovery logic. |
| RTM-051 | 36 | §4.2.6 | QPS design shall consider abnormal events affecting electrical supply. | None | V24_LOOKUP_REQUIRED | LOOP, CIS supply loss, compressor supply loss, voltage dip/short interruption. |
| RTM-052 | 36 | §4.2.6 | QPS design shall consider abnormal events affecting the cryogenic system. | None | V24_LOOKUP_REQUIRED | Compressor/turbine/storage/purity/vacuum/internal discharge failure cases. |
| RTM-053 | 36 | §4.2.6 | QPS design shall consider abnormal events affecting utilities. | None | V24_LOOKUP_REQUIRED | Cooling-water and instrument-air loss response. |
| RTM-054 | 37 | §4.2.6 | QPS design shall consider abnormal events affecting controls and instrumentation. | None | V24_LOOKUP_REQUIRED | Local control-power, communication, sensor/actuator and remote-supervision failure. |
| RTM-055 | 37 | §4.3.1 | QPS shall have a minimum service life of at least 40 years. | None | V24_LOOKUP_REQUIRED | Lifetime design evidence and lifecycle assumptions. |
| RTM-056 | 37 | §4.3.1 | QPS shall withstand at least 50 complete warm-up/cool-down cycles over service life. | None | V24_LOOKUP_REQUIRED | Cyclic-life basis and fatigue/thermal-cycle evidence. |
| RTM-057 | 37 | §4.3.2 | QPS shall use industrially proven technologies/processes with demonstrated comparable operating experience and controlled exceptions. | OFFER-11 direct | V24_LOOKUP_REQUIRED | Proven-technology evidence, critical equipment and approval of limited-reference technology. |
| RTM-058 | 37 | §4.3.2 | Contractor shall perform an Availability & Reliability Assessment for the QPS. | OFFER-11 direct | V24_LOOKUP_REQUIRED | RAM methodology, failure modes/classes, MTBF/MTTR and Engineering File. |
| RTM-059 | 37 | §4.3.2 | Availability & Reliability Assessment shall use a system-level reliability model representing actual QPS architecture. | OFFER-11 direct | V24_LOOKUP_REQUIRED | Redundancy, functional chains, common-cause failures, utility dependencies, single-failure impacts. |
| RTM-060 | 38 | §4.3.2 | Contractor shall maintain/update the Availability & Reliability Assessment throughout the Contract. | OFFER-11 direct | V24_LOOKUP_REQUIRED | Design-change updates, phase submissions, OEM/field/predictive MTBF/MTTR evidence, assumptions/distributions. |
| RTM-061 | 38 | §4.3.2 | Contractor shall include the defined failure classes in the Availability & Reliability Assessment. | OFFER-11 direct | V24_LOOKUP_REQUIRED | Class A/B/C consequence and recovery mapping. |
| RTM-062 | 38 | §4.3.2 | QPS design shall comply with the specified availability requirements. | OFFER-11 direct | V24_LOOKUP_REQUIRED | 90-day 2K-OP, 12-month 2K refrigeration and 5-year cryogenic-refrigeration continuity evidence. |
| RTM-063 | 38 | §4.3.2 | QPS design shall comply with reliability requirements defined in Table 10. | OFFER-11 direct | V24_LOOKUP_REQUIRED | Table-10 reliability proof and reference-period interpretation. |

## Canonical OFFER boundary

RTM-048..056 have **no canonical OFFER link** and shall not be back-filled with inferred OFFER relationships.

RTM-057..063 map directly to **OFFER-11 — Reliability, MTBF & Recovery Strategy**. OFFER-11 is partial tender-stage evidence only and cannot close these RTMs by itself.

## Evidence questions for review

### RTM-048..054 — abnormal events

Confirm one controlled abnormal-event model/register covers electrical, cryogenic, utilities and controls/CIS failure families, with cause, detection, consequence, safe-state transition, recovery path, required backup/service assumptions, and verification route. Existing transient, LOOP, voltage-dip, WCS and recovery studies may be proposed as evidence but remain derived until governed promotion.

### RTM-055..056 — lifetime

Require an explicit 40-year lifecycle basis and evidence that at least 50 full 2 K → ambient → 2 K thermal cycles are tolerated by affected equipment, piping, supports, seals, insulation/vacuum systems and interfaces. Derived fatigue/maintenance arguments do not amend the contractual lifecycle requirements.

### RTM-057..063 — RAM / MTBF / recovery

Require a coherent system-level RAM model tied to the actual QPS architecture and operating states. The review should reconcile equipment MTBF/MTTR evidence, N+1/common-cause assumptions, failure classes, recovery times, uninterrupted-operation requirements and Table-10 targets. OFFER-11 is an evidence interface into this review, not the authority layer.

## Promotion controls

No item leaves `REVIEW / DERIVED EVIDENCE ONLY` unless:

- canonical RTM text/source anchor is preserved;
- any OFFER link matches the canonical 50-item crosswalk;
- v24 rank/tier is obtained from v24 itself or a demonstrably v24-derived governed export;
- evidence ownership and verification route are explicit;
- bidder/evaluation content remains outside requirement wording;
- governed review explicitly approves promotion.

## Next governed order

After this batch:

1. RTM-281..309
2. RTM-236..280

No generic-infrastructure expansion is inserted into this sequence.
