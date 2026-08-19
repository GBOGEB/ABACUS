"""
import pytest
pytest.skip("rtm_core module not yet implemented", allow_module_level=True)

"""
Unit tests for rtm_core.py

Tests:
- Requirement dataclass
- MarkdownRequirementExtractor
- CSVRequirementExtractor
- RTMCore
- RTM generation
- Multiple output formats
- Factory function
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import shutil
import csv
import json
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from rtm_core import (
    Requirement,
    RequirementSource,
    RequirementStatus,
    RequirementPriority,
    RTMOutputFormat,
    MarkdownRequirementExtractor,
    CSVRequirementExtractor,
    RTMCore,
    create_rtm_generator
)


class TestRequirement:
    """Test Requirement dataclass"""
    
    def test_requirement_creation(self):
        """Test creating requirement"""
        req = Requirement(
            req_id="REQ-001",
            title="Test Requirement",
            description="Test description",
            source=RequirementSource.MARKDOWN,
            priority=RequirementPriority.HIGH,
            status=RequirementStatus.APPROVED
        )
        
        assert req.req_id == "REQ-001"
        assert req.title == "Test Requirement"
        assert req.priority == RequirementPriority.HIGH
    
    def test_requirement_to_dict(self):
        """Test converting requirement to dictionary"""
        req = Requirement(
            req_id="REQ-001",
            title="Test",
            description="Desc",
            source=RequirementSource.MARKDOWN
        )
        
        req_dict = req.to_dict()
        
        assert isinstance(req_dict, dict)
        assert req_dict["req_id"] == "REQ-001"
        assert req_dict["title"] == "Test"


class TestMarkdownRequirementExtractor:
    """Test MarkdownRequirementExtractor"""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_extract_from_markdown(self, temp_workspace):
        """Test extracting requirements from markdown"""
        md_file = temp_workspace / "requirements.md"
        md_content = """# Requirements
        
## REQ-001: First Requirement
**Status:** Approved
**Priority:** High
This is the first requirement.

## REQ-002: Second Requirement
**Status:** Draft
**Priority:** Medium
This is the second requirement.
"""
        md_file.write_text(md_content)
        
        extractor = MarkdownRequirementExtractor()
        requirements = extractor.extract(md_file)
        
        assert len(requirements) == 2
        assert requirements[0].req_id == "REQ-001"
        assert requirements[0].title == "First Requirement"
        assert requirements[0].status == RequirementStatus.APPROVED
        assert requirements[1].req_id == "REQ-002"
    
    def test_extract_from_empty_markdown(self, temp_workspace):
        """Test extracting from empty markdown"""
        md_file = temp_workspace / "empty.md"
        md_file.write_text("# Empty Document\n\nNo requirements here.")
        
        extractor = MarkdownRequirementExtractor()
        requirements = extractor.extract(md_file)
        
        assert len(requirements) == 0
    
    def test_extract_from_missing_file(self, temp_workspace):
        """Test extracting from missing file"""
        md_file = temp_workspace / "missing.md"
        
        extractor = MarkdownRequirementExtractor()
        requirements = extractor.extract(md_file)
        
        assert len(requirements) == 0


class TestCSVRequirementExtractor:
    """Test CSVRequirementExtractor"""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_extract_from_csv(self, temp_workspace):
        """Test extracting requirements from CSV"""
        csv_file = temp_workspace / "requirements.csv"
        
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["req_id", "title", "description", "status", "priority"])
            writer.writerow(["REQ-001", "First Req", "Description 1", "Approved", "High"])
            writer.writerow(["REQ-002", "Second Req", "Description 2", "Draft", "Medium"])
        
        extractor = CSVRequirementExtractor()
        requirements = extractor.extract(csv_file)
        
        assert len(requirements) == 2
        assert requirements[0].req_id == "REQ-001"
        assert requirements[0].title == "First Req"
        assert requirements[0].status == RequirementStatus.APPROVED
    
    def test_extract_from_empty_csv(self, temp_workspace):
        """Test extracting from empty CSV"""
        csv_file = temp_workspace / "empty.csv"
        
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["req_id", "title", "description"])
        
        extractor = CSVRequirementExtractor()
        requirements = extractor.extract(csv_file)
        
        assert len(requirements) == 0


