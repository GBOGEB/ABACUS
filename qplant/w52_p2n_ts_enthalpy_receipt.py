"""W53-P05K: thermal-shield enthalpy receipt using exact current LKT OFFER-07 2K-OP states.

Source semantics:
- USER/contract base load: 8200 W
- LKT design target: 8610 W (= 8200 * 1.05)
- current LKT OFFER-07 2K-OP: D=40.24 K/12.6 bara; E=60.41 K/11.6 bara
- current LKT thermal-shield mass flow: 81 g/s

The exact current-offer pressure/temperature state supersedes the older HP-window-only guard for this scenario.
Runtime property success remains separate from independent HEPAK/reference validation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from models.helium_properties.provider import state_tp

BAR = 1e5
MDOT_KG_S = 81.0 / 1000.0
Q_CONTRACT_W = 8200.0
Q_LKT_DESIGN_W = 8610.0
ENERGY_TOLERANCE_PERCENT = 1.0


@dataclass(frozen=True)
class ReceiptPoint:
    basis: str
    T_D_K: float
    P_D_bara: float
    T_E_K: float
    P_E_bara: float
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


def evaluate_state(T_D_K: float, P_D_bara: float, T_E_K: float, P_E_bara: float, basis: str) -> ReceiptPoint:
    d = state_tp(T_D_K, P_D_bara * BAR)
    e = state_tp(T_E_K, P_E_bara * BAR)
    q_calc = MDOT_KG_S * (e.enthalpy_J_kg - d.enthalpy_J_kg)
    r_contract = q_calc - Q_CONTRACT_W
    r_lkt = q_calc - Q_LKT_DESIGN_W
    rp_contract = 100.0 * r_contract / Q_CONTRACT_W
    rp_lkt = 100.0 * r_lkt / Q_LKT_DESIGN_W
    return ReceiptPoint(
        basis=basis,
        T_D_K=T_D_K,
        P_D_bara=P_D_bara,
        T_E_K=T_E_K,
        P_E_bara=P_E_bara,
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


def evaluate(hp_bara: float, basis: str) -> ReceiptPoint:
    if not 9.0 <= hp_bara <= 14.0:
        raise ValueError("HP must remain inside source-bound LKT 9..14 bara control window")
    return evaluate_state(40.0, hp_bara, 60.0, hp_bara - 1.0, basis)


def report() -> dict:
    exact = evaluate_state(40.24, 12.6, 60.41, 11.6, "CURRENT_LKT_OFFER_07_2KOP_EXACT")
    window = [evaluate(p, "LKT_HP_WINDOW_SENSITIVITY") for p in (9, 10, 11, 12, 13, 14)]
    projection = evaluate(14.0, "CONTRACT_PROJECTION_APPROXIMATE_14_13_BARA")
    return {
        "schema": "qps-w53-p05k-ts-enthalpy-receipt/v1",
        "reference_chain": {
            "contract_base_W": Q_CONTRACT_W,
            "design_margin_percent": 5.0,
            "lkt_design_target_W": Q_LKT_DESIGN_W,
            "current_offer_source": "LKT OFFER-07 p2 / combined PDF p392",
        },
        "exact_current_offer_state": {
            "mdot_g_s": 81.0,
            "D": {"T_K": 40.24, "P_bara": 12.6},
            "E": {"T_K": 60.41, "P_bara": 11.6},
        },
        "exact_current_offer_receipt": asdict(exact),
        "window_points": [asdict(p) for p in window],
        "contract_projection_14_13": asdict(projection),
        "engineering_tolerance_percent": ENERGY_TOLERANCE_PERCENT,
        "strict_status": "PASS_RUNTIME_IF_EXACT_RECEIPT_WITHIN_1PCT_ELSE_FAIL_RUNTIME; INDEPENDENT_REFERENCE_GATE_SEPARATE",
        "guards": [
            "8200W_is_contract_base_not_LKT_design_target",
            "8610W_is_8200W_plus_5_percent_design_margin",
            "exact_OFFER07_state_supersedes_HP_window_for_current_2KOP",
            "runtime_property_success_is_not_independent_HEPAK_reference_validation",
            "strict_1_of_5_requires_child_disposition_and_governed_reference_policy",
        ],
    }
