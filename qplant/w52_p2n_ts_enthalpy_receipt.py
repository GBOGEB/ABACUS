"""W52-P2N: thermal-shield enthalpy receipt against contract and LKT design target.

Source semantics:
- USER/contract base load: 8200 W
- LKT design target: 8610 W (= 8200 * 1.05)
- LKT thermal-shield state: 81 g/s, 40 K at HP -> 60 K at HP-1 bar
- LKT HP control window: 9..14 bara

The strict residual remains open until the exact 2K-OP HP operating point is source-bound.
Until then this module emits a governed residual envelope and a separate 14/13 bara
contract-projection diagnostic. Neither sensitivity nor projection alone earns 1/5.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from models.helium_properties.provider import state_tp

BAR = 1e5
MDOT_KG_S = 81.0 / 1000.0
Q_CONTRACT_W = 8200.0
Q_LKT_DESIGN_W = 8610.0
ENERGY_TOLERANCE_PERCENT = 1.0  # engineering-control tolerance, not contract acceptance


@dataclass(frozen=True)
class ReceiptPoint:
    basis: str
    hp_bara: float
    return_bara: float
    h_D_J_kg: float
    h_E_J_kg: float
    calculated_duty_W: float
    residual_vs_contract_W: float
    residual_vs_contract_percent: float
    residual_vs_lkt_design_W: float
    residual_vs_lkt_design_percent: float
    runtime_validation_D: str
    runtime_validation_E: str
    within_engineering_tolerance_vs_lkt: bool


def evaluate(hp_bara: float, basis: str) -> ReceiptPoint:
    if not 9.0 <= hp_bara <= 14.0:
        raise ValueError("HP must remain inside source-bound LKT 9..14 bara control window")
    p_e_bara = hp_bara - 1.0
    d = state_tp(40.0, hp_bara * BAR)
    e = state_tp(60.0, p_e_bara * BAR)
    q_calc = MDOT_KG_S * (e.enthalpy_J_kg - d.enthalpy_J_kg)
    r_contract = q_calc - Q_CONTRACT_W
    r_lkt = q_calc - Q_LKT_DESIGN_W
    rp_contract = 100.0 * r_contract / Q_CONTRACT_W
    rp_lkt = 100.0 * r_lkt / Q_LKT_DESIGN_W
    return ReceiptPoint(
        basis=basis,
        hp_bara=hp_bara,
        return_bara=p_e_bara,
        h_D_J_kg=d.enthalpy_J_kg,
        h_E_J_kg=e.enthalpy_J_kg,
        calculated_duty_W=q_calc,
        residual_vs_contract_W=r_contract,
        residual_vs_contract_percent=rp_contract,
        residual_vs_lkt_design_W=r_lkt,
        residual_vs_lkt_design_percent=rp_lkt,
        runtime_validation_D=d.validation,
        runtime_validation_E=e.validation,
        within_engineering_tolerance_vs_lkt=abs(rp_lkt) <= ENERGY_TOLERANCE_PERCENT,
    )


def report() -> dict:
    window = [evaluate(p, "LKT_HP_WINDOW_SENSITIVITY") for p in (9, 10, 11, 12, 13, 14)]
    projection = evaluate(14.0, "CONTRACT_PROJECTION_APPROXIMATE_14_13_BARA")
    q_values = [p.calculated_duty_W for p in window]
    residuals = [p.residual_vs_lkt_design_W for p in window]
    return {
        "schema": "qps-w52-p2n-ts-enthalpy-receipt/v1",
        "reference_chain": {
            "contract_base_W": Q_CONTRACT_W,
            "design_margin_percent": 5.0,
            "lkt_design_target_W": Q_LKT_DESIGN_W,
        },
        "source_state": {
            "mdot_g_s": 81.0,
            "T_D_K": 40.0,
            "T_E_K": 60.0,
            "P_D": "HP",
            "P_E": "HP-1 bar",
            "HP_window_bara": [9.0, 14.0],
        },
        "window_points": [asdict(p) for p in window],
        "contract_projection_14_13": asdict(projection),
        "calculated_duty_envelope_W": {"min": min(q_values), "max": max(q_values)},
        "lkt_design_residual_envelope_W": {"min": min(residuals), "max": max(residuals)},
        "pressure_sensitivity_W": max(q_values) - min(q_values),
        "engineering_tolerance_percent": ENERGY_TOLERANCE_PERCENT,
        "strict_status": "OPEN_EXACT_2K_OP_HP_SETPOINT_AND_CHILD_DISPOSITION",
        "strict_score_effect": 0,
        "guards": [
            "8200W_is_contract_base_not_LKT_design_target",
            "8610W_is_8200W_plus_5_percent_design_margin",
            "14_13_bara_is_contract_projection_not_exact_LKT_2K_OP_setpoint",
            "runtime_property_success_is_not_independent_reference_validation",
            "no_1_of_5_without_exact_basis_tolerance_provenance_and_child_disposition",
        ],
    }
