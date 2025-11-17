import pytest
from pathlib import Path
import tempfile
import shutil
import json
from DMAIC_V3.phases.phase2_measure import Phase2Measure
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
def phase2(config, state_manager):
    return Phase2Measure(config, state_manager)


@pytest.fixture
def sample_python_file(temp_workspace):
    file_path = temp_workspace / "sample.py"
    content = '''
def hello_world():
    """Say hello"""
    print("Hello, World!")

class Calculator:
    """Simple calculator"""
    
    def add(self, a, b):
        return a + b
    
    def subtract(self, a, b):
        return a - b

import os
import sys
from pathlib import Path
'''
    file_path.write_text(content)
    return file_path


@pytest.mark.phase2
@pytest.mark.unit
class TestPhase2Measure:
    
    def test_initialization(self, phase2, config):
        assert phase2.config == config
        assert phase2.workspace_root == config.paths.workspace_root
    
    def test_analyze_python_file(self, phase2, sample_python_file):
        result = phase2.analyze_python_file(str(sample_python_file))
        
        assert result['success'] is True
        assert 'metrics' in result
        metrics = result['metrics']
        
        assert metrics['total_lines'] > 0
        assert metrics['lines_of_code'] > 0
        assert metrics['function_count'] >= 2
        assert metrics['class_count'] >= 1
        assert metrics['import_count'] >= 3
    
    def test_analyze_invalid_python_file(self, phase2, temp_workspace):
        invalid_file = temp_workspace / "invalid.py"
        invalid_file.write_text("def broken(:\n    pass")
        
        result = phase2.analyze_python_file(str(invalid_file))
        assert result['success'] is False
        assert 'error' in result
    
    def test_analyze_nonexistent_file(self, phase2, temp_workspace):
        result = phase2.analyze_python_file(str(temp_workspace / "nonexistent.py"))
        assert result['success'] is False
    
    def test_complexity_calculation(self, phase2, temp_workspace):
        simple_file = temp_workspace / "simple.py"
        simple_file.write_text("x = 1")
        
        complex_file = temp_workspace / "complex.py"
        complex_content = '''
import os
import sys
import json

class A:
    def method1(self): pass
    def method2(self): pass

class B:
    def method3(self): pass

def func1(): pass
def func2(): pass
def func3(): pass
'''
        complex_file.write_text(complex_content)
        
        simple_result = phase2.analyze_python_file(str(simple_file))
        complex_result = phase2.analyze_python_file(str(complex_file))
        
        assert complex_result['metrics']['complexity'] > simple_result['metrics']['complexity']
    
    def test_execute_with_phase1_output(self, phase2, temp_workspace, config):
        phase1_dir = config.paths.output_root / "iteration_1" / "phase1_define"
        phase1_dir.mkdir(parents=True, exist_ok=True)
        
        (temp_workspace / "test.py").write_text("print('test')")
        
        phase1_output = {
            'phase': 'DEFINE',
            'iteration': 1,
            'files': [str(temp_workspace / "test.py")],
            'total_files': 1
        }
        
        phase1_file = phase1_dir / "phase1_define.json"
        phase1_file.write_text(json.dumps(phase1_output))
        
        result = phase2.execute(iteration=1)
        
        assert result['phase'] == 'MEASURE'
        assert result['iteration'] == 1
        assert 'statistics' in result
        assert 'measurements' in result
    
    def test_output_structure(self, phase2, temp_workspace, config):
        phase1_dir = config.paths.output_root / "iteration_1" / "phase1_define"
        phase1_dir.mkdir(parents=True, exist_ok=True)
        
        phase1_output = {
            'phase': 'DEFINE',
            'iteration': 1,
            'files': [],
            'total_files': 0
        }
        
        phase1_file = phase1_dir / "phase1_define.json"
        phase1_file.write_text(json.dumps(phase1_output))
        
        result = phase2.execute(iteration=1)
        
        assert 'phase' in result
        assert 'iteration' in result
        assert 'timestamp' in result
        assert 'statistics' in result
        assert 'file_metrics' in result
        assert 'measurements' in result
    
    def test_dual_output_locations(self, phase2, temp_workspace, config):
        phase1_dir = config.paths.output_root / "iteration_1" / "phase1_define"
        phase1_dir.mkdir(parents=True, exist_ok=True)
        
        phase1_output = {
            'phase': 'DEFINE',
            'iteration': 1,
            'files': [],
            'total_files': 0
        }
        
        phase1_file = phase1_dir / "phase1_define.json"
        phase1_file.write_text(json.dumps(phase1_output))
        
        phase2.execute(iteration=1)
        
        output_dir = config.paths.output_root / "iteration_1"
        phase2_dir_file = output_dir / "phase2_measure" / "phase2_measure.json"
        phase2_metrics_file = output_dir / "phase2_metrics.json"
        
        assert phase2_dir_file.exists()
        assert phase2_metrics_file.exists()
        
        with open(phase2_dir_file) as f1, open(phase2_metrics_file) as f2:
            data1 = json.load(f1)
            data2 = json.load(f2)
            assert data1['phase'] == data2['phase']
            assert data1['iteration'] == data2['iteration']
