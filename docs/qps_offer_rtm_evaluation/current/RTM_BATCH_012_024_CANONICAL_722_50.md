# QPS RTM governed item review — RTM-012..024

Status: **REVIEW / DERIVED EVIDENCE ONLY — NO REQUIREMENT CLOSURE**

## Controlling source chain

This review uses only the current governed 722/50 source chain:

1. **SCK CEN/90508872 Addendum II Technical Requirements** — authoritative contract source.
2. **Canonical RTM/OFFER workbook** — `QPS_OFFER_Cluster_v3_3_Canonical_RTM_722.xlsx`:
   - RTM-001..RTM-722 only;
   - OFFER-01..OFFER-50 only;
   - PDF controls RTM/OFFER numbering and page anchors;
   - DOCX controls clean verbatim paragraph/bullet text.
3. **RTM/OFFER technical-evaluation BT/PCA SSOT** — `QPS_OFFER_Evaluation_FULL_v24.xlsx`:
   - canonical current technical-evaluation SSOT for the fixed 50 OFFER × 722 RTM universe;
   - bidder-independent ranking, tiering and BT/PCA outputs;
   - used only for review order, prioritisation and derived analytical fields;
   - does not override Addendum II or the canonical RTM/OFFER projection;
   - supersedes v23 for this role.
4. **Bidder-evidence/compliance SSOT** — `03_DATA_SSOT/offer_evidence_full.json` and `03_DATA_SSOT/rtm_evidence_full.json`:
   - downstream evidence layer only;
   - fixed cardinality of 50 OFFER and 722 RTM records;
   - applicant/bidder status, notes and evidence remain outside the authority layer.

The previous 735-row extraction is **superseded** and is not used as canonical input, content source, numbering source, ranking source, traceability source or fallback source for this review.

## Source roles — do not cross these boundaries

| Source | Role | May define requirement? | May define review priority? | May carry bidder evidence? |
|---|---|---:|---:|---:|
| Addendum II PDF/DOCX | Contract authority | Yes | No | No |
| Canonical 722/50 workbook | Governed numbered projection / crosswalk | Projection only | No | No |
| `QPS_OFFER_Evaluation_FULL_v24.xlsx` | Technical-evaluation BT/PCA SSOT | No | Yes | No — ranking is bidder-independent |
| `offer_evidence_full.json` / `rtm_evidence_full.json` | Evidence/compliance SSOT | No | No | Yes |

No lower layer may silently promote content into a higher layer.

## Authority boundary

- Contract / Addendum II remains authoritative.
- RTM remains the governed numbered projection.
- OFFER links remain request/evidence interfaces only and never substitute for RTM compliance.
- No applicant reply, bidder evaluation, negotiation response, compliance disposition or bidder score is assimilated into the requirement layer.
- Range allocation is work ordering only and does not claim individual requirement closure.
- DOW / KEB / PCA / BT outputs remain derived/proposed evidence until governed promotion.

## Canonical batch — RTM-012..024

