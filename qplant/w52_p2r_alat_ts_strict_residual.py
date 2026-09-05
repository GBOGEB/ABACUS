"""W52-P2R: ALAT thermal-shield strict residual attempt.

Source point (ALAT current offer, explicitly non-binding example):
- mdot = 77.01 g/s
- D = 14.12 bara, 35 K
- E = 13.12 bara, 55 K
- QTS = 8200 W
- ALAT quoted hD = 196438 J/kg, hE = 302915 J/kg

Runtime model: repository-pinned CoolProp provider.
Independent/reference layers are reported separately and never averaged.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from models.helium_properties.provider import state_tp

BAR = 1e5
MDOT_KG_S = 77.01 / 1000.0
Q_REF_W = 8200.0
P_D_BARA = 14.12
T_D_K = 35.0
P_E_BARA = 13.12
T_E_K = 55.0
ALAT_H_D = 196438.0
ALAT_H_E = 302915.0
ENERGY_TOLERANCE_PERCENT = 1.0
ENTHALPY_CROSSCHECK_TOLERANCE_PERCENT = 1.0


@dataclass(frozen=True)
class Result:
    provider: str
    h_D_J_kg: float
    h_E_J_kg: float
    delta_h_J_kg: float
    duty_W: float
    residual_W: float
    residual_percent: float


def calc(provider: str, h_d: float, h_e: float) -> Result:
    dh = h_e - h_d
    q = MDOT_KG_S * dh
    r = q - Q_REF_W
    return Result(provider, h_d, h_e, dh, q, r, 100.0 * r / Q_REF_W)


def pct_delta(a: float, b: float) -> float:
    return 100.0 * (a - b) / b


def report() -> dict:
    d = state_tp(T_D_K, P_D_BARA * BAR)
    e = state_tp(T_E_K, P_E_BARA * BAR)
    runtime = calc(f"{d.backend} {d.backend_version}", d.enthalpy_J_kg, e.enthalpy_J_kg)
    bidder = calc("ALAT_QUOTED_ENTHALPY", ALAT_H_D, ALAT_H_E)
    h_d_delta_pct = pct_delta(runtime.h_D_J_kg, ALAT_H_D)
    h_e_delta_pct = pct_delta(runtime.h_E_J_kg, ALAT_H_E)
    runtime_pass = abs(runtime.residual_percent) <= ENERGY_TOLERANCE_PERCENT
    bidder_pass = abs(bidder.residual_percent) <= ENERGY_TOLERANCE_PERCENT
    crosscheck_pass = max(abs(h_d_delta_pct), abs(h_e_delta_pct)) <= ENTHALPY_CROSSCHECK_TOLERANCE_PERCENT
    independent_reference_status = "NIST_EOS_AUTHORITY_BOUND_NUMERIC_SAME_POINT_PENDING"
    strict_pass = runtime_pass and bidder_pass and crosscheck_pass and independent_reference_status.endswith("PASS")
    return {
        "schema": "qps-w52-p2r-alat-ts-strict-residual/v1",
        "source_state": {
            "mdot_g_s": 77.01,
            "D": {"P_bara": P_D_BARA, "T_K": T_D_K},
            "E": {"P_bara": P_E_BARA, "T_K": T_E_K},
            "Q_reference_W": Q_REF_W,
            "source_role": "ALAT_CURRENT_OFFER_NON_BINDING_EXAMPLE",
        },
        "runtime": asdict(runtime),
        "alat_quoted_enthalpy_crosscheck": asdict(bidder),
        "crosscheck": {
            "runtime_minus_ALAT_hD_percent": h_d_delta_pct,
            "runtime_minus_ALAT_hE_percent": h_e_delta_pct,
            "tolerance_percent": ENTHALPY_CROSSCHECK_TOLERANCE_PERCENT,
            "pass": crosscheck_pass,
        },
        "energy_gate": {
            "tolerance_percent": ENERGY_TOLERANCE_PERCENT,
            "runtime_pass": runtime_pass,
            "alat_quoted_enthalpy_pass": bidder_pass,
        },
        "independent_reference": {
            "model_authority": "NIST helium EOS / REFPROP lineage",
            "same_point_numeric_status": independent_reference_status,
            "note": "ALAT quoted enthalpies are source-independent from the ABACUS runtime calculation but not independent of the bidder. Strict 1/5 remains fail-closed until a same-point numeric independent reference is bound.",
        },
        "strict_residual": {
            "status": "PASS" if strict_pass else "DEFER_INDEPENDENT_NUMERIC_REFERENCE",
            "score_before": "0/5",
            "score_after": "1/5" if strict_pass else "0/5",
            "formal_credit_delta": 0,
        },
    }


if __name__ == "__main__":
    print(json.dumps(report(), indent=2, sort_keys=True))
