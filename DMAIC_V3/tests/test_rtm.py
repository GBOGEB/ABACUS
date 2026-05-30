import json
from pathlib import Path

import yaml

from src.qplant_presentation_engine.rtm import generate_rtm_artifacts


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
    _write_json(reports / "dmaic_snapshot.json", {"artifact": "dmaic_snapshot", "truth_matrix_integrated": True})
    _write_json(reports / "governance_snapshot.json", {"artifact": "governance_snapshot", "governance_passed": True})
    _write_json(reports / "completion_vector.json", {"artifact": "completion_vector", "completed_phases": 5})


def test_generate_rtm_artifacts_creates_required_outputs(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    rtm = tmp_path / "rtm"
    _seed_reports(reports)

    generated = generate_rtm_artifacts(reports_dir=reports, rtm_dir=rtm)

    requirements = yaml.safe_load((rtm / "requirements.yaml").read_text(encoding="utf-8"))
    evidence_map = yaml.safe_load((rtm / "evidence_map.yaml").read_text(encoding="utf-8"))
    trace_matrix = json.loads((rtm / "trace_matrix.json").read_text(encoding="utf-8"))

    assert generated["requirements"] == requirements
    assert generated["evidence_map"] == evidence_map
    assert generated["trace_matrix"] == trace_matrix

    assert any(req["id"] == "REQ-RTM-001" for req in requirements["requirements"])
    assert "REQ-RTM-001" in evidence_map["requirements"]
    assert trace_matrix["rows"]

    runtime_artifacts = {
        entry["evidence_artifact"]
        for entry in trace_matrix["rows"]
        if entry["evidence_domain"] == "runtime"
    }
    governance_artifacts = {
        entry["evidence_artifact"]
        for entry in trace_matrix["rows"]
        if entry["evidence_domain"] == "governance"
    }
    assert str(reports / "runtime_status.json") in runtime_artifacts
    assert str(reports / "runtime_registry_report.json") in runtime_artifacts
    assert str(reports / "governance_snapshot.json") in governance_artifacts
    assert str(reports / "completion_vector.json") in governance_artifacts

    row_pairs = {(row["requirement_id"], row["evidence_id"]) for row in trace_matrix["rows"]}
    assert len(row_pairs) == len(trace_matrix["rows"])


def test_generate_rtm_artifacts_uses_runtime_publish_status_fallback(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    rtm = tmp_path / "rtm"
    _seed_reports(reports)
    (reports / "runtime_status.json").unlink()
    _write_json(reports / "runtime_publish_status.json", {"status": "published", "runtime_evidence": True})

    generate_rtm_artifacts(reports_dir=reports, rtm_dir=rtm)

    evidence_map = yaml.safe_load((rtm / "evidence_map.yaml").read_text(encoding="utf-8"))
    runtime_status_evidence = evidence_map["requirements"]["REQ-RTM-001"]["evidence"][0]
    assert runtime_status_evidence["evidence_id"] == "runtime_status"
    assert runtime_status_evidence["artifact"] == str(reports / "runtime_publish_status.json")
    assert runtime_status_evidence["available"] is True
