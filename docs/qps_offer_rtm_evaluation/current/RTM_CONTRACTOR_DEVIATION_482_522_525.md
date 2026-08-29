# Contractor deviation register — RTM-482 and RTM-522..525

Status: **RETURNED CONTRACTOR POSITION / OWNER DISPOSITION REQUIRED — NO REQUIREMENT CLOSURE**

## Governing order

This register is subordinate to the Contract/RTM and the Owner-controlled acceptance baseline. It does not rewrite requirements.

**Contract/Addendum II → canonical RTM → Owner acceptance definition → Contractor position → delta/deviation → Owner disposition → verification evidence → closure.**

A Contractor statement of compliance, suggestion, clarification, deviation or proposed test method is evidence of the Contractor position only. Where that position reduces, omits or changes a contractual test state, sequence, duration, acceptance criterion or required validation, the contractual baseline remains unchanged unless SCK CEN explicitly approves a governed deviation/equivalence.

## Disposition vocabulary

| Code | Meaning | Effect on RTM |
|---|---|---|
| C | Contractor position aligns with the Owner-controlled contractual baseline and objective evidence is identified. | May support later closure; does not close by itself. |
| CL | Clarification required to determine whether the Contractor position actually meets the baseline. | Open. |
| D | Contractor position omits, reduces or changes a contractual obligation. | Open deviation; Contractor action required. |
| EQ | Contractor proposes an alternative verification method that could be technically equivalent. | Open until equivalence is demonstrated and explicitly approved by Owner. |
| NE | No sufficiently precise returned evidence recovered in this pass. | Open; evidence recovery required. |

## ALAT — granular deviation disposition

| RTM | Owner-controlled baseline | Returned ALAT position | Classification | Contractor action required | Owner disposition |
|---|---|---|---|---|---|
| RTM-482 | Commissioning validation includes ≥24 h WCS compressor operation, cycle-gas purity, oil-removal performance, dryer-capacity validation, vibration spectral analysis and QPS:CIS interface/control-logic validation before SAT. | Returned matrix accepts several commissioning elements but proposes visual oil inspection and states dryer-capacity validation will not be performed. | **D** | Revise commissioning programme to demonstrate every contractual validation element, or submit a technically substantiated equivalent method for explicit approval. Visual inspection alone shall not silently replace the required oil-removal validation. | **REJECT AS BASELINE CHANGE.** Contract/RTM remains controlling. Equivalent methods may be reviewed only as explicit EQ submissions. |
| RTM-522 | TS-SB SAT: POINT_A 4K-SB → POINT_B TS-SB; VLP compressors not in operation; ≥24 h steady operation at B; return to A; no discontinuity; contractual performance achieved. | No-VLP condition is accepted, but ALAT repeatedly limits SAT to tests in its technical proposal and marks required execution/transition/24 h/return elements as deviations. | **D** | Confirm full contractual sequence and ≥24 h duration, with retained continuous data; otherwise submit a formal deviation/equivalence request identifying the proposed substitute and quantitative verification strength. | **REJECT REDUCED TEST SCOPE pending governed deviation/equivalence.** |
| RTM-523 | 10K-SB SAT: A=4K-SB, B/C=10K-SB predefined points; VLP compressors off; ≥12 h steady operation at B and ≥12 h at C; required transitions/return; no discontinuity; performance achieved. | No-VLP operation is accepted, but operating-point/test execution/duration elements are treated as suggestions/deviations under ALAT's proposal-only SAT limitation. | **D / CL** | Explicitly map proposed B and C test points to controlled RTM-503 definitions and commit to both ≥12 h runs and transitions, or submit a governed alternative. | **CLARIFY POINT MAPPING; REJECT duration/sequence reduction unless approved EQ.** |
| RTM-524 | 4K-SB SAT: minimum LHe levels; ≥48 h at predefined 4K-SB POINT_A with sub-atmospheric compressors off; transition to Standby POINT_B including compressor start-up; no discontinuity; performance achieved. | ALAT accepts bath-level and compressor-off conditions but marks test execution, ≥48 h run and transition/start-up obligation as deviations; acceptance elements are suggestions. | **D** | Commit to ≥48 h sustained test and controlled transition/start-up demonstration with continuous data, or submit quantified equivalent verification proposal. | **REJECT REDUCED duration/transition scope pending approved EQ.** |
| RTM-525 | 2K SAT: Standby, predefined 2K-OP and Design Point; three back-to-back runs, each ≥48 h; no discontinuity; contractual performance achieved. Minimum sustained run time = **144 h**, excluding preparation/transitions. | ALAT marks operating points, execution, the three-run structure, each 48 h duration and acceptance elements as deviations/suggestions under its proposal-only limitation. | **D — MATERIAL** | Confirm the full 3 × ≥48 h back-to-back campaign and retained data. If proposing reduction, provide a formal equivalence case demonstrating at least equal verification of sustained 2 K stability, capacity, transitions and reliability; schedule/cost convenience is not technical equivalence. | **REJECT REDUCED 2 K campaign as a unilateral change. Owner approval required for any alternative.** |

