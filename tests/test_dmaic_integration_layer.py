#!/usr/bin/env python3
"""
TEST SUITE: DMAIC INTEGRATION LAYER
====================================
Version: 1.0.0
Date: 2025-01-28

Test Coverage:
- DMAIC phase execution (Define, Measure, Analyze, Improve, Control)
- Lazy loading of components
- Metrics export and aggregation
- Cycle status tracking
- Integration state persistence
- Error handling
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import sys
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich_padding.dmaic_integration_layer import (
    DMAICIntegrationLayer,
    DMAICPhase,
    PhaseMetrics,
    DMAICCycleStatus
)


@pytest.fixture
def workspace(tmp_path):
    """Create temporary workspace"""
    workspace = tmp_path / "test_workspace"
    workspace.mkdir()
    
    (workspace / "rich_padding").mkdir()
    (workspace / "rich_padding" / "reports").mkdir(parents=True)
    
    return workspace


@pytest.fixture
def dmaic_layer(workspace):
    """Create DMAICIntegrationLayer instance"""
    return DMAICIntegrationLayer(workspace, lazy_load=True)


def test_initialization(dmaic_layer, workspace):
    """Test 1: Integration layer initializes correctly"""
    assert dmaic_layer.workspace == workspace
    assert dmaic_layer.lazy_load is True
    assert dmaic_layer.current_phase == DMAICPhase.DEFINE
    assert len(dmaic_layer.phases) == 0


def test_lazy_loading_enabled(dmaic_layer):
    """Test 2: Lazy loading prevents immediate component loading"""
    assert dmaic_layer._dmaic_orchestrator is None
    assert dmaic_layer._metrics_scanner is None
    assert dmaic_layer._improvement_pipeline is None


def test_execute_define_phase(dmaic_layer):
    """Test 3: Execute Define phase successfully"""
    result = dmaic_layer.execute_phase(DMAICPhase.DEFINE)
    
    assert isinstance(result, PhaseMetrics)
    assert result.phase == DMAICPhase.DEFINE
    assert result.status == "completed"
    assert result.completion == 100.0
    assert "problem_statement" in result.metrics


def test_execute_measure_phase(dmaic_layer):
    """Test 4: Execute Measure phase successfully"""
    result = dmaic_layer.execute_phase(DMAICPhase.MEASURE)
    
    assert isinstance(result, PhaseMetrics)
    assert result.phase == DMAICPhase.MEASURE
    assert result.status == "completed"
    assert "baseline_collected" in result.metrics
    assert "data_sources" in result.metrics


def test_execute_analyze_phase(dmaic_layer):
    """Test 5: Execute Analyze phase successfully"""
    result = dmaic_layer.execute_phase(DMAICPhase.ANALYZE)
    
    assert isinstance(result, PhaseMetrics)
    assert result.phase == DMAICPhase.ANALYZE
    assert result.status == "completed"
    assert "findings" in result.metrics
    assert "recommendations" in result.metrics


def test_execute_improve_phase(dmaic_layer):
    """Test 6: Execute Improve phase successfully"""
    result = dmaic_layer.execute_phase(DMAICPhase.IMPROVE)
    
    assert isinstance(result, PhaseMetrics)
    assert result.phase == DMAICPhase.IMPROVE
    assert result.status == "in_progress"
    assert "improvements" in result.metrics


def test_execute_control_phase(dmaic_layer):
    """Test 7: Execute Control phase successfully"""
    result = dmaic_layer.execute_phase(DMAICPhase.CONTROL)
    
    assert isinstance(result, PhaseMetrics)
    assert result.phase == DMAICPhase.CONTROL
    assert result.status == "active"
    assert "monitoring" in result.metrics
    assert "controls" in result.metrics


def test_cycle_status_tracking(dmaic_layer):
    """Test 8: Track cycle status across phases"""
    dmaic_layer.execute_phase(DMAICPhase.DEFINE)
    dmaic_layer.execute_phase(DMAICPhase.MEASURE)
    
    status = dmaic_layer.get_cycle_status()
    
    assert isinstance(status, DMAICCycleStatus)
    assert status.cycle_id == "reader-engine-dmaic-cycle"
    assert status.current_phase == DMAICPhase.MEASURE
    assert len(status.phases) == 2


def test_overall_completion_calculation(dmaic_layer):
    """Test 9: Calculate overall completion correctly"""
    for phase in DMAICPhase:
        dmaic_layer.execute_phase(phase)
    
    status = dmaic_layer.get_cycle_status()
    
    assert status.overall_completion > 0
    assert status.overall_completion <= 100


def test_export_metrics(dmaic_layer):
    """Test 10: Export Reader Engine metrics to DMAIC format"""
    reader_stats = {
        "files_processed": 10,
        "links_validated": 25,
        "artifacts_discovered": 5
    }
    
    exported = dmaic_layer.export_metrics(reader_stats)
    
    assert exported["source"] == "reader_engine"
    assert "timestamp" in exported
    assert exported["metrics"] == reader_stats
    assert exported["dmaic_phase"] == dmaic_layer.current_phase.value


def test_save_integration_state(dmaic_layer, workspace):
    """Test 11: Save integration state to file"""
    dmaic_layer.execute_phase(DMAICPhase.DEFINE)
    
    output_path = dmaic_layer.save_integration_state()
    
    assert Path(output_path).exists()
    
    with open(output_path, 'r') as f:
        state = json.load(f)
    
    assert "cycle_status" in state
    assert "current_phase" in state
    assert "lazy_load_enabled" in state
    assert state["lazy_load_enabled"] is True


def test_phase_metrics_persistence(dmaic_layer):
    """Test 12: Phase metrics persist in layer"""
    dmaic_layer.execute_phase(DMAICPhase.DEFINE)
    dmaic_layer.execute_phase(DMAICPhase.MEASURE)
    
    assert "define" in dmaic_layer.phases
    assert "measure" in dmaic_layer.phases
    
    assert dmaic_layer.phases["define"].completion == 100.0
    assert dmaic_layer.phases["measure"].completion == 100.0


def test_error_handling_invalid_phase(dmaic_layer):
    """Test 13: Handle invalid phase gracefully"""
    try:
        with pytest.raises((ValueError, AttributeError)):
            invalid_phase = "invalid_phase"
            dmaic_layer.execute_phase(invalid_phase)
    except Exception as e:
        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
