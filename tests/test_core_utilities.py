"""
Unit tests for core_utilities.py

Tests:
- WorkspaceUtilities: config loading, JSON/YAML operations
- PathUtilities: file scanning, path operations
- LoggingUtilities: logger creation and configuration
- MetricsUtilities: metrics creation and finalization
- TemporalContext: temporal context handling
"""

import pytest
import json
import yaml
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, mock_open
import tempfile
import shutil

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core_utilities import (
    WorkspaceUtilities,
    PathUtilities,
    LoggingUtilities,
    MetricsUtilities,
    TemporalContext,
    get_logger
)


class TestWorkspaceUtilities:
    """Test WorkspaceUtilities class"""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for testing"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_load_config_json(self, temp_workspace):
        """Test loading JSON config"""
        config_path = temp_workspace / "config.json"
        config_data = {"key": "value", "number": 42}
        
        with open(config_path, 'w') as f:
            json.dump(config_data, f)
        
        loaded = WorkspaceUtilities.load_config(config_path)
        assert loaded == config_data
    
    def test_load_config_yaml(self, temp_workspace):
        """Test loading YAML config"""
        config_path = temp_workspace / "config.yaml"
        config_data = {"key": "value", "list": [1, 2, 3]}
        
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)
        
        loaded = WorkspaceUtilities.load_config(config_path)
        assert loaded == config_data
    
    def test_load_config_missing_file(self, temp_workspace):
        """Test loading missing config returns empty dict"""
        config_path = temp_workspace / "missing.yaml"
        loaded = WorkspaceUtilities.load_config(config_path)
        assert loaded == {}
    
    def test_save_json(self, temp_workspace):
        """Test saving JSON data"""
        output_path = temp_workspace / "output.json"
        data = {"test": "data", "number": 123}
        
        WorkspaceUtilities.save_json(data, output_path)
        
        assert output_path.exists()
        with open(output_path) as f:
            loaded = json.load(f)
        assert loaded == data
    
    def test_save_yaml(self, temp_workspace):
        """Test saving YAML data"""
        output_path = temp_workspace / "output.yaml"
        data = {"test": "data", "list": [1, 2, 3]}
        
        WorkspaceUtilities.save_yaml(data, output_path)
        
        assert output_path.exists()
        with open(output_path) as f:
            loaded = yaml.safe_load(f)
        assert loaded == data
    
    def test_save_text(self, temp_workspace):
        """Test saving text file"""
        output_path = temp_workspace / "output.txt"
        content = "Test content\nLine 2"
        
        WorkspaceUtilities.save_text(content, output_path)
        
        assert output_path.exists()
        assert output_path.read_text() == content
    
    def test_to_json(self):
        """Test JSON string conversion"""
        data = {"key": "value"}
        json_str = WorkspaceUtilities.to_json(data)
        assert "key" in json_str
        assert "value" in json_str
    
    def test_get_temporal_context(self):
        """Test temporal context extraction"""
        context = WorkspaceUtilities.get_temporal_context()
        
        assert isinstance(context, TemporalContext)
        assert context.session_id is not None
        assert context.timestamp is not None
        assert context.dow is not None
        assert context.week_number > 0
        assert context.year >= 2024


class TestPathUtilities:
    """Test PathUtilities class"""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace with test files"""
        temp_dir = Path(tempfile.mkdtemp())
        
        (temp_dir / "file1.py").write_text("# Python file")
        (temp_dir / "file2.md").write_text("# Markdown")
        (temp_dir / "file3.txt").write_text("Text file")
        
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        (subdir / "nested.py").write_text("# Nested")
        
        excluded = temp_dir / "__pycache__"
        excluded.mkdir()
        (excluded / "cache.py").write_text("# Cache")
        
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_scan_files_single_pattern(self, temp_workspace):
        """Test scanning files with single pattern"""
        files = PathUtilities.scan_files(
            root=temp_workspace,
            patterns=["*.py"],
            recursive=False
        )
        
        file_names = [f.name for f in files]
        assert "file1.py" in file_names
        assert "file2.md" not in file_names
    
    def test_scan_files_multiple_patterns(self, temp_workspace):
        """Test scanning files with multiple patterns"""
        files = PathUtilities.scan_files(
            root=temp_workspace,
            patterns=["*.py", "*.md"],
            recursive=False
        )
        
        file_names = [f.name for f in files]
        assert "file1.py" in file_names
        assert "file2.md" in file_names
        assert "file3.txt" not in file_names
    
    def test_scan_files_recursive(self, temp_workspace):
        """Test recursive file scanning"""
        files = PathUtilities.scan_files(
            root=temp_workspace,
            patterns=["*.py"],
            recursive=True
        )
        
        file_names = [f.name for f in files]
        assert "file1.py" in file_names
        assert "nested.py" in file_names
    
    def test_scan_files_exclude_dirs(self, temp_workspace):
        """Test excluding directories"""
        files = PathUtilities.scan_files(
            root=temp_workspace,
            patterns=["*.py"],
            recursive=True,
            exclude_dirs=["__pycache__"]
        )
        
        file_names = [f.name for f in files]
        assert "cache.py" not in file_names
    
    def test_ensure_dir(self, temp_workspace):
        """Test directory creation"""
        new_dir = temp_workspace / "new" / "nested" / "dir"
        
        PathUtilities.ensure_dir(new_dir)
        
        assert new_dir.exists()
        assert new_dir.is_dir()


class TestLoggingUtilities:
    """Test LoggingUtilities class"""
    
    def test_setup_logger_basic(self):
        """Test basic logger setup"""
        logger = LoggingUtilities.setup_logger("test_logger")
        
        assert logger.name == "test_logger"
        assert logger.level > 0
    
    def test_setup_logger_with_session(self):
        """Test logger with session ID"""
        logger = LoggingUtilities.setup_logger(
            "test_logger_session",
            session_id="test_session_123"
        )
        
        assert logger.name == "test_logger_session"
    
    def test_get_logger(self):
        """Test convenience get_logger function"""
        logger = get_logger("convenience_test")
        
        assert logger.name == "convenience_test"


class TestMetricsUtilities:
    """Test MetricsUtilities class"""
    
    def test_create_metrics_dict(self):
        """Test metrics dictionary creation"""
        metrics = MetricsUtilities.create_metrics_dict(
            component_name="test_component",
            session_id="test_session",
            version="1.0.0"
        )
        
        assert metrics["component"] == "test_component"
        assert metrics["session_id"] == "test_session"
        assert metrics["version"] == "1.0.0"
        assert "timestamp" in metrics
        assert "operations" in metrics
        assert "errors" in metrics
    
    def test_finalize_metrics(self):
        """Test metrics finalization"""
        metrics = MetricsUtilities.create_metrics_dict("test", "session")
        
        metrics["operations"].append({"op": "test", "count": 10})
        metrics["errors"].append("Error 1")
        
        finalized = MetricsUtilities.finalize_metrics(metrics)
        
        assert "end_timestamp" in finalized
        assert "total_operations" in finalized
        assert "total_errors" in finalized
        assert finalized["total_operations"] == 1
        assert finalized["total_errors"] == 1


class TestTemporalContext:
    """Test TemporalContext dataclass"""
    
    def test_temporal_context_creation(self):
        """Test creating temporal context"""
        context = TemporalContext(
            session_id="test_session",
            timestamp=datetime.now(),
            dow="Monday",
            week_number=50,
            year=2024
        )
        
        assert context.session_id == "test_session"
        assert context.dow == "Monday"
        assert context.week_number == 50
        assert context.year == 2024


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
