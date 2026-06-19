# QPS Line S - t_available grid (time-to-limit)

GATED: depends on unresolved `P_LIMIT` and `P_initial`. Conservative column uses the energy bound. Values are linearized estimates pending resolved inputs and time-integrated energy balance.

The generator emits the full CSV/Markdown grid from:

```text
models/qps_line_s/t_available_grid.py
```

## Representative screening rows

| V_eff_m3 | case | P_LIMIT_bar | P_initial_bar | dP_allowed_bar | t_avail_energy_min | t_avail_isothermal_min | basis |
|---:|---|---:|---:|---:|---:|---:|---|
| 9 | B_pre_HP_transient | 2.0 | 1.2 | 0.8 | 0.963 | 1.605 | linearized_RFI_placeholders |
| 9 | D_peak_without_HP | 2.0 | 1.2 | 0.8 | 0.116 | 0.193 | linearized_RFI_placeholders |
| 30 | B_pre_HP_transient | 2.0 | 1.2 | 0.8 | 3.210 | 5.349 | linearized_RFI_placeholders |
| 30 | D_peak_without_HP | 2.0 | 1.2 | 0.8 | 0.385 | 0.642 | linearized_RFI_placeholders |
| 120 | B_pre_HP_transient | 2.0 | 1.2 | 0.8 | 12.838 | 21.396 | linearized_RFI_placeholders |
| 120 | D_peak_without_HP | 2.0 | 1.2 | 0.8 | 1.541 | 2.568 | linearized_RFI_placeholders |
| 240 | B_pre_HP_transient | 2.0 | 1.2 | 0.8 | 25.676 | 42.793 | linearized_RFI_placeholders |
| 240 | D_peak_without_HP | 2.0 | 1.2 | 0.8 | 3.081 | 5.135 | linearized_RFI_placeholders |

## Release rule

Do not present this as a final pressure allowance. It is the screening grid used to identify how strongly the unresolved `V_eff`, `P_LIMIT`, and recovery-power assumptions control the answer.
