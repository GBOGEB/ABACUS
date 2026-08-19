#!/usr/bin/env python3
"""
Parallel Execution System Tests - Phase 2B
Version: 1.0.0
Date: 2025-12-04

Tests for the parallel execution system including config validation,
execution types (DOW/KEB/GBOGEB), knowledge bridge, and orchestration.
"""

import pytest
import yaml
from pathlib import Path
from datetime import datetime
import json
from typing import Dict, List, Any


@pytest.fixture
def parallel_config_path():
    """Path to parallel execution config"""
    return Path(__file__).parent.parent / "rich_padding" / "parallel_execution" / "parallel_execution_config.yaml"


@pytest.fixture
def parallel_config(parallel_config_path):
    """Load parallel execution config"""
    if parallel_config_path.exists():
        with open(parallel_config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return None


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace"""
    workspace = tmp_path / "parallel_execution_workspace"
    workspace.mkdir()
    return workspace


class TestParallelExecutionConfig:
    """Test parallel execution configuration"""
    
    def test_config_file_exists(self, parallel_config_path):
        """Test that parallel execution config file exists"""
        assert parallel_config_path.exists(), f"Config file not found: {parallel_config_path}"
    
    def test_config_loads_successfully(self, parallel_config):
        """Test that config loads without errors"""
        assert parallel_config is not None
        assert isinstance(parallel_config, dict)
    
    def test_config_has_execution_types(self, parallel_config):
        """Test that config defines all three execution types"""
        if parallel_config is None:
            pytest.skip("Config file not found")
        
        assert 'type_1_session_handover' in parallel_config
        assert 'type_2_persistent_ai' in parallel_config
        assert 'type_3_implementation_struct' in parallel_config
    
    def test_config_knowledge_bridge_settings(self, parallel_config):
        """Test knowledge bridge configuration"""
        if parallel_config is None:
            pytest.skip("Config file not found")
        
        assert 'knowledge_bridge' in parallel_config
        kb_config = parallel_config['knowledge_bridge']
        assert kb_config['enabled'] is True
        assert 'workspace_path' in kb_config
        assert 'state_file' in kb_config


class TestExecutionTypeDOW:
    """Test Type 1: Session Handover Integration (DOW engine)"""
    
    def test_type1_configuration(self, parallel_config):
        """Test Type 1 session handover configuration"""
        if parallel_config is None:
            pytest.skip("Config file not found")
        
        type1 = parallel_config.get('type_1_session_handover')
        assert type1 is not None
        assert type1['type_id'] == 'TYPE_1_SESSION_HANDOVER'
        assert type1['engine'] == 'DOW'
        assert type1['priority'] == 1
    
    def test_type1_integration_points(self, parallel_config):
        """Test Type 1 has required integration points"""
        if parallel_config is None:
            pytest.skip("Config file not found")
        
        type1 = parallel_config.get('type_1_session_handover')
        integration_points = type1.get('integration_points', [])
        
        assert 'WORKSPACE_MASTER_INDEX.md' in integration_points
        assert 'SESSION_TUPLE_TEMPLATE_v2.md' in integration_points
        assert '00_CANONICAL_START_HOOK.md' in integration_points
    
    def test_type1_devops_gates(self, parallel_config):
        """Test Type 1 has all required DevOps gates"""
        if parallel_config is None:
            pytest.skip("Config file not found")
        
        type1 = parallel_config.get('type_1_session_handover')
        gates = type1.get('devops_gates', [])
        
        required_gates = [
            'G1_CODE_TESTS',
            'G2_DOC_ALIGNMENT',
            'G3_CI_PIPELINE_GREEN',
            'G4_VALIDATION_CLAIMS_CHECKED',
            'G5_INTEGRATION_DOW',
            'G6_MANIFEST_COMPLETE'
        ]
        
        for gate in required_gates:
            assert gate in gates


class TestExecutionTypeKEB:
    """Test Type 2: Persistent AI Integration (KEB engine)"""
    
    def test_type2_configuration(self, parallel_config):
        """Test Type 2 persistent AI configuration"""
        if parallel_config is None:
            pytest.skip("Config file not found")
        
        type2 = parallel_config.get('type_2_persistent_ai')
        assert type2 is not None
        assert type2['type_id'] == 'TYPE_2_PERSISTENT_AI'
        assert type2['engine'] == 'KEB'
        assert type2['priority'] == 2
    
    def test_type2_knowledge_bridge_enabled(self, parallel_config):
        """Test Type 2 has knowledge bridge enabled"""
        if parallel_config is None:
            pytest.skip("Config file not found")
        
        type2 = parallel_config.get('type_2_persistent_ai')
        kb = type2.get('knowledge_bridge')
        
        assert kb is not None
        assert kb['enabled'] is True
        assert kb['sync_mode'] == 'bidirectional'
        assert kb['persistence'] is True


class TestExecutionTypeGBOGEB:
    """Test Type 3: Implementation Structure (GBOGEB engine)"""
    
    def test_type3_configuration(self, parallel_config):
        """Test Type 3 implementation structure configuration"""
        if parallel_config is None:
            pytest.skip("Config file not found")
        
        type3 = parallel_config.get('type_3_implementation_struct')
        assert type3 is not None
        assert type3['type_id'] == 'TYPE_3_IMPLEMENTATION_STRUCT'
        assert type3['engine'] == 'GBOGEB'
        assert type3['priority'] == 3
    
    def test_type3_devops_mapping(self, parallel_config):
        """Test Type 3 has DevOps lifecycle mapping"""
        if parallel_config is None:
            pytest.skip("Config file not found")
        
        type3 = parallel_config.get('type_3_implementation_struct')
        devops_mapping = type3.get('devops_mapping')
        
        assert devops_mapping is not None
        assert 'prototype' in devops_mapping
        assert 'mvp' in devops_mapping
        assert 'production' in devops_mapping


class TestKnowledgeBridge:
    """Test Knowledge Bridge functionality"""
    
    def test_knowledge_bridge_workspace_setup(self, temp_workspace):
        """Test knowledge bridge workspace initialization"""
        kb_path = temp_workspace / ".knowledge_bridge"
        kb_path.mkdir(exist_ok=True)
        
        assert kb_path.exists()
        assert kb_path.is_dir()
    
    def test_knowledge_bridge_state_persistence(self, temp_workspace):
        """Test knowledge bridge state file persistence"""
        kb_path = temp_workspace / ".knowledge_bridge"
        kb_path.mkdir(exist_ok=True)
        
        state_file = kb_path / "bridge_state.json"
        test_state = {
            "timestamp": datetime.now().isoformat(),
            "status": "active",
            "executions": []
        }
        
        with open(state_file, 'w') as f:
            json.dump(test_state, f)
        
        assert state_file.exists()
        
        with open(state_file, 'r') as f:
            loaded_state = json.load(f)
        
        assert loaded_state['status'] == 'active'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
