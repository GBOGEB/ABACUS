"""W52-P2H: QPLANT/WCS thermodynamic proof harness.

Uses the governed helium property provider for state properties and computes
reference compression metrics for the current LKT FSD575 design point.
The purpose is validation and reconciliation, not vendor-performance promotion.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass

from models.helium_properties.provider import state_tp

R_HE_IDEAL = 2077.0  # J/kg/K, screening only


@dataclass(frozen=True)
class CompressorProof:
    mdot_kg_s: float
    T1_K: float
    P1_Pa: float
    P2_Pa: float
    pressure_ratio: float
    w_isothermal_J_kg: float
    P_isothermal_kW: float
    h1_J_kg: float
    s1_J_kgK: float
    h2s_J_kg: float
    P_isentropic_kW: float
    package_input_kW: float
    eta_isothermal_reference: float
    eta_isentropic_reference: float
    formal_credit_delta: int = 0


def fsd575_design_proof(
    mdot_g_s: float = 112.0,
    T1_K: float = 298.0,
    P1_bara: float = 1.05,
    P2_bara: float = 14.0,
    package_input_kW: float = 357.0,
) -> CompressorProof:
    mdot = mdot_g_s / 1000.0
    P1 = P1_bara * 1e5
    P2 = P2_bara * 1e5
    st1 = state_tp(T1_K, P1)
    h2s = float(__import__("CoolProp.CoolProp", fromlist=["PropsSI"]).PropsSI("H", "P", P2, "S", st1.entropy_J_kgK, "Helium"))
    p_is = mdot * (h2s - st1.enthalpy_J_kg) / 1000.0
    w_iso = R_HE_IDEAL * T1_K * math.log(P2 / P1)
    p_iso = mdot * w_iso / 1000.0
    return CompressorProof(
        mdot_kg_s=mdot,
        T1_K=T1_K,
        P1_Pa=P1,
        P2_Pa=P2,
        pressure_ratio=P2 / P1,
        w_isothermal_J_kg=w_iso,
        P_isothermal_kW=p_iso,
        h1_J_kg=st1.enthalpy_J_kg,
        s1_J_kgK=st1.entropy_J_kgK,
        h2s_J_kg=h2s,
        P_isentropic_kW=p_is,
        package_input_kW=package_input_kW,
        eta_isothermal_reference=p_iso / package_input_kW,
        eta_isentropic_reference=p_is / package_input_kW,
    )


def nominal_2kop_configurations(total_hp_flow_g_s: float = 326.0) -> list[dict]:
    out = []
    for active in (3, 4):
        out.append({
            "active_units": active,
            "standby_units": 4 - active,
            "total_hp_flow_g_s": total_hp_flow_g_s,
            "flow_per_active_unit_g_s": total_hp_flow_g_s / active,
            "status": "CANDIDATE_NOT_SELECTED",
        })
    return out


def main() -> None:
    payload = {
        "schema": "qps-w52-p2h-wcs-thermo-proof/v1",
        "design_point": asdict(fsd575_design_proof()),
        "nominal_2K_OP_HP_configurations": nominal_2kop_configurations(),
        "guards": [
            "all_compression_ratios_use_absolute_pressure",
            "14_bara_is_not_converted_as_14_barg",
            "3_of_4_and_4_of_4_are_both_candidates_until_control_strategy_is_source_bound",
            "PVPS_must_be_driven_by_B_return_flow_not_HP_total_flow",
            "reference_efficiencies_are_diagnostics_not_vendor_guarantees",
            "formal_credit_delta=0",
        ],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
