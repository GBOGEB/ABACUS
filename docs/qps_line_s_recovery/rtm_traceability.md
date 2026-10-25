# RTM Traceability Map

Status reconciled under ABACUS #1313.

The assumptions SSOT has zero open MDA gates.

The generated runtime verdict is `PROCEED_MDA`.

The statuses below distinguish MDA model/package readiness from engineering
and source evidence that remains unresolved.

## RTM-260

### RTM-260 interpretation

Credited abnormal recovery shall not lose more than one percent helium
inventory.

### RTM-260 current evidence

The reduced model and Applicant package include no-loss framing.

Final credited lost-mass evidence still depends on source/calibration closure
and recovery-path state.

### RTM-260 status

`EVIDENCE_PENDING`

## RTM-261

### RTM-261 interpretation

QPS shall cope with Line S / QRB.S return-flow context.

### RTM-261 current evidence

The scenario matrix covers 100, 112, 150, and 200 g/s contexts.

Current assumptions resolve V_eff, pressure limit, recovery power, and HP
capacity.

The source trace for `MDOT_IN_PRE_HP_MAX=112 g/s` remains unresolved.
112 g/s is not an RTM-292 use case (those are 0.1, 100, 150 and 200 g/s).
In this repository 112 g/s appears only as the HP compressor 72 Hz maximum
reference (`qplant/w53_p05m_hp_power_receipt.py`).

### RTM-261 status

`MDA_MODELLED_SOURCE_TRACE_PENDING`

## RTM-262

### RTM-262 interpretation

QPS shall recover normal helium circulation after the abnormal event.

### RTM-262 current evidence

HP/recovery capability is represented.

Appendix 8.4 is now source-bound to the locked D2.1 document.

The 23 / 23 mode inventory is bound to the embedded Appendix figures.
Abnormal/fallback valve-state evidence is partially extracted, while the
remaining mode topology and the full recovery procedure remain incomplete.

### RTM-262 status

`SOURCE_BOUND_PARTIAL`

## RTM-292

### RTM-292 interpretation

RTM-292 sets the flow conditions at QRB.S (Addendum II rev 146, p. 68,
"Warm Piping System (WPS) > Specificities for Line S interface"):

- nominal flow temperature: ambient temperature +/- 15 K;
- nominal return pressure: 1.1 bar +/- 5 mbar;
- minimum allowable pressure: 1.05 bar;
- mass-flow use cases: residual return <= 0.1 g/s continuous;
  uncontrolled reheating 100 g/s nominal with spikes to 150 g/s during
  6-8 h; QVE insulation-vacuum break spike up to 200 g/s for ~100 s;
- clean helium suitable for direct use.

RTM-293 (p. 69) adds that QPS design and operating sequences shall not let
the WPS.S pressure drop below the RTM-292 minimum.

RTM-292 states no maximum pressure or build-up ceiling. The earlier reading
"pressure build-up requirement" was wrong.

### RTM-292 current evidence

The wording is vendored verbatim in
`docs/qps_line_s_recovery/addendum2_rev146_rtm_292_293_061.json`
(cryoplant-project `b0dddd9b` contract extraction, contract JSON sha256
`16b56d57...`). `tests/test_rtm292_contract.py` checks it against the
`rtm_292_envelope` in `ssot_heat_loads.yaml` and the scenario flows.

`ASSUM-PLIMIT` (1.30 bar) is the `p_fullop_backpressure` value from the
He_line_safety sheet, not an RTM-292 value. Its nominal (1.10 bar) and
minimum (1.05 bar) components are RTM-292 values.

Pressure and t_available calculations exist.

### RTM-292 status

`SOURCE_BOUND`

## OFFER-22

### OFFER-22 interpretation

Applicant recovery strategy and maximum flow accepted from Line S.

### OFFER-22 current evidence

The generated Applicant package and scenario/recovery matrices provide the
bounded MDA model response.

Remaining source/calibration items are listed below.

### OFFER-22 status

`MDA_PACKAGE_READY_EVIDENCE_PENDING`

## REQ-130 / REQ-131

### REQ-130 / REQ-131 interpretation

Each QCELL shall stay at or below the defined Thermal Shield temperature
limit for the entire failure event. Both IDs carry the same wording
(Addendum II "Availability & Reliability", paragraphs 538 and 543 in
`qplant/canonical_master/attributes/requirements.json`).

