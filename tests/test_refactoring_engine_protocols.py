"""
Unit tests for refactoring_engine_protocols.py

Tests:
- RefactoringEngine protocol
- RefactoringResult dataclass
- BaseRefactoringEngine
- DOWRefactorEngineAdapter
- CanonicalRefactoringEngineAdapter
- RefactoringEngineFactory
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from refactoring_engine_protocols import (
    RefactoringEngine,
    RefactoringResult,
    BaseRefactoringEngine,
    DOWRefactorEngineAdapter,
    CanonicalRefactoringEngineAdapter,
    RefactoringEngineFactory
)


class TestRefactoringResult:
    """Test RefactoringResult dataclass"""
    
    def test_result_creation(self):
        """Test creating refactoring result"""
        result = RefactoringResult(
            engine_name="test_engine",
            status="success",
            execution_time=1.5,
            artifacts=[Path("artifact1.txt")],
            metrics={"count": 10},
            errors=[],
            warnings=["Warning 1"],
            metadata={"version": "1.0"}
        )
        
        assert result.engine_name == "test_engine"
        assert result.status == "success"
        assert result.execution_time == 1.5
        assert len(result.artifacts) == 1
        assert result.metrics["count"] == 10
        assert len(result.warnings) == 1
    
    def test_result_to_dict(self):
        """Test converting result to dictionary"""
        result = RefactoringResult(
            engine_name="test",
            status="success",
            execution_time=1.0,
            artifacts=[],
            metrics={},
            errors=[],
            warnings=[],
            metadata={}
        )
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict["engine_name"] == "test"
        assert result_dict["status"] == "success"


class TestBaseRefactoringEngine:
    """Test BaseRefactoringEngine implementation"""
    
    def test_base_engine_initialization(self):
        """Test base engine initialization"""
        engine = BaseRefactoringEngine()
        
        assert engine.name == "BaseRefactoringEngine"
        assert engine.workspace_root is None
        assert engine.config == {}
        assert engine.logger is None
        assert engine._initialized is False
    
    def test_base_engine_initialize(self):
        """Test engine initialization"""
        engine = BaseRefactoringEngine()
        workspace = Path(".")
        config = {"key": "value"}
        
        result = engine.initialize(workspace, config)
        
        assert result is True
        assert engine.workspace_root == workspace
        assert engine.config == config
        assert engine._initialized is True
    
    def test_base_engine_validate_before_init(self):
        """Test validation before initialization"""
        engine = BaseRefactoringEngine()
        
        result = engine.validate()
        
        assert result is False
    
    def test_base_engine_validate_after_init(self):
        """Test validation after initialization"""
        engine = BaseRefactoringEngine()
        engine.initialize(Path("."), {})
        
        result = engine.validate()
        
        assert result is True
    
    def test_base_engine_get_status(self):
        """Test getting engine status"""
        engine = BaseRefactoringEngine()
        
        status = engine.get_status()
        
        assert isinstance(status, dict)
        assert "initialized" in status
        assert "workspace_root" in status


class TestDOWRefactorEngineAdapter:
    """Test DOWRefactorEngineAdapter"""
    
    @patch('refactoring_engine_protocols.DOWRefactorMaster')
    def test_adapter_initialization(self, mock_dow):
        """Test adapter initialization"""
        adapter = DOWRefactorEngineAdapter()
        
        assert adapter.name == "DOWRefactorEngine"
        assert adapter._dow_master is None
    
    @patch('refactoring_engine_protocols.DOWRefactorMaster')
    def test_adapter_initialize(self, mock_dow):
        """Test adapter initialize method"""
        adapter = DOWRefactorEngineAdapter()
        workspace = Path(".")
        config = {"auto_iterate": False}
        
        result = adapter.initialize(workspace, config)
        
        assert result is True
        assert adapter.workspace_root == workspace
    
    @patch('refactoring_engine_protocols.DOWRefactorMaster')
    def test_adapter_execute(self, mock_dow):
        """Test adapter execute method"""
        mock_instance = MagicMock()
        mock_instance.state.current_phase.value = "COMPLETED"
        mock_instance.state.operations = [1, 2, 3]
        mock_instance.state.iterations = 1
        mock_dow.return_value = mock_instance
        
        adapter = DOWRefactorEngineAdapter()
        adapter.initialize(Path("."), {})
        
        result = adapter.execute()
        
        assert isinstance(result, RefactoringResult)
        assert result.engine_name == "DOWRefactorEngine"
        mock_instance.execute_full_cycle.assert_called_once()
    
    @patch('refactoring_engine_protocols.DOWRefactorMaster')
    def test_adapter_execute_error(self, mock_dow):
        """Test adapter execute with error"""
        mock_instance = MagicMock()
        mock_instance.execute_full_cycle.side_effect = Exception("Test error")
        mock_dow.return_value = mock_instance
        
        adapter = DOWRefactorEngineAdapter()
        adapter.initialize(Path("."), {})
        
        result = adapter.execute()
        
        assert result.status == "error"
        assert len(result.errors) > 0


class TestCanonicalRefactoringEngineAdapter:
    """Test CanonicalRefactoringEngineAdapter"""
    
    @patch('refactoring_engine_protocols.CanonicalDocumentRefactorer')
    def test_adapter_initialization(self, mock_canonical):
        """Test adapter initialization"""
        adapter = CanonicalRefactoringEngineAdapter()
        
        assert adapter.name == "CanonicalRefactoringEngine"
        assert adapter._canonical_refactorer is None
    
    @patch('refactoring_engine_protocols.CanonicalDocumentRefactorer')
    def test_adapter_initialize(self, mock_canonical):
        """Test adapter initialize method"""
        adapter = CanonicalRefactoringEngineAdapter()
        workspace = Path(".")
        
        result = adapter.initialize(workspace, {})
        
        assert result is True
        assert adapter.workspace_root == workspace
    
    @patch('refactoring_engine_protocols.CanonicalDocumentRefactorer')
    @patch('refactoring_engine_protocols.PathUtilities')
    def test_adapter_execute(self, mock_path_utils, mock_canonical):
        """Test adapter execute method"""
        mock_instance = MagicMock()
        mock_canonical.return_value = mock_instance
        mock_path_utils.scan_files.return_value = [Path("doc1.md"), Path("doc2.md")]
        
        adapter = CanonicalRefactoringEngineAdapter()
        adapter.initialize(Path("."), {})
        
        result = adapter.execute()
        
        assert isinstance(result, RefactoringResult)
        assert result.engine_name == "CanonicalRefactoringEngine"
        assert mock_instance.reconcile_document.call_count == 2


class TestRefactoringEngineFactory:
    """Test RefactoringEngineFactory"""
    
    @patch('refactoring_engine_protocols.DOWRefactorMaster')
    def test_factory_create_dow_engine(self, mock_dow):
        """Test creating DOW engine"""
        engine = RefactoringEngineFactory.create_engine(
            engine_type="dow",
            workspace_root=Path("."),
            config={}
        )
        
        assert isinstance(engine, DOWRefactorEngineAdapter)
        assert engine.workspace_root == Path(".")
    
    @patch('refactoring_engine_protocols.CanonicalDocumentRefactorer')
    def test_factory_create_canonical_engine(self, mock_canonical):
        """Test creating canonical engine"""
        engine = RefactoringEngineFactory.create_engine(
            engine_type="canonical",
            workspace_root=Path("."),
            config={}
        )
        
        assert isinstance(engine, CanonicalRefactoringEngineAdapter)
        assert engine.workspace_root == Path(".")
    
    def test_factory_invalid_engine_type(self):
        """Test creating engine with invalid type"""
        with pytest.raises(ValueError):
            RefactoringEngineFactory.create_engine(
                engine_type="invalid_type",
                workspace_root=Path(".")
            )
    
    @patch('refactoring_engine_protocols.DOWRefactorMaster')
    @patch('refactoring_engine_protocols.CanonicalDocumentRefactorer')
    def test_factory_create_multiple_engines(self, mock_canonical, mock_dow):
        """Test creating multiple engines"""
        engines = RefactoringEngineFactory.create_engines(
            engine_types=["dow", "canonical"],
            workspace_root=Path("."),
            config={}
        )
        
        assert len(engines) == 2
        assert isinstance(engines[0], DOWRefactorEngineAdapter)
        assert isinstance(engines[1], CanonicalRefactoringEngineAdapter)
    
    @patch('refactoring_engine_protocols.DOWRefactorMaster')
    def test_factory_with_logger(self, mock_dow):
        """Test factory with logger dependency injection"""
        mock_logger = Mock()
        
        engine = RefactoringEngineFactory.create_engine(
            engine_type="dow",
            workspace_root=Path("."),
            logger=mock_logger
        )
        
        assert engine.logger == mock_logger


class TestProtocolCompliance:
    """Test protocol compliance"""
    
    def test_dow_adapter_implements_protocol(self):
        """Test DOW adapter implements RefactoringEngine protocol"""
        adapter = DOWRefactorEngineAdapter()
        
        assert hasattr(adapter, 'initialize')
        assert hasattr(adapter, 'execute')
        assert hasattr(adapter, 'validate')
        assert hasattr(adapter, 'get_status')
        assert hasattr(adapter, 'cleanup')
    
    def test_canonical_adapter_implements_protocol(self):
        """Test canonical adapter implements RefactoringEngine protocol"""
        adapter = CanonicalRefactoringEngineAdapter()
        
        assert hasattr(adapter, 'initialize')
        assert hasattr(adapter, 'execute')
        assert hasattr(adapter, 'validate')
        assert hasattr(adapter, 'get_status')
        assert hasattr(adapter, 'cleanup')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
