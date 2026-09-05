"""W52-P2R: ALAT thermal-shield strict residual attempt.

The ALAT current offer gives a non-binding thermodynamic example with QTS=8200 W,
D=14.12 bara/35 K, E=13.12 bara/55 K and quoted hD/hE. The 77.01 g/s flow
was reconstructed from Q/delta-h, so this pulse is a property-consistency proof,
not an independent physical residual closure.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from models.helium_properties.provider import state_tp

BAR = 1e5
MDOT_KG_S = 77.01 / 1000.0
Q_REF_W = 8200.0
P_D_BARA, T_D_K = 14.12, 35.0
P_E_BARA, T_E_K = 13.12, 55.0
ALAT_H_D, ALAT_H_E = 196438.0, 302915.0
ENERGY_TOLERANCE_PERCENT = 1.0
DELTA_H_CROSSCHECK_TOLERANCE_PERCENT = 1.0


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
    delta_h_delta_pct = pct_delta(runtime.delta_h_J_kg, bidder.delta_h_J_kg)
    runtime_pass = abs(runtime.residual_percent) <= ENERGY_TOLERANCE_PERCENT
    bidder_pass = abs(bidder.residual_percent) <= ENERGY_TOLERANCE_PERCENT
    crosscheck_pass = abs(delta_h_delta_pct) <= DELTA_H_CROSSCHECK_TOLERANCE_PERCENT
    independent_flow_status = "PENDING_INDEPENDENT_EXACT_TS_FLOW"
    independent_numeric_reference_status = "ALAT_QUOTED_DELTA_H_CROSSCHECK_PASS" if crosscheck_pass else "FAIL"
    strict_pass = False  # fail-closed: 77.01 g/s is reconstructed from Q/delta-h
    return {
        "schema": "qps-w52-p2r-alat-ts-strict-residual/v2",
        "source_state": {
            "mdot_g_s": 77.01,
            "mdot_role": "DERIVED_FROM_ALAT_Q_AND_QUOTED_DELTA_H_NOT_INDEPENDENT",
            "D": {"P_bara": P_D_BARA, "T_K": T_D_K},
            "E": {"P_bara": P_E_BARA, "T_K": T_E_K},
            "Q_reference_W": Q_REF_W,
            "source_role": "ALAT_CURRENT_OFFER_NON_BINDING_EXAMPLE",
        },
        "runtime": asdict(runtime),
        "alat_quoted_enthalpy_crosscheck": asdict(bidder),
        "crosscheck": {
            "quantity": "delta_h_not_absolute_h",
            "reason": "absolute_enthalpy_reference_zero_can_differ_between_property_packages",
            "runtime_minus_ALAT_delta_h_percent": delta_h_delta_pct,
            "tolerance_percent": DELTA_H_CROSSCHECK_TOLERANCE_PERCENT,
            "pass": crosscheck_pass,
        },
        "energy_gate": {
            "tolerance_percent": ENERGY_TOLERANCE_PERCENT,
            "runtime_pass": runtime_pass,
            "alat_quoted_enthalpy_pass": bidder_pass,
        },
        "independence_gate": {
            "numeric_property_crosscheck": independent_numeric_reference_status,
            "flow_independence": independent_flow_status,
            "contract_table9_flow": "approximately 77 g/s; useful corroboration but not an exact independent operating flow",
            "pass": false if False else False,
        },
        "strict_residual": {
            "status": "PASS" if strict_pass else "DEFER_DERIVED_FLOW_NOT_INDEPENDENT",
            "score_before": "0/5",
            "score_after": "1/5" if strict_pass else "0/5",
            "formal_credit_delta": 0,
        },
    }


if __name__ == "__main__":
    print(json.dumps(report(), indent=2, sort_keys=True))
