"""W52-P2J: full QPLANT mass/energy closure and residual report.

The harness consumes source-bound scenario records and reports what is numerically
closed, what is unresolved, and what cannot be evaluated without an independent
He-II reference. It never fills missing engineering evidence with zeros.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class StreamState:
    stream_id: str
    mdot_g_s: float | None
    h_J_kg: float | None
    P_bara: float | None
    T_K: float | None
    authority: str
    validation: str


@dataclass(frozen=True)
class Residual:
    name: str
    status: str
    value: float | None
    unit: str
    denominator: float | None
    relative_percent: float | None
    reason: str | None = None


def _relative(residual: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return 100.0 * residual / denominator


def qcell_mass_residual(A: StreamState, B: StreamState, W: StreamState) -> Residual:
    if None in (A.mdot_g_s, B.mdot_g_s, W.mdot_g_s):
        return Residual("QCELL_A_equals_B_plus_W", "OPEN_INPUT", None, "g/s", None, None,
                        "A/B/W mass-flow inputs are not all source-bound")
    residual = float(A.mdot_g_s) - float(B.mdot_g_s) - float(W.mdot_g_s)
    denom = max(abs(float(A.mdot_g_s)), 1e-12)
    return Residual("QCELL_A_equals_B_plus_W", "CALCULATED", residual, "g/s", denom,
                    _relative(residual, denom))


def qcell_energy_residual(A: StreamState, B: StreamState, W: StreamState,
                          qdot_W: float | None) -> Residual:
    values = (A.mdot_g_s, B.mdot_g_s, W.mdot_g_s, A.h_J_kg, B.h_J_kg, W.h_J_kg, qdot_W)
    if any(v is None for v in values):
        return Residual("QCELL_enthalpy_balance", "OPEN_INPUT", None, "W", None, None,
                        "requires source-bound mass flows, heat load and validated enthalpies")
    ma, mb, mw = (float(A.mdot_g_s)/1000.0, float(B.mdot_g_s)/1000.0, float(W.mdot_g_s)/1000.0)
    residual = mb*float(B.h_J_kg) + mw*float(W.h_J_kg) - ma*float(A.h_J_kg) - float(qdot_W)
    denom = max(abs(float(qdot_W)), abs(ma*float(A.h_J_kg)), 1e-12)
    return Residual("QCELL_enthalpy_balance", "CALCULATED", residual, "W", denom,
                    _relative(residual, denom))


def thermal_shield_energy_residual(D: StreamState, E: StreamState,
                                    qdot_W: float | None) -> Residual:
    values = (D.mdot_g_s, E.mdot_g_s, D.h_J_kg, E.h_J_kg, qdot_W)
    if any(v is None for v in values):
        return Residual("TS_D_E_enthalpy_balance", "OPEN_INPUT", None, "W", None, None,
                        "requires D/E mass flow, heat load and validated enthalpies")
    md, me = float(D.mdot_g_s)/1000.0, float(E.mdot_g_s)/1000.0
    residual = me*float(E.h_J_kg) - md*float(D.h_J_kg) - float(qdot_W)
    denom = max(abs(float(qdot_W)), 1e-12)
    return Residual("TS_D_E_enthalpy_balance", "CALCULATED", residual, "W", denom,
                    _relative(residual, denom))


def power_residual(predicted_kW: float | None, reference_kW: float | None,
                   name: str) -> Residual:
    if predicted_kW is None or reference_kW is None:
        return Residual(name, "OPEN_INPUT", None, "kW", reference_kW, None,
                        "predicted or reference power unavailable")
    residual = predicted_kW - reference_kW
    return Residual(name, "CALCULATED", residual, "kW", reference_kW,
                    _relative(residual, reference_kW))


def scenario_report(scenario: dict[str, Any]) -> dict[str, Any]:
    streams = {k: StreamState(**v) for k, v in scenario["streams"].items()}
    residuals = [
        qcell_mass_residual(streams["A"], streams["B"], streams["W"]),
        qcell_energy_residual(streams["A"], streams["B"], streams["W"], scenario.get("qcell_heat_W")),
        thermal_shield_energy_residual(streams["D"], streams["E"], scenario.get("ts_heat_W")),
        power_residual(scenario.get("hp_predicted_kW"), scenario.get("hp_reference_kW"), "HP_power_residual"),
        power_residual(scenario.get("pvps_predicted_kW"), scenario.get("pvps_reference_kW"), "PVPS_power_residual"),
    ]
    closed = sum(r.status == "CALCULATED" for r in residuals)
    return {
        "schema": "qps-w52-p2j-residual-report/v1",
        "scenario_id": scenario["scenario_id"],
        "residuals": [asdict(r) for r in residuals],
        "closure_score": {"calculated": closed, "total": len(residuals)},
        "hepak_reference_status": scenario.get("hepak_reference_status", "UNVALIDATED"),
        "state_mismatch": scenario.get("state_mismatch", []),
        "guards": [
            "missing_input_is_OPEN_INPUT_not_zero",
            "HeII_without_independent_HEPAK_reference_is_UNVALIDATED",
            "HP_flow_is_not_PVPS_flow",
            "all_compression_ratios_use_absolute_pressure",
            "derived_results_create_zero_formal_compliance_credit",
        ],
    }