## LKT — evidence recovery lane

No LKT position is to be inferred from absence of a flagged row. The same Owner baseline applies to both Contractors.

| RTM | Current LKT state | Required next action |
|---|---|---|
| RTM-482 | **NE — exact granular returned evidence still to be bound** | Recover the LKT compliance/technical-proposal source statement and classify C / CL / D / EQ against the Owner baseline. |
| RTM-522 | **NE** | Same, including exact proposed TS-SB sequence and duration. |
| RTM-523 | **NE** | Same, including B/C point definitions and both 12 h periods. |
| RTM-524 | **NE** | Same, including 48 h run and compressor start-up transition. |
| RTM-525 | **NE** | Same, including three back-to-back ≥48 h 2 K runs. |

`NE` is deliberately not interpreted as compliance or deviation.

## Contractor response required

For every D or EQ row, the Contractor response shall identify:

1. the exact RTM and contractual element affected;
2. whether the Contractor now accepts the contractual baseline without exception;
3. if not, the exact proposed change;
4. technical justification rather than schedule/cost preference alone;
5. proposed verification method, instrumentation and data set;
6. quantitative demonstration that an EQ proposal has equal or greater verification strength;
7. impacts on reliability, availability, performance, safety, interfaces and acceptance schedule;
8. the controlled document/procedure in which the commitment will be incorporated.

A generic reference to the Contractor technical proposal is insufficient where the proposal does not explicitly preserve every contractual element.

## Owner decision gate

Owner disposition is one of:

- **ACCEPT BASELINE** — Contractor confirms the Contract/RTM requirement as written; evidence still required at the defined lifecycle gate.
- **REQUEST CLARIFICATION** — ambiguity remains; no baseline change.
- **REJECT DEVIATION** — Contractor shall comply with the contractual baseline.
- **REVIEW EQUIVALENCE** — technical alternative is assessed against an explicit equivalence case; no change until approved.
- **APPROVE GOVERNED DEVIATION** — only through the applicable contractual change/deviation authority, with traceable impact and updated controlled records.

No bidder evaluation score, OFFER response, BT/PCA rank, DOW/KEB analysis or reviewer comment can by itself exercise this authority.

## Immediate negotiation/RFI questions — ALAT

| ID | RTM | Question / required confirmation |
|---|---|---|
| ALAT-SAT-01 | RTM-482 | Confirm that the commissioning programme will validate oil-removal performance and dryer capacity as required. If an alternative to the specified validation is proposed, provide the method, acceptance basis and equivalence justification. |
| ALAT-SAT-02 | RTM-522 | Confirm execution of the complete A→B, ≥24 h TS-SB, B→A sequence with VLP compressors off and continuous retained evidence. |
| ALAT-SAT-03 | RTM-523 | Confirm controlled POINT_B and POINT_C definitions and ≥12 h steady operation at each point, including required transitions and return. |
| ALAT-SAT-04 | RTM-524 | Confirm ≥48 h at 4K-SB POINT_A with sub-atmospheric compressors off, followed by the required transition to Standby including compressor start-up. |
| ALAT-SAT-05 | RTM-525 | Confirm three back-to-back ≥48 h runs at Standby, predefined 2K-OP and Design Point. If not accepted, submit a formal deviation/equivalence proposal with quantitative verification-strength comparison. |
| ALAT-SAT-06 | 482/522..525 | Identify all instrumentation, sample rates, historian tags, calibration evidence and raw-data deliverables proposed for Owner acceptance. |
| ALAT-SAT-07 | 522..525 | Define what ALAT considers a test interruption/discontinuity and the conditions that reset the contractual sustained-duration clock. Owner acceptance is required. |

## Control / closure rule

This register closes a **review action** only when the Contractor position is explicit and Owner disposition is recorded. It does **not** close the underlying RTM. RTM closure remains evidence-based at the contractual verification gate.

The accepted-release/local-PC receipt HOLD is independent and unchanged.
