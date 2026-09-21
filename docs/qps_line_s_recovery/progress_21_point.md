# 21-Point Integration Progress Tracker

Status reconciled on 2026-09-21 under issue #1313 against the current Line-S assumptions/runtime SSOT.

## Authority boundary

The four original MDA gates are resolved in `assumptions_register.yaml`, and the generated runtime verdict is `PROCEED_MDA` with zero open gates. That is a model/package state only. It is not engineering acceptance, compliance credit, or proof that all source/evidence work is complete.

| # | Work element | Status | Owner / helper | Notes |
|---:|---|---|---|---|
| 1 | Clear Applicant answer structure | complete | assistant | Controlled Applicant package and generated package exist for MDA use; engineering acceptance remains separate. |
| 2 | Reduced model boundary | complete | assistant | Boundary defined around QCELL/QVE -> Line S -> recovery compressors -> HP path. |
| 3 | Source register from D2.1 | complete | assistant | `source_register.md` exists; Appendix 8.4 remains explicitly source-pending. |
| 4 | RTM traceability table | started | Agent A | Reconciled to current SSOT under #1313; RTM-262 recovery-path evidence and exact RTM-292 wording remain source/evidence pending. |
| 5 | Scenario matrix | complete | Agent A / runner | Canonical scenario inputs and reproducible generated matrix exist. |
| 6 | Pressure-build-up formula set | complete | assistant | Ideal-gas/recovery model and current pressure-limit basis are present. |
| 7 | 100 / 112 / 150 / 200 g/s sensitivity | complete | assistant | Canonical scenario set covers the principal flow cases and mitigation cases. |
| 8 | HP compressor start-delay sensitivity | started | assistant | `comp_start_s` exists; contractor/plant timing basis remains evidence-pending. |
| 9 | Volume sensitivity | complete | Agent B / model | Sensitivity exists; authoritative MDA V_eff is 3.12 m3 in the assumptions SSOT, with isometric cross-check deferred. |
| 10 | Temperature sensitivity | started | Agent B / model | Temperature is represented; `T_GAS` remains `CALIBRATION_PENDING`. |
| 11 | Initial-condition sensitivity | started | assistant | Initial conditions are represented; evidence/calibration closure remains open. |
| 12 | Appendix 8.2 topology extraction | started | Agent A | PFD topology is identified; detailed governed extraction remains pending. |
| 13 | Appendix 8.3 model block map | started | assistant | SIMCRYOGENICS lineage exists at high level; detailed crosswalk remains incomplete. |
| 14 | Appendix 8.4 mode/valve extraction | started | Agent A | Fail-closed extraction contract exists; source rows remain `SOURCE_PENDING` and no valve state is inferred. |
| 15 | Excel block structure | complete | assistant | Excel-compatible outputs/build path exists; release integration is separate. |
| 16 | Python block structure | complete | Agent B | `line_s_buffer.py`, `run_scenarios.py`, `recovery_model.py`, and runtime integration exist. |
| 17 | CoolProp upgrade path | complete | Agent B | CoolProp 7.2.0 is exercised in model CI; independent HEPAK low-T oracle remains separate/open evidence. |
| 18 | ABACUS repo scaffold plan | complete | assistant | W001/W002 implementation merged into `main`. |
| 19 | CODEX reusable tooling plan | complete | CODEX helper | CODEX helper issue #237 is closed; QPS-specific manifest/index/glossary surfaces exist in ABACUS. |
| 20 | PR text / branch plan | complete | assistant | W001/W002 PRs merged; residual closure is now governed by #1313. |
| 21 | Open issue / confirmation list | complete | assistant | MDA gates and remaining non-gate uncertainties are now separated below. |

## Current completion view

- Complete: 14 / 21
- Started: 7 / 21
- Not started: 0 / 21
- Blocked: 0 / 21

## MDA gate status

The original four MDA gates are **resolved** in `assumptions_register.yaml`:

- `ASSUM-VEFF` — RESOLVED
- `ASSUM-PLIMIT` — RESOLVED
- `ASSUM-RECOV-PWR` — RESOLVED
- `ASSUM-ENERGY-MODEL` — RESOLVED

Generated `runtime_status.json` reports `PROCEED_MDA`, `n_open_gates=0`, and no missing artefacts.

## Remaining non-gate evidence / calibration work

These items remain open and must not be converted into acceptance credit:

- `MDOT_IN_PRE_HP_MAX` source trace — `UNRESOLVED`
- `T_GAS` — `CALIBRATION_PENDING`
- heat-load margin factor 1.44 pedigree — `UNRESOLVED`
- `H2_heat_to_flow` — `CALIBRATION_PENDING`
- independent HEPAK low-temperature reference — separate/open
- exact RTM-292 wording/source citation — source trace pending
- Appendix 8.4 mode/valve-state extraction — `SOURCE_PENDING`

## Front-heavy execution rule

Prioritize source extraction, RTM evidence closure, Appendix 8.4 mode/valve-state lineage, and independent property evidence before expanding into full SIMCRYOGENICS reproduction.

Authority transfer: false. Formal credit delta: 0.
