import pytest
from pathlib import Path
import tempfile
import shutil
import json
from DMAIC_V3.phases.phase1_define import Phase1Define
from DMAIC_V3.phases.phase2_measure import Phase2Measure
from DMAIC_V3.phases.phase3_analyze import Phase3Analyze
from DMAIC_V3.phases.phase4_improve import Phase4Improve
from DMAIC_V3.phases.phase5_control import Phase5Control
from DMAIC_V3.config import DMAICConfig
from DMAIC_V3.core.state import StateManager


@pytest.fixture
def temp_workspace():
    temp_dir = tempfile.mkdtemp()
    workspace = Path(temp_dir)
    
    (workspace / "test1.py").write_text("def func1(): pass")
    (workspace / "test2.py").write_text("def func2(): pass")
    (workspace / "README.md").write_text("# Documentation")
    
    yield workspace
    shutil.rmtree(temp_dir)


@pytest.fixture
def config(temp_workspace):
    config = DMAICConfig()
    config.paths.workspace_root = temp_workspace
    config.paths.output_root = temp_workspace / "output"
    return config


@pytest.fixture
def state_manager(config):
    return StateManager(config)


@pytest.mark.integration
@pytest.mark.slow
class TestFullDMAICCycle:
    
    def test_complete_cycle_iteration_1(self, config, state_manager, temp_workspace):
        iteration = 1
        
        phase1 = Phase1Define(config, state_manager)
        result1 = phase1.execute(iteration=iteration)
        assert result1['phase'] == 'DEFINE'
        assert result1['iteration'] == iteration
        assert result1['total_files'] >= 3
        
        phase2 = Phase2Measure(config, state_manager)
        result2 = phase2.execute(iteration=iteration)
        assert result2['phase'] == 'MEASURE'
        assert result2['iteration'] == iteration
        
        phase3 = Phase3Analyze(config, state_manager)
        result3 = phase3.execute(iteration=iteration)
        assert result3['phase'] == 'ANALYZE'
        assert result3['iteration'] == iteration
        
        phase4 = Phase4Improve(config, state_manager)
        result4 = phase4.execute(iteration=iteration)
        assert result4['phase'] == 'IMPROVE'
        assert result4['iteration'] == iteration
        
        phase5 = Phase5Control(config, state_manager)
        result5 = phase5.execute(iteration=iteration)
        assert result5['phase'] == 'CONTROL'
        assert result5['iteration'] == iteration
    
    def test_phase_handoffs(self, config, state_manager, temp_workspace):
        iteration = 1
        
        phase1 = Phase1Define(config, state_manager)
        phase1.execute(iteration=iteration)
        
        phase1_output = config.paths.output_root / f"iteration_{iteration}" / "phase1_define" / "phase1_define.json"
        assert phase1_output.exists()
        
        phase2 = Phase2Measure(config, state_manager)
        phase2.execute(iteration=iteration)
        
        phase2_output1 = config.paths.output_root / f"iteration_{iteration}" / "phase2_measure" / "phase2_measure.json"
        phase2_output2 = config.paths.output_root / f"iteration_{iteration}" / "phase2_metrics.json"
        assert phase2_output1.exists()
        assert phase2_output2.exists()
        
        phase3 = Phase3Analyze(config, state_manager)
        phase3.execute(iteration=iteration)
        
        phase3_output = config.paths.output_root / f"iteration_{iteration}" / "phase3_analysis.json"
        assert phase3_output.exists()
        
        phase4 = Phase4Improve(config, state_manager)
        phase4.execute(iteration=iteration)
        
        phase4_output1 = config.paths.output_root / f"iteration_{iteration}" / "phase4_improvements.json"
        phase4_output2 = config.paths.output_root / f"iteration_{iteration}" / "phase4_improve" / "phase4_improve.json"
        assert phase4_output1.exists()
        assert phase4_output2.exists()
        
        phase5 = Phase5Control(config, state_manager)
        phase5.execute(iteration=iteration)
        
        phase5_output = config.paths.output_root / f"iteration_{iteration}" / "phase5_control" / "phase5_control.json"
        assert phase5_output.exists()
    
    def test_data_persistence(self, config, state_manager, temp_workspace):
        iteration = 1
        
        phase1 = Phase1Define(config, state_manager)
        result1 = phase1.execute(iteration=iteration)
        
        phase1_file = config.paths.output_root / f"iteration_{iteration}" / "phase1_define" / "phase1_define.json"
        with open(phase1_file) as f:
            saved_data = json.load(f)
            assert saved_data['phase'] == result1['phase']
            assert saved_data['iteration'] == result1['iteration']
    
    def test_multiple_iterations(self, config, state_manager, temp_workspace):
        for iteration in [1, 2]:
            phase1 = Phase1Define(config, state_manager)
            result = phase1.execute(iteration=iteration)
            assert result['iteration'] == iteration
            
            output_file = config.paths.output_root / f"iteration_{iteration}" / "phase1_define" / "phase1_define.json"
            assert output_file.exists()
    
    def test_error_handling_missing_input(self, config, state_manager, temp_workspace):
        phase3 = Phase3Analyze(config, state_manager)
        result = phase3.execute(iteration=999)
        
        assert result is not None
        assert result['phase'] == 'ANALYZE'
    
    def test_idempotency(self, config, state_manager, temp_workspace):
        iteration = 1
        
        phase1 = Phase1Define(config, state_manager)
        result1 = phase1.execute(iteration=iteration)
        result2 = phase1.execute(iteration=iteration)
        
        assert result1['phase'] == result2['phase']
        assert result1['iteration'] == result2['iteration']
    
    def test_output_directory_structure(self, config, state_manager, temp_workspace):
        iteration = 1
        
        phase1 = Phase1Define(config, state_manager)
        phase1.execute(iteration=iteration)
        
        phase2 = Phase2Measure(config, state_manager)
        phase2.execute(iteration=iteration)
        
        phase3 = Phase3Analyze(config, state_manager)
        phase3.execute(iteration=iteration)
        
        phase4 = Phase4Improve(config, state_manager)
        phase4.execute(iteration=iteration)
        
        phase5 = Phase5Control(config, state_manager)
        phase5.execute(iteration=iteration)
        
        iter_dir = config.paths.output_root / f"iteration_{iteration}"
        assert iter_dir.exists()
        assert (iter_dir / "phase1_define").exists()
        assert (iter_dir / "phase2_measure").exists()
        assert (iter_dir / "phase2_metrics.json").exists()
        assert (iter_dir / "phase3_analysis.json").exists()
        assert (iter_dir / "phase4_improvements.json").exists()
        assert (iter_dir / "phase4_improve").exists()
        assert (iter_dir / "phase5_control").exists()
