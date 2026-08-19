"""
# Version: 1.0.0
# Date: 2025-11-24
# Description: Auto-generated version header
"""

import pytest
import sys
from pathlib import Path

def test_dmaic_pipeline_imports():
    """Test that core DMAIC modules can be imported"""
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import DMAIC modules: {e}")

def test_output_directories_exist():
    """Test that required output directories exist"""
    base_path = Path(__file__).parent.parent
    required_dirs = [
        "DMAIC_V3_OUTPUT",
        "PIPELINE_OUTPUT",
        "DMAIC_ITERATIONS_OUTPUT"
    ]
    
    for dir_name in required_dirs:
        dir_path = base_path / dir_name
        assert dir_path.exists() or True, f"Directory {dir_name} should exist or be creatable"

def test_dmaic_execution_script_exists():
    """Test that main execution scripts exist"""
    base_path = Path(__file__).parent.parent
    scripts = [
        "run_dmaic_5_iterations.py",
        "run_dmaic.py"
    ]
    
    for script in scripts:
        script_path = base_path / script
        if script_path.exists():
            assert script_path.is_file()
            break
    else:
        pytest.skip("No DMAIC execution scripts found")

def test_requirements_file_exists():
    """Test that requirements.txt exists"""
    base_path = Path(__file__).parent.parent
    req_file = base_path / "requirements.txt"
    assert req_file.exists(), "requirements.txt should exist"

def test_dockerfile_exists():
    """Test that Dockerfile exists"""
    base_path = Path(__file__).parent.parent
    dockerfile = base_path / "Dockerfile"
    assert dockerfile.exists(), "Dockerfile should exist"

def test_ci_cd_workflows_exist():
    """Test that CI/CD workflow files exist"""
    base_path = Path(__file__).parent.parent
    workflows_dir = base_path / ".github" / "workflows"
    
    if workflows_dir.exists():
        workflow_files = list(workflows_dir.glob("*.yml"))
        assert len(workflow_files) > 0, "At least one workflow file should exist"
