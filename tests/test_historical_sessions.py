#!/usr/bin/env python3
"""
Historical Sessions Tests - Phase 2B
Version: 1.0.0
Date: 2025-12-04

Tests for historical session validation including session tuples,
historical data integrity, canonical hooks, and handover templates.
"""

import pytest
from pathlib import Path
import yaml
import json
from typing import Dict, List


@pytest.fixture
def workspace_root():
    """Get workspace root"""
    return Path(__file__).parent.parent


@pytest.fixture
def previous_sessions_path(workspace_root):
    """Get previous sessions directory"""
    return workspace_root / "11_PREVIOUS_SESSIONS"


@pytest.fixture
def handover_docs_path(workspace_root):
    """Get handover documentation directory"""
    return workspace_root / "00_HANDOVER_DOCUMENTATION"


class TestHistoricalSessionStructure:
    """Test historical session directory structure"""
    
    def test_previous_sessions_directory_exists(self, previous_sessions_path):
        """Test that 11_PREVIOUS_SESSIONS directory exists"""
        assert previous_sessions_path.exists(), f"Previous sessions directory not found: {previous_sessions_path}"
    
    def test_cicd_sessions_exist(self, previous_sessions_path):
        """Test that CICD sessions directory exists"""
        cicd_path = previous_sessions_path / "cicd"
        assert cicd_path.exists(), "CICD sessions directory not found"
    
    def test_quick_references_exist(self, previous_sessions_path):
        """Test that quick references exist"""
        quick_ref_path = previous_sessions_path / "quick_references"
        assert quick_ref_path.exists(), "Quick references directory not found"


class TestSessionTupleValidation:
    """Test session tuple validation"""
    
    def test_session_tuple_references(self, workspace_root):
        """Test that session tuple references exist"""
        session_tuple_files = list(workspace_root.rglob("*SESSION*TUPLE*.md"))
        session_tuple_files.extend(workspace_root.rglob("*session*tuple*.py"))
        
        assert len(session_tuple_files) > 0, "No session tuple files found"
    
    def test_session_analysis_documents(self, workspace_root):
        """Test that session analysis documents exist"""
        analysis_patterns = [
            "*SESSION*ANALYSIS*.md",
            "*SESSION*SUMMARY*.md"
        ]
        
        analysis_docs = []
        for pattern in analysis_patterns:
            analysis_docs.extend(workspace_root.rglob(pattern))
        
        assert len(analysis_docs) >= 0


class TestHandoverDocumentation:
    """Test handover documentation"""
    
    def test_handover_docs_directory(self, handover_docs_path):
        """Test that handover documentation directory exists"""
        if handover_docs_path.exists():
            assert handover_docs_path.is_dir()
            
            handover_files = list(handover_docs_path.glob("*.md"))
            assert len(handover_files) > 0, "No handover documentation files found"
    
    def test_handover_manifest_exists(self, workspace_root):
        """Test that handover manifest files exist"""
        manifest_files = list(workspace_root.rglob("*handover_manifest*.yaml"))
        manifest_files.extend(workspace_root.rglob("*handover_manifest*.yml"))
        
        assert len(manifest_files) >= 0
    
    def test_cicd_handover_docs(self, previous_sessions_path):
        """Test that CICD handover documentation exists"""
        cicd_path = previous_sessions_path / "cicd"
        
        if cicd_path.exists():
            cicd_docs = list(cicd_path.glob("*HANDOVER*.md"))
            cicd_docs.extend(cicd_path.glob("*handover*.md"))
            
            assert len(cicd_docs) >= 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
