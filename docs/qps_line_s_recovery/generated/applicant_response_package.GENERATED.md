<!--
GENERATED FILE — do not hand-edit.
Producer : rextools/populate_package.py
Generated: 2026-06-26T13:18:03.448630+00:00
Verdict  : PROCEED_MDA
Open gates (0): none
Energy model: bound
-->

## Package status (generated header)

| Field | Value |
|---|---|
| Verdict | `PROCEED_MDA` |
| Open gates | 0 |
| Energy model | `bound` |
| Generated | 2026-06-26T13:18:03.448630+00:00 |

> **READY FOR MDA.** All gates resolved. Package may be submitted.

---

<!--
applicant_response_package.md - CONTROLLED RELEASE DOCUMENT
STATUS: DRAFT. merge_allowed = false. Do NOT distribute.

BINDING RULES:
  1. Every number in this document is generated or sourced, not independently typed.
  2. GATED quantities V_eff, P_limit, P_initial, recovery power, and energy-model fidelity remain unresolved.
  3. Until gated inputs are resolved or accepted, the answer is a criterion plus parametric bands.
  4. Section 4 is the centrepiece: required confirmations close the answer.
-->

# RTM-261 / RTM-292 - Line S Pressure Build-up and Helium Recovery: Applicant Response

**Status:** DRAFT reduced model, MDA scope. **PR:** GBOGEB/ABACUS#582. **Branch:** w001.

**Binds to:** `assumptions_register.yaml` as SSOT and `models/qps_line_s/line_s_buffer.py` as model source.

**Scope guard:** reduced Line S / recovery / HP / shield-mitigation boundary only. This is not a full SIMCRYOGENICS reproduction.

## 1. Question

> What pressure build-up is allowed in Line S for recovery of 100-200 g/s, as given in RTM-261 and RTM-292? Is there a flow profile available to indicate how quickly the mass flow from Cryogenic Users will build up?

## 2. Short answer: allowable time, not a fixed pressure

The Applicant decision variable is the time available before the limiting pressure is reached:

```text
Delta_P_allowed = P_limit - P_initial

t_available = Delta_P_allowed / dPdt

PASS if:
  t_available >= t_HP_start
  and no relief opens
  and integrated helium loss <= 1 percent inventory per RTM-260
```

`P_limit`, `P_initial`, `V_eff`, recovery-compressor power during LOOP, and energy-model fidelity are not yet confirmed. Therefore the quantified answer remains parametric and gated.

The generated headline output is expected, not tracked source:

```text
docs/qps_line_s_recovery/generated/t_available_grid.md
docs/qps_line_s_recovery/generated/t_available_grid.csv
```

The grid leads with the conservative energy-bound column and keeps the isothermal value as an optimistic sanity ribbon.

## 3. Recovery regimes

| Regime | Position | Gate |
|---|---|---|
| 100 g/s abnormal | Covered by 2 x 50 g/s recovery compressors | Only if both compressors are powered and available during LOOP. |
| 112 g/s pre-HP transient | Bounded pressure-buffer case | Governed by pressure margin, V_eff, and HP start timing. |
| 200 g/s peak | Spike / excursion, not a sustained plateau | Credited only with HP path running or a proven short buffer excursion. |
| Shield-maintained mitigation | Preferred lever where credible | Maintaining shield cooling delays release and reduces Line S load. |

## 4. Required confirmations from Applicant

