import json

from scripts.proposal_compatibility import emit_mip, validate_envelope


def contract():
    return {
        "required_fields": [
            "schema_version",
            "proposal_id",
            "method",
            "source_sha",
            "proposal_type",
            "risk_class",
            "scope",
            "mutation_mode",
            "worker_model",
            "protected_holds",
            "evidence_receipts",
            "admission",
            "coverage_growth",
            "authority",
        ],
        "compatible_methods": ["DAB", "MIP", "3PSTAR", "DOW", "CI_PROOF"],
        "risk_classes": ["LOW_MECHANICAL", "MEDIUM", "HIGH_OR_PROTECTED", "MEASURED"],
        "mutation_modes": ["READ_ONLY_PROPOSAL", "SINGLE_WRITER_MUTATION"],
        "coverage_growth": {
            "required_fields": ["applicability", "baseline_receipt", "target", "result"]
        },
    }


def test_emit_mip_is_compatible(tmp_path):
    evidence = tmp_path / "evidence.json"
    evidence.write_text(json.dumps({"status": "PASS"}), encoding="utf-8")
    envelope = emit_mip("a" * 40, evidence)
    assert validate_envelope(envelope, contract()) == []


def test_validator_rejects_authority_transfer(tmp_path):
    evidence = tmp_path / "evidence.json"
    evidence.write_text("{}", encoding="utf-8")
    envelope = emit_mip("b" * 40, evidence)
    envelope["authority"]["authority_transfer"] = True
    assert "authority_transfer" in validate_envelope(envelope, contract())
