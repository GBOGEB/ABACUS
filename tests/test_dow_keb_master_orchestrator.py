"""
Unit tests for DOW-KEB-MASTER Integration Orchestrator

Tests:
- DOW framework initialization
- KEB baseline configuration
- Master document parsing
- Phase execution
- Integration reporting
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from integration_DOW_KEB_MASTER.dow_keb_master_orchestrator import (
    DOWKEBMasterOrchestrator,
    DOWPhase,
    KEBArchitecture,
    MasterDocType
)


@pytest.mark.integration
@pytest.mark.dow
@pytest.mark.dmaic
class TestDOWKEBMasterOrchestrator:
    
    @pytest.fixture
    def temp_workspace(self, tmp_path):
        workspace = tmp_path / "test_workspace"
        workspace.mkdir()
        return workspace
    
    @pytest.fixture
    def mock_master_doc(self, tmp_path):
        doc_path = tmp_path / "test_master.docx"
        doc_path.touch()
        return doc_path
    
    @pytest.fixture
    def orchestrator(self, temp_workspace, mock_master_doc):
        return DOWKEBMasterOrchestrator(
            workspace_root=temp_workspace,
            master_doc_path=mock_master_doc
        )
    
    def test_initialization(self, orchestrator, temp_workspace, mock_master_doc):
        assert orchestrator.workspace_root == temp_workspace
        assert orchestrator.master_doc_path == mock_master_doc
        assert orchestrator.state["orchestrator_version"] == "1.0.0"
        assert orchestrator.state["framework"] == "DOW + KEB v6.1 + MASTER.doc"
        assert orchestrator.state["integration_status"] == "INITIALIZED"
    
    def test_initialize_dow_framework(self, orchestrator):
        dow_config = orchestrator.initialize_dow_framework()
        
        assert dow_config["framework_name"] == "DOW"
        assert dow_config["version"] == "3.0"
        assert len(dow_config["phases"]) == 8
        assert dow_config["orchestration_mode"] == "SEQUENTIAL_WITH_FEEDBACK"
        assert "dmaic_alignment" in dow_config
        assert orchestrator.state["current_phase"] == DOWPhase.INIT.value
    
    def test_initialize_keb_baseline(self, orchestrator):
        keb_baseline = orchestrator.initialize_keb_baseline()
        
        assert keb_baseline["version"] == "6.1"
        assert len(keb_baseline["architecture_tiers"]) == 4
        assert KEBArchitecture.GOD_TIER.value in keb_baseline["architecture_tiers"]
        assert KEBArchitecture.COG_TIER.value in keb_baseline["architecture_tiers"]
        assert KEBArchitecture.EXEC_TIER.value in keb_baseline["architecture_tiers"]
        assert KEBArchitecture.DATA_TIER.value in keb_baseline["architecture_tiers"]
    
    @patch('integration_DOW_KEB_MASTER.dow_keb_master_orchestrator.Document')
    def test_parse_master_document(self, mock_doc_class, orchestrator, mock_master_doc):
        mock_doc = MagicMock()
        mock_doc.paragraphs = []
        mock_doc.tables = []
        mock_doc.sections = [Mock()]
        mock_doc_class.return_value = mock_doc
        
        master_index = orchestrator.parse_master_document()
        
        assert "document_name" in master_index
        assert "statistics" in master_index
        assert "content" in master_index
    
    def test_detect_document_type_addendum(self, temp_workspace):
        doc_path = temp_workspace / "Addendum_II_Cryoplant_Requirements.docx"
        doc_path.touch()
        orchestrator = DOWKEBMasterOrchestrator(temp_workspace, doc_path)
        
        doc_type = orchestrator._detect_document_type()
        assert doc_type == MasterDocType.ADDENDUM_II_CRYOPLANT.value
    
    def test_detect_document_type_kaezer(self, temp_workspace):
        doc_path = temp_workspace / "KAEZER_HPC_Integration.docx"
        doc_path.touch()
        orchestrator = DOWKEBMasterOrchestrator(temp_workspace, doc_path)
        
        doc_type = orchestrator._detect_document_type()
        assert doc_type == MasterDocType.KAEZER_HPC.value
    
    def test_detect_document_type_generic(self, temp_workspace):
        doc_path = temp_workspace / "generic_document.docx"
        doc_path.touch()
        orchestrator = DOWKEBMasterOrchestrator(temp_workspace, doc_path)
        
        doc_type = orchestrator._detect_document_type()
        assert doc_type == MasterDocType.GENERIC.value
    
    def test_extract_heading_level(self, orchestrator):
        assert orchestrator._extract_heading_level("Heading 1") == 1
        assert orchestrator._extract_heading_level("Heading 2") == 2
        assert orchestrator._extract_heading_level("Heading3") == 3
        assert orchestrator._extract_heading_level("heading 5") == 5
    
    def test_execute_dow_phases(self, orchestrator):
        orchestrator.initialize_dow_framework()
        orchestrator.initialize_keb_baseline()
        orchestrator.state["master_doc_index"] = {"content": {"headings": [], "requirements": []}}
        
        phase_results = orchestrator.execute_dow_phases()
        
        assert len(phase_results) == 8
        assert DOWPhase.INIT.value in phase_results
        assert DOWPhase.PRE_ANALYSIS.value in phase_results
        assert DOWPhase.BRIDGE_SETUP.value in phase_results
        assert DOWPhase.RANKING.value in phase_results
        assert DOWPhase.EXECUTION.value in phase_results
        assert DOWPhase.POST_ANALYSIS.value in phase_results
        assert DOWPhase.DECISION.value in phase_results
        assert DOWPhase.INTEGRATION.value in phase_results
        
        for phase_name, result in phase_results.items():
            assert result["status"] == "completed"
            assert "timestamp" in result
    
    def test_dow_phase_init(self, orchestrator):
        result = orchestrator._dow_phase_init()
        
        assert result["status"] == "completed"
        assert "initialized" in result
        assert len(result["initialized"]) == 3
    
    def test_dow_phase_ranking(self, orchestrator):
        orchestrator.initialize_keb_baseline()
        result = orchestrator._dow_phase_ranking()
        
        assert result["status"] == "completed"
        assert "ranked_components" in result
        assert len(result["ranked_components"]) > 0
        assert result["ranked_components"][0]["score"] >= result["ranked_components"][-1]["score"]
    
    def test_integrate_kaezer_hpc(self, orchestrator):
        kaezer_integration = orchestrator.integrate_kaezer_hpc()
        
        assert kaezer_integration["status"] == "INTEGRATED"
        assert "components" in kaezer_integration
        assert len(kaezer_integration["components"]) == 4
    
    def test_generate_integration_report(self, orchestrator):
        orchestrator.initialize_dow_framework()
        orchestrator.initialize_keb_baseline()
        orchestrator.state["master_doc_index"] = {
            "document_name": "test.docx",
            "document_type": "GENERIC",
            "statistics": {"paragraphs": 10, "tables": 2},
            "content": {"headings": [], "requirements": [], "tables": [], "golden_thread": []}
        }
        orchestrator.phase_results = {DOWPhase.INIT.value: {"status": "completed"}}
        
        report_path = orchestrator.generate_integration_report()
        
        assert report_path.exists()
        assert report_path.suffix == ".md"
        assert "Integration_Report" in report_path.name
    
    def test_format_dict_as_table(self, orchestrator):
        test_dict = {"key1": "value1", "key2": "value2"}
        table = orchestrator._format_dict_as_table(test_dict)
        
        assert "| Key | Value |" in table
        assert "| key1 | value1 |" in table
        assert "| key2 | value2 |" in table
    
    @patch('integration_DOW_KEB_MASTER.dow_keb_master_orchestrator.Document')
    def test_full_integration_workflow(self, mock_doc_class, orchestrator):
        mock_doc = MagicMock()
        mock_doc.paragraphs = []
        mock_doc.tables = []
        mock_doc.sections = [Mock()]
        mock_doc_class.return_value = mock_doc
        
        report_path = orchestrator.run_full_integration()
        
        assert orchestrator.state["integration_status"] == "COMPLETED"
        assert report_path.exists()
        assert len(orchestrator.phase_results) == 8


@pytest.mark.dow
@pytest.mark.dmaic_phase_1
class TestDOWPhaseEnums:
    
    def test_dow_phase_enum_values(self):
        assert DOWPhase.INIT.value == "PHASE_0_INIT"
        assert DOWPhase.PRE_ANALYSIS.value == "PHASE_1_PRE_ANALYSIS"
        assert DOWPhase.BRIDGE_SETUP.value == "PHASE_2_BRIDGE_SETUP"
        assert DOWPhase.RANKING.value == "PHASE_3_RANKING"
        assert DOWPhase.EXECUTION.value == "PHASE_4_EXECUTION"
        assert DOWPhase.POST_ANALYSIS.value == "PHASE_5_POST_ANALYSIS"
        assert DOWPhase.DECISION.value == "PHASE_6_DECISION"
        assert DOWPhase.INTEGRATION.value == "PHASE_7_INTEGRATION"


@pytest.mark.dow
@pytest.mark.dmaic_phase_2
class TestKEBArchitectureEnums:
    
    def test_keb_architecture_enum_values(self):
        assert KEBArchitecture.GOD_TIER.value == "GODLINESS"
        assert KEBArchitecture.COG_TIER.value == "COGNITIVE"
        assert KEBArchitecture.EXEC_TIER.value == "EXECUTION"
        assert KEBArchitecture.DATA_TIER.value == "DATA"


@pytest.mark.dow
@pytest.mark.dmaic_phase_1
class TestMasterDocTypeEnums:
    
    def test_master_doc_type_enum_values(self):
        assert MasterDocType.ADDENDUM_II_CRYOPLANT.value == "Addendum II - Cryoplant Technical Requirements"
        assert MasterDocType.KAEZER_HPC.value == "KAEZER HPC Integration"
        assert MasterDocType.GENERIC.value == "Generic Master Document"
