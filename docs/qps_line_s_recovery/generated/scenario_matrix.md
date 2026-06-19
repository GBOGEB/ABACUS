# Generated scenario matrix

Source: models/qps_line_s/run_scenarios.py

| V_eff_m3 | case | m_in_g_s | m_rec_g_s | m_HP_g_s | m_net_g_s | dPdt_ribbon_bar_min | dPdt_energy_est_bar_min | t_plus_1bar_ribbon_min | position |
|---|---|---|---|---|---|---|---|---|---|
| 9 | A_balanced_abnormal | 100 | 100 | 0 | 0 | 0.000 | 0.000 |  | Covered if 2x50 g/s available |
| 9 | B_pre_HP_transient | 112 | 100 | 0 | 12 | 0.499 | 0.831 | 2.006 | Bounded buffer; HP start timing governs |
| 9 | C_intermediate | 150 | 100 | 0 | 50 | 2.077 | 3.462 | 0.481 | Requires pressure margin or additional recovery |
| 9 | D_peak_without_HP | 200 | 100 | 0 | 100 | 4.154 | 6.924 | 0.241 | Not sustained unless margin and duration proven |
| 9 | E_peak_with_HP | 200 | 100 | 100 | 0 | 0.000 | 0.000 |  | Creditable if HP path running |
| 9 | F_shield_mitigated | 30 | 50 | 0 | -20 | 0.000 | 0.000 |  | Recovery exceeds mitigated release |
| 30 | A_balanced_abnormal | 100 | 100 | 0 | 0 | 0.000 | 0.000 |  | Covered if 2x50 g/s available |
| 30 | B_pre_HP_transient | 112 | 100 | 0 | 12 | 0.150 | 0.249 | 6.686 | Bounded buffer; HP start timing governs |
| 30 | C_intermediate | 150 | 100 | 0 | 50 | 0.623 | 1.039 | 1.605 | Requires pressure margin or additional recovery |
| 30 | D_peak_without_HP | 200 | 100 | 0 | 100 | 1.246 | 2.077 | 0.802 | Not sustained unless margin and duration proven |
| 30 | E_peak_with_HP | 200 | 100 | 100 | 0 | 0.000 | 0.000 |  | Creditable if HP path running |
| 30 | F_shield_mitigated | 30 | 50 | 0 | -20 | 0.000 | 0.000 |  | Recovery exceeds mitigated release |
| 120 | A_balanced_abnormal | 100 | 100 | 0 | 0 | 0.000 | 0.000 |  | Covered if 2x50 g/s available |
| 120 | B_pre_HP_transient | 112 | 100 | 0 | 12 | 0.037 | 0.062 | 26.745 | Bounded buffer; HP start timing governs |
| 120 | C_intermediate | 150 | 100 | 0 | 50 | 0.156 | 0.260 | 6.419 | Requires pressure margin or additional recovery |
| 120 | D_peak_without_HP | 200 | 100 | 0 | 100 | 0.312 | 0.519 | 3.209 | Not sustained unless margin and duration proven |
| 120 | E_peak_with_HP | 200 | 100 | 100 | 0 | 0.000 | 0.000 |  | Creditable if HP path running |
| 120 | F_shield_mitigated | 30 | 50 | 0 | -20 | 0.000 | 0.000 |  | Recovery exceeds mitigated release |
| 240 | A_balanced_abnormal | 100 | 100 | 0 | 0 | 0.000 | 0.000 |  | Covered if 2x50 g/s available |
| 240 | B_pre_HP_transient | 112 | 100 | 0 | 12 | 0.019 | 0.031 | 53.491 | Bounded buffer; HP start timing governs |
| 240 | C_intermediate | 150 | 100 | 0 | 50 | 0.078 | 0.130 | 12.838 | Requires pressure margin or additional recovery |
| 240 | D_peak_without_HP | 200 | 100 | 0 | 100 | 0.156 | 0.260 | 6.419 | Not sustained unless margin and duration proven |
| 240 | E_peak_with_HP | 200 | 100 | 100 | 0 | 0.000 | 0.000 |  | Creditable if HP path running |
| 240 | F_shield_mitigated | 30 | 50 | 0 | -20 | 0.000 | 0.000 |  | Recovery exceeds mitigated release |
