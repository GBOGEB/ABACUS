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
    assert summary["appendix_8_4_status"] == "SOURCE_PENDING"
    assert summary["appendix_8_4_source_available"] is False
    assert summary["authority_transfer"] is False
    assert summary["formal_credit_delta"] == 0


def test_appendix_8_4_rejects_inferred_rows_without_source():
    data = closure_contract.load_extraction()
    data["modes"] = [
        {
            "status": "EXTRACTED",
            "mode_id": "INFERRED",
            "mode_name": "must not pass",
            "source_ref": "inference",
            "evidence_locator": "none",
            "recovery_path": "UNKNOWN",
            "v_eff_consequence": "UNKNOWN",
            "valves": [
                {
                    "valve_id": "V-INFERRED",
                    "commanded_state": "UNKNOWN",
                    "fail_state": "UNKNOWN",
                    "source_ref": "inference",
                    "evidence_locator": "none",
                }
            ],
        }
    ]
    with pytest.raises(ValueError, match="no mode/valve rows may be inferred"):
        closure_contract.validate_extraction(data)


def test_appendix_8_4_extracted_rows_require_source_evidence():
    data = closure_contract.load_extraction()
    data["status"] = "EXTRACTED"
    data["source"]["source_material_available_in_repo"] = True
    data["source"]["source_ref"] = "D2.1"
    data["source"]["evidence_locator"] = "Appendix 8.4"
    data["modes"] = [
        {
            "status": "EXTRACTED",
            "mode_id": "MODE-1",
            "mode_name": "source-backed fixture",
            "source_ref": "",
            "evidence_locator": "Appendix 8.4 / fixture",
            "recovery_path": "UNKNOWN",
            "v_eff_consequence": "UNKNOWN",
            "valves": [
                {
                    "valve_id": "V-1",
                    "commanded_state": "UNKNOWN",
                    "fail_state": "UNKNOWN",
                    "source_ref": "D2.1",
                    "evidence_locator": "Appendix 8.4 / fixture",
                }
            ],
        }
    ]
    with pytest.raises(ValueError, match="mode\[0\]\.source_ref"):
        closure_contract.validate_extraction(data)


def test_appendix_8_4_allows_source_bound_unknown_states():
    data = closure_contract.load_extraction()
    data["status"] = "EXTRACTED"
    data["source"]["source_material_available_in_repo"] = True
    data["source"]["source_ref"] = "D2.1"
    data["source"]["evidence_locator"] = "Appendix 8.4"
    data["modes"] = [
        {
            "status": "EXTRACTED",
            "mode_id": "MODE-1",
            "mode_name": "source-backed fixture",
            "source_ref": "D2.1",
            "evidence_locator": "Appendix 8.4 / fixture",
            "recovery_path": "UNKNOWN",
            "v_eff_consequence": "UNKNOWN",
            "valves": [
                {
                    "valve_id": "V-1",
                    "commanded_state": "UNKNOWN",
                    "fail_state": "UNKNOWN",
                    "source_ref": "D2.1",
                    "evidence_locator": "Appendix 8.4 / fixture",
                }
            ],
        }
    ]
    assert closure_contract.validate_extraction(data)["status"] == "EXTRACTED"


def test_appendix_8_4_rejects_extracted_empty_modes_when_source_available():
    data = closure_contract.load_extraction()
    data["status"] = "EXTRACTED"
    data["source"]["source_material_available_in_repo"] = True
    data["source"]["source_ref"] = "D2.1"
    data["source"]["evidence_locator"] = "Appendix 8.4"
    data["modes"] = []
    with pytest.raises(ValueError, match="at least one mode row"):
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
