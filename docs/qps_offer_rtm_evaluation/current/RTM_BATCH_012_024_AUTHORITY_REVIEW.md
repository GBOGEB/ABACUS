# QPS RTM governed item review — RTM-012..024

Status: **REVIEW / DERIVED EVIDENCE ONLY — NO REQUIREMENT CLOSURE**

## Authority boundary

This batch is governed by the following precedence and interpretation rules:

1. **Contract / Addendum II remains authoritative.**
2. **The RTM remains the governed numbered projection of that authority.**
3. **OFFER links are request/evidence interfaces only.** They do not redefine, amend, close, or supersede an RTM requirement.
4. **No applicant reply, bidder evaluation, negotiation response, compliance disposition, or scoring outcome is assimilated into the requirement layer.**
5. **Range allocation is a work-order / prioritisation device only.** Inclusion in this batch does not claim individual requirement closure.
6. **DOW / KEB / PCA / BT / analytical feedback is derived or proposed evidence until separately promoted through a governed approval path.**

Working RTM source for this review: the governed 735-row projection tied to **SCK CEN/90508872 PDF+DOCX (08-Apr-2026)**. Existing derived evidence routes and BT/PCA prioritisation are used only to order and prepare review work.

## Batch objective

Review RTM-012 through RTM-024 at item level, preserving the canonical requirement statement and source section while making the evidence route explicit enough for later design review, verification planning, and controlled promotion. This file does **not** modify canonical requirement text.

## Item register

| RTM | Contract section | Governed requirement projection | Current derived evidence route | OFFER interface | Review disposition |
|---|---|---|---|---|---|
| RTM-012 | §4.2.2 | Contractor defines and implements all necessary QPS operational scenarios and transitions, including those specified in §4.2.2. | Calculation/model + functional design/configuration review and sequence/interface demonstration. | None expected | Review evidence definition; no closure. |
| RTM-013 | §4.2.2 | Operational scenarios/transitions are integrated into QPS design and control, including QPS:CIS execution/status information. | Calculation/model + functional design/configuration review and sequence/interface demonstration. | None expected | Review CIS/state evidence; no closure. |
| RTM-014 | §4.2.2 | Contractor defines QPS/user interaction, boundary conditions, process envelopes/ramp limits, readiness/hold/abort conditions, trip/recovery behaviour and state information. | Calculation/model + functional sequence/interface demonstration + RAM/recovery evidence. | None expected | Review interface and recovery evidence; no closure. |
| RTM-015 | §4.2.2 | Contractor progressively defines detailed implementation of each scenario/transition through Basic and Detailed Design, including sub-steps, transition conditions, interface conditions and control ranges. | Calculation/model + functional design/configuration review. | None expected | **Priority review** under current BT model; no closure. |
| RTM-016 | §4.2.2.1 | QPS implements the Steady State Operational Scenarios defined in Table 3. | Calculation/model + functional design/configuration review. | None expected | Review scenario implementation evidence; no closure. |
| RTM-017 | §4.2.2.1 | Contractor defines objective achieved/stable criteria for each steady-state scenario, including controlled variables, stability bands and minimum stable duration. | Witnessed FAT/SAT/commissioning evidence + calculation/model + functional design/configuration review. | None expected | **High-priority item-level review** under current BT model; no closure. |
| RTM-018 | §4.2.2.1 | Contractor specifies maximum sustainable cooling capacity available to Cryogenic Users for each steady-state scenario. | Calculation/model + functional design/configuration review. | None expected | Review capability-envelope evidence; no closure. |
| RTM-019 | §4.2.2.2 | QPS implements the Transient Operational Scenarios defined in Table 4. | Calculation/model + functional design/configuration review. | OFFER-04 evidence interface | OFFER link retained only as evidence/request interface; no closure. |
| RTM-020 | §4.2.2.2 | For cooldown/warmup scenarios, Contractor provides and substantiates process-flow conditions, expected duration and sustainable refrigeration power at discrete temperatures. | Calculation/model / recorded trend. | OFFER-04 evidence interface | Priority transient-model evidence review; no closure. |
| RTM-021 | §4.2.2.2 | Cooldown/warm-up design basis includes permitted simultaneous/sequential user operation and specified QRB.D/QRB.E temperature-difference constraint. | Calculation/model / recorded trend. | OFFER-04 evidence interface | Priority transient-design-basis review; no closure. |
| RTM-022 | §4.2.2.2 | 2K-RAMP is a controlled 2K-SB↔2K-OP transient with defined interface/ramp behaviour and permissible ramp-rate constraints. | Calculation/model + functional sequence/interface demonstration + document/QC review. | OFFER-04 evidence interface | **T1 / priority review** in current BT projection; no closure. |
| RTM-023 | §4.2.2.3 | QPS implements transitions between Operational Scenarios defined in Figure 8. | Calculation/model + functional design/configuration review and sequence/interface demonstration. | None expected | Review transition-state evidence; no closure. |
| RTM-024 | §4.2.2.3 | Contractor verifies each Transient Operational Scenario with the Cryogenic User Transient Model, confirming installed capacity, estimating transient duration and specifying performance limitations. | Calculation/model + functional sequence/interface demonstration + document/QC review. | None expected | **T1 / priority review**; explicit model-verification evidence required; no closure. |

## BT/PCA use in this batch

BT/PCA is used to decide **review order and evidence attention**, not contractual authority or compliance disposition.

Current governed ranking material identifies RTM-017 as a high T1 item and RTM-015, RTM-022 and RTM-024 as T1 items. RTM-012, RTM-013, RTM-016, RTM-018, RTM-019 and RTM-023 appear in the T2 secondary group in the current projection. These tiers may guide reviewer effort but shall not be written back as requirement status.

## First-pass evidence questions

The following are review questions, not new requirements:

- **RTM-012..015:** Is there a single controlled scenario/state model that shows identifiers, sub-steps, entry/exit criteria, setpoint ranges, hold/abort logic and user-interface constraints without ambiguity?
- **RTM-016..018:** Are steady-state definitions backed by objective stability criteria and a traceable sustainable-capacity envelope for each state?
- **RTM-019..021:** Does the transient model cover the contract-defined scenarios, flow-permission conditions, duration and temperature-dependent refrigeration capability, including the QRB.D/QRB.E constraint?
- **RTM-022:** Are 2K-RAMP ramp limits, dQ/dt or equivalent mass-flow/process ramps, interface envelopes and state-transition behaviour explicitly parameterised and traceable?
- **RTM-023..024:** Can every Figure-8 transition be traced to a Cryogenic User Transient Model case showing installed-capacity sufficiency, estimated duration and limiting performance constraints?

Any DOW/KEB/PCA/model output used to answer these questions remains **derived evidence** until reviewed and promoted through the governed process.

## Promotion rule

An item may move beyond `REVIEW / DERIVED EVIDENCE ONLY` only when all of the following are explicit:

- canonical RTM ID and exact authoritative source are preserved;
- proposed evidence is linked without rewriting the requirement;
- any OFFER link is identified as an interface only;
- no bidder reply/evaluation text has entered the requirement layer;
- evidence ownership and verification route are identified;
- a governed reviewer explicitly approves promotion.

## Next governed batch order

After this batch is reviewed/merged, continue without generic-infrastructure expansion:

1. RTM-048..063
2. RTM-281..309
3. RTM-236..280

The sequence follows the existing BT/PCA priority model and does not itself imply requirement closure.
