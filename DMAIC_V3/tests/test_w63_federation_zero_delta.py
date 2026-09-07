from pathlib import Path

from DMAIC_V3.core.federation_zero_delta import roundtrip_ssot


def test_real_ssot_authority_roundtrips_zero_delta():
    root = Path(__file__).resolve().parents[2]
    receipt = roundtrip_ssot(root, "QPS_CLARIFICATION_REGISTER")
    assert receipt.zero_delta is True
    assert receipt.payload_sha256 == receipt.returned_payload_sha256
    assert receipt.authority_path == "ssot/clarification_register.yaml"
    assert receipt.authority == "AUTHORITATIVE_REFERENCE_ONLY"


def test_repeat_roundtrip_is_deterministic():
    root = Path(__file__).resolve().parents[2]
    first = roundtrip_ssot(root, "SSOT_STYLE")
    second = roundtrip_ssot(root, "SSOT_STYLE")
    assert first.to_dict() == second.to_dict()
