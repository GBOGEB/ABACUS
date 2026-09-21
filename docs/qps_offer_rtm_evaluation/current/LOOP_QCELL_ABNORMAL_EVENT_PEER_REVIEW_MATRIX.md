# QPS LOOP / QCELL abnormal-event peer-review matrix

Status: **OWNER FIRST PASS / PEER-REVIEW INPUT — NO REQUIREMENT CLOSURE / NO SCORE CHANGE**

## Purpose

Provide one actionable review surface for the LOOP event, electrical/support-system dependencies, QCELL/Cryogenic User response, abnormal-event control logic and FAT/SAT verification.

This matrix does **not** alter the controlled RTM/OFFER baseline. It preserves the following authority chain:

```text
CONTROLLED
Current Addendum II / canonical RTM / approved current interface data
        ↓
SOURCE-SUPPORTED CURRENT INTERFACE
2026-08-28 SCK CEN LOOP operational email
        ↓
HISTORIC RECURSIVE BOUND
D2.1 anticipated QCELL / combined-user response
        ↓
BIDDER / SELECTED-DESIGN EVIDENCE
LKT / ALAT topology, controls, utilities, calculations
        ↓
VERIFICATION
FAT / SAT / approved safe simulation or partial-test evidence
```

D2.1 is therefore used for the **anticipated behaviour of QCELLs as the combined Cryogenic User load seen by QPLANT**, not as current selected-design authority.

## Owner disposition vocabulary

- **KEEP** — retain the requirement and current acceptance intent.
- **KEEP / CLARIFY** — retain the requirement, but clarify timing, ownership, interface or evidence route.
- **DO NOT RELAX** — bidder deviation or reduced performance should not be accepted as satisfying the current predicate.
- **EQUIVALENT PROOF MAY BE ACCEPTABLE** — the test method may change only if an approved alternative demonstrates the same acceptance predicate.

## Review matrix