In contract numbering they are the Class A and Class B bullets of RTM-061
(rev 146, p. 38): failure of sustaining 2 K operation (restored within
24 h) and failure of sustaining 2 K refrigeration (recovered within 5 days).
Class C allows the limit to be exceeded.

### REQ-130 / REQ-131 current evidence

`models/qps_line_s/loop_transient.py` `simulate()` integrates the TS Mass
temperature T_TS(t) during LOOP boil-off with the Tables 27-29 two-lump
model. It reports `ts_at_dryout_k` and a 10-minute `series` of T_TS.

`tests/test_loop_transient.py` pins the heat-load signs, the initial Q1
magnitude and the dry-out bracket of that model.

`tests/test_ssot_tables_contract.py` asserts that every Tables 27-29 value
in `models/qps_line_s/ssot_tables.py` equals the vendored contract rows in
`docs/qps_line_s_recovery/addendum2_rev146_tables_27_29.json`
(cryoplant-project W365 extraction, contract JSON sha256 `16b56d57...`).

The TS Mass lump is a thermal-shield proxy; QCELL-level temperatures are not
modelled. Rev 146 gives no number for the Thermal Shield temperature limit.
The closest contract data is Table 7, scenario TS-SB: line D ~40 K +/- 5 K
and line E ~60 K +/- 10 K. The limit stays an owner question, so no test
compares T_TS(t) with it.

### REQ-130 / REQ-131 status

`MODEL_LINKED_LIMIT_PENDING`

## Current authoritative evidence

- `docs/qps_line_s_recovery/assumptions_register.yaml`
- `docs/qps_line_s_recovery/generated/runtime_status.json`
- `docs/qps_line_s_recovery/generated/scenario_matrix.md`
- `docs/qps_line_s_recovery/generated/recovery_matrix.md`
- `docs/qps_line_s_recovery/generated/applicant_response_package.GENERATED.md`
- `docs/qps_line_s_recovery/p_limit_register.md`
- `models/qps_line_s/line_s_buffer.py`
- `models/qps_line_s/recovery_model.py`
- `models/qps_line_s/loop_transient.py`
- `models/qps_line_s/ssot_tables.py`
- `docs/qps_line_s_recovery/addendum2_rev146_tables_27_29.json`
- `tests/test_loop_transient.py`
- `tests/test_ssot_tables_contract.py`
- `docs/qps_line_s_recovery/addendum2_rev146_rtm_292_293_061.json`
- `tests/test_rtm292_contract.py`
- `docs/qps_line_s_recovery/appendix_8_4_mode_valve_extraction.yaml`

## Resolved MDA gates

- `ASSUM-VEFF` — `RESOLVED`
- `ASSUM-PLIMIT` — `RESOLVED`
- `ASSUM-RECOV-PWR` — `RESOLVED`
- `ASSUM-ENERGY-MODEL` — `RESOLVED`

## Remaining traceability / evidence gaps

1. Closed: RTM-292 wording and source location are bound (rev 146, p. 68;
   vendored and tested).
2. Bind source pedigree for `MDOT_IN_PRE_HP_MAX = 112 g/s`. It is not an
   RTM-292 use case; its only repository source is the HP compressor 72 Hz
   maximum reference, so it remains unresolved.
3. Complete the remaining Appendix 8.4 state transcription: 15 modes are
   mode-identified only and 8 modes remain partially extracted.
4. Quantify mode-dependent V_eff only after the remaining topology is
   source-bound.
5. Keep `T_GAS` calibration-pending until its basis is reconciled.
6. Resolve or explicitly carry the 1.44 heat-load margin pedigree.
7. Resolve `H2_heat_to_flow` calibration for credited transient use.
8. Complete independent HEPAK low-temperature reference where required.
9. Bind the Thermal Shield temperature limit (REQ-130 / REQ-131) and add a
   T_TS(t) <= limit check to the LOOP transient tests.

Mode-dependent recovery paths and connected V_eff shall not be frozen until
the relevant Appendix 8.4 topology is fully source-bound.

No status above constitutes engineering acceptance or compliance closure
merely because the MDA gate set is resolved.

Authority transfer: false.

Formal credit delta: 0.
