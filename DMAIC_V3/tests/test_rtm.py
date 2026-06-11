import json
from pathlib import Path

import yaml

from src.qplant_presentation_engine.rtm import generate_rtm_artifacts


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


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


def _seed_repo(repo: Path) -> None:
    """Create minimal schema/content evidence files under a synthetic repo root."""
    schema_dir = repo / "patterns" / "scientific_visualization"
    _write_json(
        schema_dir / "schema.json",
        {"visualization_types": ["sankey", "boxplot", "violin", "timeline", "heatmap", "process_flow"]},
    )
    _write_text(schema_dir / "validation_rules.yaml", "allowed_visualization_types:\n  - sankey\n")
    content_dir = repo / "content" / "qplant"
    _write_text(content_dir / "process_flow.yaml", "title: Process Flow\nstages: []\n")
    _write_text(content_dir / "thermodynamics.yaml", "title: Thermodynamics\nequations: []\n")


def test_generate_rtm_artifacts_creates_required_outputs(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    rtm = tmp_path / "rtm"
    repo = tmp_path / "repo"
    _seed_reports(reports)
    _seed_repo(repo)

    generated = generate_rtm_artifacts(reports_dir=reports, rtm_dir=rtm, repo_dir=repo)

    requirements = yaml.safe_load((rtm / "requirements.yaml").read_text(encoding="utf-8"))
    evidence_map = yaml.safe_load((rtm / "evidence_map.yaml").read_text(encoding="utf-8"))
    trace_matrix = json.loads((rtm / "trace_matrix.json").read_text(encoding="utf-8"))
    rtm_summary = json.loads((rtm / "rtm_summary.json").read_text(encoding="utf-8"))

    assert generated["requirements"] == requirements
    assert generated["evidence_map"] == evidence_map
    assert generated["trace_matrix"] == trace_matrix
    assert generated["rtm_summary"] == rtm_summary

    req_ids = {req["id"] for req in requirements["requirements"]}
    assert "REQ-001" in req_ids
    assert "REQ-001" in evidence_map["requirements"]
    assert trace_matrix["rows"]

    runtime_artifacts = {
        entry["evidence_artifact"]
        for entry in trace_matrix["rows"]
        if entry["evidence_domain"] == "runtime"
    }
    assert str(reports / "runtime_status.json") in runtime_artifacts
    assert str(reports / "runtime_registry_report.json") in runtime_artifacts

    schema_artifacts = {
        entry["evidence_artifact"]
        for entry in trace_matrix["rows"]
        if entry["evidence_domain"] == "schema"
    }
    assert str(repo / "patterns" / "scientific_visualization" / "schema.json") in schema_artifacts

    row_pairs = {(row["requirement_id"], row["evidence_id"]) for row in trace_matrix["rows"]}
    assert len(row_pairs) == len(trace_matrix["rows"])


def test_generate_rtm_summary_coverage_ratio(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    rtm = tmp_path / "rtm"
    repo = tmp_path / "repo"
    _seed_reports(reports)
    _seed_repo(repo)

    generated = generate_rtm_artifacts(reports_dir=reports, rtm_dir=rtm, repo_dir=repo)
    summary = generated["rtm_summary"]

    assert summary["total_requirements"] == 9
    assert summary["requirements_with_evidence"] == 9
    assert summary["uncovered_requirements"] == []
    assert summary["coverage_ratio"] == 1.0
    assert summary["validation_passed"] is True


def test_generate_rtm_summary_file_written(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    rtm = tmp_path / "rtm"
    repo = tmp_path / "repo"
    _seed_reports(reports)
    _seed_repo(repo)

    generate_rtm_artifacts(reports_dir=reports, rtm_dir=rtm, repo_dir=repo)

    summary_path = rtm / "rtm_summary.json"
    assert summary_path.exists()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert "coverage_ratio" in summary
    assert "validation_passed" in summary
    assert "generated_at" in summary


def test_generate_rtm_artifacts_uses_runtime_publish_status_fallback(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    rtm = tmp_path / "rtm"
    repo = tmp_path / "repo"
    _seed_reports(reports)
    _seed_repo(repo)
    (reports / "runtime_status.json").unlink()
    _write_json(reports / "runtime_publish_status.json", {"status": "published", "runtime_evidence": True})

    generate_rtm_artifacts(reports_dir=reports, rtm_dir=rtm, repo_dir=repo)

    evidence_map = yaml.safe_load((rtm / "evidence_map.yaml").read_text(encoding="utf-8"))
    runtime_status_evidence = evidence_map["requirements"]["REQ-001"]["evidence"][0]
    assert runtime_status_evidence["evidence_id"] == "runtime_status"
    assert runtime_status_evidence["artifact"] == str(reports / "runtime_publish_status.json")
    assert runtime_status_evidence["available"] is True
