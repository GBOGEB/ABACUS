"""Canonical collector regression tests for observed DMAIC pipeline diagnostics.

All filesystem operations remain isolated to tmp_path; no real repair is
authorized and no external worker is launched.
"""

import json

import pytest

from DMAIC_V3.debug_pipeline import PipelineDebugger


@pytest.fixture
def debugger(tmp_path):
    return PipelineDebugger(workspace_root=tmp_path)


def test_empty_phase_receipt_preserves_all_failure_types(debugger):
    root = debugger.output_root / "iteration_2"
    (root / "phase1_define").mkdir(parents=True)
    (root / "phase2_measure").mkdir()
    (root / "phase3_analyze").mkdir()
    (root / "phase4_improve").mkdir()
    (root / "phase2_measure" / "empty.json").write_text("{}", encoding="utf-8")
    (root / "phase3_analyze" / "bad.json").write_text("not-json", encoding="utf-8")
    (root / "phase4_improve" / "ok.json").write_text(
        '{"status": "ok"}', encoding="utf-8"
    )

    result = debugger._check_empty_phases()
    assert result["status"] == "warning"
    assert {entry["reason"] for entry in result["empty_phases"]} == {
        "no_json_files",
        "empty_json",
        "invalid_json",
    }
    assert len(result["empty_phases"]) == 3


def test_empty_phases_clean_receipt_is_not_none(debugger):
    folder = debugger.output_root / "iteration_7" / "phase1_define"
    folder.mkdir(parents=True)
    (folder / "phase1_define.json").write_text(
        '{"status": "success"}', encoding="utf-8"
    )
    assert debugger._check_empty_phases() == {"status": "ok", "empty_phases": []}


def test_malformed_iteration_warns_without_fabricating_an_empty_phase(
    debugger,
):
    (debugger.output_root / "iteration_notanumber").mkdir(parents=True)
    receipt = debugger._check_empty_phases()
    assert receipt == {"status": "ok", "empty_phases": []}
    assert any(issue["category"] == "empty_phases" for issue in debugger.issues)


def test_output_structure_creates_root_and_scopes_iteration(debugger):
    first = debugger._check_output_structure()
    assert first["status"] == "ok"
    assert debugger.output_root.is_dir()
    assert debugger.fixes_applied == ["Created DMAIC_V3_OUTPUT directory"]

    valid = debugger.output_root / "iteration_3" / "phase1_define"
    valid.mkdir(parents=True)
    (valid / "receipt.json").write_text("{}", encoding="utf-8")
    (debugger.output_root / "iteration_bad").mkdir()
    second = debugger._check_output_structure()
    assert len(second["iterations"]) == 1
    assert second["iterations"][0]["number"] == 3
    assert second["iterations"][0]["phases"]["phase1"]["files"] == 1
    assert second["iterations"][0]["phases"]["phase2"]["exists"] is False


def test_failed_iterations_record_incomplete_and_complete(debugger):
    partial = debugger.output_root / "iteration_1"
    partial.mkdir(parents=True)
    (partial / "phase0_init").mkdir()
    full = debugger.output_root / "iteration_2"
    for phase in range(9):
        (full / f"phase{phase}_example").mkdir(parents=True)
    (debugger.output_root / "iteration_invalid").mkdir()
    result = debugger._check_failed_iterations()
    assert result["status"] == "warning"
    assert result["failures"] == [
        {
            "iteration": 1,
            "completed_phases": 1,
            "expected_phases": 9,
            "status": "incomplete",
        }
    ]
    assert debugger.issues[-1]["category"] == "failures"


def test_syntax_census_accepts_good_and_rejects_invalid_python(debugger):
    phases = debugger.dmaic_root / "phases"
    phases.mkdir(parents=True)
    (phases / "phase1_define.py").write_text(
        "def execute():\n    return True\n", encoding="utf-8"
    )
    (phases / "phase2_measure.py").write_text("def execute(:\n", encoding="utf-8")
    result = debugger._check_imports()
    assert result["status"] == "error"
    assert len(result["errors"]) == 1
    assert "phase2_measure.py" in result["errors"][0]
    assert debugger.issues[-1]["severity"] == "critical"


def test_missing_phase_files_are_critical(debugger):
    (debugger.dmaic_root / "phases").mkdir(parents=True)
    result = debugger._check_phase_files()
    assert result["status"] == "ok"
    assert len(result["phases"]) == 9
    assert len(debugger.issues) == 9
    assert all(x["severity"] == "critical" for x in debugger.issues)


