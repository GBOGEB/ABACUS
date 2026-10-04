from __future__ import annotations

from DMAIC_V3.debug_pipeline import PipelineDebugger


def _make_required_structure(root):
    for relative in (
        "DMAIC_V3/phases", "DMAIC_V3/core",
        "DMAIC_V3/convergence", "DMAIC_V3_OUTPUT",
    ):
        (root / relative).mkdir(parents=True, exist_ok=True)


def test_python_and_structure_checks_report_healthy_workspace(tmp_path):
    _make_required_structure(tmp_path)
    debugger = PipelineDebugger(tmp_path)
    assert debugger._check_python_env()["status"] == "ok"
    assert debugger._check_dmaic_structure()["status"] == "ok"
    assert debugger.issues == []


def test_structure_check_records_missing_directories(tmp_path):
    debugger = PipelineDebugger(tmp_path)
    result = debugger._check_dmaic_structure()
    assert result["status"] == "error"
    assert "DMAIC_V3" in result["missing_dirs"]
    assert any(i["category"] == "structure" for i in debugger.issues)


def test_import_check_reports_only_invalid_phase(tmp_path):
    _make_required_structure(tmp_path)
    phases = tmp_path / "DMAIC_V3" / "phases"
    (phases / "phase1_ok.py").write_text(
        "def execute():\n    return True\n", encoding="utf-8"
    )
    (phases / "phase2_bad.py").write_text(
        "def execute(:\n    return False\n", encoding="utf-8"
    )
    debugger = PipelineDebugger(tmp_path)
    result = debugger._check_imports()
    assert result["status"] == "error"
    assert len(result["errors"]) == 1
    assert "phase2_bad.py" in result["errors"][0]


def test_output_check_creates_missing_output_directory(tmp_path):
    (tmp_path / "DMAIC_V3").mkdir()
    debugger = PipelineDebugger(tmp_path)
    assert not debugger.output_root.exists()
    result = debugger._check_output_structure()
    assert debugger.output_root.exists()
    assert result["status"] == "ok"
    assert "Created DMAIC_V3_OUTPUT directory" in debugger.fixes_applied
