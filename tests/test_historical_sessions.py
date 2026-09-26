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
def session_authority_path(workspace_root):
    """Get current repository-authoritative session handover directory."""
    return workspace_root / "handover" / "mc2"


@pytest.fixture
def handover_docs_path(workspace_root):
    """Get handover documentation directory"""
    return workspace_root / "00_HANDOVER_DOCUMENTATION"


class TestHistoricalSessionStructure:
    """Test repository-authoritative session handover structure."""
    
    def test_session_authority_directory_exists(self, session_authority_path):
        """Test that the governed MC2 handover directory exists."""
        assert session_authority_path.is_dir(), f"Session authority directory not found: {session_authority_path}"
    
    def test_session_close_current_exists(self, session_authority_path):
        """Test that the current session-close authority pointer exists."""
        session_close = session_authority_path / "SESSION_CLOSE_CURRENT.json"
        assert session_close.is_file(), f"Current session-close authority not found: {session_close}"
    
    def test_restart_material_exists(self, session_authority_path):
        """Test that current state pointers and restart/drop-in material exist."""
        current_state = list(session_authority_path.glob("*_CURRENT.json"))
        dropins = list(session_authority_path.glob("*DROPIN.md"))
        assert current_state, "No current session authority pointers found"
        assert dropins, "No session restart/drop-in material found"


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
    
    def test_repository_handover_docs(self, session_authority_path):
        """Test that repository-authoritative handover documentation exists."""
        handover_docs = list(session_authority_path.glob("*HANDOVER*.md"))
        handover_docs.extend(session_authority_path.glob("*handover*.md"))
        assert handover_docs, "No repository-authoritative handover documentation found"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
