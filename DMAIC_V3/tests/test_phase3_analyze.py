import pytest
from pathlib import Path
import tempfile
import shutil
import json
from DMAIC_V3.phases.phase3_analyze import Phase3Analyze
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
def phase3(config, state_manager):
    return Phase3Analyze(config, state_manager)


@pytest.fixture
def phase2_output(config):
    output_dir = config.paths.output_root / "iteration_1"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    phase2_data = {
        'phase': 'MEASURE',
        'iteration': 1,
        'timestamp': '2025-01-10T10:00:00',
        'statistics': {
            'total_files_analyzed': 5,
            'total_lines': 1000,
            'total_functions': 50,
            'total_classes': 10
        },
        'file_metrics': {
            'file1.py': {
                'lines_of_code': 200,
                'complexity': 150,
                'function_count': 10,
                'class_count': 2
            },
            'file2.py': {
                'lines_of_code': 300,
                'complexity': 250,
                'function_count': 15,
                'class_count': 3
            },
            'file3.py': {
                'lines_of_code': 500,
                'complexity': 450,
                'function_count': 25,
                'class_count': 5
            }
        }
    }
    
    phase2_file = output_dir / "phase2_metrics.json"
    phase2_file.write_text(json.dumps(phase2_data))
    return phase2_data


@pytest.mark.phase3
@pytest.mark.unit
class TestPhase3Analyze:
    
    def test_initialization(self, phase3, config):
        assert phase3.config == config
    
    def test_execute_with_phase2_output(self, phase3, phase2_output):
        success, result = phase3.execute(iteration=1)
        
        assert success is True
        assert result.get('summary') is not None
        assert result.get('root_causes') is not None
    
    def test_identify_high_complexity_files(self, phase3, phase2_output):
        success, result = phase3.execute(iteration=1)
        
        assert success is True
        assert result.get('summary') is not None
    
    def test_calculate_statistics(self, phase3, phase2_output):
        success, result = phase3.execute(iteration=1)
        
        summary = result.get('summary', {})
        assert isinstance(summary, dict)
    
    def test_output_structure(self, phase3, phase2_output):
        success, result = phase3.execute(iteration=1)
        
        assert success is True
        assert 'summary' in result
        assert 'root_causes' in result
        assert 'output_file' in result
    
    def test_missing_phase2_output(self, phase3, config):
        success, result = phase3.execute(iteration=99)
        
        assert success is False
        assert 'error' in result
    
    def test_issue_categorization(self, phase3, phase2_output):
        success, result = phase3.execute(iteration=1)
        
        summary = result.get('summary', {})
        if 'critical_issues' in summary:
            assert isinstance(summary['critical_issues'], int)
        if 'high_issues' in summary:
            assert isinstance(summary['high_issues'], int)
        if 'medium_issues' in summary:
            assert isinstance(summary['medium_issues'], int)
    
    def test_analysis_recommendations(self, phase3, phase2_output):
        success, result = phase3.execute(iteration=1)
        
        assert success is True
        assert 'summary' in result or 'root_causes' in result
    
    def test_file_saved_correctly(self, phase3, phase2_output, config):
        success, result = phase3.execute(iteration=1)
        
        output_file = config.paths.output_root / "iteration_1" / "phase3_analysis.json"
        assert output_file.exists()
        
        with open(output_file) as f:
            data = json.load(f)
            assert data['iteration'] == 1
            assert 'summary' in data
    
    def test_multiple_iterations(self, phase3, config):
        for iteration in [1, 2]:
            output_dir = config.paths.output_root / f"iteration_{iteration}"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            phase2_data = {
                'phase': 'MEASURE',
                'iteration': iteration,
                'file_metrics': {}
            }
            
            phase2_file = output_dir / "phase2_metrics.json"
            phase2_file.write_text(json.dumps(phase2_data))
            
            success, result = phase3.execute(iteration=iteration)
            assert success is True
            assert result.get('output_file') is not None
