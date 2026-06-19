import csv
import math
from pathlib import Path

import pytest

from models.qps_line_s import runtime
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
            {"id": "DONE", "gate": True, "status": "RESOLVED"},
        ]
    }
    gates = runtime.open_gates(data)
    assert [gate["id"] for gate in gates] == ["ASSUM-VEFF", "ASSUM-PLIMIT", "ASSUM-RECOV-PWR"]


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


def test_runtime_enforce_exits_when_gates_open(monkeypatch):
    monkeypatch.setattr(runtime, "run_generators", lambda: None)
    monkeypatch.setattr(runtime, "missing_artefacts", lambda: [])
    monkeypatch.setattr(runtime, "open_gates", lambda: [{"id": "ASSUM-RECOV-PWR"}])
    monkeypatch.setattr(runtime, "energy_provenance", lambda: "bound")
    monkeypatch.setattr(runtime.STATUS_OUT, "write_text", lambda text: None)
    with pytest.raises(SystemExit) as exc:
        runtime.runtime(regenerate=True, enforce=True)
    assert exc.value.code == 1
