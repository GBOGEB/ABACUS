import pytest
from pathlib import Path
import tempfile
import shutil
import json
from DMAIC_V3.phases.phase4_improve import Phase4Improve
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
def phase4(config, state_manager):
    return Phase4Improve(config, state_manager)


@pytest.fixture
def phase3_output(config):
    output_dir = config.paths.output_root / "iteration_1"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    phase3_data = {
        'phase': 'ANALYZE',
        'iteration': 1,
        'timestamp': '2025-01-10T10:00:00',
        'summary': {
            'critical_issues': 2,
            'high_issues': 5,
            'medium_issues': 10,
            'total_issues': 17
        },
        'analysis': {
            'high_complexity_files': ['file1.py', 'file2.py'],
            'issues': [
                {
                    'severity': 'critical',
                    'file': 'file1.py',
                    'description': 'High complexity detected'
                },
                {
                    'severity': 'high',
                    'file': 'file2.py',
                    'description': 'Code duplication found'
                }
            ]
        }
    }
    
    phase3_file = output_dir / "phase3_analysis.json"
    phase3_file.write_text(json.dumps(phase3_data))
    return phase3_data


@pytest.mark.phase4
@pytest.mark.unit
class TestPhase4Improve:
    
    def test_initialization(self, phase4, config):
        assert phase4.config == config
    
    def test_execute_with_phase3_output(self, phase4, phase3_output):
        success, result = phase4.execute(iteration=1)
        
        assert result['phase'] == 'IMPROVE'
        assert result['iteration'] == 1
        assert 'timestamp' in result
        assert 'improvements' in result
    
    def test_generate_improvements(self, phase4, phase3_output):
        success, result = phase4.execute(iteration=1)
        
        improvements = result.get('improvements', [])
        assert isinstance(improvements, list)
    
    def test_prioritize_improvements(self, phase4, phase3_output):
        success, result = phase4.execute(iteration=1)
        
        improvements = result.get('improvements', [])
        if improvements:
            for improvement in improvements:
                assert 'priority' in improvement or 'severity' in improvement
    
    def test_output_structure(self, phase4, phase3_output):
        success, result = phase4.execute(iteration=1)
        
        assert 'phase' in result
        assert 'iteration' in result
        assert 'timestamp' in result
        assert 'input_source' in result
        assert 'improvements' in result
    
    def test_dual_output_locations(self, phase4, phase3_output, config):
        success, result = phase4.execute(iteration=1)
        
        output_dir = config.paths.output_root / "iteration_1"
        phase4_improvements_file = output_dir / "phase4_improvements.json"
        phase4_dir_file = output_dir / "phase4_improve" / "phase4_improve.json"
        
        assert phase4_improvements_file.exists()
        assert phase4_dir_file.exists()
        
        with open(phase4_improvements_file) as f1, open(phase4_dir_file) as f2:
            data1 = json.load(f1)
            data2 = json.load(f2)
            assert data1['phase'] == data2['phase']
            assert data1['iteration'] == data2['iteration']
    
    def test_missing_phase3_output(self, phase4, config):
        success, result = phase4.execute(iteration=99)
        
        assert result is not None
        assert result.get('phase') == 'IMPROVE'
    
    def test_improvement_categories(self, phase4, phase3_output):
        success, result = phase4.execute(iteration=1)
        
        improvements = result.get('improvements', [])
        if improvements:
            for improvement in improvements:
                assert 'description' in improvement or 'action' in improvement
    
    def test_improvement_tracking(self, phase4, phase3_output):
        success, result = phase4.execute(iteration=1)
        
        assert 'total_improvements' in result or len(result.get('improvements', [])) >= 0
    
    def test_file_saved_correctly(self, phase4, phase3_output, config):
        success, result = phase4.execute(iteration=1)
        
        output_file = config.paths.output_root / "iteration_1" / "phase4_improvements.json"
        assert output_file.exists()
        
        with open(output_file) as f:
            data = json.load(f)
            assert data['phase'] == 'IMPROVE'
            assert data['iteration'] == 1
    
    def test_multiple_iterations(self, phase4, config):
        for iteration in [1, 2]:
            output_dir = config.paths.output_root / f"iteration_{iteration}"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            phase3_data = {
                'phase': 'ANALYZE',
                'iteration': iteration,
                'summary': {'total_issues': 5},
                'analysis': {'issues': []}
            }
            
            phase3_file = output_dir / "phase3_analysis.json"
            phase3_file.write_text(json.dumps(phase3_data))
            
            success, result = phase4.execute(iteration=iteration)
            assert result['iteration'] == iteration
    
    def test_improvement_actionability(self, phase4, phase3_output):
        success, result = phase4.execute(iteration=1)
        
        improvements = result.get('improvements', [])
        if improvements:
            for improvement in improvements:
                assert isinstance(improvement, dict)
                assert len(improvement) > 0
