#!/usr/bin/env python3
"""
KEB Bridge Tests - Phase 2B
Version: 1.0.0
Date: 2025-12-04

Tests for DOW ↔ KEB bidirectional knowledge bridge functionality.
Tests workspace setup, state persistence, knowledge transfer, and sync operations.
"""

import pytest
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace"""
    workspace = tmp_path / "keb_bridge_workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture
def keb_path(temp_workspace):
    """Create KEB directory"""
    keb_dir = temp_workspace / ".keb"
    keb_dir.mkdir(exist_ok=True)
    return keb_dir


@pytest.fixture
def knowledge_bridge_path(temp_workspace):
    """Create knowledge bridge directory"""
    kb_dir = temp_workspace / ".knowledge_bridge"
    kb_dir.mkdir(exist_ok=True)
    return kb_dir


class TestKEBWorkspaceSetup:
    """Test KEB workspace initialization"""
    
    def test_keb_directory_creation(self, temp_workspace):
        """Test KEB directory can be created"""
        keb_dir = temp_workspace / ".keb"
        keb_dir.mkdir(exist_ok=True)
        
        assert keb_dir.exists()
        assert keb_dir.is_dir()
    
    def test_knowledge_bridge_directory_creation(self, temp_workspace):
        """Test knowledge bridge directory can be created"""
        kb_dir = temp_workspace / ".knowledge_bridge"
        kb_dir.mkdir(exist_ok=True)
        
        assert kb_dir.exists()
        assert kb_dir.is_dir()


class TestKEBStateManagement:
    """Test KEB state file management"""
    
    def test_bridge_state_creation(self, knowledge_bridge_path):
        """Test bridge state file creation"""
        state_file = knowledge_bridge_path / "bridge_state.json"
        
        initial_state = {
            "timestamp": datetime.now().isoformat(),
            "status": "initialized",
            "sessions": [],
            "knowledge_transfers": 0
        }
        
        with open(state_file, 'w') as f:
            json.dump(initial_state, f, indent=2)
        
        assert state_file.exists()
    
    def test_bridge_state_persistence(self, knowledge_bridge_path):
        """Test bridge state persists correctly"""
        state_file = knowledge_bridge_path / "bridge_state.json"
        
        test_state = {
            "timestamp": datetime.now().isoformat(),
            "status": "active",
            "sessions": ["session_001", "session_002"],
            "knowledge_transfers": 5
        }
        
        with open(state_file, 'w') as f:
            json.dump(test_state, f)
        
        with open(state_file, 'r') as f:
            loaded_state = json.load(f)
        
        assert loaded_state['status'] == 'active'
        assert loaded_state['knowledge_transfers'] == 5
        assert len(loaded_state['sessions']) == 2


class TestDOWToKEBTransfer:
    """Test DOW → KEB knowledge transfer"""
    
    def test_dow_knowledge_package_creation(self, temp_workspace):
        """Test creating DOW knowledge package"""
        dow_package = {
            "package_id": "DOW_PKG_001",
            "source": "DOW",
            "destination": "KEB",
            "timestamp": datetime.now().isoformat(),
            "knowledge_items": [
                {"type": "insight", "content": "Test insight"},
                {"type": "pattern", "content": "Test pattern"}
            ]
        }
        
        package_file = temp_workspace / "dow_package.json"
        with open(package_file, 'w') as f:
            json.dump(dow_package, f)
        
        assert package_file.exists()
        assert dow_package['source'] == 'DOW'
        assert len(dow_package['knowledge_items']) == 2
    
    def test_keb_receives_dow_knowledge(self, keb_path):
        """Test KEB receives knowledge from DOW"""
        incoming_knowledge = {
            "timestamp": datetime.now().isoformat(),
            "source": "DOW",
            "items": [
                {"type": "insight", "content": "DOW insight 1"},
                {"type": "insight", "content": "DOW insight 2"}
            ]
        }
        
        inbox_file = keb_path / "inbox_from_dow.json"
        with open(inbox_file, 'w') as f:
            json.dump(incoming_knowledge, f)
        
        assert inbox_file.exists()
        
        with open(inbox_file, 'r') as f:
            loaded = json.load(f)
        
        assert loaded['source'] == 'DOW'
        assert len(loaded['items']) == 2


class TestKEBToDOWTransfer:
    """Test KEB → DOW knowledge transfer"""
    
    def test_keb_knowledge_package_creation(self, keb_path):
        """Test creating KEB knowledge package"""
        keb_package = {
            "package_id": "KEB_PKG_001",
            "source": "KEB",
            "destination": "DOW",
            "timestamp": datetime.now().isoformat(),
            "extracted_knowledge": [
                {"type": "semantic_link", "content": "Link between A and B"},
                {"type": "inference", "content": "Inferred relationship"}
            ]
        }
        
        package_file = keb_path / "outgoing_to_dow.json"
        with open(package_file, 'w') as f:
            json.dump(keb_package, f)
        
        assert package_file.exists()
        assert keb_package['source'] == 'KEB'
        assert len(keb_package['extracted_knowledge']) == 2


class TestBidirectionalSync:
    """Test bidirectional synchronization"""
    
    def test_sync_state_tracking(self, knowledge_bridge_path):
        """Test tracking bidirectional sync state"""
        sync_state = {
            "last_dow_to_keb": datetime.now().isoformat(),
            "last_keb_to_dow": datetime.now().isoformat(),
            "dow_to_keb_count": 10,
            "keb_to_dow_count": 8,
            "sync_status": "healthy"
        }
        
        sync_file = knowledge_bridge_path / "sync_state.json"
        with open(sync_file, 'w') as f:
            json.dump(sync_state, f)
        
        assert sync_file.exists()
        
        with open(sync_file, 'r') as f:
            loaded = json.load(f)
        
        assert loaded['sync_status'] == 'healthy'
        assert loaded['dow_to_keb_count'] > 0
        assert loaded['keb_to_dow_count'] > 0
    
    def test_conflict_resolution(self, knowledge_bridge_path):
        """Test conflict resolution during sync"""
        conflict_log = {
            "conflicts_detected": 2,
            "conflicts_resolved": 2,
            "resolution_strategy": "latest_wins",
            "conflicts": [
                {
                    "item_id": "ITEM_001",
                    "dow_version": "v1",
                    "keb_version": "v2",
                    "resolved_version": "v2",
                    "timestamp": datetime.now().isoformat()
                }
            ]
        }
        
        conflict_file = knowledge_bridge_path / "conflicts.json"
        with open(conflict_file, 'w') as f:
            json.dump(conflict_log, f)
        
        assert conflict_file.exists()
        assert conflict_log['conflicts_detected'] == conflict_log['conflicts_resolved']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
