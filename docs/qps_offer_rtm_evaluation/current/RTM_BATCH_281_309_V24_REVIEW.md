# QPS RTM governed item review — RTM-281..309

Status: **REVIEW / DERIVED EVIDENCE ONLY — NO REQUIREMENT CLOSURE**

## Controlling source chain

1. **SCK CEN/90508872 Addendum II Technical Requirements** — contractual authority.
2. **Canonical 722 RTM / 50 OFFER projection** — governed numbering, page/section anchors and OFFER crosswalk.
3. **`QPS_OFFER_Evaluation_FULL_v24.xlsx`** — current bidder-independent BT/PCA technical-evaluation SSOT for review priority only.
4. **Exact-source extraction from v24 `RTM_RANKING`** — governed prioritisation metadata evidence only.
5. **Bidder/compliance evidence SSOT** — downstream evidence only; may not rewrite the authority layer.

The superseded 735-row extraction is prohibited as canonical input or fallback.

## Authority boundary

- Contract/Addendum II remains authoritative.
- RTM remains the governed numbered projection.
- OFFER links remain request/evidence interfaces only.
- No applicant reply, bidder evaluation, negotiation response, score or compliance disposition is assimilated into requirement text.
- Range allocation is work ordering only and does not imply requirement closure.
- DOW / KEB / PCA / BT outputs remain derived/proposed evidence until governed promotion.

## v24 ranking handling

The exact historical FULL v24 binary was recovered from frozen commit `0291d43990d73a45058ad19fe5ce6ed97e92e178`, verified as Git blob SHA-1 `bccab3a8ccf539db7c4a9636f1f2abee86885494`, raw SHA-256 `3e84a3cab305b5b6b9bcf73367a47b3d49fef9f74077cff95e5cfe7e1b4a7118`, size `641318` bytes, and read directly from sheet `RTM_RANKING`. GitHub Actions run `33244181179` completed successfully and required one exact row for every target RTM with no duplicate or missing target IDs. Artifact `9712296635` has ZIP digest `sha256:173d2fc70857d05fea47b7e1e5d7e51672832ab0f39b3913a04d95f598efa2e4`.

The v24 priority values below are direct v24 metadata, not values copied or inferred from v23 or another workbook. Rank/tier remain bidder-independent technical-evaluation prioritisation and do not modify requirement authority or compliance state.

## Canonical OFFER boundary

**RTM-281..RTM-309 have no canonical OFFER link.** No OFFER relationship is to be inferred into this range.

`OFFER-25 — Supplier Experience & Reference Justification` begins later at RTM-321..RTM-327 and is outside this batch.

## Engineering grouping

The tables below are **controlled review synopses**. They do not replace canonical verbatim requirement text; full verbatim remains governed by Addendum II and the canonical 722-row workbook.

### A. QDB / WPS interface control — RTM-281..297

| RTM | Section | Controlled synopsis | Evidence/review focus | v24 priority |
|---|---|---|---|---|
| RTM-281 | §4.5.1 | QPS mechanically interfaces with QDB at the QRB–QLM connection; interface definition and site connection execution are led/performed by SCK CEN via the QDB Contractor. | Interface ownership, physical boundary, responsibility split. | R637 · T3 Contextual |
| RTM-282 | §4.5.1 | Contractor supports definition of the QRB–QLM interface, including QRB-side constraints such as geometry, space envelope, accessibility and allowable loads. | ICD/interface data completeness. | R638 · T3 Contextual |
| RTM-283 | §4.5.1 | QRB includes a removable test cap allowing QPS operation before QDB connection, including SAT. | SAT independence, test-cap envelope/handling, temporary boundary control. | R333 · T2 Secondary |
| RTM-284 | §4.5.1 | QRB interface to QLM Spool complies with the stated interface/site-activity requirements. | Mechanical integration and site execution without cold-box modification. | R639 · T3 Contextual |
| RTM-285 | §4.5.1 | QRB–QLM connection is defined and frozen through the stated design-phase sequence. | Configuration freeze, interface change control, milestones. | R565 · T3 Contextual |
| RTM-286 | §4.5.2 | QPS mechanically interfaces with WPS at QRB–WPS connections for warm headers W, U and S. | Boundary definition for three warm interfaces. | R640 · T3 Contextual |
| RTM-287 | §4.5.2 | QRB–WPS connections are defined and frozen through the stated design-phase sequence. | ICD/configuration freeze and owner/contractor coordination. | R641 · T3 Contextual |
| RTM-288 | §4.5.2.1 | QRB.U supports purge/conditioning and other defined U-line use cases. | Use-case completeness and operating-state compatibility. | R642 · T3 Contextual |
| RTM-289 | §4.5.2.1 | Flow conditions at QRB.U satisfy the contract-defined temperature, pressure, flow and helium-quality envelope. | Thermodynamic/interface envelope verification. | R251 · T2 Secondary |
| RTM-290 | §4.5.2.1 | QRB.U contains the specified shut-off, pressure-limiting and overpressure-protection functions. | Functional safety, setpoint/protection evidence, CIS indication. | R383 · T2 Secondary |
| RTM-291 | §4.5.2.2 | QRB.S supports room-temperature helium return from Cryogenic Users. | S-line functional use case. | R643 · T3 Contextual |
| RTM-292 | §4.5.2.2 | Flow conditions at QRB.S satisfy the contract-defined interface envelope. | Pressure/temperature/flow envelope and transient assumptions. | R252 · T2 Secondary |
| RTM-293 | §4.5.2.2 | QPS design and operating sequences shall not pull WPS.S pressure below the minimum allowable pressure in RTM-292. | Transient/suction interaction and protection against under-pressure. | R644 · T3 Contextual |
| RTM-294 | §4.5.2.2 | QRB.S contains the specified remotely controlled isolation and associated interface/protection equipment. | Remote isolation, feedback, failure response and protection. | R295 · T2 Secondary |
| RTM-295 | §4.5.2.3 | QRB.W supports room-temperature helium return from Cryogenic Users. | W-line functional use case. | R645 · T3 Contextual |
| RTM-296 | §4.5.2.3 | Flow conditions at QRB.W satisfy the contract-defined interface envelope. | Pressure/temperature/flow envelope verification. | R253 · T2 Secondary |
| RTM-297 | §4.5.2.3 | QRB.W contains the specified remotely controlled shut-off and pressure-protection arrangement. | Isolation, sensing, user-originating overpressure boundary. | R296 · T2 Secondary |