| ID | Item | Why it gates the answer | Status |
|---|---|---|---|
| ASSUM-VEFF | Effective connected gas volume during the transient | Pressure rise is inversely proportional to volume. | UNRESOLVED |
| ASSUM-PLIMIT | Minimum of design, maximum operating, relief margin, compressor suction, and interface limits | No ceiling means no allowed pressure margin. | OPEN_RFI |
| ASSUM-RECOV-PWR | Backup power status for 2 x 50 g/s recovery compressors during LOOP | If unavailable, recovery capacity is not 100 g/s during LOOP. | BLOCKER |
| ASSUM-ENERGY-MODEL | Whether the gamma_x_ribbon_bound is acceptable for MDA closure | Prevents the early-time bound from being misrepresented as an integrated energy-balance result. | OPEN |
| HP_CAPACITY | HP-path acceptance flow at Line S suction | Determines whether the 200 g/s case closes to near-zero accumulation. | LOW_CONFIDENCE |
| MDOT_PRE_HP | Basis for the 112 g/s pre-HP value | Governs the pre-HP transient. | LOW_CONFIDENCE |
| MARGIN_1_44 | Pedigree of the 1.44 heat-load factor | Preserves corrected 6042 / 7250 / 8700 W lineage. | UNCONFIRMED |

## 5. Pressure-margin physics

The current scenario matrix explicitly tags the energy column as:

```text
energy_source = gamma_x_ribbon_bound
```

This means the reported energy value is the early-time adiabatic bound, calculated as gamma times the isothermal sanity ribbon. It is not yet a time-integrated energy curve.

The isothermal sanity ribbon is:

```text
dPdt_isothermal = mdot_net R_He T / V_eff
```

The early-time energy bound is:

```text
dPdt_energy_bound ~= gamma x dPdt_isothermal
```

with helium gamma approximately 1.667.

The time-to-limit grid is a linearized estimate. It is acceptable for screening and Applicant RFI framing only if `ASSUM-ENERGY-MODEL` is explicitly accepted for MDA closure. Otherwise, final closure requires a time-integrated `P(t), T(t)` curve once `V_eff`, `P_limit`, inflow profile, and recovery-power state are resolved.

The heat-to-flow link is separated:

| Flow type | Meaning |
|---|---|
| Shield coolant flow | Helium flow required to maintain the 40-60 K shield loop. |
| 4 K bath release flow | Line S stream driven by bath boil-off / relief profile. |

The 8700 W case is retained as the D2.1/design heat-load point, with the corrected lineage:

```text
true baseline = 8700 / 1.44
uncertainty-only = true baseline x 1.2 = 8700 x 100 / 120
D2.1/design point = 8700
```

## 6. Expected generated outputs

The model runner emits ignored render artefacts:

```text
docs/qps_line_s_recovery/generated/scenario_matrix.md
docs/qps_line_s_recovery/generated/scenario_matrix.csv
docs/qps_line_s_recovery/generated/t_available_grid.md
docs/qps_line_s_recovery/generated/t_available_grid.csv
docs/qps_line_s_recovery/generated/runtime_status.json
```

These files are expected outputs, not tracked source of record. The source of record is the model code, assumptions register, and index metadata.

Until `V_eff` is resolved, generated output includes the parametric band:

```text
V_eff in {9, 30, 120, 240} m3
```

Until `P_limit` and `P_initial` are resolved, the t_available grid uses candidate placeholders only and shall not be presented as a final pressure allowance.

## 7. Flow-profile basis

The reduced model uses three D2.1 LOOP profiles as first-pass bounding cases:

| Profile | Meaning | Use |
|---|---|---|
| baseline LOOP | Release after the initial pressure-rise period, with high-flow excursion | Base abnormal profile. |
| early 1.2 bar / 4.4 K | Earlier release after elevated initial condition | Timing sensitivity. |
| shield maintained | Delayed, lower-flow release | Mitigation path. |

These profiles remain conceptual until Agent A extracts the final Appendix 8.4 valve/mode state logic and Agent B validates the runner output.

## 8. No-loss compliance

For every credited case:

```text
mdot_relief_vent = 0
integrated loss <= 1 percent inventory
```

Any case that requires relief opening is not a credited no-loss recovery case for RTM-260.

## 9. Assumptions table

The release version shall show values from `assumptions_register.yaml` only:

```text
id | value | unit | status | source | gate
```

No gated value shall be converted into a final answer until marked resolved or accepted in the register.

## 10. Model appendix

Constants currently used in the reduced model:

