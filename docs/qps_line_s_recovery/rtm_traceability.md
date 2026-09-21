# RTM Traceability Map

Status: reconciled MDA traceability under ABACUS #1313.

The assumptions SSOT currently has zero open MDA gates and the generated runtime verdict is `PROCEED_MDA`. The statuses below deliberately distinguish **MDA model/package readiness** from engineering/source evidence that remains unresolved.

| Requirement | Interpretation for MDA | Current model/evidence | Current status |
|---|---|---|---|
| RTM-260 | Credited abnormal recovery shall not lose more than 1 percent helium inventory. | Reduced model and Applicant package include no-loss framing, but final credited lost-mass evidence still depends on source/calibration closure and recovery-path state. | EVIDENCE_PENDING |
| RTM-261 | QPS shall cope with Line S / QRB.S return flow: 100 g/s abnormal and 200 g/s normal/peak context. | Scenario matrix covers 100, 112, 150, and 200 g/s contexts; current assumptions resolve V_eff, pressure limit, recovery power, and HP capacity. The source trace for `MDOT_IN_PRE_HP_MAX=112 g/s` remains unresolved. | MDA_MODELLED_SOURCE_TRACE_PENDING |
| RTM-262 | QPS shall recover normal helium circulation after the abnormal event is resolved. | HP/recovery capability is represented, but Appendix 8.4 operating-mode/valve-state extraction and recovery procedure evidence are not yet source-bound. | SOURCE_PENDING |
| RTM-292 | Line S / recovery interface pressure build-up requirement. | `ASSUM-PLIMIT` is resolved at 1.30 bar for the current MDA model and the pressure/t_available calculations exist. Exact RTM-292 wording/source citation remains to be bound. | MDA_MODELLED_WORDING_TRACE_PENDING |
| OFFER-22 | Applicant shall present recovery strategy and maximum flow accepted from Line S. | Generated Applicant package, scenario/recovery matrices and current MDA gate closure provide the bounded model response. Remaining source/calibration items are listed below. | MDA_PACKAGE_READY_EVIDENCE_PENDING |

## Current authoritative evidence

- `docs/qps_line_s_recovery/assumptions_register.yaml` — model/input SSOT; four original MDA gates resolved
- `docs/qps_line_s_recovery/generated/runtime_status.json` — `PROCEED_MDA`, zero open gates
- `docs/qps_line_s_recovery/generated/scenario_matrix.md`
- `docs/qps_line_s_recovery/generated/recovery_matrix.md`
- `docs/qps_line_s_recovery/generated/applicant_response_package.GENERATED.md`
- `docs/qps_line_s_recovery/p_limit_register.md`
- `models/qps_line_s/line_s_buffer.py`
- `models/qps_line_s/recovery_model.py`
- `models/qps_line_s/loop_transient.py`
- `docs/qps_line_s_recovery/appendix_8_4_mode_valve_extraction.yaml`

## Resolved MDA gates

- `ASSUM-VEFF` — RESOLVED
- `ASSUM-PLIMIT` — RESOLVED
- `ASSUM-RECOV-PWR` — RESOLVED
- `ASSUM-ENERGY-MODEL` — RESOLVED

## Remaining traceability / evidence gaps

1. Bind the exact RTM-292 wording/source location.
2. Bind the source pedigree for `MDOT_IN_PRE_HP_MAX = 112 g/s`.
3. Extract Appendix 8.4 mode/valve states from the authoritative source before freezing any recovery-path topology or mode-dependent V_eff.
4. Retain `T_GAS` as calibration-pending until the mixed-temperature basis is reconciled.
5. Resolve or explicitly carry the 1.44 heat-load margin pedigree.
6. Resolve `H2_heat_to_flow` calibration for credited transient/no-loss use.
7. Complete the independent HEPAK low-temperature reference path where required.

No row above constitutes engineering acceptance or compliance closure merely because the MDA gate set is resolved.

Authority transfer: false. Formal credit delta: 0.
