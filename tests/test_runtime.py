import csv
import math
from pathlib import Path

import pytest

from models.qps_line_s import rfi_package, runtime
from models.qps_line_s.t_available_grid import t_available_min


def test_decide_pipeline_fail_when_missing():
    assert runtime.decide(["missing.csv"], []) == "PIPELINE_FAIL"


def test_decide_issue_rfi_when_gates_open():
    gates = [{"id": "ASSUM-VEFF", "status": "UNRESOLVED", "severity": None}]
    assert runtime.decide([], gates) == "ISSUE_RFI"


def test_decide_proceed_when_no_missing_and_no_gates():
    assert runtime.decide([], []) == "PROCEED_MDA"


def test_open_gates_supports_current_blocker_structure():
    data = {
        "blockers": [
            {"id": "ASSUM-VEFF", "gate": True, "status": "UNRESOLVED"},
            {"id": "ASSUM-PLIMIT", "gate": True, "status": "OPEN_RFI"},
            {"id": "ASSUM-RECOV-PWR", "gate": True, "status": "BLOCKER", "severity": "high"},
            {"id": "ASSUM-ENERGY-MODEL", "gate": True, "status": "OPEN", "severity": "medium"},
            {"id": "DONE", "gate": True, "status": "RESOLVED"},
        ]
    }
    gates = runtime.open_gates(data)
    assert [gate["id"] for gate in gates] == [
        "ASSUM-VEFF",
        "ASSUM-PLIMIT",
        "ASSUM-RECOV-PWR",
        "ASSUM-ENERGY-MODEL",
    ]


def test_energy_provenance_detects_bound(tmp_path: Path):
    matrix = tmp_path / "matrix.csv"
    with matrix.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["energy_source"])
        writer.writeheader()
        writer.writerow({"energy_source": "gamma_x_ribbon_bound"})
    assert runtime.energy_provenance(matrix) == "bound"


def test_energy_provenance_detects_integrated(tmp_path: Path):
    matrix = tmp_path / "matrix.csv"
    with matrix.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["energy_source"])
        writer.writeheader()
        writer.writerow({"energy_source": "solver@t0"})
    assert runtime.energy_provenance(matrix) == "integrated"


def test_t_available_rejects_invalid_pressure_margin():
    assert math.isnan(t_available_min(1.0, 1.2, 0.1))


def test_runtime_enforce_exits_when_gates_open(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime, "run_generators", lambda: None)
    monkeypatch.setattr(runtime, "missing_artefacts", lambda: [])
    monkeypatch.setattr(runtime, "open_gates", lambda: [{"id": "ASSUM-RECOV-PWR"}])
    monkeypatch.setattr(runtime, "energy_provenance", lambda: "bound")
    monkeypatch.setattr(runtime, "STATUS_OUT", tmp_path / "runtime_status.json")
    with pytest.raises(SystemExit) as exc:
        runtime.runtime(regenerate=True, enforce=True)
    assert exc.value.code == 1


def test_rfi_package_filters_open_gates():
    data = {
        "blockers": [
            {"id": "ASSUM-VEFF", "gate": True, "status": "UNRESOLVED", "why_it_matters": "volume matters"},
            {"id": "ASSUM-PLIMIT", "gate": True, "status": "ACCEPTED"},
            {
                "id": "ASSUM-ENERGY-MODEL",
                "gate": True,
                "status": "OPEN",
                "rationale": "bound only",
                "resolution_options": ["accept", "integrate"],
            },
        ]
    }
    items = rfi_package.open_gate_items(data)
    assert [item["id"] for item in items] == ["ASSUM-VEFF", "ASSUM-ENERGY-MODEL"]


def test_rfi_package_renders_open_gate_count_sections_and_provenance():
    items = [
        {
            "id": "ASSUM-VEFF",
            "title": "Effective volume",
            "status": "UNRESOLVED",
            "severity": "high",
            "rationale": "Need connected gas volume.",
            "resolution_options": ["provide volume"],
        }
    ]
    text = rfi_package.render_rfi(items)
    assert "Generated:" in text
    assert "Source register: docs/qps_line_s_recovery/assumptions_register.yaml" in text
    assert "Register SHA256:" in text
    assert "Git commit:" in text
    assert "Renderer: models/qps_line_s/rfi_package.py" in text
    assert "Do not hand-edit this rendered file" in text
    assert "Open gate count: 1" in text
    assert "## RFI-1: ASSUM-VEFF - Effective volume" in text
    assert "Need connected gas volume." in text
    assert "- provide volume" in text


