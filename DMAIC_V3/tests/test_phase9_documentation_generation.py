"""
DMAIC V3 Test Suite - Phase 9: Documentation Generation Tests
"""

import pytest
import json
from pathlib import Path

from DMAIC_V3.phases.phase9_documentation_generation import Phase9_DocumentationGeneration


@pytest.fixture
def phase9():
    return Phase9_DocumentationGeneration()


@pytest.fixture
def phase9_in_tmp(monkeypatch, tmp_path):
    """Phase9 instance with working directory redirected to tmp_path."""
    monkeypatch.chdir(tmp_path)
    return Phase9_DocumentationGeneration()


@pytest.fixture
def minimal_phase_outputs(tmp_path):
    """Create minimal Phase 1 and Phase 2 output files required by Phase 9."""
    iteration_dir = tmp_path / "DMAIC_V3_OUTPUT" / "iteration_1"

    phase1_dir = iteration_dir / "phase1_define"
    phase1_dir.mkdir(parents=True)
    (phase1_dir / "phase1_define.json").write_text(json.dumps({
        "phase": "DEFINE",
        "iteration": 1,
        "total_files": 100,
        "python_files": ["a.py", "b.py"],
        "markdown_files": ["README.md"],
    }))

    phase2_dir = iteration_dir / "phase2_measure"
    phase2_dir.mkdir(parents=True)
    (phase2_dir / "phase2_measure.json").write_text(json.dumps({
        "phase": "MEASURE",
        "iteration": 1,
        "python_files_analyzed": 2,
        "analysis_success_rate": 1.0,
    }))

    return tmp_path


@pytest.mark.unit
class TestPhase9DocumentationGeneration:

    def test_initialization(self, phase9):
        assert phase9.output_dir == Path("DMAIC_V3_OUTPUT")
        assert phase9.canonical_dir == Path("CANONICAL_KNOWLEDGE")
        assert phase9.books_generated == []

    def test_execute_returns_two_tuple(self, phase9_in_tmp):
        result = phase9_in_tmp.execute(iteration=1)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_execute_returns_bool_and_dict(self, phase9_in_tmp):
        success, result = phase9_in_tmp.execute(iteration=1)
        assert isinstance(success, bool)
        assert isinstance(result, dict)

    def test_skips_when_no_prior_phases(self, phase9_in_tmp):
        # Without phase1/phase2 output files, Phase 9 should skip gracefully
        success, result = phase9_in_tmp.execute(iteration=1)
        assert success is False
        assert result.get('status') == 'skipped'
        assert result.get('reason') == 'execution_not_successful'

    def test_skip_result_has_phase_field(self, phase9_in_tmp):
        success, result = phase9_in_tmp.execute(iteration=1)
        assert result.get('phase') == 'phase9_documentation_generation'

    def test_skip_result_has_iteration(self, phase9_in_tmp):
        success, result = phase9_in_tmp.execute(iteration=7)
        assert result.get('iteration') == 7

    def test_skip_result_saved_to_disk(self, phase9_in_tmp, tmp_path):
        phase9_in_tmp.execute(iteration=1)
        output_file = (
            tmp_path / "DMAIC_V3_OUTPUT" / "iteration_1"
            / "phase9_documentation_generation" / "phase9_documentation_generation.json"
        )
        assert output_file.exists()

    def test_succeeds_when_prior_phases_present(self, monkeypatch, minimal_phase_outputs):
        monkeypatch.chdir(minimal_phase_outputs)
        phase9 = Phase9_DocumentationGeneration()
        success, result = phase9.execute(iteration=1)
        assert success is True
        assert result.get('status') == 'success'

    def test_generates_books_when_successful(self, monkeypatch, minimal_phase_outputs):
        monkeypatch.chdir(minimal_phase_outputs)
        phase9 = Phase9_DocumentationGeneration()
        success, result = phase9.execute(iteration=1)
        assert success is True
        assert result.get('books_generated', 0) >= 4  # dmaic, 12cluster, execution, action_tracking

    def test_success_result_has_discrepancies_field(self, monkeypatch, minimal_phase_outputs):
        monkeypatch.chdir(minimal_phase_outputs)
        phase9 = Phase9_DocumentationGeneration()
        success, result = phase9.execute(iteration=1)
        assert success is True
        assert 'discrepancies_found' in result
        assert isinstance(result['discrepancies_found'], int)

    def test_success_result_saved_to_disk(self, monkeypatch, minimal_phase_outputs):
        monkeypatch.chdir(minimal_phase_outputs)
        phase9 = Phase9_DocumentationGeneration()
        phase9.execute(iteration=1)
        output_file = (
            minimal_phase_outputs / "DMAIC_V3_OUTPUT" / "iteration_1"
            / "phase9_documentation_generation" / "phase9_documentation_generation.json"
        )
        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert data['phase'] == 'phase9_documentation_generation'

    def test_multiple_iterations_are_independent(self, monkeypatch, minimal_phase_outputs):
        # Create outputs for iteration 2 as well
        iter2_dir = minimal_phase_outputs / "DMAIC_V3_OUTPUT" / "iteration_2"
        ph1 = iter2_dir / "phase1_define"
        ph1.mkdir(parents=True)
        (ph1 / "phase1_define.json").write_text(json.dumps({"phase": "DEFINE", "iteration": 2}))
        ph2 = iter2_dir / "phase2_measure"
        ph2.mkdir(parents=True)
        (ph2 / "phase2_measure.json").write_text(json.dumps({"phase": "MEASURE", "iteration": 2}))

        monkeypatch.chdir(minimal_phase_outputs)
        for iteration in [1, 2]:
            phase9 = Phase9_DocumentationGeneration()
            success, result = phase9.execute(iteration=iteration)
            assert success is True
            assert result.get('iteration') == iteration


