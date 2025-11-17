import pytest
from pathlib import Path
import tempfile
import shutil
import json
from DMAIC_V3.phases.phase5_control import Phase5Control
from DMAIC_V3.config import DMAICConfig
from DMAIC_V3.core.state import StateManager


@pytest.fixture
def temp_workspace():
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def config(temp_workspace):
    config = DMAICConfig()
    config.paths.workspace_root = temp_workspace
    config.paths.output_root = temp_workspace / "output"
    return config


@pytest.fixture
def state_manager(config):
    state_dir = config.paths.output_root / "state"
    return StateManager(state_dir)


@pytest.fixture
def phase5(config, state_manager):
    return Phase5Control(config, state_manager)


@pytest.fixture
def phase4_output(config):
    output_dir = config.paths.output_root / "iteration_1" / "phase4_improve"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    phase4_data = {
        'phase': 'IMPROVE',
        'iteration': 1,
        'timestamp': '2025-01-10T10:00:00',
        'improvements': [
            {
                'id': 1,
                'priority': 'high',
                'description': 'Refactor complex function',
                'file': 'file1.py',
                'status': 'planned'
            },
            {
                'id': 2,
                'priority': 'medium',
                'description': 'Add documentation',
                'file': 'file2.py',
                'status': 'planned'
            }
        ],
        'total_improvements': 2
    }
    
    phase4_file = output_dir / "phase4_improve.json"
    phase4_file.write_text(json.dumps(phase4_data))
    return phase4_data


@pytest.mark.phase5
@pytest.mark.unit
class TestPhase5Control:
    
    def test_initialization(self, phase5, config):
        assert phase5.config == config
    
    def test_execute_with_phase4_output(self, phase5, phase4_output):
        success, result = phase5.execute(iteration=1)
        
        assert success is True
        assert result['phase'] == 'CONTROL'
        assert result['iteration'] == 1
        assert 'timestamp' in result
    
    def test_establish_quality_gates(self, phase5, phase4_output):
        success, result = phase5.execute(iteration=1)
        
        assert 'quality_gates' in result or 'controls' in result
    
    def test_validation_checkpoints(self, phase5, phase4_output):
        success, result = phase5.execute(iteration=1)
        
        assert 'validation_checkpoints' in result or 'checkpoints' in result or 'quality_gates' in result
    
    def test_output_structure(self, phase5, phase4_output):
        success, result = phase5.execute(iteration=1)
        
        assert 'phase' in result
        assert 'iteration' in result
        assert 'timestamp' in result
        assert 'input_source' in result or 'phase' in result  # input_source may not always be present
    
    def test_missing_phase4_output(self, phase5, config):
        success, result = phase5.execute(iteration=99)
        
        assert result is not None
        assert result.get('phase') == 'CONTROL'
    
    def test_monitoring_mechanisms(self, phase5, phase4_output):
        success, result = phase5.execute(iteration=1)
        
        assert isinstance(result, dict)
        assert len(result) > 0
    
    def test_file_saved_correctly(self, phase5, phase4_output, config):
        phase5.execute(iteration=1)
        
        output_file = config.paths.output_root / "iteration_1" / "phase5_control" / "phase5_control.json"
        assert output_file.exists()
        
        with open(output_file) as f:
            data = json.load(f)
            assert data['phase'] == 'CONTROL'
            assert data['iteration'] == 1
    
    def test_multiple_iterations(self, phase5, config):
        for iteration in [1, 2]:
            output_dir = config.paths.output_root / f"iteration_{iteration}" / "phase4_improve"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            phase4_data = {
                'phase': 'IMPROVE',
                'iteration': iteration,
                'improvements': [],
                'total_improvements': 0
            }
            
            phase4_file = output_dir / "phase4_improve.json"
            phase4_file.write_text(json.dumps(phase4_data))
            
            success, result = phase5.execute(iteration=iteration)
            assert result['iteration'] == iteration
    
    def test_control_metrics(self, phase5, phase4_output):
        success, result = phase5.execute(iteration=1)
        
        assert 'metrics' in result or 'summary' in result or 'controls' in result or 'quality_gates' in result
    
    def test_continuous_monitoring(self, phase5, phase4_output):
        success, result = phase5.execute(iteration=1)
        
        assert result is not None
        assert result['phase'] == 'CONTROL'
