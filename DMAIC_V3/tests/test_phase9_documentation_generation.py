"""
DMAIC V3 Test Suite - Phase 9: Documentation Generation Tests
"""

import pytest
import json
import tempfile
import shutil
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
