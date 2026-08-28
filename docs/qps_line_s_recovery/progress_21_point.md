# 21-Point Integration Progress Tracker

Status refreshed after merged W001/W002 implementation review on 2026-08-28.

| # | Work element | Status | Owner / helper | Notes |
|---:|---|---|---|---|
| 1 | Clear Applicant answer structure | started | assistant | Controlled Applicant package exists; final consolidation still gated by open evidence. |
| 2 | Reduced model boundary | complete | assistant | Boundary defined around QCELL/QVE -> Line S -> recovery compressors -> HP path. |
| 3 | Source register from D2.1 | complete | assistant | `source_register.md` exists. |
| 4 | RTM traceability table | started | Agent A | `rtm_traceability.md` exists but still carries STARTED / OPEN_RFI states. |
| 5 | Scenario matrix | complete | Agent A / runner | Canonical scenario inputs exist in `models/qps_line_s/scenarios.json`; generated scenario matrix is reproducible output. |
| 6 | Pressure-build-up formula set | complete | assistant | Ideal-gas formula and recovery model are present. |
| 7 | 100 / 112 / 150 / 200 g/s sensitivity | complete | assistant | Canonical scenario set contains all four principal flow cases plus mitigation cases. |
| 8 | HP compressor start-delay sensitivity | started | assistant | Recovery model contains `comp_start_s`; contractor/plant timing basis remains RFI. |
| 9 | Volume sensitivity | complete | Agent B / model | Canonical volume band `[9, 30, 120, 240] m3` exists and is model input. |
| 10 | Temperature sensitivity | started | Agent B / model | Temperature is represented but current 300 K basis remains calibration-sensitive. |
| 11 | Initial-condition sensitivity | started | assistant | Initial conditions represented; evidence closure remains open. |
| 12 | Appendix 8.2 topology extraction | started | Agent A | PFD topology identified; detailed governed extraction remains pending. |
| 13 | Appendix 8.3 model block map | started | assistant | SIMCRYOGENICS lineage captured at high level; detailed crosswalk remains incomplete. |
| 14 | Appendix 8.4 mode/valve extraction plan | started | Agent A | Valve-state extraction remains pending. |
| 15 | Excel block structure | complete | assistant | Excel-compatible outputs/build path exist; release integration is handled by GOV-001 roundtrip. |
| 16 | Python block structure | complete | Agent B | `line_s_buffer.py`, `run_scenarios.py`, `recovery_model.py`, and runtime integration exist. |
| 17 | CoolProp upgrade path | complete | Agent B | CoolProp 7.2.0 is pinned in model CI; independent HEPAK oracle remains separate and open. |
| 18 | ABACUS repo scaffold plan | complete | assistant | W001/W002 implementation merged into `main`. |
| 19 | CODEX reusable tooling plan | started | CODEX helper | Generic helper issue #237 remains open; QPS-specific manifests/index/glossary exist in ABACUS. |
| 20 | PR text / branch plan | complete | assistant | W001/W002 PRs merged. |
| 21 | Open issue / confirmation list | started | assistant | Open gates remain explicit: ASSUM-VEFF, ASSUM-PLIMIT, ASSUM-RECOV-PWR, ASSUM-ENERGY-MODEL. |

## Current completion view

- Complete: 10 / 21
- Started: 11 / 21
- Not started: 0 / 21
- Blocked: 0 / 21

## Remaining evidence gates

The package is not promoted to closed/accepted model status. The current open-gate set remains:

- `ASSUM-VEFF`
- `ASSUM-PLIMIT`
- `ASSUM-RECOV-PWR`
- `ASSUM-ENERGY-MODEL`

Independent HEPAK property validation also remains open. Completion of implementation tasks must not be read as engineering acceptance of unresolved assumptions.

## Front-heavy execution rule

Prioritize governed source extraction, RTM closure, interface/pressure evidence and Applicant RFI closure before expanding into full SIMCRYOGENICS reproduction.