import json
from pathlib import Path

from src.qplant_presentation_engine.dmaic import build_dmaic_snapshot


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_build_dmaic_snapshot_generates_artifact_with_truth_matrix(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    _write_json(reports / "runtime_status.json", {"runtime_status": "ok", "validation_status": "ready"})
    _write_json(
        reports / "runtime_registry_report.json",
        {
            "repositories": {
                "ABACUS": {"runtime_coverage": "95%"},
                "QPLANT": {"runtime_coverage": "94%"},
            }
        },
    )
    _write_json(
        reports / "dashboard_status.json",
        {"status": "dashboard_generated", "dashboard_generated": True, "runtime_registry_consumed": True},
    )
    _write_json(
        reports / "truth_matrix_snapshot.json",
        {"truth_score": 0.97, "principles": ["ci_execution_observed"], "evidence": {"ci_execution_observed": True}},
    )
    _write_json(reports / "pca_snapshot.json", {"forward_pca": 0.94, "backward_pca": 0.93})
    _write_json(reports / "geti_snapshot.json", {"geti": 0.95, "truth_score": 0.97})

    snapshot = build_dmaic_snapshot(reports_dir=reports)

    written = json.loads((reports / "dmaic_snapshot.json").read_text(encoding="utf-8"))
    assert written == snapshot
    assert snapshot["truth_matrix_integrated"] is True
    assert snapshot["phase_status"]["control"]["complete"] is True
    assert snapshot["source_metrics"]["truth_principles"] == ["ci_execution_observed"]
    assert snapshot["source_metrics"]["forward_pca"] == 0.94
    assert snapshot["source_metrics"]["geti"] == 0.95


def test_build_dmaic_snapshot_handles_missing_inputs(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    reports.mkdir(parents=True, exist_ok=True)

    snapshot = build_dmaic_snapshot(reports_dir=reports)

    assert snapshot["truth_matrix_integrated"] is False
    assert snapshot["phase_status"]["define"]["complete"] is False
    assert snapshot["phase_status"]["measure"]["complete"] is False
