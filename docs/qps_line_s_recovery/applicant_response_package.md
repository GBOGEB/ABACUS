<!--
applicant_response_package.md - CONTROLLED RELEASE DOCUMENT
STATUS: DRAFT. merge_allowed = false. Do NOT distribute.

BINDING RULES:
  1. Every number in this document is generated or sourced, not independently typed.
  2. GATED quantities V_eff, P_limit, P_initial, and recovery power remain unresolved.
  3. Until gated inputs are resolved, the answer is a criterion plus parametric bands.
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

`P_limit`, `P_initial`, `V_eff`, and recovery-compressor power during LOOP are not yet confirmed. Therefore the quantified answer remains parametric.

The generated headline output is:

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

The time-to-limit grid is a linearized estimate. It is acceptable for screening and Applicant RFI framing, but final closure still requires a time-integrated `P(t), T(t)` curve once `V_eff`, `P_limit`, inflow profile, and recovery-power state are resolved.

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

## 6. Generated outputs

The model runner emits:

```text
docs/qps_line_s_recovery/generated/scenario_matrix.md
docs/qps_line_s_recovery/generated/scenario_matrix.csv
docs/qps_line_s_recovery/generated/t_available_grid.md
docs/qps_line_s_recovery/generated/t_available_grid.csv
```

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

No gated value shall be converted into a final answer until marked resolved in the register.

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
