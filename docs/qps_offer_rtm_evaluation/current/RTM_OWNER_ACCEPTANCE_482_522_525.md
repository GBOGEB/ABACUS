# Owner-controlled acceptance baseline — RTM-482 and RTM-522..525

Status: **OWNER REQUIREMENT / ACCEPTANCE DEFINITION — CONTRACT CONTROLLED**

This document intentionally defines the Owner baseline first. It is derived from Addendum II and the canonical 722 RTM projection. Contractor proposals, replies, limitations and deviations do **not** modify this baseline. They are assessed afterwards against it.

## Control rule

For every requirement element the order is:

**Contract / RTM → Owner acceptance criterion → Contractor offered method/evidence → delta/deviation → Owner disposition → verification evidence → closure.**

A Contractor deviation is therefore a delta **from** the controlled baseline, never an alternative source for defining the baseline.

## RTM-482 — commissioning validation before SAT

Owner acceptance baseline:

| Element | Owner-controlled requirement / acceptance |
|---|---|
| Phase | Commissioning, completed before SAT so SAT can subsequently be executed efficiently. |
| Scope | All required performance, capacity and quality tests necessary to validate compliance with the Technical Specification. |
| SAT helium inventory | Required helium inventory available before SAT execution. |
| WCS long-duration demonstration | Compression station operates continuously for **minimum 24 h** at specified conditions. |
| Long-run purpose | Demonstrate thermal stability and mechanical reliability. |
| Cycle-gas purity | O2, N2 and H2O remain at or below guaranteed values throughout the relevant long-duration operation. |
| Oil removal | Oil-removal efficiency is objectively validated; a visual check alone is not presumed equivalent. |
| Dryer | Dryer capacity is objectively validated; controlled water injection is an identified possible method, not the only permitted method. Any alternative must demonstrate equivalent capacity evidence. |
| Vibration | Vibration spectral analysis is performed to identify potential vibration sources. |
| Interfaces | All interface control logic between QPS:CIS and MCS, MIT and MIS is validated. |
| Records | Time-correlated raw data, test configuration, calibrated-channel list, events/alarms, deviations and signed test report retained as acceptance evidence. |

**Owner state:** acceptance definition can be completed internally. RTM compliance remains open until Contractor execution/evidence is accepted.

## RTM-522 — TS-SB cooling-capacity SAT

| Element | Owner-controlled requirement / acceptance |
|---|---|
| POINT_A | QPLANT Predefined Test Point per RTM-503 within **4K-SB**. |
| POINT_B | QPLANT Predefined Test Point per RTM-503 within **TS-SB**. |
| VLP compressors | **Not operating** during the test run. |
| Sequence | Start A → transition A→B → operate at B → return B→A. |
| Duration | **At least 24 h steady-state at POINT_B.** |
| Continuity | No discontinuous operation during the full testing period. |
| Performance | Achieved values comply with specified performance requirements. |
| Evidence | Continuous state/process logging sufficient to prove point, compressor state, transition, steady duration, continuity and performance. |

## RTM-523 — 10K-SB cooling-capacity SAT

| Element | Owner-controlled requirement / acceptance |
|---|---|
| POINT_A | RTM-503 predefined point within **4K-SB**. |
| POINT_B | RTM-503 predefined point within **10K-SB**. |
| POINT_C | RTM-503 predefined point within **10K-SB**. |
| VLP compressors | **Not operating** during the test run. |
| Sequence | A → B → C → contractual return/completion sequence. |
| Duration B | **At least 12 h steady-state.** |
| Duration C | **At least 12 h steady-state.** |
| Continuity/performance | No discontinuous operation; achieved values comply with specified performance requirements. |
| Owner prerequisite | B and C must be configuration-bound to the applicable RTM-503 definitions before SAT; they cannot be collapsed into one bidder-selected point without approved equivalence. |

## RTM-524 — 4K-SB cooling-capacity SAT

| Element | Owner-controlled requirement / acceptance |
|---|---|
| POINT_A | RTM-503 QPLANT Predefined Test Point within **4K-SB**. |
| POINT_B | **QPLANT Standby Point.** |
| Inventory condition | All liquid-helium baths at least at minimum operating level. |
| Main run | **At least 48 h at POINT_A.** |
| Sub-atmospheric compressors during main run | **Not running.** |
| Transition | After the run, transition to POINT_B including start-up of the sub-atmospheric compressors. |
| Continuity/performance | No discontinuous operation; achieved values comply with specified performance requirements. |
| Evidence | Bath levels, compressor states, timestamps, process variables, transition response and alarms/events are retained continuously. |

