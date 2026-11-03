"""Behaviour tests for src/qplant_presentation_engine/rtm.py.

Every run writes into ``tmp_path`` (explicit dirs, or ``Path.cwd()`` after a
``chdir`` for the default-directory branch).
"""

import json

import yaml

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("src/qplant_presentation_engine/rtm.py", name="abn_qplant_rtm")


def _repo(tmp_path, with_content=True):
    repo = tmp_path / "repo"
    sv = repo / "patterns" / "scientific_visualization"
    qp = repo / "content" / "qplant"
    sv.mkdir(parents=True)
    qp.mkdir(parents=True)
    if with_content:
        for path in (
            sv / "schema.json",
            sv / "validation_rules.yaml",
            qp / "process_flow.yaml",
            qp / "thermodynamics.yaml",
        ):
            path.write_bytes(b"{}")
    return repo


def test_unique_preserve_order():
    assert mod._unique_preserve_order(["b", "a", "b", "c", "a"]) == ["b", "a", "c"]
    assert mod._unique_preserve_order([]) == []


def test_runtime_status_path_prefers_primary(tmp_path):
    fallback = tmp_path / "runtime_publish_status.json"
    assert mod._resolve_runtime_status_path(tmp_path) == fallback
    (tmp_path / "runtime_status.json").write_bytes(b"{}")
    assert mod._resolve_runtime_status_path(tmp_path) == (
        tmp_path / "runtime_status.json"
    )


def test_requirements_catalogue_is_consistent(tmp_path):
    reqs = mod._requirements()
    assert [r["id"] for r in reqs] == ["REQ-00" + str(i) for i in range(1, 10)]
    catalog = mod._evidence_catalog(tmp_path, tmp_path)
    for req in reqs:
        assert set(req["evidence"]) <= set(catalog)
    assert all(entry["available"] is False for entry in catalog.values())
    assert catalog["dmaic_snapshot"]["domain"] == "dmaic"


def test_evidence_catalog_marks_present_files(tmp_path):
    reports = tmp_path / "reports"
    reports.mkdir()
    for name in ("runtime_status", "dashboard_status", "completion_vector"):
        (reports / (name + ".json")).write_bytes(b"{}")
    catalog = mod._evidence_catalog(reports, _repo(tmp_path))
    assert catalog["runtime_status"]["available"] is True
    assert catalog["runtime_status"]["artifact"].endswith("runtime_status.json")
    assert catalog["dashboard_status"]["available"] is True
    assert catalog["completion_vector"]["available"] is True
    assert catalog["governance_snapshot"]["available"] is False
    assert catalog["scientific_visualization_schema"]["available"] is True
    assert catalog["qplant_thermodynamics_content"]["available"] is True


def test_generate_summary_full_coverage():
    reqs = [dict(id="R1", evidence=["e"]), dict(id="R2", evidence=["f"])]
    rows = [
        dict(requirement_id="R1", evidence_id="e"),
        dict(requirement_id="R2", evidence_id="f"),
    ]
    summary = mod._generate_summary(reqs, rows)
    assert summary["coverage_ratio"] == 1.0
    assert summary["validation_passed"] is True
    assert summary["uncovered_requirements"] == []
    assert summary["generated_at"].endswith("+00:00")


def test_generate_summary_uncovered_and_duplicates():
    reqs = [dict(id="R1", evidence=["e"]), dict(id="R2", evidence=[])]
    rows = [dict(requirement_id="R1", evidence_id="e")] * 2
    summary = mod._generate_summary(reqs, rows)
    assert summary["requirements_with_evidence"] == 1
    assert summary["uncovered_requirements"] == ["R2"]
    assert summary["coverage_ratio"] == 0.5
    assert summary["validation_passed"] is False
    dup = mod._generate_summary([dict(id="R1", evidence=["e"])], rows)
    assert dup["coverage_ratio"] == 1.0
    assert dup["validation_passed"] is False


def test_generate_summary_empty():
    summary = mod._generate_summary([], [])
    assert summary["total_requirements"] == 0
    assert summary["coverage_ratio"] == 0.0
    assert summary["validation_passed"] is False


def test_generate_rtm_artifacts_explicit_dirs(tmp_path):
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "runtime_publish_status.json").write_bytes(b"{}")
    rtm_dir = tmp_path / "out" / "rtm"
    result = mod.generate_rtm_artifacts(reports, rtm_dir, _repo(tmp_path))
    rows = result["trace_matrix"]["rows"]
    assert len(rows) == 12
    assert len({(r["requirement_id"], r["evidence_id"]) for r in rows}) == 12
    runtime = [r for r in rows if r["evidence_id"] == "runtime_status"][0]
    assert runtime["available"] is True
    assert runtime["evidence_artifact"].endswith("runtime_publish_status.json")
    assert result["rtm_summary"]["validation_passed"] is True
    assert result["evidence_map"]["reports_dir"] == str(reports)
    req5 = result["evidence_map"]["requirements"]["REQ-005"]["evidence"]
    assert [e["evidence_id"] for e in req5] == [
        "qplant_process_flow_content",
        "qplant_thermodynamics_content",
    ]
    on_disk = json.loads((rtm_dir / "rtm_summary.json").read_text(encoding="utf-8"))
    assert on_disk["total_requirements"] == 9
    trace = json.loads((rtm_dir / "trace_matrix.json").read_text(encoding="utf-8"))
    assert trace["artifact"] == "trace_matrix"
    reqs = yaml.safe_load((rtm_dir / "requirements.yaml").read_text(encoding="utf-8"))
    assert [r["id"] for r in reqs["requirements"]][0] == "REQ-001"
    assert "evidence" not in reqs["requirements"][0]
    emap = yaml.safe_load((rtm_dir / "evidence_map.yaml").read_text(encoding="utf-8"))
    assert emap["artifact"] == "evidence_map"


def test_generate_rtm_artifacts_defaults_use_cwd_and_repo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = mod.generate_rtm_artifacts()
    assert result["evidence_map"]["reports_dir"] == str(tmp_path / "reports")
    assert (tmp_path / "rtm" / "trace_matrix.json").is_file()
    schema_row = [
        r
        for r in result["trace_matrix"]["rows"]
        if r["evidence_id"] == "scientific_visualization_schema"
    ][0]
    assert schema_row["evidence_artifact"].startswith(str(mod._DEFAULT_REPO_DIR))


def test_duplicate_evidence_ids_are_collapsed(tmp_path, monkeypatch):
    reqs = [
        dict(
            id="R1",
            title="t",
            description="d",
            evidence=["dmaic_snapshot", "dmaic_snapshot", "dashboard_status"],
        ),
        dict(id="R1", title="t2", description="d2", evidence=["dmaic_snapshot"]),
    ]
    monkeypatch.setattr(mod, "_requirements", lambda: reqs)
    result = mod.generate_rtm_artifacts(
        tmp_path / "r", tmp_path / "o", _repo(tmp_path, with_content=False)
    )
    assert [r["evidence_id"] for r in result["trace_matrix"]["rows"]] == [
        "dmaic_snapshot",
        "dashboard_status",
    ]
    # The second R1 overwrites the evidence map entry; its row is deduplicated.
    entry = result["evidence_map"]["requirements"]["R1"]
    assert entry["title"] == "t2"
    assert len(entry["evidence"]) == 1
    assert result["rtm_summary"]["validation_passed"] is True
