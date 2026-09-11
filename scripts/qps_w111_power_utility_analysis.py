#!/usr/bin/env python3
"""Deterministic W111 analysis consuming the exact sanitized QPS/KEB payload."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

R_HE_KJ_KG_K = 2.077
GAMMA_IDEAL_HE = 5.0 / 3.0
ROOT = Path(__file__).resolve().parents[1]
PAYLOAD_PATH = (
    ROOT / "triage" / "payloads" / "QPS_W111_POWER_UTILITY_SANITIZED_v1.json"
)
EXPECTED_PAYLOAD_SHA256 = (
    "cb66708b29a57abd8cd2721e40706a114f74e1941c1692af8c465370d96e124b"
)


@dataclass(frozen=True)
class CompressionPoint:
    name: str
    mass_flow_kg_s: float
    T1_K: float
    P1_bara: float
    P2_bara: float
    package_input_kW: float
    frequency_Hz: float


def canonical_payload_sha256(body: dict) -> str:
    encoded = json.dumps(
        body,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_payload() -> tuple[dict, str]:
    envelope = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))
    body = envelope.get("payload_body")
    if not isinstance(body, dict):
        raise ValueError("payload_body must be a mapping")
    calculated = canonical_payload_sha256(body)
    declared = str(envelope.get("payload_sha256", ""))
    if calculated != declared:
        raise ValueError("W111 payload declared/calculated SHA256 mismatch")
    if declared != EXPECTED_PAYLOAD_SHA256:
        raise ValueError("unexpected W111 payload digest")
    confidentiality = body.get("confidentiality", {})
    for flag in (
        "raw_bidder_pdf_included",
        "raw_offer_text_included",
        "commercial_price_table_included",
    ):
        if confidentiality.get(flag) is not False:
            raise ValueError(f"forbidden payload flag: {flag}")
    return body, declared


def atom_map(body: dict) -> dict[str, dict]:
    return {str(atom["id"]): atom for atom in body.get("atoms", [])}


def atom_value(atoms: dict[str, dict], atom_id: str) -> float:
    return float(atoms[atom_id]["value"])


def ideal_isothermal_power_kW(point: CompressionPoint) -> float:
    return (
        point.mass_flow_kg_s
        * R_HE_KJ_KG_K
        * point.T1_K
        * math.log(point.P2_bara / point.P1_bara)
    )


def ideal_isentropic_reference_power_kW(
    point: CompressionPoint,
    gamma: float = GAMMA_IDEAL_HE,
) -> float:
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
        "classification": (
            "CANDIDATE_IF_CONTROL_VOLUME_MATCHES"
            if applicable
            else "REFERENCE_ONLY"
        ),
        "reason": (
            "Full 1.05->14 bara HP package is strongly intercooled/multistage; "
            "an apparent efficiency above one proves that the single adiabatic-stage "
            "reference does not match the package work/control-volume boundary."
            if not applicable
            else "Numerically physical, but stage/control-volume compatibility is "
            "still required before promotion."
        ),
    }


def invcop(power_kW: float, qeq_kW: float) -> float:
    return power_kW / qeq_kW


def analyze() -> dict[str, object]:
    body, payload_sha256 = load_payload()
    atoms = atom_map(body)

    normal = CompressionPoint(
        "LKT_HP_56Hz_each",
        atom_value(atoms, "LKT_HP_FLOW_EACH_2KOP") / 1000.0,
        298.0,
        atom_value(atoms, "LKT_HP_P1"),
        atom_value(atoms, "LKT_HP_P2"),
        atom_value(atoms, "LKT_HP_ELECTRICAL_2KOP") / 4.0,
        atom_value(atoms, "LKT_HP_FREQUENCY_2KOP"),
    )

    # Separate bidder-selected maximum point remains source-bound in the DOW manifest.
    max_ref = CompressionPoint(
        "LKT_HP_72Hz_each",
        0.112,
        298.0,
        1.05,
        14.0,
        357.0,
        72.0,
    )

    points = []
    for point in (normal, max_ref):
        points.append(
            {
                "input": asdict(point),
                "ideal_isothermal_kW": ideal_isothermal_power_kW(point),
                "package_isothermal_efficiency": package_isothermal_efficiency(point),
                "isentropic_reference": isentropic_boundary_diagnostic(point),
            }
        )

    qeq = atom_value(atoms, "LKT_INV_COP_QEQ_MARGIN")
    controlled_subtotal = atom_value(atoms, "LKT_CONTROLLED_OPERATING_SUBTOTAL")
    bidder_invCOP = atom_value(atoms, "LKT_INV_COP_REFERENCE")
    bidder_implied_total = atom_value(
        atoms,
        "LKT_INV_COP_IMPLIED_TOTAL_ELECTRICAL",
    )
    residual = atom_value(atoms, "LKT_UNRECONCILED_ELECTRICAL")

    return {
        "schema": "abacus-dow-w111-power-utility-receipt/0.2",
        "authority_scope": "REPO_LOCAL_ANALYTICAL_RUNTIME",
        "engineering_promotion_forbidden": True,
        "source_contract": {
            "qps_child": "GBOGEB/cryoplant-project",
            "source_ssot": (
                "ocd-adr/20_canonical/control/"
                "QPS_W111_POWER_UTILITY_SOURCE_SSOT_v1.json"
            ),
            "source_ssot_git_blob_sha": (
                "d19975a150a3530cc4db3bd2fbbf4180f757c2a4"
            ),
            "keb_contract": (
                "GBOGEB/CODEX:triage/"
                "W111_QPS_POWER_UTILITY_KEB_BRIDGE.yaml"
            ),
            "input_payload_sha256": payload_sha256,
            "payload_digest_verified": True,
        },
        "compression_points": points,
        "invCOP_screen": {
            "Qeq_margin_kW": qeq,
            "controlled_operating_subtotal_kW": controlled_subtotal,
            "controlled_subtotal_invCOP_W_per_W": invcop(
                controlled_subtotal,
                qeq,
            ),
            "bidder_reference_invCOP_W_per_W": bidder_invCOP,
            "bidder_implied_total_electrical_kW": bidder_implied_total,
            "unreconciled_electrical_kW": residual,
            "residual_classification": "SOURCE_GAP_NOT_BASELOAD",
        },
        "baseload": {
            "status": "DEFER_NOT_IDENTIFIED",
            "reason": (
                "Need >=3 independent same-boundary operating points and explicit "
                "electrical metering boundary before fitting an intercept."
            ),
        },
        "pca": {
            "status": "DEFER_SAMPLE_INADEQUATE_FOR_CURRENT_TWO_POINT_HP_SET",
            "minimum_sample_rule": (
                "n >= max(10, 3*p) unless alternate adequacy test is documented"
            ),
        },
        "next_BG": (
            "UNRECONCILED_E3_ELECTRICAL_BOUNDARY_AND_MISSING_"
            "HP_PVPS_AUXILIARY_SPLIT"
        ),
        "next_CG": (
            "SOURCE_BOUND_SLD_LOAD_SCHEDULE_PLUS_SAME_POINT_"
            "MOTOR_VFD_AUXILIARY_DECOMPOSITION"
        ),
    }


def validate_receipt(receipt: dict[str, object]) -> None:
    assert receipt["engineering_promotion_forbidden"] is True
    assert receipt["source_contract"]["input_payload_sha256"] == EXPECTED_PAYLOAD_SHA256
    assert receipt["source_contract"]["payload_digest_verified"] is True
    points = receipt["compression_points"]
    assert isinstance(points, list) and len(points) == 2
    normal = points[0]
    assert normal["input"]["frequency_Hz"] == 56.0
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
