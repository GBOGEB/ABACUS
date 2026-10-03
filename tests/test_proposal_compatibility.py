import json

from scripts.proposal_compatibility import (
    emit_mip,
    iter_envelopes,
    main as validate_main,
    valid_empty_queue,
    validate_envelope,
)


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
        "proposal_types": ["STATIC_REPAIR", "PRESSURE_QUEUE"],
        "worker_model": {
            "proposal_workers": {
                "mode": "READ_ONLY",
                "scalable": True,
                "min": 1,
                "max": 8,
            },
            "mutation_writer": {"count": 1, "required_for_mutation": True},
        },
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


def test_validator_rejects_unknown_type_and_incompatible_worker_model(tmp_path):
    evidence = tmp_path / "evidence.json"
    evidence.write_text("{}", encoding="utf-8")
    envelope = emit_mip("c" * 40, evidence)
    envelope["proposal_type"] = "UNRECOGNIZED"
    envelope["worker_model"]["proposal_workers"] = "SCALABLE_READ_ONLY"
    errors = validate_envelope(envelope, contract())
    assert "proposal_type" in errors
    assert "proposal_workers" in errors


def test_proposal_entries_preserve_malformed_positions():
    entries = iter_envelopes({"proposals": [{"proposal_id": "ok"}, "malformed"]})
    assert entries == [{"proposal_id": "ok"}, "malformed"]


def test_validator_reports_non_object_proposal_by_index(
    tmp_path,
    monkeypatch,
    capsys,
):
    evidence = tmp_path / "evidence.json"
    evidence.write_text("{}", encoding="utf-8")
    payload = {
        "proposals": [emit_mip("e" * 40, evidence), "malformed"],
    }
    input_path = tmp_path / "queue.json"
    input_path.write_text(json.dumps(payload), encoding="utf-8")
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(json.dumps(contract()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "proposal_compatibility.py",
            "--contract",
            str(contract_path),
            "validate",
            "--input",
            str(input_path),
        ],
    )

    assert validate_main() == 1
    assert "1:not_object" in capsys.readouterr().out


def test_empty_queue_is_valid_only_with_clean_or_protected_receipt():
    queue = {
        "schema_version": "abacus-dab-proposal-queue/1.0.0",
        "source_sha": "d" * 40,
        "measurement": {"total": 0, "families": {}},
        "protected_holds": {},
        "worker_model": {
            "proposal_workers": {"min": 2, "max": 8, "mode": "READ_ONLY"},
            "mutation_writer_count": 1,
            "parallel_proposals_allowed": True,
            "parallel_mutation_for_same_scope_allowed": False,
        },
        "governance": {
            "authority_transfer": False,
            "formal_credit_delta": 0,
            "engineering_credit_delta": 0,
        },
        "proposals": [],
    }
    assert valid_empty_queue(queue)
    queue["measurement"] = {"total": 1, "families": {"E999": 1}}
    queue["protected_holds"] = {"E999": {"count": 1}}
    assert valid_empty_queue(queue)
    queue["protected_holds"] = {}
    assert not valid_empty_queue(queue)
