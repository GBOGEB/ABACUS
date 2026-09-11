#!/usr/bin/env python3
"""Deterministic W111 power/utility analysis for governed QPS inputs.

This is an analytical receipt generator. It deliberately does not fetch bidder
PDFs, does not impute UNKNOWN auxiliaries, and cannot promote QPS engineering state.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict

R_HE_KJ_KG_K = 2.077
GAMMA_IDEAL_HE = 5.0 / 3.0


@dataclass(frozen=True)
class CompressionPoint:
    name: str
    mass_flow_kg_s: float
    T1_K: float
    P1_bara: float
    P2_bara: float
    package_input_kW: float
    frequency_Hz: float


def ideal_isothermal_power_kW(point: CompressionPoint) -> float:
    return point.mass_flow_kg_s * R_HE_KJ_KG_K * point.T1_K * math.log(point.P2_bara / point.P1_bara)


def ideal_isentropic_reference_power_kW(point: CompressionPoint, gamma: float = GAMMA_IDEAL_HE) -> float:
    cp = gamma / (gamma - 1.0) * R_HE_KJ_KG_K
    exponent = (gamma - 1.0) / gamma
    ratio = point.P2_bara / point.P1_bara
    return point.mass_flow_kg_s * cp * point.T1_K * (ratio**exponent - 1.0)


def package_isothermal_efficiency(point: CompressionPoint) -> float:
    return ideal_isothermal_power_kW(point) / point.package_input_kW


def isentropic_boundary_diagnostic(point: CompressionPoint) -> dict[str, object]:
    ideal = ideal_isentropic_reference_power_kW(point)
    apparent = ideal / point.package_input_kW
    applicable = apparent <= 1.0
    return {
        "ideal_isentropic_reference_kW": ideal,
        "apparent_full_ratio_efficiency": apparent,
        "classification": "REFERENCE_ONLY" if not applicable else "CANDIDATE_IF_CONTROL_VOLUME_MATCHES",
        "reason": (
            "Full 1.05->14 bara HP package is strongly intercooled/multistage; an apparent efficiency above one proves "
            "the single adiabatic-stage reference does not match the package work/control-volume boundary."
            if not applicable
            else "Numerically physical, but stage/control-volume compatibility is still required before promotion."
        ),
    }


def invcop(power_kW: float, qeq_kW: float) -> float:
    return power_kW / qeq_kW


def analyze() -> dict[str, object]:
    normal = CompressionPoint("LKT_HP_56Hz_each", 0.0815, 298.0, 1.05, 14.0, 203.5, 56.0)
    max_ref = CompressionPoint("LKT_HP_72Hz_each", 0.112, 298.0, 1.05, 14.0, 357.0, 72.0)

    points = []
    for point in (normal, max_ref):
        points.append({
            "input": asdict(point),
            "ideal_isothermal_kW": ideal_isothermal_power_kW(point),
            "package_isothermal_efficiency": package_isothermal_efficiency(point),
            "isentropic_reference": isentropic_boundary_diagnostic(point),
        })

    qeq = 3.423
    controlled_subtotal = 908.0
    bidder_invCOP = 310.0
    bidder_implied_total = bidder_invCOP * qeq
    residual = bidder_implied_total - controlled_subtotal

    return {
        "schema": "abacus-dow-w111-power-utility-receipt/0.1",
        "authority_scope": "REPO_LOCAL_ANALYTICAL_RUNTIME",
        "engineering_promotion_forbidden": True,
        "source_contract": {
            "qps_child": "GBOGEB/cryoplant-project",
            "source_ssot": "ocd-adr/20_canonical/control/QPS_W111_POWER_UTILITY_SOURCE_SSOT_v1.json",
            "source_ssot_git_blob_sha": "d19975a150a3530cc4db3bd2fbbf4180f757c2a4",
            "keb_contract": "GBOGEB/CODEX:triage/W111_QPS_POWER_UTILITY_KEB_BRIDGE.yaml",
        },
        "compression_points": points,
        "invCOP_screen": {
            "Qeq_margin_kW": qeq,
            "controlled_operating_subtotal_kW": controlled_subtotal,
            "controlled_subtotal_invCOP_W_per_W": invcop(controlled_subtotal, qeq),
            "bidder_reference_invCOP_W_per_W": bidder_invCOP,
            "bidder_implied_total_electrical_kW": bidder_implied_total,
            "unreconciled_electrical_kW": residual,
            "residual_classification": "SOURCE_GAP_NOT_BASELOAD",
        },
        "baseload": {
            "status": "DEFER_NOT_IDENTIFIED",
            "reason": "Need >=3 independent same-boundary operating points and explicit electrical metering boundary before fitting an intercept.",
        },
        "pca": {
            "status": "DEFER_SAMPLE_INADEQUATE_FOR_CURRENT_TWO_POINT_HP_SET",
            "minimum_sample_rule": "n >= max(10, 3*p) unless alternate adequacy test is documented",
        },
        "next_BG": "UNRECONCILED_E3_ELECTRICAL_BOUNDARY_AND_MISSING_HP_PVPS_AUXILIARY_SPLIT",
        "next_CG": "SOURCE_BOUND_SLD_LOAD_SCHEDULE_PLUS_SAME_POINT_MOTOR_VFD_AUXILIARY_DECOMPOSITION",
    }


def validate_receipt(receipt: dict[str, object]) -> None:
    assert receipt["engineering_promotion_forbidden"] is True
    points = receipt["compression_points"]
    assert isinstance(points, list) and len(points) == 2
    normal = points[0]
    assert 0.63 < normal["package_isothermal_efficiency"] < 0.66
    assert normal["isentropic_reference"]["classification"] == "REFERENCE_ONLY"
    inv = receipt["invCOP_screen"]
    assert abs(inv["bidder_implied_total_electrical_kW"] - 1061.13) < 1e-6
    assert abs(inv["unreconciled_electrical_kW"] - 153.13) < 1e-6
    assert receipt["baseload"]["status"] == "DEFER_NOT_IDENTIFIED"


if __name__ == "__main__":
    result = analyze()
    validate_receipt(result)
    print(json.dumps(result, indent=2, sort_keys=True))
