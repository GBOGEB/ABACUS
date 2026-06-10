"""
DMAIC V3 Test Suite - Phase 7: Action Tracking Tests
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path

from DMAIC_V3.phases.phase7_action_tracking import Phase7ActionTracking
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
def phase7(config, state_manager, monkeypatch, tmp_path):
    # Redirect relative path operations to tmp_path
    monkeypatch.chdir(tmp_path)
    return Phase7ActionTracking(config, state_manager)


@pytest.mark.unit
class TestPhase7ActionTracking:

    def test_initialization(self, phase7, config, state_manager):
        assert phase7.config is not None
        assert phase7.state_mgr is not None
        assert phase7.tracker is not None

    def test_execute_returns_two_tuple(self, phase7):
        result = phase7.execute(iteration=1)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_execute_returns_bool_and_dict(self, phase7):
        success, result = phase7.execute(iteration=1)
        assert isinstance(success, bool)
        assert isinstance(result, dict)

    def test_execute_succeeds_with_no_prior_phases(self, phase7):
        # With no prior phase output, Phase 7 collects 0 actions and still succeeds
        success, result = phase7.execute(iteration=1)
        assert success is True

    def test_result_has_phase_field(self, phase7):
        success, result = phase7.execute(iteration=1)
        assert result.get('phase') == 'phase7_action_tracking'

    def test_result_has_iteration(self, phase7):
        success, result = phase7.execute(iteration=3)
        assert result.get('iteration') == 3

    def test_result_has_local_actions(self, phase7):
        success, result = phase7.execute(iteration=1)
        assert 'local_actions' in result
        assert isinstance(result['local_actions'], list)

    def test_result_has_global_statistics(self, phase7):
        success, result = phase7.execute(iteration=1)
        assert 'global_statistics' in result
        assert isinstance(result['global_statistics'], dict)

    def test_result_has_action_links(self, phase7):
        success, result = phase7.execute(iteration=1)
        assert 'action_links' in result
        assert isinstance(result['action_links'], dict)

    def test_result_has_feedback(self, phase7):
        success, result = phase7.execute(iteration=1)
        assert 'feedback' in result
        assert isinstance(result['feedback'], dict)

    def test_output_files_created(self, phase7, tmp_path):
        success, result = phase7.execute(iteration=1)
        output_dir = tmp_path / "DMAIC_V3_OUTPUT" / "iteration_1" / "phase7_action_tracking"
        assert output_dir.exists()
        assert (output_dir / "phase7_action_tracking.json").exists()

    def test_action_report_created(self, phase7, tmp_path):
        success, result = phase7.execute(iteration=1)
        report_file = tmp_path / "DMAIC_V3_OUTPUT" / "iteration_1" / "phase7_action_tracking" / "action_report.md"
        assert report_file.exists()

    def test_with_prior_phase4_output(self, phase7, tmp_path):
        # Create a mock Phase 4 output with actions
        output_dir = tmp_path / "DMAIC_V3_OUTPUT" / "iteration_1"
        output_dir.mkdir(parents=True)
        phase4_file = output_dir / "phase4_improvements.json"
        phase4_data = {
            "phase": "IMPROVE",
            "iteration": 1,
            "implementation_results": {
                "docstrings_added": [
                    {"file": "test.py", "modifications": 2}
                ]
            }
        }
        phase4_file.write_text(json.dumps(phase4_data))

        success, result = phase7.execute(iteration=1)
        assert success is True
        assert len(result['local_actions']) > 0