def test_existing_phase_without_execute_is_warning(debugger):
    folder = debugger.dmaic_root / "phases"
    folder.mkdir(parents=True)
    (folder / "phase1_define.py").write_text(
        "def unrelated():\n    pass\n", encoding="utf-8"
    )
    result = debugger._check_phase_files()
    assert result["phases"]["phase1_define.py"]["exists"]
    assert result["phases"]["phase1_define.py"]["has_execute"] is False
    assert any(x["severity"] == "warning" for x in debugger.issues)


def test_canonical_file_receipts_flag_missing_then_present(debugger):
    initial = debugger._check_canonical_files()
    assert len(initial["files"]) == 4
    assert len(debugger.issues) == 4
    for name in ("index.json", "ranking.json", "ranking.yaml", "manifest.json"):
        (debugger.workspace_root / name).write_text("{}", encoding="utf-8")
    again = debugger._check_canonical_files()
    assert all(x["exists"] for x in again["files"].values())
    assert all(x["size"] > 0 for x in again["files"].values())


def test_common_missing_import_is_root_cause_not_inferred_fix(debugger):
    source = debugger.dmaic_root / "phases" / "phase1_define.py"
    source.parent.mkdir(parents=True)
    source.write_text("ensure_directory(output)\n", encoding="utf-8")
    bad = debugger._check_common_errors()
    assert bad["status"] == "error"
    assert len(bad["errors"]) == 1
    source.write_text(
        "from ..core.utils import ensure_directory\n" "ensure_directory(output)\n",
        encoding="utf-8",
    )
    good = debugger._check_common_errors()
    assert good == {"status": "ok", "errors": []}


def test_log_analyzer_reveals_errors_and_failed_receipts(debugger):
    latest = debugger.output_root / "iteration_12"
    latest.mkdir(parents=True)
    (latest / "error.json").write_text('{"error": "red root"}', encoding="utf-8")
    (latest / "failed.json").write_text('{"success": false}', encoding="utf-8")
    (latest / "invalid.json").write_text("{broken", encoding="utf-8")
    result = debugger._analyze_logs()
    assert result["status"] == "warning"
    assert len(result["recent_errors"]) == 2
    assert {entry["error"] for entry in result["recent_errors"]} == {
        "red root",
        "Unknown failure",
    }


@pytest.mark.parametrize(
    "severity,expected",
    [
        (None, "healthy"),
        ("warning", "warning"),
        ("critical", "critical"),
    ],
)
def test_aggregated_diagnostics_keep_severity_and_typed_census(
    debugger, monkeypatch, severity, expected
):
    methods = [
        "_check_python_env",
        "_check_dmaic_structure",
        "_check_imports",
        "_check_phase_files",
        "_check_output_structure",
        "_check_empty_phases",
        "_check_failed_iterations",
        "_check_canonical_files",
        "_check_common_errors",
        "_analyze_logs",
    ]
    for method in methods:
        monkeypatch.setattr(debugger, method, lambda: {"status": "ok"})
    if severity is not None:
        debugger.issues.append(
            {"severity": severity, "category": "test", "message": "measured diagnostic"}
        )
    result = debugger.run_full_diagnostic()
    assert result["status"] == expected
    assert len(result["checks"]) == 10
    assert all(isinstance(v, dict) for v in result["checks"].values())
    assert result["issues"] == debugger.issues
    assert result["fixes"] == []


@pytest.mark.parametrize("state", ["healthy", "warning", "critical"])
def test_summary_outputs_exact_observed_severity(debugger, capsys, state):
    issues = (
        [] if state == "healthy" else [{"severity": state, "message": "observed issue"}]
    )
    debugger._print_diagnostic_summary(
        {
            "status": state,
            "issues": issues,
            "fixes": [],
        }
    )
    stdout = capsys.readouterr().out
    assert f" {state.upper()}" in stdout
    assert "Issues Found: " in stdout


def test_auto_fix_creates_only_missing_templates_and_is_idempotent(debugger):
    first = debugger.auto_fix()
    assert len(first) == 4
    assert debugger.output_root.is_dir()
    for name in ("index.json", "ranking.json", "manifest.json"):
        assert json.loads((debugger.workspace_root / name).read_text(encoding="utf-8"))
    assert debugger.auto_fix() == []


def test_python_environment_has_valid_evidence(debugger):
    result = debugger._check_python_env()
    assert result["status"] == "ok"
    assert result["details"]["version"]
    assert result["details"]["executable"]
    assert "missing_modules" not in result["details"]
