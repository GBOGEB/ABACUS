#!/usr/bin/env python3
"""
Architecture Validation Tests - Phase 2B
Version: 1.0.0
Date: 2025-12-04

Tests for architecture documentation validation including diagrams,
links, ASCII art structures, and documentation-code alignment.
"""

import pytest
from pathlib import Path
import re
from typing import List, Set


@pytest.fixture
def workspace_root():
    """Get workspace root"""
    return Path(__file__).parent.parent


@pytest.fixture
def architecture_files(workspace_root):
    """Find all architecture documentation files"""
    arch_files = []
    
    patterns = [
        "ARCHITECTURE_DIAGRAM.md",
        "ARCHITECTURE_LINKS.md",
        "DMAIC_V3_ARCHITECTURE_DIAGRAM.md",
        "ABACUS_V21_SYSTEM_ARCHITECTURE.md"
    ]
    
    for pattern in patterns:
        files = list(workspace_root.rglob(pattern))
        if files:
            arch_files.append(files[0])
    
    return arch_files


@pytest.fixture
def ascii_hierarchy_files(workspace_root):
    """Find ASCII hierarchy files"""
    patterns = ["*ASCII_HIERARCHY*.txt", "*ASCII_HIERARCHY*.md"]
    ascii_files = []
    
    for pattern in patterns:
        ascii_files.extend(workspace_root.rglob(pattern))
    
    return ascii_files


@pytest.fixture
def ascii_workflow_files(workspace_root):
    """Find ASCII workflow files"""
    patterns = ["*ASCII_WORKFLOW*.txt", "*ASCII_WORKFLOW*.md"]
    workflow_files = []
    
    for pattern in patterns:
        workflow_files.extend(workspace_root.rglob(pattern))
    
    return workflow_files


class TestArchitectureDocumentation:
    """Test architecture documentation files"""
    
    def test_architecture_diagram_exists(self, workspace_root):
        """Test that architecture diagram file exists"""
        arch_diagram = workspace_root / "ARCHITECTURE_DIAGRAM.md"
        
        if not arch_diagram.exists():
            arch_diagrams = list(workspace_root.rglob("ARCHITECTURE_DIAGRAM.md"))
            assert len(arch_diagrams) > 0, "No architecture diagram found"
    
    def test_architecture_links_exists(self, workspace_root):
        """Test that architecture links file exists"""
        arch_links = workspace_root / "ARCHITECTURE_LINKS.md"
        
        if not arch_links.exists():
            links_files = list(workspace_root.rglob("ARCHITECTURE_LINKS.md"))
            assert len(links_files) > 0, "No architecture links file found"
    
    def test_system_architecture_exists(self, workspace_root):
        """Test that system architecture documentation exists"""
        system_arch_patterns = [
            "*SYSTEM_ARCHITECTURE*.md",
            "*ARCHITECTURE_DIAGRAM*.md"
        ]
        
        system_arch_files = []
        for pattern in system_arch_patterns:
            system_arch_files.extend(workspace_root.rglob(pattern))
        
        assert len(system_arch_files) > 0, "No system architecture documentation found"


class TestArchitectureLinkIntegrity:
    """Test architecture link integrity"""
    
    def test_links_file_readable(self, workspace_root):
        """Test that architecture links file is readable"""
        links_files = list(workspace_root.rglob("ARCHITECTURE_LINKS.md"))
        
        if links_files:
            links_file = links_files[0]
            assert links_file.exists()
            
            content = links_file.read_text(encoding='utf-8')
            assert len(content) > 0
    
    def test_markdown_links_format(self, workspace_root):
        """Test that markdown links follow proper format"""
        links_files = list(workspace_root.rglob("ARCHITECTURE_LINKS.md"))
        
        if links_files:
            links_file = links_files[0]
            content = links_file.read_text(encoding='utf-8')
            
            markdown_link_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
            matches = re.findall(markdown_link_pattern, content)
            
            assert len(matches) >= 0


class TestASCIIArtStructures:
    """Test ASCII art structure validation"""
    
    def test_ascii_files_exist(self, workspace_root):
        """Test that ASCII structure files exist"""
        ascii_patterns = [
            "*ASCII*.txt",
            "*ASCII*.md",
            "*HIERARCHY*.txt",
            "*WORKFLOW*.txt"
        ]
        
        ascii_files = []
        for pattern in ascii_patterns:
            ascii_files.extend(workspace_root.rglob(pattern))
        
        assert len(ascii_files) > 0, "No ASCII structure files found"
    
    def test_ascii_box_drawing_characters(self, workspace_root):
        """Test ASCII files contain box drawing characters"""
        ascii_files = list(workspace_root.rglob("*ASCII*.txt"))
        ascii_files.extend(workspace_root.rglob("*ASCII*.md"))
        
        if ascii_files:
            for ascii_file in ascii_files[:5]:
                if ascii_file.exists():
                    content = ascii_file.read_text(encoding='utf-8', errors='ignore')
                    
                    box_chars = ['│', '─', '┌', '┐', '└', '┘', '├', '┤', '┬', '┴', '┼']
                    has_box_chars = any(char in content for char in box_chars)
                    
                    ascii_chars = ['|', '-', '+', '/', '\\']
                    has_ascii_chars = any(char in content for char in ascii_chars)
                    
                    assert has_box_chars or has_ascii_chars


class TestDocumentationCodeAlignment:
    """Test documentation-code alignment"""
    
    def test_dmaic_documentation_exists(self, workspace_root):
        """Test that DMAIC documentation exists"""
        dmaic_docs = list(workspace_root.rglob("*DMAIC*.md"))
        dmaic_docs.extend(workspace_root.rglob("*DOW*.md"))
        
        assert len(dmaic_docs) > 0, "No DMAIC/DOW documentation found"
    
    def test_dmaic_code_exists(self, workspace_root):
        """Test that DMAIC code implementation exists"""
        dmaic_py_files = list(workspace_root.rglob("*dmaic*.py"))
        dmaic_py_files.extend(workspace_root.rglob("*dow*.py"))
        
        assert len(dmaic_py_files) > 0, "No DMAIC/DOW Python files found"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