def test_provenance_header_accepts_deterministic_values():
    header = rfi_package.provenance_header(
        generated_at="2026-06-20T00:00:00+00:00",
        register_hash="abc123",
        commit="deadbeef",
    )
    assert "Generated: 2026-06-20T00:00:00+00:00" in header
    assert "Register SHA256: abc123" in header
    assert "Git commit: deadbeef" in header


from models.qps_line_s import closure_contract


def _mode_by_id(data, mode_id):
    return next(mode for mode in data["modes"] if mode["mode_id"] == mode_id)


def _valve_by_id(mode, valve_id):
    return next(
        valve for valve in mode["valves"] if valve["valve_id"] == valve_id
    )


def test_line_s_closure_contract_matches_current_ssot(monkeypatch):
    monkeypatch.setattr(
        closure_contract,
        "missing_required_artefacts",
        lambda root=closure_contract.ROOT: [],
    )
    summary = closure_contract.validate_current_contract()
    assert summary["status"] == "PASS"
    assert summary["open_mda_gates"] == 0
    assert summary["runtime_verdict"] == "PROCEED_MDA"
    assert summary["appendix_8_4_status"] == "PARTIAL_EXTRACTED"
    assert summary["appendix_8_4_source_available"] is True
    assert summary["appendix_8_4_source_available_in_repo"] is False
    assert summary["appendix_8_4_source_location"] == (
        "USER_LIBRARY_LOCKED_SOURCE"
    )
    assert summary["appendix_8_4_receipt_status"] == (
        "SOURCE_BOUND_PARTIAL_EXTRACTION"
    )
    assert summary["authority_transfer"] is False
    assert summary["formal_credit_delta"] == 0


def test_appendix_8_4_rejects_inferred_rows_without_source():
    data = closure_contract.load_extraction()
    data["status"] = "SOURCE_PENDING"
    data["source"]["source_material_available"] = False
    data["source"]["source_material_location"] = None
    with pytest.raises(ValueError, match="no mode/valve rows may be inferred"):
        closure_contract.validate_extraction(data)


def test_appendix_8_4_extracted_rows_require_source_evidence():
    data = closure_contract.load_extraction()
    data["modes"][0]["source_ref"] = ""
    with pytest.raises(ValueError, match=r"mode\[0\]\.source_ref"):
        closure_contract.validate_extraction(data)


def test_appendix_8_4_allows_source_bound_unknown_states():
    data = closure_contract.load_extraction()
    result = closure_contract.validate_extraction(data)
    assert result["status"] == "PARTIAL_EXTRACTED"
    assert len(result["modes"]) == 23
    unknown = _mode_by_id(result, "A84-03")
    assert unknown["extraction_state"] == "MODE_IDENTIFIED"
    assert {
        valve["commanded_state"] for valve in unknown["valves"]
    } == {"UNKNOWN"}


def test_appendix_8_4_rejects_extracted_empty_modes_when_source_available():
    data = closure_contract.load_extraction()
    data["status"] = "EXTRACTED"
    data["modes"] = []
    with pytest.raises(ValueError, match="at least one mode row"):
        closure_contract.validate_extraction(data)


def test_appendix_8_4_inventory_is_exact_and_partial():
    data = closure_contract.validate_extraction(
        closure_contract.load_extraction()
    )
    assert data["status"] == "PARTIAL_EXTRACTED"
    assert data["coverage"]["mode_inventory_expected"] == 23
    assert data["coverage"]["mode_rows_present"] == 23
    assert data["coverage"]["state_complete_modes"] == 0
    assert data["coverage"]["state_partial_modes"] == 8
    assert data["coverage"]["mode_identified_only"] == 15
    assert data["coverage"]["extraction_complete"] is False
    assert {mode["status"] for mode in data["modes"]} == {"SOURCE_BOUND"}
    assert all(len(mode["figure_sha256"]) == 64 for mode in data["modes"])
    ids = [mode["mode_id"] for mode in data["modes"]]
    assert len(ids) == len(set(ids)) == 23


def test_appendix_8_4_rejects_invalid_figure_digest():
    data = closure_contract.load_extraction()
    data["modes"][0]["figure_sha256"] = "not-a-sha"
    with pytest.raises(ValueError, match="figure_sha256"):
        closure_contract.validate_extraction(data)


