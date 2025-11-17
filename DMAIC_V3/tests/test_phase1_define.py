import pytest
from pathlib import Path
import tempfile
import shutil
from DMAIC_V3.phases.phase1_define import Phase1Define
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
def phase1(config, state_manager):
    return Phase1Define(config, state_manager)


@pytest.mark.phase1
@pytest.mark.unit
class TestPhase1Define:
    
    def test_initialization(self, phase1, config):
        assert phase1.config == config
        assert phase1.workspace_root == config.paths.workspace_root
    
    def test_scan_empty_directory(self, phase1, temp_workspace):
        result = phase1.execute(iteration=1)
        assert result['phase'] == 'DEFINE'
        assert result['iteration'] == 1
        assert result['total_files'] >= 0
    
    def test_scan_with_python_files(self, phase1, temp_workspace):
        (temp_workspace / "test.py").write_text("print('hello')")
        (temp_workspace / "module.py").write_text("def func(): pass")
        
        result = phase1.execute(iteration=1)
        assert result['total_files'] >= 2
        assert result['code_files'] >= 2
    
    def test_scan_with_documentation(self, phase1, temp_workspace):
        (temp_workspace / "README.md").write_text("# Documentation")
        (temp_workspace / "docs.txt").write_text("Documentation")
        
        result = phase1.execute(iteration=1)
        assert result['documentation_files'] >= 2
    
    def test_scan_excludes_venv(self, phase1, temp_workspace):
        venv_dir = temp_workspace / "venv"
        venv_dir.mkdir()
        (venv_dir / "test.py").write_text("# Should be excluded")
        
        result = phase1.execute(iteration=1)
        files = result.get('files', [])
        assert not any('venv' in str(f) for f in files)
    
    def test_scan_excludes_pycache(self, phase1, temp_workspace):
        cache_dir = temp_workspace / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "test.pyc").write_text("# Should be excluded")
        
        result = phase1.execute(iteration=1)
        files = result.get('files', [])
        assert not any('__pycache__' in str(f) for f in files)
    
    def test_output_structure(self, phase1):
        result = phase1.execute(iteration=1)
        
        assert 'phase' in result
        assert 'iteration' in result
        assert 'timestamp' in result
        assert 'total_files' in result
        assert 'code_files' in result
        assert 'documentation_files' in result
        assert 'duration' in result
    
    def test_multiple_iterations(self, phase1):
        result1 = phase1.execute(iteration=1)
        result2 = phase1.execute(iteration=2)
        
        assert result1['iteration'] == 1
        assert result2['iteration'] == 2
        assert result1['timestamp'] != result2['timestamp']
    
    def test_file_categorization(self, phase1, temp_workspace):
        (temp_workspace / "code.py").write_text("# Python")
        (temp_workspace / "script.js").write_text("// JavaScript")
        (temp_workspace / "README.md").write_text("# Docs")
        (temp_workspace / "data.json").write_text("{}")
        
        result = phase1.execute(iteration=1)
        assert result['total_files'] >= 4
        assert result['code_files'] >= 2
        assert result['documentation_files'] >= 1