### B. QPS:CIS general controls — RTM-298..309

| RTM | Section | Controlled synopsis | Evidence/review focus | v24 priority |
|---|---|---|---|---|
| RTM-298 | §4.6.3 | Contractor designs QPS:CIS in accordance with Controls, Interlocks and IT Documentation in [AD_05]. | Controlled external-reference applicability and design traceability. | R658 · T3 Contextual |
| RTM-299 | §4.6.3 | QPS:CIS includes all Figure-11 green components plus any additional systems/subsystems needed for QPS performance, function and safety. | Architecture completeness and scope closure. | R659 · T3 Contextual |
| RTM-300 | §4.6.3 | QPS:CIS uses a commercially available industrial-grade platform with lifecycle support and vendor independence, meeting applicable safety/performance/reliability and regulatory requirements. | Platform lifecycle, supportability, vendor lock-in, regulatory evidence. | R49 · T1 Primary |
| RTM-301 | §4.6.3 | QPS:CIS enables autonomous operation across all defined operational scenarios/transitions without operator intervention. | Sequence automation, state-machine completeness, fallback behaviour. | R660 · T3 Contextual |
| RTM-302 | §4.6.3 | QPS:CIS provides real-time instrument-health monitoring with alarms/diagnostics for early fault detection. | Sensor diagnostic coverage, drift/dropout/deviation logic. | R532 · T3 Contextual |
| RTM-303 | §4.6.3 | Upgradeable software components support an automatable offline upgrade procedure and required tool list. | Reproducible offline maintenance, restoration and toolchain evidence. | R661 · T3 Contextual |
| RTM-304 | §4.6.3 | Contractor follows applicable GSHRC sections for software, firmware and interoperability per [AD_04]/Table 30. | External-control applicability matrix and evidence mapping. | R662 · T3 Contextual |
| RTM-305 | §4.6.3 | Interlock thresholds are not remotely writable and may be changed only by authorised personnel after formal approval. | Access control, change control, auditability and protected parameters. | R663 · T3 Contextual |
| RTM-306 | §4.6.3 | QPS:CIS should permit manual actuator control in malfunction conditions. | Manual override philosophy, permissions, safe-state interaction. | R510 · T3 Contextual |
| RTM-307 | §4.6.3 | In maintenance mode, operator-set sensor values can be interpreted by QPS:CIS as real sensor values. | Simulation/substitution controls, mode indication, safeguards and audit trail. | R321 · T2 Secondary |
| RTM-308 | §4.6.3 | QPS:CIS stores historical measured values, valve positions, operator actions, alarms, etc., accessible through SCADA. | Historian coverage, retention, timestamps, auditability and retrieval. | R311 · T2 Secondary |
| RTM-309 | §4.6.3 | QPS:CIS includes automated testing functionality to validate correct operation of the whole QPS, e.g. during SAT. | Automated SAT/test procedure, coverage, acceptance evidence and repeatability. | R370 · T2 Secondary |

The exact extraction additionally records Gate, Weighted S, BT Win %, BT λ index and Primary dimension for each item. Those fields remain traceable to the exact v24 source and are not required to alter this review synopsis.

## Evidence questions for governed review

- **RTM-281..287:** Is there one controlled interface dataset/ICD showing ownership, geometry, loads, access, temporary SAT configuration, final connection and design-freeze milestones?
- **RTM-288..297:** Are U/S/W line use cases, pressure/temperature/flow envelopes, valves, sensing and protection functions traceable from contract requirement through calculation/P&ID/control sequence to FAT/SAT evidence?
- **RTM-298..304:** Does the QPS:CIS architecture trace all contract/external-document obligations into a controlled design baseline without relying on unstated vendor assumptions?
- **RTM-305..309:** Are protected interlock parameters, manual override, maintenance-value substitution, historian/audit data and automated SAT functions governed by explicit access modes, traceable change control and verification procedures?

These questions are evidence-structuring prompts only and do not add requirements.

## Promotion rule

No item may be promoted beyond `REVIEW / DERIVED EVIDENCE ONLY` unless canonical RTM identity/text are preserved, evidence ownership and verification route are explicit, any external-reference applicability is governed, and a reviewer explicitly approves promotion. v24 metadata must remain bound to the verified exact FULL v24 binary and exact-row extraction evidence.

## Ordered continuation

This was the final batch carrying `V24_LOOKUP_REQUIRED`. The planned four-range item-level review sequence remains complete. Further work is evidence acquisition/reconciliation only; no generic-infrastructure work or fifth RTM batch is introduced.
