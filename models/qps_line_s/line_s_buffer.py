"""Reduced Line S pressure-buffer model.

Scope: first-order model for RTM-261 / RTM-292 transient recovery checks.
This is not a full SIMCRYOGENICS reproduction.

Review change implemented:
- Keep the legacy isothermal ribbon for sanity checks only.
- Use the energy-balance / adiabatic charging limit as the governing early-rise
  pressure rate until V_eff, P_limit, and thermodynamic path are resolved.
"""

R_HE = 2077.1  # J/(kg.K)
CP_HE = 5193.0  # J/(kg.K), engineering constant for helium near ambient
CV_HE = 3115.8  # J/(kg.K)
GAMMA_HE = CP_HE / CV_HE
PA_PER_BAR = 100000.0
SECONDS_PER_MIN = 60.0

DESIGN_HEAT_LOAD_W = 8700.0
TRUE_BASELINE_HEAT_W = DESIGN_HEAT_LOAD_W / 1.44
UNCERTAINTY_ONLY_HEAT_W = DESIGN_HEAT_LOAD_W * 100.0 / 120.0
PREVIOUS_HIGH_SIDE_STRESS_W = DESIGN_HEAT_LOAD_W * 1.2

# Constants for future 4 K bath release modelling.
H_FG_4K_J_KG = 20700.0
CALIBRATED_DH_RELEASE_J_KG = 72500.0  # pending formal calibration against D2.1 profile


def pressure_rise_isothermal_bar_per_min(net_flow_g_s, volume_m3=120.0, temperature_k=300.0):
    """Legacy isothermal pressure-rise ribbon in bar/min.

    Use for comparison only. In the early charging limit, this under-predicts
    the energy-balance / adiabatic rise by approximately gamma.
    """
    net_flow_kg_s = max(net_flow_g_s, 0.0) / 1000.0
    dpdt_pa_s = net_flow_kg_s * R_HE * temperature_k / volume_m3
    return dpdt_pa_s * SECONDS_PER_MIN / PA_PER_BAR


def pressure_rise_energy_bar_per_min(net_flow_g_s, volume_m3=120.0, temperature_k=300.0):
    """Energy-balance pressure-rise rate in bar/min.

    This is the governing first-pass rate for charging a rigid control volume
    when the thermodynamic path is not yet resolved.
    """
    return GAMMA_HE * pressure_rise_isothermal_bar_per_min(
        net_flow_g_s, volume_m3=volume_m3, temperature_k=temperature_k
    )


def pressure_rise_bar_per_min(net_flow_g_s, volume_m3=120.0, temperature_k=300.0, mode="energy"):
    """Return pressure-rise rate in bar/min.

    mode="energy" is the default. mode="isothermal" retains the old sanity ribbon.
    """
    if mode == "isothermal":
        return pressure_rise_isothermal_bar_per_min(net_flow_g_s, volume_m3, temperature_k)
    return pressure_rise_energy_bar_per_min(net_flow_g_s, volume_m3, temperature_k)


def time_to_margin_min(delta_p_bar, net_flow_g_s, volume_m3=120.0, temperature_k=300.0, mode="energy"):
    """Return minutes to consume a pressure margin."""
    rate = pressure_rise_bar_per_min(net_flow_g_s, volume_m3, temperature_k, mode=mode)
    if rate <= 0:
        return float("inf")
    return delta_p_bar / rate


def net_accumulation_g_s(inflow_g_s, recovery_g_s=0.0, hp_g_s=0.0):
    """Positive value means accumulation in Line S."""
    return inflow_g_s - recovery_g_s - hp_g_s


def shield_flow_g_s(heat_load_w, delta_t_k=20.0, cp_eff_j_kg_k=5250.0):
    """Estimate thermal-shield helium coolant flow in g/s.

    This function is retained for the shield-cooling mitigation loop only. It is
    not the Line S 4 K bath boil-off stream.
    """
    return 1000.0 * heat_load_w / (cp_eff_j_kg_k * delta_t_k)


def bath_release_flow_g_s(heat_load_w, dh_release_j_kg=CALIBRATED_DH_RELEASE_J_KG):
    """Estimate 4 K bath release flow in g/s from an effective enthalpy basis.

    The default effective enthalpy is deliberately calibrated/pending, not a
    final thermodynamic assertion. Replace with CoolProp or validated D2.1
    calibration in a later wave.
    """
    return 1000.0 * heat_load_w / dh_release_j_kg


def corrected_heat_sensitivity():
    """Return corrected heat sensitivity cases.

    8700 W is treated as true baseline x 1.44. The uncertainty-only case is
    true baseline x 1.2, equivalently 8700 x 100 / 120.
    """
    cases = [
        ("true_nominal_baseline", 1.0, TRUE_BASELINE_HEAT_W),
        ("uncertainty_only", 1.2, UNCERTAINTY_ONLY_HEAT_W),
        ("design_point", 1.44, DESIGN_HEAT_LOAD_W),
        ("previous_high_side_stress", 1.728, PREVIOUS_HIGH_SIDE_STRESS_W),
    ]
    return [
        {
            "name": name,
            "factor_vs_true_baseline": factor,
            "heat_load_w": heat_load_w,
            "shield_flow_g_s": shield_flow_g_s(heat_load_w),
            "bath_release_flow_g_s": bath_release_flow_g_s(heat_load_w),
        }
        for name, factor, heat_load_w in cases
    ]


if __name__ == "__main__":
    for flow in [12, 50, 100, 150, 200]:
        print(flow, pressure_rise_bar_per_min(flow))
    for case in corrected_heat_sensitivity():
        print(case)