| Review point | Canonical anchor | D2.1 / current LOOP evidence role | LKT native evidence | ALAT native evidence | Owner first pass | Closure / negotiation evidence required |
|---|---|---|---|---|---|---|
| Combined QCELL/user response during LOOP | RTM-014; RTM-024 | D2.1 supplies a historical aggregate QCELL/user behavioural challenge profile; current Cryogenic User Transient Model remains controlling. | OFFER-21 / OFFER-22; LKT offer excerpt pp. 9, 38–39; T.13: TEC_ID_060, TEC_ID_063..066, TEC_ID_069, TEC_ID_070; Offer pp. 59–60. | C1462 abnormal-event rows; ALAT Offer pp. 295–296; ALAT-R08. | **KEEP / CLARIFY** | Current model shall show the combined user inventory/return-flow/pressure/thermal response and explain any material departure from D2.1. |
| LOOP electrical abnormal-event sequence | RTM-051; RTM-258 / OFFER-21 | Current email supplies automatic normal→backup transfer, 15 min preferred / 30 min maximum before one HP is energised, ~1–2 h peak backup load, manual return to normal. | OFFER-21, excerpt p. 9: one recovery compressor on emergency power up to ~110 g/s; UPS-backed controls/valves; instrument-air dependence. | ALAT-R08; ALAT Offer pp. 295–296; nominal ~80 g/s LOOP recovery and expected higher-frequency point subject to utilities. | **KEEP / CLARIFY** | One time-sequenced load/state table for 0–15, 15–30, 30–120 and >120 min, including HP start/continuous demand and all support loads. |
| Pre-HP bridge: first 15–30 min | RTM-258; RTM-260; RTM-261 / OFFER-21, OFFER-22 | D2.1 is most useful here as a historical user-side challenge profile before active HP recovery can be credited. | T.13 refs above; LKT recovery argument is not closure where suction/HP is assumed available at event onset. | ALAT-R08; preliminary recovery philosophy does not close the pre-start interval. | **DO NOT RELAX** | Selected Line-S/WSH effective volume, initial P/T, user inflow profile, valve/control sequence, relief headroom and no-loss calculation for the full pre-start interval. |
| Abnormal/LOOP recovery ≥100 g/s | RTM-261 / OFFER-22 | Current site interface indicates an approximate one-HP cap near 100 g/s; this is an interface point, not a relaxed RTM. | OFFER-22 pp. 38–39; ~110 g/s claimed; T.13 TEC_ID_060, 063..066, 069, 070. | ALAT-R08; ~80 g/s nominal at ~275 kW; ~100 g/s expected near ~340 kW, dependent on power/water. | **DO NOT RELAX** | Guaranteed accepted one-HP operating point, duration, inlet/outlet conditions, electrical/cooling demand and proof of no inventory loss. |
| ≤1% helium inventory loss | RTM-260 / OFFER-22 | D2.1 may challenge the transient, but current RTM defines the loss predicate. | OFFER-21/22 controlled gaps: no quantified full loss result / full inventory closure; LKT expects temporary venting for pressure peaks in some cases. | ALAT-R08: PSV/burst-disk and loss-of-vacuum relief vent to atmosphere; excess-flow disposition includes venting. | **DO NOT RELAX** | Event-by-event helium mass balance through buffering, recovery and relief; accepted loss boundary and instrumentation/measurement method. |
| Short 200 g/s transient / high return | RTM-260; RTM-261 | Historic D2.1 order-of-magnitude spikes are supporting only; current controlled event envelope governs. | OFFER-22: normal intake ~125 g/s; 110 g/s LOOP; possible temporary venting; full 200 g/s no-loss proof not demonstrated. | ALAT-R08 / abnormal-event rows; recovery and venting path require explicit disposition. | **KEEP / CLARIFY** | Selected-design calculation/simulation showing Line-S/WSH pressure trajectory, active recovery, relief margin and final helium-loss outcome. |
| Instrument-air endurance and ownership | RTM-433; supporting link to RTM-258/260/261 | Current LOOP email adds no new instrument-air evidence. | OFFER-21 states dependence on instrument air; controlled gap includes missing instrument-air endurance. | ALAT-R09; ALAT Offer p. 322: 6 h requirement to be specified, but instrument-air buffer stated outside ALAT supply scope. | **KEEP / CLARIFY** | Freeze design/supply/install ownership, required autonomy, storage/pressure basis, failure consequence and acceptance test. |
| Cooling-water / utility support for one-HP recovery | RTM-428; RTM-258; RTM-261 | Current email makes support utilities part of the same timeline; a nominal utility rating alone does not prove the function. | OFFER-21/22: one recovery compressor depends on cooling water; emergency-load list and transient proof remain incomplete. | ALAT-R08: ~80/~100 g/s recovery explicitly dependent on available backup power and water capacity. | **KEEP / CLARIFY** | Continuous and starting electrical load, cooling-water duty/flow/temperature, heat rejection, distribution path, one-failure consequence and duration margin. |
| QPS:CIS abnormal-event state machine | RTM-013..015; RTM-298..309; supporting OFFER-28 | D2.1 acts as a stimulus/challenge profile; current control sequence and setpoints remain controlled implementation evidence. | Exact LKT native control item IDs for this specific LOOP bridge are **not yet source-bound**; do not infer them. Use OFFER-21/22 and formal QPS:CIS/FAT evidence returned in negotiation. | ALAT-E01: Offer p. 306 states non-compliance with AD_05.01 due to Siemens protocol requirements. ALAT-E03: matrix items 1472, 1474, 1501, 1502, 1503; C1462 Offer p. 312 states MIS not foreseen at this stage. | **DO NOT RELAX** for required interfaces; **KEEP / CLARIFY** for implementation detail | Cause/effect, state transitions, automatic backup transfer, load shedding, hold/abort, recovery permissions, operator actions, alarms/interlocks and failure handling. |
| QPS↔MIS abnormal-event boundary | RTM-372 | Current LOOP review must identify which event/status/interlock signals cross the hardwired slow-interlock boundary. | Exact LKT native row for this bridge remains to be recovered; mark **SOURCE GAP**, not compliant by silence. | ALAT-E03; matrix items 1472, 1474, 1501, 1502, 1503; C1462 Offer p. 312. | **DO NOT RELAX** | Approved signal/interface list, ownership, fail-safe behaviour, test method and controlled mapping to AD_05.01 / AD_05.03. |
| Historian / event chronology | RTM-308 | Needed to reconstruct the full LOOP sequence and compare actual user/QPS response with current model and historical D2.1 envelope. | No exact native LKT row bound in this LOOP slice; require evidence in QPS:CIS return. | ALAT controls architecture remains open under E03 and related controls blocks. | **KEEP** | Time-synchronised record of power loss, transfer, user response, HP start, valve states, flow/pressure, alarms/interlocks, manual retransfer and restoration. |
| Restoration to normal circulation and power | RTM-262 / OFFER-22 | Current email establishes manual operator-triggered return to normal power; RTM remains authority for restoring normal helium circulation. | OFFER-22 recovery strategy provides architecture evidence but no complete accepted restoration sequence. | ALAT-R08 recovery philosophy does not close end-to-end restoration. | **KEEP / CLARIFY** | Stepwise exit criteria, operator authority, normal-power retransfer, compressor/valve sequence, process stabilisation criteria and failure fallback. |
| FAT/SAT programme and approval | RTM-491..495; OFFER-39 | LOOP is a bounded abnormal-event verification dependency; it does not automatically require a full live site blackout test. | T.15: TEC_ID_119, TEC_ID_120, TEC_ID_124; Offer p. 62. LKT proposes DDS-based FAT outline rather than a comprehensive acceptance programme; end-to-end authority/timing remain open. LKT-D10 source: 7.2 Compliance Matrix Technical Addendum II + Technical Proposal §6.5.1. | ALAT FAT/SAT family: C1462 Offer pp. 336–351. ALAT-A06: pp. 347–351 excludes several SAT tests. ALAT-A01: p. 351 + ALAT-T&C-092 proposes no particular WSH SAT / commissioning checks and separately deemed PAC language. | **KEEP** | Approved programme before test, RACI, resources, test boundaries, instrumentation, records, acceptance criteria, NCR/retest and configuration-control rules. |
| LOOP controls/I/O FAT | RTM-497; RTM-498; RTM-309 | Safe simulation can reproduce the event sequence without physically removing site supply where unsafe or impracticable. | LKT-D10 / T.15 refs above; exact LOOP test case to be returned. | C1462 pp. 336–351; ALAT-A06 pp. 347–351; control architecture evidence under E01/E03. | **EQUIVALENT PROOF MAY BE ACCEPTABLE** | Functional cause/effect, emergency-power I/O, utility/valve/sensor paths, interlocks, load shedding and HP-start timing tested by approved FAT/simulation route. |
| Site-level LOOP response verification | RTM-518 plus approved SAT programme | Current site conditions should close what cannot be proven at FAT; a full live LOOP event is not inferred as mandatory solely from this review. | LKT T.15 + returned site test method required. | ALAT FAT/SAT family plus returned site method required. | **EQUIVALENT PROOF MAY BE ACCEPTABLE** | Approved partial/live/simulated SAT method demonstrating the same predicate: transition, limited-service state, recovery capacity, support utilities, records and restoration. |