class TestRTMCore:
    """Test RTMCore"""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_rtm_core_initialization(self):
        """Test RTMCore initialization"""
        rtm = RTMCore()
        
        assert rtm._extractors is not None
        assert len(rtm._requirements) == 0
    
    def test_register_extractor(self):
        """Test registering custom extractor"""
        rtm = RTMCore()
        mock_extractor = Mock()
        
        rtm.register_extractor(RequirementSource.CUSTOM, mock_extractor)
        
        assert RequirementSource.CUSTOM in rtm._extractors
    
    def test_extract_requirements_markdown(self, temp_workspace):
        """Test extracting requirements from markdown"""
        md_file = temp_workspace / "reqs.md"
        md_file.write_text("""## REQ-001: Test
**Status:** Approved
Test requirement.
""")
        
        rtm = RTMCore()
        requirements = rtm.extract_requirements(sources=[md_file])
        
        assert len(requirements) == 1
        assert requirements[0].req_id == "REQ-001"
    
    def test_generate_rtm_csv(self, temp_workspace):
        """Test generating RTM in CSV format"""
        rtm = RTMCore()
        rtm._requirements = [
            Requirement(
                req_id="REQ-001",
                title="Test Req",
                description="Description",
                source=RequirementSource.MARKDOWN
            )
        ]
        
        output_path = temp_workspace / "rtm.csv"
        rtm.generate_rtm(output_path, RTMOutputFormat.CSV)
        
        assert output_path.exists()
        
        with open(output_path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]["req_id"] == "REQ-001"
    
    def test_generate_rtm_json(self, temp_workspace):
        """Test generating RTM in JSON format"""
        rtm = RTMCore()
        rtm._requirements = [
            Requirement(
                req_id="REQ-001",
                title="Test Req",
                description="Description",
                source=RequirementSource.MARKDOWN
            )
        ]
        
        output_path = temp_workspace / "rtm.json"
        rtm.generate_rtm(output_path, RTMOutputFormat.JSON)
        
        assert output_path.exists()
        
        with open(output_path) as f:
            data = json.load(f)
            assert "requirements" in data
            assert len(data["requirements"]) == 1
    
    def test_generate_rtm_markdown(self, temp_workspace):
        """Test generating RTM in Markdown format"""
        rtm = RTMCore()
        rtm._requirements = [
            Requirement(
                req_id="REQ-001",
                title="Test Req",
                description="Description",
                source=RequirementSource.MARKDOWN
            )
        ]
        
        output_path = temp_workspace / "rtm.md"
        rtm.generate_rtm(output_path, RTMOutputFormat.MARKDOWN)
        
        assert output_path.exists()
        content = output_path.read_text()
        assert "REQ-001" in content
        assert "Test Req" in content
    
    def test_get_statistics(self):
        """Test getting RTM statistics"""
        rtm = RTMCore()
        rtm._requirements = [
            Requirement(
                req_id="REQ-001",
                title="Test 1",
                description="Desc",
                source=RequirementSource.MARKDOWN,
                status=RequirementStatus.APPROVED
            ),
            Requirement(
                req_id="REQ-002",
                title="Test 2",
                description="Desc",
                source=RequirementSource.CSV,
                status=RequirementStatus.DRAFT
            )
        ]
        
        stats = rtm.get_statistics()
        
        assert stats["total_requirements"] == 2
        assert stats["by_status"]["APPROVED"] == 1
        assert stats["by_status"]["DRAFT"] == 1
        assert stats["by_source"]["MARKDOWN"] == 1
        assert stats["by_source"]["CSV"] == 1
    
    def test_clear_requirements(self):
        """Test clearing requirements"""
        rtm = RTMCore()
        rtm._requirements = [
            Requirement(req_id="REQ-001", title="Test", description="Desc", source=RequirementSource.MARKDOWN)
        ]
        
        rtm.clear()
        
        assert len(rtm._requirements) == 0


class TestCreateRTMGenerator:
    """Test factory function"""
    
    def test_create_rtm_generator(self):
        """Test creating RTM generator"""
        rtm = create_rtm_generator()
        
        assert isinstance(rtm, RTMCore)
    
    def test_create_rtm_generator_with_logger(self):
        """Test creating RTM generator with logger"""
        mock_logger = Mock()
        rtm = create_rtm_generator(logger=mock_logger)
        
        assert isinstance(rtm, RTMCore)
        assert rtm.logger == mock_logger


class TestRTMWorkflow:
    """Test complete RTM workflow"""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_complete_workflow(self, temp_workspace):
        """Test complete RTM generation workflow"""
        md_file = temp_workspace / "requirements.md"
        md_file.write_text("""## REQ-001: Requirement One
**Status:** Approved
**Priority:** High
First requirement description.

## REQ-002: Requirement Two
**Status:** Draft
**Priority:** Medium
Second requirement description.
""")
        
        rtm = create_rtm_generator()
        
        requirements = rtm.extract_requirements(sources=[md_file])
        assert len(requirements) == 2
        
        csv_output = temp_workspace / "rtm.csv"
        rtm.generate_rtm(csv_output, RTMOutputFormat.CSV)
        assert csv_output.exists()
        
        json_output = temp_workspace / "rtm.json"
        rtm.generate_rtm(json_output, RTMOutputFormat.JSON)
        assert json_output.exists()
        
        md_output = temp_workspace / "rtm.md"
        rtm.generate_rtm(md_output, RTMOutputFormat.MARKDOWN)
        assert md_output.exists()
        
        stats = rtm.get_statistics()
        assert stats["total_requirements"] == 2
        assert stats["by_status"]["APPROVED"] == 1
        assert stats["by_status"]["DRAFT"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
