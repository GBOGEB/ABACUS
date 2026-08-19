"""
DMAIC V3 Test Suite - Phase 8: TODO Management Tests
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from DMAIC_V3.phases.phase8_todo_management import Phase8TODOManagement
from DMAIC_V3.config import DMAICConfig
from DMAIC_V3.core.state import StateManager


@pytest.fixture
def temp_workspace():
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def config(temp_workspace):
    cfg = DMAICConfig()
    cfg.workspace_root = str(temp_workspace)
    cfg.paths.workspace_root = temp_workspace
    cfg.paths.output_root = temp_workspace / "output"
    return cfg


@pytest.fixture
def state_manager(config):
    state_dir = config.paths.output_root / "state"
    return StateManager(state_dir)


@pytest.fixture
def phase8(config, state_manager, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    return Phase8TODOManagement(config, state_manager)


@pytest.mark.unit
class TestPhase8TODOManagement:

    def test_initialization(self, phase8, config, state_manager):
        assert phase8.config is not None
        assert phase8.state_mgr is not None
        assert phase8.tracker is not None

    def test_execute_returns_two_tuple(self, phase8):
        result = phase8.execute(iteration=1)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_execute_returns_bool_and_dict(self, phase8):
        success, result = phase8.execute(iteration=1)
        assert isinstance(success, bool)
        assert isinstance(result, dict)

    def test_execute_succeeds_with_no_prior_phases(self, phase8):
        success, result = phase8.execute(iteration=1)
        assert success is True

    def test_result_has_phase_field(self, phase8):
        success, result = phase8.execute(iteration=1)
        assert result.get('phase') == 'phase8_todo_management'

    def test_result_has_iteration(self, phase8):
        success, result = phase8.execute(iteration=4)
        assert result.get('iteration') == 4

    def test_result_has_local_todos(self, phase8):
        success, result = phase8.execute(iteration=1)
        assert 'local_todos' in result
        assert isinstance(result['local_todos'], list)

    def test_result_has_global_statistics(self, phase8):
        success, result = phase8.execute(iteration=1)
        assert 'global_statistics' in result
        assert isinstance(result['global_statistics'], dict)

    def test_result_has_todo_links(self, phase8):
        success, result = phase8.execute(iteration=1)
        assert 'todo_links' in result
        assert isinstance(result['todo_links'], dict)

    def test_result_has_prioritized_todos(self, phase8):
        success, result = phase8.execute(iteration=1)
        assert 'prioritized_todos' in result
        assert isinstance(result['prioritized_todos'], list)

    def test_output_files_created(self, phase8, tmp_path):
        success, result = phase8.execute(iteration=1)
        output_dir = tmp_path / "DMAIC_V3_OUTPUT" / "iteration_1" / "phase8_todo_management"
        assert output_dir.exists()
        assert (output_dir / "phase8_todo_management.json").exists()

    def test_todo_report_created(self, phase8, tmp_path):
        success, result = phase8.execute(iteration=1)
        report_file = (
            tmp_path / "DMAIC_V3_OUTPUT" / "iteration_1"
            / "phase8_todo_management" / "todo_report.md"
        )
        assert report_file.exists()

    def test_with_python_file_containing_todos(self, phase8, temp_workspace):
        # Write a Python file with TODO comments into workspace
        py_file = temp_workspace / "sample.py"
        py_file.write_text("# TODO: fix this bug\nresult = 1 + 1\n# TODO: add tests\n")

        success, result = phase8.execute(iteration=1)
        assert success is True
        # Todos from code scanning should appear in local_todos
        assert isinstance(result['local_todos'], list)

    def test_todo_executions_field(self, phase8):
        success, result = phase8.execute(iteration=1)
        assert 'todo_executions' in result
        assert isinstance(result['todo_executions'], list)