## Provisional owner conclusions for peer review

### Requirements to retain without relaxation

- **RTM-260 ≤1% inventory-loss predicate.**
- **RTM-261 ≥100 g/s abnormal/LOOP recovery predicate.**
- Required QPS:CIS / MIS interface and fail-safe controls obligations.
- End-to-end acceptance-programme responsibility and pre-test approval.
- Recovery/restoration sequence and objective evidence.

These are system-level predicates. Bidder inability to demonstrate them at offer stage is an evidence/deviation issue, not by itself evidence that the requirement is too stringent.

### Areas where clarification is more appropriate than relaxation

- Exact NA.ES02/QPS electrical interface and accepted one-HP emergency operating point.
- Ownership and endurance of instrument-air backup.
- Cooling-water distribution and margin for the emergency compressor.
- Manual retransfer authority and detailed restoration sequencing.
- Which LOOP functions are demonstrated at FAT, SAT, integrated commissioning or approved simulation.

### Test-method flexibility

The acceptance **predicate should be retained**, while the method can be negotiated where a live event is unsafe, impracticable or not technically representative. An alternative is acceptable only when it provides equivalent objective evidence and is approved in the test programme.

## Peer-review questions

1. Do reviewers agree that D2.1 remains useful as a historical QCELL/user behavioural bound while the current transient model remains authoritative?
2. Is the 15 min preferred / 30 min maximum HP-start boundary an accepted site-interface design input, or still a provisional assumption requiring NA.ES02 confirmation?
3. Should ~100 g/s be treated as the accepted site one-HP emergency interface point, with bidder claims above it requiring explicit electrical/load approval?
4. Is any relaxation of RTM-260 or RTM-261 technically justified by current evidence, or should both remain non-negotiable pending selected-design proof?
5. Which support utilities are SCK CEN supply versus Contractor scope, and where is the acceptance boundary?
6. Which abnormal-event control functions must be proven at FAT versus SAT/integrated site testing?
7. For any omitted live LOOP test, what exact simulation/partial-test package would constitute equivalent proof?

## Control note

This matrix is a **review navigation and owner-assessment artifact**. It creates no compliance credit, requirement closure, canonical OFFER edge or BT/PCA change. Bidder-native IDs are preserved where source-bound; unresolved native-reference gaps remain explicitly marked.
