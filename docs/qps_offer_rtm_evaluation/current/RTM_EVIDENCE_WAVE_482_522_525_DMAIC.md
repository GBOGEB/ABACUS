# QPS granular evidence wave — RTM-482 and RTM-522..525

Status: **EVIDENCE RECONCILIATION / DMAIC CHECKPOINT — NO REQUIREMENT CLOSURE**

## Why this wave is next

The refreshed exact-v24 unresolved selector, validated by Actions run `33249301687`, detected 146 governed reviewed RTMs and 576 unresolved ranked RTMs. The next five unresolved items are:

| RTM | v24 rank | Tier | Gate | Weighted S | BT Win % | BT λ index | Primary dimension |
|---|---:|---|---|---:|---:|---:|---|
| RTM-482 | 44 | T1 Primary | No | 76.666667 | 94.0361 | 51.8933 | Reliability |
| RTM-522 | 45 | T1 Primary | No | 67.333333 | 93.6893 | 50.2298 | Reliability |
| RTM-523 | 46 | T1 Primary | No | 67.333333 | 93.6893 | 50.2298 | Reliability |
| RTM-524 | 47 | T1 Primary | No | 67.333333 | 93.6893 | 50.2298 | Reliability |
| RTM-525 | 48 | T1 Primary | No | 67.333333 | 93.6893 | 50.2298 | Reliability |

This wave deliberately shifts from requirement-routing infrastructure toward returned evidence, local acceptance criteria, DOW/KEB feedback capture, and internally closable verification obligations.

## Authority boundary

- Addendum II remains contractual authority.
- The canonical 722/50 workbook remains the governed RTM numbering/text/crosswalk projection.
- Exact v24 BT/PCA controls review priority only.
- OFFER links are evidence interfaces, not requirement authority.
- Applicant replies and bidder compliance matrices remain returned evidence only and are not assimilated into requirement wording.
- No row below is marked compliant or closed by this checkpoint.
- The QPS COST_Master accepted-release HOLD remains independent and is not advanced here.

## Evidence-state matrix

| RTM | Canonical obligation | OFFER boundary | Returned evidence observed | Current disposition | Internally closable now | External / returned evidence still required |
|---|---|---|---|---|---|---|
| RTM-482 | Commissioning shall include all required performance/capacity/quality validation before SAT, including ≥24 h WCS long-duration run, cycle-gas purity, oil-removal validation, dryer-capacity validation, vibration spectral analysis and QPS:CIS interface-logic validation. | No OFFER link expected. | ALAT explicitly accepts several commissioning elements, but proposes only a visual oil check and states dryer-capacity validation will not be performed; the collated bidder review classifies RTM-482 as a deviation/issue. | **OPEN — substantive test-scope gap** | Define owner acceptance matrix, measurable criteria, data channels, sampling/record retention and allowed equivalent validation methods. | Contractor commitment to a complete commissioning programme and objective evidence for oil removal, dryer capacity, vibration and interface-control validation. |
| RTM-522 | TS-SB SAT cooling-capacity demonstration: 4K-SB POINT_A → TS-SB POINT_B, no VLP compressors, ≥24 h steady operation, return to A, no discontinuity, achieved values meet performance requirements. | OFFER-39 supporting/contextual only. | ALAT records the no-VLP condition as compliant, but marks the required test execution, transition, 24 h run and return sequence as deviations and limits SAT to tests listed in its technical proposal. | **OPEN — negotiation / SAT scope** | Freeze the test sequence, point definitions, instrumentation, steady-state criterion, discontinuity definition and acceptance calculations. | Contractor acceptance of the full sequence/duration or a formally approved technically equivalent demonstration. |
| RTM-523 | 10K-SB SAT cooling-capacity demonstration: A=4K-SB, B/C=10K-SB predefined points, no VLP compressors, ≥12 h at B and ≥12 h at C, transitions and return, no discontinuity, performance acceptance. | OFFER-39 supporting/contextual only. | ALAT accepts no-VLP operation but records the operating-point definition/execution/durations and associated acceptance elements as suggestions/deviations, again restricting SAT to its proposal. | **OPEN — negotiation / SAT scope** | Define B/C distinction from RTM-503, steady-state windows, continuous logging and transition acceptance. | Contractor commitment to both 10K points and required sustained runs, or governed equivalent accepted by SCK CEN. |
| RTM-524 | 4K-SB SAT test: A=predefined 4K-SB, B=standby point, LHe baths above minimum levels, ≥48 h at A with sub-atmospheric compressors off, then transition to B including compressor start-up; no discontinuity and performance acceptance. | OFFER-39 supporting/contextual only. | ALAT accepts minimum LHe level and compressor-off conditions, but marks execution, the 48 h run and transition/start-up requirement as deviations; acceptance criteria are treated as suggestions. | **OPEN — negotiation / SAT scope** | Define bath-level evidence, exact start/end timestamps, compressor-status channels, restart transition success criteria and continuous-operation rules. | Contractor acceptance of 48 h demonstration and transition/start-up test, with retained SAT data. |
| RTM-525 | 2K-OP/2K-SB SAT cooling-capacity demonstration at Standby, predefined 2K-OP and Design Point; three back-to-back runs of at least 48 h each; no discontinuity and performance acceptance. | OFFER-39 supporting/contextual only. | ALAT records the operating points, execution, three back-to-back runs, all three 48 h durations and acceptance elements as deviations/suggestions under its proposal-only SAT limitation. | **OPEN — highest evidence burden in this wave** | Freeze the three-point test architecture, test-boundary definition, reset/non-reset rule, required logged variables and statistical/acceptance treatment. | Explicit Contractor agreement to the 3×48 h campaign or a formally approved equivalent with demonstrated equal or greater verification strength. |