## RTM-525 — 2K-OP / 2K-SB cooling-capacity SAT

| Element | Owner-controlled requirement / acceptance |
|---|---|
| POINT_A | **QPLANT Standby Point.** |
| POINT_B | RTM-503 QPLANT Predefined Test Point within **2K-OP**. |
| POINT_C | **QPLANT Design Point.** |
| Sequence | **Three runs back-to-back.** |
| Run 1 | **At least 48 h at POINT_A.** |
| Run 2 | **At least 48 h at POINT_B.** |
| Run 3 | **At least 48 h at POINT_C.** |
| Minimum scheduled sustained-test time | **144 h**, excluding preparation, transitions and any restart/reset time. |
| Continuity | No discontinuous operation during the full testing period. |
| Performance | Achieved values comply with specified performance requirements. |
| Reset principle | An interruption that breaks the contractual continuous/back-to-back demonstration is not silently deducted from elapsed time. Treatment must be agreed in the approved SAT procedure; a material interruption requires restart/repetition of the affected acceptance window unless SCK CEN formally accepts otherwise. |

## Common Owner measurement definition

The SAT/commissioning procedure shall convert each contractual criterion into a directly auditable record. At minimum the Owner matrix shall identify:

- controlled RTM ID and requirement element;
- controlled operating point/state and configuration;
- preconditions and required equipment status;
- test start/end timestamps and minimum duration;
- required process variables and calibrated instrumentation;
- sampling/logging interval adequate to demonstrate stability and transitions;
- steady-state definition where the contract uses steady-state operation;
- event/alarm/trip record and discontinuity classification;
- calculation used to compare achieved capacity/performance with specified values;
- raw-data file/run identifier and signed report reference;
- deviation/equivalence identifier, if any, with explicit Owner disposition.

Numerical tolerances or sampling rates not explicitly stated in the Contract are **not invented here**. They shall be fixed in the Owner-approved test procedure using applicable controlled design/performance requirements and adequate measurement uncertainty.

# Contractor deviation layer — subordinate to Owner baseline

The following is a comparison layer only and does not rewrite the RTM.

| RTM | Contractor-returned position observed | Delta from Owner baseline | Required disposition |
|---|---|---|---|
| RTM-482 | Returned ALAT evidence limits/changes parts of the commissioning test scope, including visual oil checking and non-performance of dryer-capacity validation. | Objective validation scope is reduced relative to RTM-482. | Contractor to confirm full compliance or submit a specific equivalent method with technical justification and evidence strength for Owner approval. |
| RTM-522 | ALAT states SAT checks are limited to its technical proposal and records required execution/transition/24 h elements as deviations. | Required A→B→A sequence and ≥24 h steady TS-SB demonstration are not fully committed. | **Contractor deviation / negotiation item.** Require compliance or formal equivalence proposal. |
| RTM-523 | ALAT similarly limits tests and records required point/execution/duration elements as suggestions/deviations. | Contractual two-point 10K demonstration and sustained periods are not fully committed. | **Contractor deviation / negotiation item.** Require B/C coverage and durations or governed equivalence. |
| RTM-524 | ALAT records execution, 48 h run and transition/start-up elements as deviations. | Required sustained 4K-SB proof and transition evidence are reduced. | **Contractor deviation / negotiation item.** Require contractual test or governed equivalent. |
| RTM-525 | ALAT records the operating points, three back-to-back runs, each 48 h duration and acceptance elements as deviations/suggestions. | Material reduction of the strongest sustained 2 K SAT demonstration. | **Major Contractor deviation / negotiation item.** Baseline remains 3×48 h; any alternative must quantitatively demonstrate equal or greater verification strength and receive explicit Owner approval. |

## Deviation workflow

A Contractor-proposed change is acceptable for assessment only when it states: affected RTM element; proposed alternative; reason; technical equivalence argument; effect on performance/reliability/safety/interfaces; verification method; evidence to be delivered; schedule/cost consequence if relevant; and requested Owner disposition.

Allowed Owner dispositions are **ACCEPT CONTRACT BASELINE**, **REQUEST CLARIFICATION**, **ACCEPT EQUIVALENT WITH CONDITIONS**, or **REJECT DEVIATION**. No silence, OFFER wording or bidder matrix status constitutes acceptance.

## Closure gate

`Owner acceptance definition complete` is an internal engineering milestone. `RTM verified/closed` requires the Contractor to execute the accepted contractual/equivalent method and provide satisfactory objective evidence. These states shall remain separate in the RTM/evidence system.
