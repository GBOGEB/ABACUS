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

Line S / recovery interface pressure build-up requirement.

### RTM-292 current evidence

`ASSUM-PLIMIT` is resolved at 1.30 bar for the current MDA model.

Pressure and t_available calculations exist.

Exact RTM-292 wording/source citation remains to be bound.

### RTM-292 status

`MDA_MODELLED_WORDING_TRACE_PENDING`

## OFFER-22

### OFFER-22 interpretation

Applicant recovery strategy and maximum flow accepted from Line S.

### OFFER-22 current evidence

The generated Applicant package and scenario/recovery matrices provide the
bounded MDA model response.

Remaining source/calibration items are listed below.

### OFFER-22 status

`MDA_PACKAGE_READY_EVIDENCE_PENDING`

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
- `docs/qps_line_s_recovery/appendix_8_4_mode_valve_extraction.yaml`

## Resolved MDA gates

- `ASSUM-VEFF` — `RESOLVED`
- `ASSUM-PLIMIT` — `RESOLVED`
- `ASSUM-RECOV-PWR` — `RESOLVED`
- `ASSUM-ENERGY-MODEL` — `RESOLVED`

## Remaining traceability / evidence gaps

1. Bind exact RTM-292 wording/source location.
2. Bind source pedigree for `MDOT_IN_PRE_HP_MAX = 112 g/s`.
3. Complete the remaining Appendix 8.4 state transcription: 15 modes are
   mode-identified only and 8 modes remain partially extracted.
4. Quantify mode-dependent V_eff only after the remaining topology is
   source-bound.
5. Keep `T_GAS` calibration-pending until its basis is reconciled.
6. Resolve or explicitly carry the 1.44 heat-load margin pedigree.
7. Resolve `H2_heat_to_flow` calibration for credited transient use.
8. Complete independent HEPAK low-temperature reference where required.

Mode-dependent recovery paths and connected V_eff shall not be frozen until
the relevant Appendix 8.4 topology is fully source-bound.

No status above constitutes engineering acceptance or compliance closure
merely because the MDA gate set is resolved.

Authority transfer: false.

Formal credit delta: 0.
