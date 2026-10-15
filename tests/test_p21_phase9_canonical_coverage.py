"""Canonical Phase 9 behavioral and receipt coverage with isolated workspaces."""

import json

import pytest

from DMAIC_V3.phases.phase9_documentation_generation import (
    Phase9_DocumentationGeneration,
)


@pytest.fixture
def phase9(tmp_path):
    phase = Phase9_DocumentationGeneration()
    phase.output_dir = tmp_path / "output"
    phase.canonical_dir = tmp_path / "canonical"
    iteration = phase.output_dir / "iteration_4"
    values = {
        "phase1_define": {
            "total_files": 120000,
            "python_files": ["first.py"],
            "markdown_files": ["guide.md"],
        },
        "phase2_measure": {
            "python_files_analyzed": 12,
            "analysis_success_rate": 0.75,
            "average_complexity": 2.5,
            "documentation_coverage": 0.5,
        },
    }
    for name, value in values.items():
        target = iteration / name
        target.mkdir(parents=True)
        (target / f"{name}.json").write_text(
            json.dumps(value), encoding="utf-8"
        )
    return phase


def _control_receipt(phase, payload):
    path = (
        phase.output_dir / "iteration_4" / "phase5_control"
        / "phase5_control.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_open_bugs_stop_book_creation_and_save_rejection(phase9):
    _control_receipt(phase9, {
        "bugs": [
            {"id": "BD-1", "status": "open"},
            {"id": "BD-2", "status": "closed"},
        ],
        "quality_gates": {"unit": {"passed": True}},
    })
    ok, receipt = phase9.execute(4)
    assert not ok
    assert receipt["reason"] == "bugs_detected"
    assert [v["id"] for v in receipt["details"]] == ["BD-1"]
    saved = (
        phase9.output_dir / "iteration_4"
        / "phase9_documentation_generation"
        / "phase9_documentation_generation.json"
    )
    assert json.loads(saved.read_text(encoding="utf-8"))["status"] == (
        "skipped"
    )
    assert not phase9.canonical_dir.exists()


def test_failing_quality_gate_stops_publication(phase9):
    _control_receipt(phase9, {
        "bugs": [{"status": "closed"}],
        "quality_gates": {
            "runtime": {"passed": True},
            "security": {"passed": False},
        },
    })
    ok, receipt = phase9.execute(4)
    assert not ok
    assert receipt["reason"] == "quality_gates_failed"
    assert receipt["status"] == "skipped"
    assert not phase9.canonical_dir.exists()


def test_corrupt_quality_receipt_cannot_be_reported_as_success(phase9):
    path = _control_receipt(phase9, {})
    path.write_text("{broken", encoding="utf-8")
    ok, receipt = phase9.execute(4)
    assert not ok
    assert "error" in receipt
    assert not phase9.canonical_dir.exists()


def test_generated_books_include_real_metrics_actions_and_receipts(phase9):
    _control_receipt(phase9, {
        "bugs": [{"id": "BD-closed", "status": "closed"}],
        "quality_gates": {"runtime": {"passed": True}},
    })
    iteration = phase9.output_dir / "iteration_4"
    phase4 = iteration / "phase4_improve"
    phase4.mkdir()
    (phase4 / "phase4_improve.json").write_text(
        json.dumps({
            "modifications": [
                {"file": "alpha.py", "type": "docstring"},
                {"file": "alpha.py", "type": "format"},
                {"file": "beta.py", "type": "docstring"},
            ]
        }), encoding="utf-8"
    )
    phase7 = iteration / "phase7_action_tracking"
    phase7.mkdir()
    (phase7 / "phase7_action_tracking.json").write_text(
        json.dumps({"local_actions": [
            {"status": "completed"}, {"status": "pending"},
            {"status": "completed"}, {},
        ]}), encoding="utf-8"
    )
    (phase7 / "feedback_for_next_iteration.json").write_text(
        json.dumps({
            "pending_actions": [{}],
            "completed_actions": [{}, {}],
            "failed_actions": [],
            "recommendations": [{}],
        }), encoding="utf-8"
    )

    ok, receipt = phase9.execute(4)
    assert ok
    assert receipt["status"] == "success"
    assert receipt["books_generated"] == 4
    assert len(receipt["book_paths"]) == 4
    assert all(
        phase9.canonical_dir in __import__("pathlib").Path(book).parents
        for book in receipt["book_paths"]
    )

    metrics_path = (
        phase9.canonical_dir / "Execution_Logs"
        / "EXECUTION_METRICS_BOOK_iteration_4.md"
    )
    metrics = metrics_path.read_text(encoding="utf-8")
    assert "Files Modified:** 2" in metrics
    assert "docstring: 2" in metrics
    assert "format: 1" in metrics
    assert "Success Rate:** 75.0%" in metrics
    assert "Documentation Coverage:** 50.0%" in metrics

    action_path = (
        phase9.canonical_dir / "Planning"
        / "ACTION_TRACKING_BOOK_iteration_4.md"
    )
    action_text = action_path.read_text(encoding="utf-8")
    assert "Total Actions:** 4" in action_text
    assert "completed: 2" in action_text
    assert "pending: 1" in action_text
    assert "unknown: 1" in action_text
    assert "Recommendations:** 1" in action_text

    adjustment_path = (
        phase9.output_dir / "iteration_4"
        / "phase9_documentation_generation" / "canonical_adjustments.json"
    )
    adjustments = json.loads(adjustment_path.read_text(encoding="utf-8"))
    assert adjustments["iteration"] == 4
    assert {v["field"] for v in adjustments["adjustments"]} == {
        "python_files"
    }
    saved = json.loads((
        adjustment_path.parent / "phase9_documentation_generation.json"
    ).read_text(encoding="utf-8"))
    assert saved["status"] == "success"
    assert saved["adjustments_made"] == 1


def test_no_discrepancy_does_not_write_adjustment_receipt(
    phase9, monkeypatch
):
    monkeypatch.setattr(phase9, "_detect_discrepancies", lambda _: [])
    ok, receipt = phase9.execute(4)
    assert ok
    assert receipt["adjustments_made"] == 0
    assert receipt["discrepancies_found"] == 0
    adjustment = (
        phase9.output_dir / "iteration_4"
        / "phase9_documentation_generation" / "canonical_adjustments.json"
    )
    assert not adjustment.exists()


def test_discrepancy_detection_preserves_signed_percent_and_severity(phase9):
    findings = phase9._detect_discrepancies(4)
    assert len(findings) == 1
    finding = findings[0]
    assert finding["field"] == "python_files"
    assert finding["canonical"] == 12000
    assert finding["actual"] == 1
    assert finding["difference"] == -11999
    assert finding["percentage"] < -90
    assert finding["severity"] == "high"
    assert phase9._detect_discrepancies(99) == []


@pytest.mark.parametrize("number,data,fragment", [
    (0, {}, "**Status:**"),
    (1, {"total_files": 120000, "python_files": ["a.py"],
         "markdown_files": ["x.md"]}, "120,000"),
    (2, {"python_files_analyzed": 13,
         "analysis_success_rate": 0.5}, "50.0%"),
    (4, {"modifications": [{"file": "f.py"}]}, "1"),
    (5, {"quality_gates": {
        "first": {"passed": True},
        "second": {"passed": False},
    }}, "1/2 passed"),
    (6, {"books_loaded": 3, "maturity_score": 73}, "73/100"),
])
def test_phase_summary_contract(number, data, fragment):
    assert fragment in Phase9_DocumentationGeneration()._format_phase_summary(
        number, data
    )


def test_unknown_phase_name_is_explicit_fallback():
    phase = Phase9_DocumentationGeneration()
    assert phase._get_phase_name(4) == "phase4_improve"
    assert phase._get_phase_name(9) == "phase9"


def test_failure_in_phase_book_data_does_not_emit_success_receipt(phase9):
    path = (
        phase9.output_dir / "iteration_4"
        / "phase1_define" / "phase1_define.json"
    )
    path.write_text("{bad-json", encoding="utf-8")
    ok, receipt = phase9.execute(4)
    assert not ok
    assert "error" in receipt
    assert not phase9.canonical_dir.exists()
