"""W53-P05M: nominal 2K-OP high-pressure compressor power receipt.

Uses the source-bound aggregate operating point from the QPS offer SSOT:
- total HP helium flow = 326 g/s
- suction = 298 K / 1.05 bara
- discharge = 14 bara
- reported HP electrical power = 814 kW

The 112 g/s / 357 kW FSD575 point is retained only as a 72 Hz maximum-reference
sensitivity. It shall not be promoted to the nominal 2K-OP operating point.
"""
from __future__ import annotations

import json
import math

R_HE_IDEAL = 2077.0  # J/kg/K screening ideal-gas constant


def isothermal_power_kW(mdot_g_s: float, T_K: float, P1_bara: float, P2_bara: float) -> float:
    mdot = mdot_g_s / 1000.0
    return mdot * R_HE_IDEAL * T_K * math.log(P2_bara / P1_bara) / 1000.0


def report() -> dict:
    mdot_total = 326.0
    T1 = 298.0
    P1 = 1.05
    P2 = 14.0
    source_power = 814.0

    p_iso_total = isothermal_power_kW(mdot_total, T1, P1, P2)
    eta_required = p_iso_total / source_power

    max_ref_flow = 112.0
    max_ref_input = 357.0
    p_iso_max_ref = isothermal_power_kW(max_ref_flow, T1, P1, P2)
    eta_max_ref = p_iso_max_ref / max_ref_input
    nominal_pred_from_max_ref_eff = p_iso_total / eta_max_ref
    residual_from_max_ref_eff = nominal_pred_from_max_ref_eff - source_power

    configs = []
    for active in (3, 4):
        configs.append({
            "active_units": active,
            "flow_per_unit_g_s": mdot_total / active,
            "electrical_power_per_unit_if_equal_share_kW": source_power / active,
            "status": "CONFIGURATION_DIAGNOSTIC_ONLY_PENDING_SOURCE_BOUND_RUNNING_CONFIGURATION",
        })

    return {
        "schema": "qps-w53-p05m-hp-power-receipt/v1",
        "source_operating_point": {
            "scenario": "2K_OP",
            "total_flow_g_s": mdot_total,
            "T_suction_K": T1,
            "P_suction_bara": P1,
            "P_discharge_bara": P2,
            "reported_HP_electrical_kW": source_power,
        },
        "independent_thermodynamic_screen": {
            "ideal_isothermal_power_kW": p_iso_total,
            "required_aggregate_isothermal_efficiency": eta_required,
            "required_aggregate_isothermal_efficiency_percent": 100.0 * eta_required,
            "interpretation": "EFFICIENCY_REQUIRED_TO_REPRODUCE_SOURCE_POWER_NOT_AN_INDEPENDENT_VENDOR_PREDICTION",
        },
        "maximum_reference_sensitivity": {
            "FSD575_flow_g_s": max_ref_flow,
            "FSD575_package_input_kW": max_ref_input,
            "ideal_isothermal_power_kW": p_iso_max_ref,
            "implied_isothermal_efficiency": eta_max_ref,
            "implied_isothermal_efficiency_percent": 100.0 * eta_max_ref,
            "nominal_total_power_if_max_reference_efficiency_reused_kW": nominal_pred_from_max_ref_eff,
            "residual_vs_814_kW": residual_from_max_ref_eff,
            "residual_percent_vs_814": 100.0 * residual_from_max_ref_eff / source_power,
            "status": "DIAGNOSTIC_ONLY_MAX_REFERENCE_NOT_NOMINAL_PREDICTOR",
        },
        "running_configuration_diagnostics": configs,
        "strict_disposition": {
            "score_before": "1/5",
            "score_after": "1/5",
            "HP_residual": "DEFER_PART_LOAD_MAP_OR_INDEPENDENT_NOMINAL_EFFICIENCY",
            "why": [
                "814_kW_and_326_g_s_are_source_bound",
                "aggregate_thermodynamic_requirement_is_executable",
                "actual_2K_OP_running_configuration_is_not_yet_source_bound",
                "independent_nominal_FSD575_VFD_efficiency_or_OEM_part_load_curve_is_missing",
                "72Hz_112g_s_357kW_reference_must_not_be_substituted_for_nominal_operation",
            ],
        },
        "next_required": [
            "recover_actual_2K_OP_active_FSD575_count_and_speed_or_load_fraction",
            "recover_OEM_or_bidder_part_load_power_or_specific_power_curve",
            "predict_HP_power_independently_at_326_g_s",
            "compare_prediction_to_814_kW_with_governed_tolerance",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(report(), indent=2, sort_keys=True))