| RTM | PDF page | Section | Canonical requirement projection | OFFER interface | Disposition |
|---|---:|---|---|---|---|
| RTM-012 | 27 | §4.2.2 | The Contractor shall define and implement all necessary QPS operational scenarios and transitions, including at minimum those specified in §4.2.2; intermediate operational steps may be introduced where required by the design. | None expected | Review only; no closure. |
| RTM-013 | 27 | §4.2.2 | All QPS operational scenarios and transitions shall be integrated into the QPS design and control system, including controlled execution and QPS:CIS scenario/sub-step/readiness/hold-abort status. | None expected | Review only; no closure. |
| RTM-014 | 27 | §4.2.2 | For each scenario and transition, the Contractor shall define the interaction with Cryogenic Users, including interface boundary conditions, process envelopes/ramp limits, readiness/hold/abort conditions, trip/recovery behaviour and state/status information. | None expected | Review only; no closure. |
| RTM-015 | 28 | §4.2.2 | During Basic and Detailed Design the Contractor shall progressively define implementation of each scenario/sub-step, including transition conditions, interface process conditions, control setpoint ranges, alarm limits and interlock thresholds. | None expected | Item-level design-evidence review; no closure. |
| RTM-016 | 28 | §4.2.2.1 | The QPS shall implement the Steady State Operational Scenarios defined in Table 3. | None expected | Review only; no closure. |
| RTM-017 | 28 | §4.2.2.1 | For each steady-state scenario, the Contractor shall define objective achieved/stable criteria including controlled variables, stability bands and the minimum duration for which those bands must be satisfied. | None expected | Item-level verification-evidence review; no closure. |
| RTM-018 | 28 | §4.2.2.1 | For each steady-state scenario, the Contractor shall specify the maximum sustainable cooling capacity available to Cryogenic Users resulting from the QPS design. | None expected | Capability-evidence review; no closure. |
| RTM-019 | 28 | §4.2.2.2 | The QPS shall implement the Transient Operational Scenarios defined in Table 4. | OFFER-04 — direct evidence interface | OFFER response is partial evidence only; no closure. |
| RTM-020 | 28 | §4.2.2.2 | For cooldown/warmup scenarios, the Contractor shall provide and substantiate the process-flow conditions, expected duration of each scenario/sub-step, and sustainable refrigeration power at discrete temperature levels between 300 K and 4.5 K. | OFFER-04 — direct evidence interface | Transient-model evidence review; no closure. |
| RTM-021 | 29 | §4.2.2.2 | Cooldown/warm-up design shall comply with the stated design basis, including permitted simultaneous/sequential user operation and the specified QRB.D/QRB.E temperature-difference constraint. | OFFER-04 — direct evidence interface | Design-basis evidence review; no closure. |
| RTM-022 | 29 | §4.2.2.2 | The 2K-RAMP shall be a controlled 2K-SB↔2K-OP transient; the QPS shall remain within specified 2 K interface envelopes and the Contractor shall define permissible ramp rates and associated dQ/dt and/or equivalent process-variable constraints. | OFFER-04 — direct evidence interface | High-value transient evidence review; no closure. |
| RTM-023 | 29 | §4.2.2.3 | The QPS shall implement the transitions between Operational Scenarios defined in Figure 8. | None expected | Transition-state evidence review; no closure. |
| RTM-024 | 29 | §4.2.2.3 | The Contractor shall verify each Transient Operational Scenario using the Cryogenic User Transient Model, at minimum confirming installed cooling-capacity sufficiency, estimating transient duration, and specifying relevant performance limitations. | None expected | Model-verification evidence review; no closure. |

## OFFER boundary for this batch

Only RTM-019..RTM-022 have a canonical direct OFFER interface in this range: **OFFER-04 — Cooldown & Thermal Performance Modelling**. That relationship is an evaluation/evidence interface. It does not modify the RTM wording and an applicant response cannot close the underlying RTM by itself.

RTM-012..018 and RTM-023..024 have no canonical OFFER link in the 722/50 workbook and shall not be back-filled with inferred OFFER relationships.

## SSOT reconciliation rule

Before any derived evidence is promoted for an item in this batch:

- RTM ID and full verbatim requirement must match the canonical 722-row workbook;
- OFFER ID, where present, must match the canonical 50-item workbook relation;
- rank/tier/BT/PCA fields must originate from `QPS_OFFER_Evaluation_FULL_v24.xlsx`, or an explicitly governed successor;
- bidder evidence/status must originate from the downstream 722/50 evidence SSOT and remain evidence-layer data;
- bidder/evaluation fields must never be written into canonical requirement wording;
- BT/PCA rank/tier may order review but must not be written back as compliance, closure or contractual status;
- disagreement between layers is a reconciliation finding, not permission to choose whichever value is convenient.

## Item-level review questions

- **RTM-012..015:** is there one controlled scenario/state model covering identifiers, sub-steps, entry/exit criteria, setpoint ranges, hold/abort logic and user-interface constraints?
- **RTM-016..018:** are all steady-state scenarios backed by objective stability criteria and a traceable maximum sustainable cooling-capacity envelope?
- **RTM-019..021:** does the Cryogenic User Transient Model substantiate scenario implementation, flow-permission conditions, durations, temperature-dependent refrigeration capability and contract constraints?
- **RTM-022:** are 2K-RAMP dQ/dt / equivalent process ramps, interface envelopes and transition behaviour explicitly parameterised and traceable?
- **RTM-023..024:** can each Figure-8 transition be mapped to a controlled transient-model case proving capacity sufficiency, duration estimate and limiting performance constraints?

These are review questions only. They do not add requirements.

## Ordered continuation

After this governed batch:

1. RTM-048..063
2. RTM-281..309
3. RTM-236..280

The order follows the existing BT/PCA prioritisation model in the governed RTM/OFFER SSOT. No generic-infrastructure expansion is inserted into this sequence.
