from __future__ import annotations

import json

from DMAIC_V3.debug_pipeline import PipelineDebugger


def test_failed_iterations_reports_incomplete_iteration(tmp_path):
    output = tmp_path / "DMAIC_V3_OUTPUT" / "iteration_3"
    output.mkdir(parents=True)
    for index in range(4):
        (output / f"phase{index}_sample").mkdir()

    debugger = PipelineDebugger(tmp_path)
    result = debugger._check_failed_iterations()

    assert result["status"] == "warning"
    assert result["failures"] == [{
        "iteration": 3,
        "completed_phases": 4,
        "expected_phases": 9,
        "status": "incomplete",
    }]
    assert any(issue["category"] == "failures" for issue in debugger.issues)


def test_canonical_file_check_reports_present_and_missing_files(tmp_path):
    (tmp_path / "index.json").write_text("{}", encoding="utf-8")
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")

    debugger = PipelineDebugger(tmp_path)
    result = debugger._check_canonical_files()

    assert result["files"]["index.json"]["exists"] is True
    assert result["files"]["manifest.json"]["exists"] is True
    assert result["files"]["ranking.json"]["exists"] is False
    assert result["files"]["ranking.yaml"]["exists"] is False
    assert sum(1 for issue in debugger.issues if issue["category"] == "canonical") == 2


def test_analyze_logs_finds_error_and_failed_success_payloads(tmp_path):
    latest = tmp_path / "DMAIC_V3_OUTPUT" / "iteration_2" / "phase1_define"
    latest.mkdir(parents=True)
    (latest / "error.json").write_text(
        json.dumps({"error": "boom"}),
        encoding="utf-8",
    )
    (latest / "failed.json").write_text(
        json.dumps({"success": False, "message": "not good"}),
        encoding="utf-8",
    )
    (latest / "ok.json").write_text(
        json.dumps({"success": True}),
        encoding="utf-8",
    )

    debugger = PipelineDebugger(tmp_path)
    result = debugger._analyze_logs()

    assert result["status"] == "warning"
    assert {item["error"] for item in result["recent_errors"]} == {"boom", "not good"}

# Wave 4 exact-main broad coverage recensus trigger.