## Evidence interpretation

### Returned evidence is not closure

The applicant compliance matrix is useful because it exposes the exact commercial/technical position, but it does not change the contract requirement. In particular, ALAT's repeated statement that no tests beyond its technical proposal will be checked is a scope limitation that must be resolved, not an alternative requirement definition.

For RTM-522..525, OFFER-39 is intentionally only supporting/contextual evidence. A concise FAT/SAT strategy response cannot replace the detailed SAT requirements.

### LKT evidence state

The current collated review package reports RTM-482 as a bidder-level `Deviation / issue`. In this pass, exact granular LKT rows for RTM-522..525 were not independently recovered with sufficient source precision to quote. They therefore remain **RETURNED-EVIDENCE LOOKUP REQUIRED**, not `no exception` and not `compliant` by inference.

## DMAIC checkpoint

### Define

**Problem:** the highest-ranked unresolved reliability requirements now concern verification scope, not missing framework. Returned evidence shows material disagreement or incomplete commitment on commissioning/SAT demonstrations.

**CTQs:**

- required test sequence is preserved;
- minimum sustained duration is objective and auditable;
- operating/test points are configuration-bound to RTM-503 and the actual design;
- all required process variables are continuously logged with calibrated instrumentation;
- `no discontinuous operation` has an agreed event/reset definition;
- acceptance uses the contractual performance requirements, not a bidder-selected reduced subset;
- deviations/equivalents require governed approval.

### Measure

For this wave:

- 5/5 items are exact-v24 **T1 Primary**;
- 5/5 are reliability-led;
- 4/5 are detailed SAT cooling-capacity demonstrations;
- 4/5 have canonical OFFER-39 links classified only as supporting/contextual;
- RTM-482 has no canonical OFFER link;
- ALAT returned evidence contains explicit substantive deviation/suggestion content for all five;
- no item currently has sufficient returned evidence for contractual closure.

### Analyse

The dominant failure mode is **verification dilution**: the bidder proposes a narrower or differently structured test programme than the contract specifies. The technical risk is not merely documentary. Shortened runs, omitted transitions, omitted dryer/oil validation, or bidder-selected operating points can conceal thermal instability, contamination breakthrough, reliability/recovery weaknesses and control-transition defects.

RTM-525 carries the largest single SAT occupation burden, but its 3×48 h structure also provides the strongest evidence for sustained 2 K capability across standby, predefined operation and design-point conditions. Any reduction should therefore be treated as a verification-equivalence decision requiring quantitative justification, not schedule convenience.

### Improve

Create one owner-controlled **QPS Commissioning/SAT Acceptance Matrix** for these five RTMs with, per test:

1. canonical RTM and requirement element;
2. operating state / POINT definition;
3. preconditions;
4. required equipment state (including VLP/sub-atmospheric compressors);
5. duration and steady-state definition;
6. mandatory logged variables and sampling rate;
7. permitted interruptions/reset logic;
8. acceptance calculation and tolerance;
9. bidder proposed method;
10. gap / deviation;
11. SCK CEN disposition;
12. evidence file / run identifier.

This matrix is an internally closable product obligation because SCK CEN can define the acceptance architecture now, before receiving the final Contractor SAT programme. It does **not** close the RTMs themselves.

### Control

- Bind the matrix to the canonical 722 RTM IDs and controlled POINT definitions.
- Treat any changed test duration/sequence as a governed deviation/equivalence request.
- Require raw time-series data plus signed SAT report summaries; do not rely on pass/fail prose alone.
- Record DOW/KEB comments as derived reviewer evidence until explicitly promoted.
- Re-run the exact-v24 unresolved selector only after a governed review/evidence status record is merged; do not remove an RTM merely because evidence was routed to it.

## Immediate action queue

| Priority | Action | Owner class | Closure type |
|---:|---|---|---|
| 1 | Build the five-RTM Commissioning/SAT Acceptance Matrix from canonical test elements and required logged variables. | SCK CEN / internal engineering | **Internally closable product obligation** |
| 2 | Issue focused technical RFI/negotiation points for ALAT on omitted/reduced commissioning and SAT tests, especially RTM-525 3×48 h. | SCK CEN + DSBT/technical support | Returned evidence required |
| 3 | Recover exact LKT granular rows for RTM-482 and RTM-522..525 and classify against the same matrix. | Evidence reconciliation | Returned evidence lookup |
| 4 | Map existing DOW/KEB/transient/RAM analyses to individual acceptance calculations without promoting them as contract evidence. | Internal engineering | Derived evidence |
| 5 | At the next DMAIC checkpoint, separate `owner acceptance definition complete` from `Contractor evidence accepted`; only the latter can support requirement closure. | Governance | Control gate |

## DOW / KEB / PCA-BT status

- **PCA/BT:** exact v24 values above are governed prioritisation metadata and define this wave's order.
- **DOW/KEB:** potentially relevant reliability/transient work exists in the project evidence estate, but no explicit governed DOW/KEB acceptance for these five RTMs was located in this pass. Status remains **DERIVED / PROPOSED EVIDENCE — PROMOTION REQUIRED**.
- **Bidder evaluation:** downstream only; its value here is to identify gaps and negotiation questions.

## Next checkpoint

Do not create another generic routing layer after this file. The next implementation step is the owner-controlled granular acceptance matrix itself, followed by exact LKT evidence recovery and bidder-by-bidder gap disposition. Only then should the refreshed v24 queue move to RTM-161 / RTM-351 / RTM-517 or later entries.