@pytest.mark.unit
class TestPhase9EvidenceBoundaries:
    """Exercise the real skip, verification and report-generation branches."""

    @pytest.mark.parametrize("missing", ["phase1_define", "phase2_measure"])
    def test_both_minimum_phase_receipts_are_required(
        self, tmp_path, monkeypatch, missing
    ):
        monkeypatch.chdir(tmp_path)
        iteration_root = tmp_path / "DMAIC_V3_OUTPUT" / "iteration_3"
        for name in ("phase1_define", "phase2_measure"):
            if name != missing:
                folder = iteration_root / name
                folder.mkdir(parents=True)
                (folder / f"{name}.json").write_text("{}", encoding="utf-8")
        phase9 = Phase9_DocumentationGeneration()
        assert phase9._verify_execution_success(3) is False
        assert not (tmp_path / "CANONICAL_KNOWLEDGE").exists()

    def test_valid_minimum_receipts_are_accepted(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        for name in ("phase1_define", "phase2_measure"):
            folder = tmp_path / "DMAIC_V3_OUTPUT" / "iteration_4" / name
            folder.mkdir(parents=True)
            (folder / f"{name}.json").write_text("{}", encoding="utf-8")
        assert Phase9_DocumentationGeneration()._verify_execution_success(4)

    def test_open_bugs_block_publication(
        self, minimal_phase_outputs, monkeypatch
    ):
        monkeypatch.chdir(minimal_phase_outputs)
        phase5 = (
            minimal_phase_outputs / "DMAIC_V3_OUTPUT" / "iteration_1"
            / "phase5_control"
        )
        phase5.mkdir()
        (phase5 / "phase5_control.json").write_text(json.dumps({
            "bugs": [{"id": "B-1", "status": "open"},
                     {"id": "B-2", "status": "closed"}],
            "quality_gates": {"safe": {"passed": True}},
        }), encoding="utf-8")
        ok, result = Phase9_DocumentationGeneration().execute(1)
        assert ok is False
        assert result["reason"] == "bugs_detected"
        assert [bug["id"] for bug in result["details"]] == ["B-1"]
        assert not (minimal_phase_outputs / "CANONICAL_KNOWLEDGE").exists()

    def test_failed_quality_gate_blocks_books(
        self, minimal_phase_outputs, monkeypatch
    ):
        monkeypatch.chdir(minimal_phase_outputs)
        phase5 = (
            minimal_phase_outputs / "DMAIC_V3_OUTPUT" / "iteration_1"
            / "phase5_control"
        )
        phase5.mkdir()
        (phase5 / "phase5_control.json").write_text(json.dumps({
            "bugs": [{"status": "closed"}],
            "quality_gates": {
                "passed": {"passed": True},
                "rejected": {"passed": False},
            },
        }), encoding="utf-8")
        ok, result = Phase9_DocumentationGeneration().execute(1)
        assert ok is False
        assert result["status"] == "skipped"
        assert result["reason"] == "quality_gates_failed"
        assert not (minimal_phase_outputs / "CANONICAL_KNOWLEDGE").exists()

    def test_passed_gates_and_closed_bugs_allow_publication(
        self, minimal_phase_outputs, monkeypatch
    ):
        monkeypatch.chdir(minimal_phase_outputs)
        phase5 = (
            minimal_phase_outputs / "DMAIC_V3_OUTPUT" / "iteration_1"
            / "phase5_control"
        )
        phase5.mkdir()
        (phase5 / "phase5_control.json").write_text(json.dumps({
            "bugs": [{"status": "closed"}],
            "quality_gates": {"security": {"passed": True}},
        }), encoding="utf-8")
        ok, result = Phase9_DocumentationGeneration().execute(1)
        assert ok is True
        assert result["books_generated"] == 4
        assert all(Path(book).is_file() for book in result["book_paths"])

    def test_discrepancy_classifies_canonical_difference(
        self, minimal_phase_outputs, monkeypatch
    ):
        monkeypatch.chdir(minimal_phase_outputs)
        phase9 = Phase9_DocumentationGeneration()
        differences = phase9._detect_discrepancies(1)
        assert {d["field"] for d in differences} == {
            "total_files", "python_files"
        }
        assert all(d["severity"] == "high" for d in differences)
        assert all(d["percentage"] < -10 for d in differences)
        assert phase9._detect_discrepancies(99) == []

    @pytest.mark.parametrize(("phase", "data", "expected"), [
        (0, {}, "**Status:**"),
        (1, {"total_files": 12345, "python_files": ["a.py"],
             "markdown_files": []}, "12,345"),
        (2, {"python_files_analyzed": 5,
             "analysis_success_rate": 0.8}, "80.0%"),
        (4, {"modifications": [{"file": "a.py"}]}, "1"),
        (5, {"quality_gates": {"a": {"passed": True}, "b": {"passed": False}}}, "1/2 passed"),
        (6, {"books_loaded": 3, "maturity_score": 72}, "72/100"),
    ])
    def test_phase_summary_reporting_paths(
        self, phase9, phase, data, expected
    ):
        assert expected in phase9._format_phase_summary(phase, data)

    def test_phase_lookup_has_explicit_unknown_fallback(self, phase9):
        assert phase9._get_phase_name(0) == "phase0_initialization"
        assert phase9._get_phase_name(8) == "phase8_todo_management"
        assert phase9._get_phase_name(42) == "phase42"

    def test_actual_books_include_metrics_actions_and_adjustment_receipt(
        self, minimal_phase_outputs, monkeypatch
    ):
        monkeypatch.chdir(minimal_phase_outputs)
        iteration = minimal_phase_outputs / "DMAIC_V3_OUTPUT" / "iteration_1"
        phase4 = iteration / "phase4_improve"
        phase4.mkdir()
        (phase4 / "phase4_improve.json").write_text(json.dumps({
            "modifications": [
                {"file": "one.py", "type": "docstring"},
                {"file": "one.py", "type": "format"},
                {"file": "two.py", "type": "docstring"},
            ],
        }), encoding="utf-8")
        phase7 = iteration / "phase7_action_tracking"
        phase7.mkdir()
        (phase7 / "phase7_action_tracking.json").write_text(json.dumps({
            "local_actions": [
                {"status": "completed"}, {"status": "pending"},
                {"status": "completed"},
            ]
        }), encoding="utf-8")
        (phase7 / "feedback_for_next_iteration.json").write_text(
            json.dumps({
                "pending_actions": [{}], "completed_actions": [{}, {}],
                "failed_actions": [], "recommendations": [{}],
            }), encoding="utf-8"
        )
        ok, result = Phase9_DocumentationGeneration().execute(1)
        assert ok is True
        assert result["books_generated"] == 4
        assert result["discrepancies_found"] == 2
        assert result["adjustments_made"] == 2
        canonical = minimal_phase_outputs / "CANONICAL_KNOWLEDGE"
        metrics = (
            canonical / "Execution_Logs" / "EXECUTION_METRICS_BOOK_iteration_1.md"
        ).read_text(encoding="utf-8")
        actions = (
            canonical / "Planning" / "ACTION_TRACKING_BOOK_iteration_1.md"
        ).read_text(encoding="utf-8")
        assert "Files Modified:** 2" in metrics
        assert "docstring: 2" in metrics
        assert "format: 1" in metrics
        assert "completed: 2" in actions
        assert "pending: 1" in actions
        assert "Completed Actions:** 2" in actions
        adjustment = json.loads((
            iteration / "phase9_documentation_generation"
            / "canonical_adjustments.json"
        ).read_text(encoding="utf-8"))
        assert {v["field"] for v in adjustment["adjustments"]} == {
            "total_files", "python_files"
        }
        saved = json.loads((
            iteration / "phase9_documentation_generation"
            / "phase9_documentation_generation.json"
        ).read_text(encoding="utf-8"))
        assert saved["status"] == "success"

    def test_invalid_quality_json_cannot_be_reported_as_success(
        self, minimal_phase_outputs, monkeypatch
    ):
        monkeypatch.chdir(minimal_phase_outputs)
        phase5 = (
            minimal_phase_outputs / "DMAIC_V3_OUTPUT" / "iteration_1"
            / "phase5_control"
        )
        phase5.mkdir()
        (phase5 / "phase5_control.json").write_text(
            "{invalid-json", encoding="utf-8"
        )
        ok, result = Phase9_DocumentationGeneration().execute(1)
        assert ok is False
        assert "error" in result
        assert not (minimal_phase_outputs / "CANONICAL_KNOWLEDGE").exists()
