#!/usr/bin/env python3
"""Deterministic W111 analysis consuming exact QPS, KEB and CoolProp receipts."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

R_HE_KJ_KG_K = 2.077
GAMMA_IDEAL_HE = 5.0 / 3.0
ROOT = Path(__file__).resolve().parents[1]
PAYLOAD_PATH = ROOT / "triage" / "payloads" / "QPS_W111_POWER_UTILITY_SANITIZED_v1.json"
KEB_RECEIPT_PATH = ROOT / "triage" / "receipts" / "KEB_W111_POWER_UTILITY_INPUT_RECEIPT.json"
COOLPROP_RECEIPT_PATH = ROOT / "triage" / "receipts" / "COOLPROP_W111_POWER_UTILITY_THERMO_RECEIPT.json"
EXPECTED_PAYLOAD_SHA256 = "cb66708b29a57abd8cd2721e40706a114f74e1941c1692af8c465370d96e124b"
EXPECTED_CHILD_SSOT_BLOB = "d19975a150a3530cc4db3bd2fbbf4180f757c2a4"
EXPECTED_KEB_ARTIFACT_ID = 10266200791
EXPECTED_COOLPROP_RECEIPT_SHA256 = "85c8a7c0796fa031381c3b2144820af7adff4bab3e4bf31e41b89b2649f5a022"


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
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def load_payload() -> tuple[dict, str]:
    envelope = load_json(PAYLOAD_PATH)
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
    for flag in ("raw_bidder_pdf_included", "raw_offer_text_included", "commercial_price_table_included"):
        if confidentiality.get(flag) is not False:
            raise ValueError(f"forbidden payload flag: {flag}")
    return body, declared


def load_and_verify_keb(payload_sha256: str) -> dict:
    envelope = load_json(KEB_RECEIPT_PATH)
    artifact = envelope.get("artifact", {})
    receipt = envelope.get("receipt", {})
    if artifact.get("artifact_id") != EXPECTED_KEB_ARTIFACT_ID:
        raise ValueError("unexpected KEB artifact id")
    if receipt.get("receipt_id") != "KEB-W111-POWER-UTILITY":
        raise ValueError("wrong KEB receipt id")
    if receipt.get("semantic_checks") != "PASS" or receipt.get("provenance_checks") != "PASS":
        raise ValueError("KEB semantic/provenance receipt not PASS")
    if receipt.get("confidentiality_checks") != "PASS":
        raise ValueError("KEB confidentiality receipt not PASS")
    if receipt.get("engineering_promotion_forbidden") is not True:
        raise ValueError("KEB promotion guard missing")
    if receipt.get("input_payload_sha256") != payload_sha256:
        raise ValueError("KEB input payload digest mismatch")
    if receipt.get("output_payload_sha256") != payload_sha256:
        raise ValueError("KEB output payload digest mismatch")
    if receipt.get("payload_digest_preserved") is not True:
        raise ValueError("KEB did not preserve payload digest")
    if receipt.get("child_source_ssot_git_blob_sha") != EXPECTED_CHILD_SSOT_BLOB:
        raise ValueError("KEB child SSOT identity mismatch")
    return envelope


def load_and_verify_coolprop() -> dict:
    envelope = load_json(COOLPROP_RECEIPT_PATH)
    artifact = envelope.get("artifact", {})
    receipt = envelope.get("receipt", {})
    if artifact.get("receipt_sha256") != EXPECTED_COOLPROP_RECEIPT_SHA256:
        raise ValueError("unexpected CoolProp receipt SHA256")
    if receipt.get("authority_scope") != "COMPATIBILITY_REFERENCE":
        raise ValueError("CoolProp authority scope mismatch")
    if receipt.get("engineering_promotion_forbidden") is not True:
        raise ValueError("CoolProp promotion guard missing")
    if receipt.get("consumer") != "GBOGEB/ABACUS":
        raise ValueError("CoolProp receipt consumer mismatch")
    qps = receipt.get("qps_child_authority", {})
    if qps.get("source_ssot_git_blob_sha") != EXPECTED_CHILD_SSOT_BLOB:
        raise ValueError("CoolProp child SSOT identity mismatch")
    inp = receipt.get("input", {})
    if not (inp.get("mass_flow_kg_s") == 0.0815 and inp.get("P1_Pa") == 105000.0 and inp.get("P2_Pa") == 1400000.0 and inp.get("T1_K") == 298.0 and inp.get("package_input_kW") == 203.5):
        raise ValueError("CoolProp same-point input mismatch")
    if receipt.get("isentropic_reference", {}).get("classification") != "REFERENCE_ONLY_FOR_INTERCOOLED_PACKAGE":
        raise ValueError("CoolProp isentropic boundary guard missing")
    return envelope


def atom_map(body: dict) -> dict[str, dict]:
    return {str(atom["id"]): atom for atom in body.get("atoms", [])}


def atom_value(atoms: dict[str, dict], atom_id: str) -> float:
    return float(atoms[atom_id]["value"])


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
        "classification": "CANDIDATE_IF_CONTROL_VOLUME_MATCHES" if applicable else "REFERENCE_ONLY",
        "reason": (
            "Full 1.05->14 bara HP package is strongly intercooled/multistage; an apparent efficiency above one proves "
            "the single adiabatic-stage reference does not match the package work/control-volume boundary."
            if not applicable
            else "Numerically physical, but stage/control-volume compatibility is still required before promotion."
        ),
    }


def invcop(power_kW: float, qeq_kW: float) -> float:
    return power_kW / qeq_kW


def relative_delta(reference: float, candidate: float) -> float:
    return (candidate - reference) / reference


def analyze() -> dict[str, object]:
    body, payload_sha256 = load_payload()
    keb = load_and_verify_keb(payload_sha256)
    coolprop = load_and_verify_coolprop()
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
    max_ref = CompressionPoint("LKT_HP_72Hz_each", 0.112, 298.0, 1.05, 14.0, 357.0, 72.0)

    points = []
    for point in (normal, max_ref):
        points.append({
            "input": asdict(point),
            "ideal_isothermal_kW": ideal_isothermal_power_kW(point),
            "package_isothermal_efficiency": package_isothermal_efficiency(point),
            "isentropic_reference": isentropic_boundary_diagnostic(point),
        })

    cp_receipt = coolprop["receipt"]
    cp_iso = float(cp_receipt["isothermal_reference"]["ideal_power_kW"])
    cp_eta = float(cp_receipt["isothermal_reference"]["package_isothermal_efficiency"])
    cp_is = float(cp_receipt["isentropic_reference"]["ideal_power_kW"])
    local_iso = float(points[0]["ideal_isothermal_kW"])
    local_eta = float(points[0]["package_isothermal_efficiency"])
    local_is = float(points[0]["isentropic_reference"]["ideal_isentropic_reference_kW"])

    qeq = atom_value(atoms, "LKT_INV_COP_QEQ_MARGIN")
    controlled_subtotal = atom_value(atoms, "LKT_CONTROLLED_OPERATING_SUBTOTAL")
    bidder_invCOP = atom_value(atoms, "LKT_INV_COP_REFERENCE")
    bidder_implied_total = atom_value(atoms, "LKT_INV_COP_IMPLIED_TOTAL_ELECTRICAL")
    residual = atom_value(atoms, "LKT_UNRECONCILED_ELECTRICAL")

    return {
        "schema": "abacus-dow-w111-power-utility-receipt/0.3",
        "authority_scope": "REPO_LOCAL_ANALYTICAL_RUNTIME",
        "engineering_promotion_forbidden": True,
        "source_contract": {
            "qps_child": "GBOGEB/cryoplant-project",
            "source_ssot": "ocd-adr/20_canonical/control/QPS_W111_POWER_UTILITY_SOURCE_SSOT_v1.json",
            "source_ssot_git_blob_sha": EXPECTED_CHILD_SSOT_BLOB,
            "input_payload_sha256": payload_sha256,
            "payload_digest_verified": True,
            "keb_receipt_verified": True,
            "keb_run_id": keb["artifact"]["run_id"],
            "keb_artifact_id": keb["artifact"]["artifact_id"],
            "coolprop_receipt_verified": True,
            "coolprop_run_id": coolprop["artifact"]["run_id"],
            "coolprop_receipt_sha256": coolprop["artifact"]["receipt_sha256"],
        },
        "compression_points": points,
        "independent_thermophysical_crosscheck": {
            "source": "GBOGEB/CoolProp exact workflow receipt",
            "coolprop_version": cp_receipt["coolprop"]["version"],
            "coolprop_git_head": cp_receipt["coolprop"]["git_head"],
            "local_ideal_isothermal_kW": local_iso,
            "coolprop_ideal_isothermal_kW": cp_iso,
            "isothermal_relative_delta": relative_delta(cp_iso, local_iso),
            "local_package_isothermal_efficiency": local_eta,
            "coolprop_package_isothermal_efficiency": cp_eta,
            "efficiency_relative_delta": relative_delta(cp_eta, local_eta),
            "local_ideal_isentropic_reference_kW": local_is,
            "coolprop_ideal_isentropic_reference_kW": cp_is,
            "isentropic_reference_relative_delta": relative_delta(cp_is, local_is),
            "disposition": "CORROBORATES_IDEAL_WORK_WITHIN_MODEL_DIFFERENCE_NOT_ENGINEERING_PROMOTION",
        },
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
    source = receipt["source_contract"]
    assert source["input_payload_sha256"] == EXPECTED_PAYLOAD_SHA256
    assert source["payload_digest_verified"] is True
    assert source["keb_receipt_verified"] is True
    assert source["coolprop_receipt_verified"] is True
    points = receipt["compression_points"]
    assert isinstance(points, list) and len(points) == 2
    normal = points[0]
    assert normal["input"]["frequency_Hz"] == 56.0
    assert 0.63 < normal["package_isothermal_efficiency"] < 0.66
    assert normal["isentropic_reference"]["classification"] == "REFERENCE_ONLY"
    cross = receipt["independent_thermophysical_crosscheck"]
    assert abs(cross["isothermal_relative_delta"]) < 0.001
    assert abs(cross["efficiency_relative_delta"]) < 0.001
    assert abs(cross["isentropic_reference_relative_delta"]) < 0.001
    inv = receipt["invCOP_screen"]
    assert abs(inv["bidder_implied_total_electrical_kW"] - 1061.13) < 1e-6
    assert abs(inv["unreconciled_electrical_kW"] - 153.13) < 1e-6
    assert receipt["baseload"]["status"] == "DEFER_NOT_IDENTIFIED"


if __name__ == "__main__":
    result = analyze()
    validate_receipt(result)
    print(json.dumps(result, indent=2, sort_keys=True))
