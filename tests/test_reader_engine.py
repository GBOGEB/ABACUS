#!/usr/bin/env python3
"""
TEST SUITE: MARKDOWN READER ENGINE
===================================
Version: 1.0.0
Date: 2025-01-28

Test Coverage:
- Markdown parsing (headers, links, code blocks)
- Link validation (internal, external, broken)
- Artifact discovery (YAML, JSON, Python files)
- Statistics generation
- Configuration loading
- Error handling
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich_padding.markdown_reader_engine import (
    MarkdownReaderEngine,
    MarkdownElement,
    ElementType,
    LinkValidationResult,
    ArtifactMetadata
)


@pytest.fixture
def workspace(tmp_path):
    """Create temporary workspace"""
    workspace = tmp_path / "test_workspace"
    workspace.mkdir()
    
    (workspace / "rich_padding").mkdir()
    (workspace / "rich_padding" / "reports").mkdir(parents=True)
    (workspace / "rich_padding" / "cache").mkdir(parents=True)
    
    return workspace


@pytest.fixture
def reader(workspace):
    """Create MarkdownReaderEngine instance"""
    return MarkdownReaderEngine(workspace)


@pytest.fixture
def sample_markdown():
    """Sample markdown content"""
    return """# Test Document

## Section 1

This is a test document with [internal link](./local.md) and [external link](https://example.com).

### Code Example

```python
def hello():
    print("Hello, World!")
```

## Section 2

- Item 1
- Item 2
- [Another link](https://google.com)
"""


def test_reader_initialization(reader, workspace):
    """Test 1: Reader engine initializes correctly"""
    assert reader.workspace == workspace
    assert reader.artifact_patterns is not None
    assert len(reader.artifact_patterns) > 0


def test_parse_markdown_headers(reader, sample_markdown):
    """Test 2: Parse markdown headers correctly"""
    elements = reader.parse_markdown(sample_markdown)
    
    headers = [e for e in elements if e.element_type == ElementType.HEADER]
    assert len(headers) == 3
    assert headers[0].content == "# Test Document"
    assert headers[1].content == "## Section 1"
    assert headers[2].content == "### Code Example"


def test_parse_markdown_links(reader, sample_markdown):
    """Test 3: Parse markdown links correctly"""
    elements = reader.parse_markdown(sample_markdown)
    
    links = [e for e in elements if e.element_type == ElementType.LINK]
    assert len(links) >= 3
    
    link_texts = [e.content for e in links]
    assert "internal link" in link_texts
    assert "external link" in link_texts


def test_parse_markdown_code_blocks(reader, sample_markdown):
    """Test 4: Parse code blocks correctly"""
    elements = reader.parse_markdown(sample_markdown)
    
    code_blocks = [e for e in elements if e.element_type == ElementType.CODE_BLOCK]
    assert len(code_blocks) == 1
    assert "python" in code_blocks[0].metadata.get("language", "")
    assert "def hello():" in code_blocks[0].content


def test_validate_internal_link_exists(reader, workspace):
    """Test 5: Validate existing internal link"""
    test_file = workspace / "test.md"
    test_file.write_text("# Test")
    
    result = reader.validate_link("./test.md", workspace)
    
    assert result.valid
    assert result.link_type == "internal"


def test_validate_internal_link_missing(reader, workspace):
    """Test 6: Detect missing internal link"""
    result = reader.validate_link("./nonexistent.md", workspace)
    
    assert not result.valid
    assert result.link_type == "internal"


def test_validate_external_link(reader):
    """Test 7: Validate external link format"""
    result = reader.validate_link("https://example.com", None)
    
    assert result.link_type == "external"


def test_discover_artifacts_yaml(reader, workspace):
    """Test 8: Discover YAML artifacts"""
    yaml_file = workspace / "config.yaml"
    yaml_file.write_text("key: value\ntest: data")
    
    artifacts = reader.discover_artifacts(workspace)
    
    yaml_artifacts = [a for a in artifacts if a.artifact_type == "yaml"]
    assert len(yaml_artifacts) >= 1
    assert any("config.yaml" in a.path for a in yaml_artifacts)


def test_discover_artifacts_json(reader, workspace):
    """Test 9: Discover JSON artifacts"""
    json_file = workspace / "data.json"
    json_file.write_text('{"key": "value"}')
    
    artifacts = reader.discover_artifacts(workspace)
    
    json_artifacts = [a for a in artifacts if a.artifact_type == "json"]
    assert len(json_artifacts) >= 1


def test_discover_artifacts_python(reader, workspace):
    """Test 10: Discover Python artifacts"""
    py_file = workspace / "script.py"
    py_file.write_text('def test():\n    pass')
    
    artifacts = reader.discover_artifacts(workspace)
    
    py_artifacts = [a for a in artifacts if a.artifact_type == "python"]
    assert len(py_artifacts) >= 1


def test_generate_statistics(reader, workspace):
    """Test 11: Generate statistics correctly"""
    test_file = workspace / "test.md"
    test_file.write_text("# Test\n\n[link](./other.md)")
    
    stats = reader.generate_statistics(workspace)
    
    assert "files_processed" in stats
    assert "total_elements" in stats
    assert "elements_by_type" in stats
    assert stats["files_processed"] >= 0


def test_error_handling_invalid_markdown(reader):
    """Test 12: Handle invalid markdown gracefully"""
    invalid_md = "# Unclosed [link](incomplete"
    
    try:
        elements = reader.parse_markdown(invalid_md)
        assert isinstance(elements, list)
    except Exception as e:
        pytest.fail(f"Should handle invalid markdown gracefully, got: {e}")


def test_export_results_json(reader, workspace):
    """Test 13: Export results to JSON"""
    test_file = workspace / "test.md"
    test_file.write_text("# Test Document")
    
    elements = reader.parse_markdown(test_file.read_text())
    
    output_path = reader.export_results(
        elements=elements,
        stats={"test": "data"},
        format="json"
    )
    
    assert Path(output_path).exists()
    assert Path(output_path).suffix == ".json"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
