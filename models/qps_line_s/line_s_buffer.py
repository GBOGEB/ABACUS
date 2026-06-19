"""Reduced Line S pressure-buffer model.

Scope: first-order ideal-gas model for RTM-261 / RTM-292 transient recovery checks.
This is not a full SIMCRYOGENICS reproduction.
"""

R_HE = 2077.1  # J/(kg.K)
PA_PER_BAR = 100000.0
SECONDS_PER_MIN = 60.0

DESIGN_HEAT_LOAD_W = 8700.0
TRUE_BASELINE_HEAT_W = DESIGN_HEAT_LOAD_W / 1.44
UNCERTAINTY_ONLY_HEAT_W = DESIGN_HEAT_LOAD_W * 100.0 / 120.0
PREVIOUS_HIGH_SIDE_STRESS_W = DESIGN_HEAT_LOAD_W * 1.2


def pressure_rise_bar_per_min(net_flow_g_s, volume_m3=120.0, temperature_k=300.0):
    """Return pressure rise rate in bar/min.

    net_flow_g_s is positive when helium accumulates in Line S.
    """
    net_flow_kg_s = net_flow_g_s / 1000.0
    dpdt_pa_s = net_flow_kg_s * R_HE * temperature_k / volume_m3
    return dpdt_pa_s * SECONDS_PER_MIN / PA_PER_BAR


def time_to_margin_min(delta_p_bar, net_flow_g_s, volume_m3=120.0, temperature_k=300.0):
    """Return minutes to consume a pressure margin."""
    rate = pressure_rise_bar_per_min(net_flow_g_s, volume_m3, temperature_k)
    if rate <= 0:
        return float("inf")
    return delta_p_bar / rate


def net_accumulation_g_s(inflow_g_s, recovery_g_s=0.0, hp_g_s=0.0):
    """Positive value means accumulation in Line S."""
    return inflow_g_s - recovery_g_s - hp_g_s


def shield_flow_g_s(heat_load_w, delta_t_k=20.0, cp_eff_j_kg_k=5250.0):
    """Estimate thermal-shield helium flow in g/s.

    cp_eff_j_kg_k is calibrated from D2.1 values around 8505 W and 81 g/s
    over a 40 K to 60 K shield loop.
    """
    return 1000.0 * heat_load_w / (cp_eff_j_kg_k * delta_t_k)


def corrected_heat_sensitivity():
    """Return corrected heat sensitivity cases.

    8700 W is treated as true baseline x 1.44. The uncertainty-only case is
    true baseline x 1.2, equivalently 8700 x 100 / 120.
    """
    return [
        {
            "name": "true_nominal_baseline",
            "factor_vs_true_baseline": 1.0,
            "heat_load_w": TRUE_BASELINE_HEAT_W,
            "shield_flow_g_s": shield_flow_g_s(TRUE_BASELINE_HEAT_W),
        },
        {
            "name": "uncertainty_only",
            "factor_vs_true_baseline": 1.2,
            "heat_load_w": UNCERTAINTY_ONLY_HEAT_W,
            "shield_flow_g_s": shield_flow_g_s(UNCERTAINTY_ONLY_HEAT_W),
        },
        {
            "name": "design_point",
            "factor_vs_true_baseline": 1.44,
            "heat_load_w": DESIGN_HEAT_LOAD_W,
            "shield_flow_g_s": shield_flow_g_s(DESIGN_HEAT_LOAD_W),
        },
        {
            "name": "previous_high_side_stress",
            "factor_vs_true_baseline": 1.728,
            "heat_load_w": PREVIOUS_HIGH_SIDE_STRESS_W,
            "shield_flow_g_s": shield_flow_g_s(PREVIOUS_HIGH_SIDE_STRESS_W),
        },
    ]


if __name__ == "__main__":
    for flow in [12, 50, 100, 150, 200]:
        print(flow, pressure_rise_bar_per_min(flow))
    for case in corrected_heat_sensitivity():
        print(case)