def test_appendix_8_4_abnormal_fallback_states_are_source_bound():
    data = closure_contract.validate_extraction(
        closure_contract.load_extraction()
    )

    minor = _mode_by_id(data, "A84-05")
    minor_supply = _valve_by_id(minor, "QVB_SUPPLY_INTERFACE")
    minor_return = _valve_by_id(minor, "QVB_RETURN_INTERFACE")
    assert (minor_supply["commanded_state"], minor_supply["fail_state"]) == (
        "CLOSED",
        "FAIL_CLOSED",
    )
    assert (minor_return["commanded_state"], minor_return["fail_state"]) == (
        "OPEN",
        "FAIL_OPEN",
    )

    utility = _mode_by_id(data, "A84-07")
    utility_qrb = _valve_by_id(utility, "QRB_CRYOLINE_INTERFACE")
    utility_return = _valve_by_id(utility, "QVB_RETURN_INTERFACE")
    assert (utility_qrb["commanded_state"], utility_qrb["fail_state"]) == (
        "CLOSED",
        "FAIL_CLOSED",
    )
    assert (utility_return["commanded_state"], utility_return["fail_state"]) == (
        "OPEN",
        "FAIL_OPEN",
    )


def test_appendix_8_4_partial_inventory_cannot_claim_full_extraction():
    data = closure_contract.load_extraction()
    data["status"] = "EXTRACTED"
    data["coverage"]["extraction_complete"] = True
    with pytest.raises(
        ValueError,
        match="EXTRACTED requires every source mode to be STATE_COMPLETE",
    ):
        closure_contract.validate_extraction(data)


def test_line_s_closure_contract_rechecks_live_artefacts(monkeypatch):
    monkeypatch.setattr(
        closure_contract,
        "missing_required_artefacts",
        lambda root=closure_contract.ROOT: [
            "docs/qps_line_s_recovery/generated/recovery_matrix.csv"
        ],
    )
    with pytest.raises(ValueError, match="required Line-S artefacts missing"):
        closure_contract.validate_current_contract()


def test_appendix_8_4_state_complete_rejects_placeholders():
    data = closure_contract.load_extraction()
    for mode in data["modes"]:
        mode["extraction_state"] = "STATE_COMPLETE"
        for valve in mode["valves"]:
            if valve["commanded_state"] == "UNKNOWN":
                valve["commanded_state"] = "CLOSED"
            if valve["fail_state"] == "UNKNOWN":
                valve["fail_state"] = "NOT_APPLICABLE"
    data["status"] = "EXTRACTED"
    data["coverage"]["state_complete_modes"] = 23
    data["coverage"]["state_partial_modes"] = 0
    data["coverage"]["mode_identified_only"] = 0
    data["coverage"]["extraction_complete"] = True
    with pytest.raises(ValueError, match="resolved recovery_path"):
        closure_contract.validate_extraction(data)


def _promote_appendix_fixture_to_complete(data, *, resolve_blockers):
    for mode in data["modes"]:
        mode["extraction_state"] = "STATE_COMPLETE"
        mode["recovery_path"] = "SOURCE_BOUND_RECOVERY_PATH"
        mode["v_eff_consequence"] = "SOURCE_BOUND_VEFF_CONSEQUENCE"
        for valve in mode["valves"]:
            if valve["commanded_state"] == "UNKNOWN":
                valve["commanded_state"] = "CLOSED"
            if valve["fail_state"] == "UNKNOWN":
                valve["fail_state"] = "NOT_APPLICABLE"
    data["status"] = "EXTRACTED"
    data["coverage"]["state_complete_modes"] = 23
    data["coverage"]["state_partial_modes"] = 0
    data["coverage"]["mode_identified_only"] = 0
    data["coverage"]["extraction_complete"] = True
    if resolve_blockers:
        for row in data.get("unresolved", []):
            if row.get("id") in closure_contract.EXTRACTION_BLOCKER_IDS:
                row["state"] = "RESOLVED"
    return data


def test_appendix_8_4_extracted_rejects_open_completion_blockers():
    data = _promote_appendix_fixture_to_complete(
        closure_contract.load_extraction(),
        resolve_blockers=False,
    )
    with pytest.raises(
        ValueError,
        match="APPENDIX_8_4_FULL_STATE_TRANSCRIPTION resolved",
    ):
        closure_contract.validate_extraction(data)


