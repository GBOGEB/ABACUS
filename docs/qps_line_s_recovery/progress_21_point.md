# 21-Point Integration Progress Tracker

Status reconciled on 2026-09-21 under issue #1313.

The current Line-S assumptions/runtime state is the authority for MDA gate
status.

## Authority boundary

The four original MDA gates are resolved in
`assumptions_register.yaml`.

The generated runtime verdict is `PROCEED_MDA` with zero open gates.

This is a model/package state only. It is not engineering acceptance,
compliance credit, or proof that all source/evidence work is complete.

## Progress items

1. **Clear Applicant answer structure — complete**
   - Owner: assistant.
   - Controlled Applicant and generated packages exist for MDA use.
   - Engineering acceptance remains separate.

2. **Reduced model boundary — complete**
   - Owner: assistant.
   - Boundary covers QCELL/QVE, Line S, recovery compressors, and HP path.

3. **Source register from D2.1 — complete**
   - Owner: assistant.
   - `source_register.md` exists.
   - Appendix 8.4 source is bound; detailed state extraction remains partial.

4. **RTM traceability table — started**
   - Owner: Agent A.
   - Reconciled to current SSOT under #1313.
   - RTM-262 is source-bound partial; recovery-path completion remains open.
   - Exact RTM-292 wording/source trace remains pending.

5. **Scenario matrix — complete**
   - Owner: Agent A / runner.
   - Canonical scenario inputs and reproducible generated matrix exist.

6. **Pressure-build-up formula set — complete**
   - Owner: assistant.
   - Pressure/recovery model and current pressure-limit basis exist.

7. **100 / 112 / 150 / 200 g/s sensitivity — complete**
   - Owner: assistant.
   - Principal flow cases and mitigation cases are represented.

8. **HP compressor start-delay sensitivity — started**
   - Owner: assistant.
   - `comp_start_s` exists.
   - Contractor/plant timing basis remains evidence-pending.

9. **Volume sensitivity — complete**
   - Owner: Agent B / model.
   - Sensitivity exists.
   - Authoritative MDA V_eff is 3.12 m3 in the assumptions SSOT.
   - Isometric cross-check remains deferred.

10. **Temperature sensitivity — started**
    - Owner: Agent B / model.
    - Temperature is represented.
    - `T_GAS` remains `CALIBRATION_PENDING`.

11. **Initial-condition sensitivity — started**
    - Owner: assistant.
    - Initial conditions are represented.
    - Evidence/calibration closure remains open.

12. **Appendix 8.2 topology extraction — started**
    - Owner: Agent A.
    - PFD topology is identified.
    - Detailed governed extraction remains pending.

13. **Appendix 8.3 model block map — started**
    - Owner: assistant.
    - SIMCRYOGENICS lineage exists at high level.
    - Detailed crosswalk remains incomplete.

14. **Appendix 8.4 mode/valve extraction — started**
    - Owner: Agent A.
    - A fail-closed extraction contract now exists.
    - Source rows remain `SOURCE_PENDING`.
    - No valve state is inferred.

15. **Excel block structure — complete**
    - Owner: assistant.
    - Excel-compatible outputs/build path exists.
    - Release integration remains separate.

16. **Python block structure — complete**
    - Owner: Agent B.
    - Runtime and recovery Python modules exist.

17. **CoolProp upgrade path — complete**
    - Owner: Agent B.
    - CoolProp 7.2.0 is exercised in model CI.
    - Independent HEPAK low-T evidence remains separate/open.

18. **ABACUS repo scaffold plan — complete**
    - Owner: assistant.
    - W001/W002 implementation is merged into `main`.

19. **CODEX reusable tooling plan — complete**
    - Owner: CODEX helper.
    - CODEX helper issue #237 is closed.
    - QPS package-specific tooling exists in ABACUS.

20. **PR text / branch plan — complete**
    - Owner: assistant.
    - W001/W002 PRs are merged.
    - Residual closure is governed by #1313.

21. **Open issue / confirmation list — complete**
    - Owner: assistant.
    - MDA gates and remaining non-gate uncertainties are separated below.

## Current completion view

- Complete: 14 / 21
- Started: 7 / 21
- Not started: 0 / 21
- Blocked: 0 / 21

## MDA gate status

The original four MDA gates are resolved in
`assumptions_register.yaml`:

- `ASSUM-VEFF` — `RESOLVED`
- `ASSUM-PLIMIT` — `RESOLVED`
- `ASSUM-RECOV-PWR` — `RESOLVED`
- `ASSUM-ENERGY-MODEL` — `RESOLVED`

Generated `runtime_status.json` reports:

- `verdict=PROCEED_MDA`
- `n_open_gates=0`
- no missing artefacts

## Remaining non-gate evidence / calibration work

These items remain open and must not become acceptance credit:

- `MDOT_IN_PRE_HP_MAX` source trace — `UNRESOLVED`
- `T_GAS` — `CALIBRATION_PENDING`
- heat-load margin factor 1.44 pedigree — `UNRESOLVED`
- `H2_heat_to_flow` — `CALIBRATION_PENDING`
- independent HEPAK low-temperature reference — separate/open
- exact RTM-292 wording/source citation — source trace pending
- Appendix 8.4 full state transcription — `PARTIAL_EXTRACTED`

## Front-heavy execution rule

Prioritize remaining state transcription, RTM evidence closure, and
Appendix 8.4 lineage, plus
independent property evidence before full SIMCRYOGENICS reproduction.

Authority transfer: false.

Formal credit delta: 0.
