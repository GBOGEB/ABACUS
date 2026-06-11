import json
from pathlib import Path

from src.qplant_presentation_engine.governance import generate_governance_artifacts


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _seed_reports(reports: Path) -> None:
    _write_json(reports / "runtime_status.json", {"runtime_status": "ok", "validation_status": "ready"})
    _write_json(
        reports / "runtime_registry_report.json",
        {"repositories": {"ABACUS": {"runtime_coverage": "95%"}}},
    )
    _write_json(
        reports / "dashboard_status.json",
        {"status": "dashboard_generated", "dashboard_generated": True, "runtime_registry_consumed": True},
    )
    _write_json(
        reports / "truth_matrix_snapshot.json",
        {"truth_score": 0.99, "principles": ["ci_execution_observed"], "evidence": {"ci_execution_observed": True}},
    )
    _write_json(reports / "pca_snapshot.json", {"forward_pca": 0.95, "backward_pca": 0.94})
    _write_json(reports / "geti_snapshot.json", {"geti": 0.97, "truth_score": 0.99})


def test_generate_governance_artifacts_writes_outputs(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    _seed_reports(reports)

    governance_snapshot, completion_vector = generate_governance_artifacts(reports_dir=reports)

    governance_written = json.loads((reports / "governance_snapshot.json").read_text(encoding="utf-8"))
    completion_written = json.loads((reports / "completion_vector.json").read_text(encoding="utf-8"))
    assert governance_snapshot == governance_written
    assert completion_vector == completion_written

    assert governance_snapshot["governance_passed"] is True
    assert governance_snapshot["truth_matrix"]["integrated"] is True
    assert governance_snapshot["truth_matrix"]["principles"] == ["ci_execution_observed"]

    assert completion_vector["completed_phases"] == completion_vector["total_phases"]
    assert completion_vector["vector"] == {
        "define": 1,
        "measure": 1,
        "analyze": 1,
        "improve": 1,
        "control": 1,
    }


def test_generate_governance_artifacts_marks_incomplete_when_evidence_missing(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    reports.mkdir(parents=True, exist_ok=True)

    governance_snapshot, completion_vector = generate_governance_artifacts(reports_dir=reports)

    assert governance_snapshot["governance_passed"] is False
    assert completion_vector["completed_phases"] == 0
    assert completion_vector["vector"]["define"] == 0