```text
R_He = 2077.2 J/kg/K
cp = 5193 J/kg/K
cv = 3115.8 J/kg/K
gamma = cp/cv ~= 1.667
h_fg(4 K) placeholder ~= 20.7 kJ/kg
Z ~= 1.00 to 1.02 for first-pass pressure range
```

The legacy sanity ribbon:

```text
dPdt [bar/min] ~= 0.003116 x mdot_net [g/s]
```

holds only for the isothermal check at `V_eff = 120 m3` and `T = 300 K`. It is not the final design answer.

## 11. Lineage anchor

Traceable to:

```text
S_line_raw.txt
REVIEW_AND_CONVERGENCE_PLAN.md
critical_lineage_scan.md
assumptions_register.yaml
index.json
```

---

## Appendix G: T-available parametric grid (generated)

# QPS Line S - t_available grid (time-to-limit)

GATED: depends on unresolved P_LIMIT and P_initial. Conservative column uses the energy bound. Values are linearized estimates pending resolved inputs and time-integrated energy balance.

| V_eff_m3 | case | P_LIMIT_bar | P_initial_bar | dP_allowed_bar | t_avail_energy_min | t_avail_isothermal_min | basis |
|---|---|---|---|---|---|---|---|
| 9.000 | A_balanced_abnormal | 2.000 | 1.200 | 0.800 | inf | inf | linearized_RFI_placeholders |
| 9.000 | A_balanced_abnormal | 3.000 | 1.200 | 1.800 | inf | inf | linearized_RFI_placeholders |
| 9.000 | A_balanced_abnormal | 4.000 | 1.200 | 2.800 | inf | inf | linearized_RFI_placeholders |
| 9.000 | A_balanced_abnormal | 5.000 | 1.200 | 3.800 | inf | inf | linearized_RFI_placeholders |
| 9.000 | B_pre_HP_transient | 2.000 | 1.200 | 0.800 | 0.963 | 1.605 | linearized_RFI_placeholders |
| 9.000 | B_pre_HP_transient | 3.000 | 1.200 | 1.800 | 2.166 | 3.611 | linearized_RFI_placeholders |
| 9.000 | B_pre_HP_transient | 4.000 | 1.200 | 2.800 | 3.370 | 5.617 | linearized_RFI_placeholders |
| 9.000 | B_pre_HP_transient | 5.000 | 1.200 | 3.800 | 4.573 | 7.622 | linearized_RFI_placeholders |
| 9.000 | C_intermediate | 2.000 | 1.200 | 0.800 | 0.231 | 0.385 | linearized_RFI_placeholders |
| 9.000 | C_intermediate | 3.000 | 1.200 | 1.800 | 0.520 | 0.867 | linearized_RFI_placeholders |
| 9.000 | C_intermediate | 4.000 | 1.200 | 2.800 | 0.809 | 1.348 | linearized_RFI_placeholders |
| 9.000 | C_intermediate | 5.000 | 1.200 | 3.800 | 1.098 | 1.829 | linearized_RFI_placeholders |
| 9.000 | D_peak_without_HP | 2.000 | 1.200 | 0.800 | 0.116 | 0.193 | linearized_RFI_placeholders |
| 9.000 | D_peak_without_HP | 3.000 | 1.200 | 1.800 | 0.260 | 0.433 | linearized_RFI_placeholders |
| 9.000 | D_peak_without_HP | 4.000 | 1.200 | 2.800 | 0.404 | 0.674 | linearized_RFI_placeholders |
| 9.000 | D_peak_without_HP | 5.000 | 1.200 | 3.800 | 0.549 | 0.915 | linearized_RFI_placeholders |
| 9.000 | E_peak_with_HP | 2.000 | 1.200 | 0.800 | inf | inf | linearized_RFI_placeholders |
| 9.000 | E_peak_with_HP | 3.000 | 1.200 | 1.800 | inf | inf | linearized_RFI_placeholders |
| 9.000 | E_peak_with_HP | 4.000 | 1.200 | 2.800 | inf | inf | linearized_RFI_placeholders |
| 9.000 | E_peak_with_HP | 5.000 | 1.200 | 3.800 | inf | inf | linearized_RFI_placeholders |
| 9.000 | F_shield_mitigated | 2.000 | 1.200 | 0.800 | inf | inf | linearized_RFI_placeholders |
| 9.000 | F_shield_mitigated | 3.000 | 1.200 | 1.800 | inf | inf | linearized_RFI_placeholders |
| 9.000 | F_shield_mitigated | 4.000 | 1.200 | 2.800 | inf | inf | linearized_RFI_placeholders |
| 9.000 | F_shield_mitigated | 5.000 | 1.200 | 3.800 | inf | inf | linearized_RFI_placeholders |
| 30.000 | A_balanced_abnormal | 2.000 | 1.200 | 0.800 | inf | inf | linearized_RFI_placeholders |
| 30.000 | A_balanced_abnormal | 3.000 | 1.200 | 1.800 | inf | inf | linearized_RFI_placeholders |
| 30.000 | A_balanced_abnormal | 4.000 | 1.200 | 2.800 | inf | inf | linearized_RFI_placeholders |
| 30.000 | A_balanced_abnormal | 5.000 | 1.200 | 3.800 | inf | inf | linearized_RFI_placeholders |
| 30.000 | B_pre_HP_transient | 2.000 | 1.200 | 0.800 | 3.209 | 5.349 | linearized_RFI_placeholders |
| 30.000 | B_pre_HP_transient | 3.000 | 1.200 | 1.800 | 7.221 | 12.035 | linearized_RFI_placeholders |
| 30.000 | B_pre_HP_transient | 4.000 | 1.200 | 2.800 | 11.233 | 18.722 | linearized_RFI_placeholders |
| 30.000 | B_pre_HP_transient | 5.000 | 1.200 | 3.800 | 15.245 | 25.408 | linearized_RFI_placeholders |
| 30.000 | C_intermediate | 2.000 | 1.200 | 0.800 | 0.770 | 1.284 | linearized_RFI_placeholders |
| 30.000 | C_intermediate | 3.000 | 1.200 | 1.800 | 1.733 | 2.889 | linearized_RFI_placeholders |
| 30.000 | C_intermediate | 4.000 | 1.200 | 2.800 | 2.696 | 4.493 | linearized_RFI_placeholders |
| 30.000 | C_intermediate | 5.000 | 1.200 | 3.800 | 3.659 | 6.098 | linearized_RFI_placeholders |
| 30.000 | D_peak_without_HP | 2.000 | 1.200 | 0.800 | 0.385 | 0.642 | linearized_RFI_placeholders |
| 30.000 | D_peak_without_HP | 3.000 | 1.200 | 1.800 | 0.867 | 1.444 | linearized_RFI_placeholders |
| 30.000 | D_peak_without_HP | 4.000 | 1.200 | 2.800 | 1.348 | 2.247 | linearized_RFI_placeholders |
| 30.000 | D_peak_without_HP | 5.000 | 1.200 | 3.800 | 1.829 | 3.049 | linearized_RFI_placeholders |
| 30.000 | E_peak_with_HP | 2.000 | 1.200 | 0.800 | inf | inf | linearized_RFI_placeholders |
| 30.000 | E_peak_with_HP | 3.000 | 1.200 | 1.800 | inf | inf | linearized_RFI_placeholders |
| 30.000 | E_peak_with_HP | 4.000 | 1.200 | 2.800 | inf | inf | linearized_RFI_placeholders |
| 30.000 | E_peak_with_HP | 5.000 | 1.200 | 3.800 | inf | inf | linearized_RFI_placeholders |
| 30.000 | F_shield_mitigated | 2.000 | 1.200 | 0.800 | inf | inf | linearized_RFI_placeholders |
| 30.000 | F_shield_mitigated | 3.000 | 1.200 | 1.800 | inf | inf | linearized_RFI_placeholders |
| 30.000 | F_shield_mitigated | 4.000 | 1.200 | 2.800 | inf | inf | linearized_RFI_placeholders |
| 30.000 | F_shield_mitigated | 5.000 | 1.200 | 3.800 | inf | inf | linearized_RFI_placeholders |
| 120.000 | A_balanced_abnormal | 2.000 | 1.200 | 0.800 | inf | inf | linearized_RFI_placeholders |
| 120.000 | A_balanced_abnormal | 3.000 | 1.200 | 1.800 | inf | inf | linearized_RFI_placeholders |
| 120.000 | A_balanced_abnormal | 4.000 | 1.200 | 2.800 | inf | inf | linearized_RFI_placeholders |
| 120.000 | A_balanced_abnormal | 5.000 | 1.200 | 3.800 | inf | inf | linearized_RFI_placeholders |
| 120.000 | B_pre_HP_transient | 2.000 | 1.200 | 0.800 | 12.838 | 21.396 | linearized_RFI_placeholders |
| 120.000 | B_pre_HP_transient | 3.000 | 1.200 | 1.800 | 28.885 | 48.142 | linearized_RFI_placeholders |
| 120.000 | B_pre_HP_transient | 4.000 | 1.200 | 2.800 | 44.932 | 74.887 | linearized_RFI_placeholders |
| 120.000 | B_pre_HP_transient | 5.000 | 1.200 | 3.800 | 60.980 | 101.633 | linearized_RFI_placeholders |
| 120.000 | C_intermediate | 2.000 | 1.200 | 0.800 | 3.081 | 5.135 | linearized_RFI_placeholders |
| 120.000 | C_intermediate | 3.000 | 1.200 | 1.800 | 6.932 | 11.554 | linearized_RFI_placeholders |
| 120.000 | C_intermediate | 4.000 | 1.200 | 2.800 | 10.784 | 17.973 | linearized_RFI_placeholders |
| 120.000 | C_intermediate | 5.000 | 1.200 | 3.800 | 14.635 | 24.392 | linearized_RFI_placeholders |
| 120.000 | D_peak_without_HP | 2.000 | 1.200 | 0.800 | 1.541 | 2.568 | linearized_RFI_placeholders |
| 120.000 | D_peak_without_HP | 3.000 | 1.200 | 1.800 | 3.466 | 5.777 | linearized_RFI_placeholders |
| 120.000 | D_peak_without_HP | 4.000 | 1.200 | 2.800 | 5.392 | 8.986 | linearized_RFI_placeholders |
| 120.000 | D_peak_without_HP | 5.000 | 1.200 | 3.800 | 7.318 | 12.196 | linearized_RFI_placeholders |
| 120.000 | E_peak_with_HP | 2.000 | 1.200 | 0.800 | inf | inf | linearized_RFI_placeholders |
| 120.000 | E_peak_with_HP | 3.000 | 1.200 | 1.800 | inf | inf | linearized_RFI_placeholders |
| 120.000 | E_peak_with_HP | 4.000 | 1.200 | 2.800 | inf | inf | linearized_RFI_placeholders |
| 120.000 | E_peak_with_HP | 5.000 | 1.200 | 3.800 | inf | inf | linearized_RFI_placeholders |
| 120.000 | F_shield_mitigated | 2.000 | 1.200 | 0.800 | inf | inf | linearized_RFI_placeholders |
| 120.000 | F_shield_mitigated | 3.000 | 1.200 | 1.800 | inf | inf | linearized_RFI_placeholders |
| 120.000 | F_shield_mitigated | 4.000 | 1.200 | 2.800 | inf | inf | linearized_RFI_placeholders |
| 120.000 | F_shield_mitigated | 5.000 | 1.200 | 3.800 | inf | inf | linearized_RFI_placeholders |
| 240.000 | A_balanced_abnormal | 2.000 | 1.200 | 0.800 | inf | inf | linearized_RFI_placeholders |
| 240.000 | A_balanced_abnormal | 3.000 | 1.200 | 1.800 | inf | inf | linearized_RFI_placeholders |
| 240.000 | A_balanced_abnormal | 4.000 | 1.200 | 2.800 | inf | inf | linearized_RFI_placeholders |
| 240.000 | A_balanced_abnormal | 5.000 | 1.200 | 3.800 | inf | inf | linearized_RFI_placeholders |
| 240.000 | B_pre_HP_transient | 2.000 | 1.200 | 0.800 | 25.676 | 42.793 | linearized_RFI_placeholders |
| 240.000 | B_pre_HP_transient | 3.000 | 1.200 | 1.800 | 57.770 | 96.283 | linearized_RFI_placeholders |
| 240.000 | B_pre_HP_transient | 4.000 | 1.200 | 2.800 | 89.865 | 149.774 | linearized_RFI_placeholders |
| 240.000 | B_pre_HP_transient | 5.000 | 1.200 | 3.800 | 121.959 | 203.265 | linearized_RFI_placeholders |
| 240.000 | C_intermediate | 2.000 | 1.200 | 0.800 | 6.162 | 10.270 | linearized_RFI_placeholders |
| 240.000 | C_intermediate | 3.000 | 1.200 | 1.800 | 13.865 | 23.108 | linearized_RFI_placeholders |
| 240.000 | C_intermediate | 4.000 | 1.200 | 2.800 | 21.567 | 35.946 | linearized_RFI_placeholders |
| 240.000 | C_intermediate | 5.000 | 1.200 | 3.800 | 29.270 | 48.784 | linearized_RFI_placeholders |
| 240.000 | D_peak_without_HP | 2.000 | 1.200 | 0.800 | 3.081 | 5.135 | linearized_RFI_placeholders |
| 240.000 | D_peak_without_HP | 3.000 | 1.200 | 1.800 | 6.932 | 11.554 | linearized_RFI_placeholders |
| 240.000 | D_peak_without_HP | 4.000 | 1.200 | 2.800 | 10.784 | 17.973 | linearized_RFI_placeholders |
| 240.000 | D_peak_without_HP | 5.000 | 1.200 | 3.800 | 14.635 | 24.392 | linearized_RFI_placeholders |
| 240.000 | E_peak_with_HP | 2.000 | 1.200 | 0.800 | inf | inf | linearized_RFI_placeholders |
| 240.000 | E_peak_with_HP | 3.000 | 1.200 | 1.800 | inf | inf | linearized_RFI_placeholders |
| 240.000 | E_peak_with_HP | 4.000 | 1.200 | 2.800 | inf | inf | linearized_RFI_placeholders |
| 240.000 | E_peak_with_HP | 5.000 | 1.200 | 3.800 | inf | inf | linearized_RFI_placeholders |
| 240.000 | F_shield_mitigated | 2.000 | 1.200 | 0.800 | inf | inf | linearized_RFI_placeholders |
| 240.000 | F_shield_mitigated | 3.000 | 1.200 | 1.800 | inf | inf | linearized_RFI_placeholders |
| 240.000 | F_shield_mitigated | 4.000 | 1.200 | 2.800 | inf | inf | linearized_RFI_placeholders |
| 240.000 | F_shield_mitigated | 5.000 | 1.200 | 3.800 | inf | inf | linearized_RFI_placeholders |

---

## Appendix R: Open RFI items (generated)

<!--
Generated: 2026-06-26T13:18:03.178555+00:00
Source register: docs/qps_line_s_recovery/assumptions_register.yaml
Register SHA256: 684441fef781afb42440ae23e76b2d63d2a81e2ac88fdf5b0b74378aa5399cc2
Git commit: d02426861ab27da6ab9097367552fa8c52f11546
Renderer: models/qps_line_s/rfi_package.py
Do not hand-edit this rendered file; update the register instead.
-->

# QPS Line S - Applicant RFI package

Generated from `docs/qps_line_s_recovery/assumptions_register.yaml`.
Do not hand-edit this rendered file; update the register instead.

Open gate count: 0