def test_appendix_8_4_fully_resolved_complete_fixture_passes():
    data = _promote_appendix_fixture_to_complete(
        closure_contract.load_extraction(),
        resolve_blockers=True,
    )
    assert closure_contract.validate_extraction(data)["status"] == "EXTRACTED"


def test_appendix_8_4_source_receipt_matches_extraction():
    extraction = closure_contract.validate_extraction(
        closure_contract.load_extraction()
    )
    receipt = closure_contract.load_source_receipt()
    validated = closure_contract.validate_source_receipt(
        extraction,
        receipt,
    )
    assert validated["status"] == "SOURCE_BOUND_PARTIAL_EXTRACTION"


def test_appendix_8_4_receipt_rejects_yaml_digest_drift():
    extraction = closure_contract.validate_extraction(
        closure_contract.load_extraction()
    )
    extraction["modes"][0]["figure_sha256"] = "0" * 64
    receipt = closure_contract.load_source_receipt()
    with pytest.raises(ValueError, match="digest mismatch"):
        closure_contract.validate_source_receipt(extraction, receipt)


def test_appendix_8_4_receipt_rejects_receipt_digest_drift():
    extraction = closure_contract.validate_extraction(
        closure_contract.load_extraction()
    )
    receipt = closure_contract.load_source_receipt()
    receipt["source"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="receipt SHA-256 mismatch"):
        closure_contract.validate_source_receipt(extraction, receipt)


def test_appendix_8_4_receipt_rejects_authority_transfer():
    extraction = closure_contract.validate_extraction(
        closure_contract.load_extraction()
    )
    receipt = closure_contract.load_source_receipt()
    receipt["authority_transfer"] = True
    with pytest.raises(ValueError, match="authority_transfer"):
        closure_contract.validate_source_receipt(extraction, receipt)


def test_appendix_8_4_receipt_rejects_formal_credit_delta():
    extraction = closure_contract.validate_extraction(
        closure_contract.load_extraction()
    )
    receipt = closure_contract.load_source_receipt()
    receipt["formal_credit_delta"] = 1
    with pytest.raises(ValueError, match="formal_credit_delta"):
        closure_contract.validate_source_receipt(extraction, receipt)


def test_appendix_8_4_extracted_rejects_missing_completion_blocker_record():
    data = _promote_appendix_fixture_to_complete(
        closure_contract.load_extraction(),
        resolve_blockers=True,
    )
    data["unresolved"] = [
        row
        for row in data["unresolved"]
        if row.get("id") != "MODE_DEPENDENT_VEFF"
    ]
    with pytest.raises(
        ValueError,
        match="blocker record MODE_DEPENDENT_VEFF",
    ):
        closure_contract.validate_extraction(data)


def test_appendix_8_4_rejects_wrong_unresolved_container_type():
    data = closure_contract.load_extraction()
    data["unresolved"] = {}
    with pytest.raises(ValueError, match="unresolved must be a list"):
        closure_contract.validate_extraction(data)


def test_appendix_8_4_source_pending_rejects_wrong_unresolved_type():
    data = closure_contract.load_extraction()
    data["status"] = "SOURCE_PENDING"
    data["source"]["source_material_available"] = False
    data["source"]["source_material_location"] = None
    data["modes"] = []
    data["unresolved"] = {}
    with pytest.raises(ValueError, match="unresolved must be a list"):
        closure_contract.validate_extraction(data)


def test_appendix_8_4_receipt_rejects_boolean_formal_credit_delta():
    extraction = closure_contract.validate_extraction(
        closure_contract.load_extraction()
    )
    receipt = closure_contract.load_source_receipt()
    receipt["formal_credit_delta"] = False
    with pytest.raises(ValueError, match="integer zero"):
        closure_contract.validate_source_receipt(extraction, receipt)


def test_appendix_8_4_extraction_rejects_boolean_formal_credit_delta():
    data = closure_contract.load_extraction()
    data["formal_credit_delta"] = False
    with pytest.raises(ValueError, match="integer zero"):
        closure_contract.validate_extraction(data)


def test_appendix_8_4_receipt_rejects_boolean_extraction_credit_delta():
    extraction = closure_contract.load_extraction()
    extraction["formal_credit_delta"] = False
    receipt = closure_contract.load_source_receipt()
    with pytest.raises(
        ValueError,
        match="extraction formal_credit_delta must remain integer zero",
    ):
        closure_contract.validate_source_receipt(extraction, receipt)
