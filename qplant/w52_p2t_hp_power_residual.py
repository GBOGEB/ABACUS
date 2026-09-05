"""W52-P2U: repaired independent HP power residual triage for nominal LKT 2K-OP point.

Source-bound bidder point:
- total HP mass flow = 326 g/s
- package input power = 814 kW

Candidate compression boundary inherited from the LKT 72 Hz reference:
- P1 = 1.05 bara, T1 = 298 K, P2 = 14 bara

Independent engineering model:
- helium ideal-isothermal work with R=2077 J/kg/K
- owner engineering electrical efficiency screening value = 50%
- secondary real-gas isentropic lower-bound from governed CoolProp provider

This script is fail-closed: it does not assume the 72 Hz boundary is the exact nominal 2K-OP boundary.
A large residual diagnoses boundary/configuration mismatch rather than vendor non-compliance.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from models.helium_properties.provider import state_tp

R_HE = 2077.0
MDOT_KG_S = 326.0 / 1000.0
T1_K = 298.0
P1_BARA = 1.05
P2_BARA = 14.0
P_REF_KW = 814.0
ETA_ELECTRICAL = 0.50


def main() -> None:
    p1 = P1_BARA * 1e5
    p2 = P2_BARA * 1e5
    st1 = state_tp(T1_K, p1)
    props = __import__("CoolProp.CoolProp", fromlist=["PropsSI"])
    h2s = float(props.PropsSI("H", "P", p2, "S", st1.entropy_J_kgK, "Helium"))

    w_iso = R_HE * T1_K * math.log(p2 / p1)
    p_iso_kw = MDOT_KG_S * w_iso / 1000.0
    p_elec_kw = p_iso_kw / ETA_ELECTRICAL
    p_isentropic_kw = MDOT_KG_S * (h2s - st1.enthalpy_J_kg) / 1000.0

    residual_kw = p_elec_kw - P_REF_KW
    residual_pct = 100.0 * residual_kw / P_REF_KW
    eta_required = p_iso_kw / P_REF_KW

    payload = {
        "schema": "qps-w52-p2u-hp-power-residual/v2",
        "source_point": {
            "hp_total_flow_g_s": 326.0,
            "hp_reference_power_kW": P_REF_KW,
            "authority": "LKT_2K_OP_OPERATING_MODE_SOURCE_BOUND_ANALYTICAL_SSOT",
        },
        "candidate_boundary": {
            "P1_bara": P1_BARA,
            "T1_K": T1_K,
            "P2_bara": P2_BARA,
            "authority": "LKT_72HZ_REFERENCE_BOUNDARY_REUSED_FOR_DIAGNOSTIC_ONLY",
            "exact_nominal_2kop_boundary_confirmed": False,
        },
        "independent_model": {
            "method": "IDEAL_ISOTHERMAL_PLUS_OWNER_50_PERCENT_ELECTRICAL_EFFICIENCY",
            "isothermal_power_kW": p_iso_kw,
            "predicted_electrical_power_kW": p_elec_kw,
            "real_gas_isentropic_lower_bound_kW": p_isentropic_kw,
            "eta_electrical_assumed": ETA_ELECTRICAL,
            "eta_isothermal_required_to_match_814": eta_required,
            "backend": f"CoolProp {st1.backend_version}",
        },
        "residual": {
            "predicted_minus_reference_kW": residual_kw,
            "relative_percent": residual_pct,
            "engineering_tolerance_percent": 5.0,
            "within_tolerance": abs(residual_pct) <= 5.0,
        },
        "strict_gate": {
            "status": "DEFER_EXACT_NOMINAL_HP_BOUNDARY" if abs(residual_pct) > 5.0 else "CANDIDATE_PASS_REQUIRES_CHILD_DISPOSITION",
            "score_before": "1/5",
            "score_after": "1/5",
            "reason": "72Hz maximum-reference boundary is not yet proven identical to nominal 326 g/s 2K-OP boundary",
        },
        "execution_guard": {
            "repo_root_injected": str(REPO_ROOT),
            "false_green_predecessor": "PR897_INVALID_RECEIPT",
        },
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
