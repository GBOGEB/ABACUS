"""Shared test fixtures for GBOGEB/ABACUS test suite."""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_dir():
    """Create a temporary directory for test artifacts."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def sample_md_valid(tmp_dir):
    """Create a valid Markdown file with proper front matter."""
    content = """---
slide_id: test-intro-001
purpose: "Test slide for validation"
audience: "Engineering team"
speaker_notes: "This is a comprehensive speaker note that exceeds the minimum fifty character requirement for validation."
routing:
  - ALL
---

# Introduction

## Overview

This is a valid slide with proper structure.

- Item one
- Item two
- Item three

See Figure arch-diagram for the architecture overview.

![arch-diagram](images/architecture.png)
"""
    path = tmp_dir / "slide_test.md"
    path.write_text(content)
    return str(path)


@pytest.fixture
def sample_md_invalid(tmp_dir):
    """Create an invalid Markdown file with multiple violations."""
    content = """# Title

#### Skipped Heading Level

- Single orphan bullet

This references Figure nonexistent but it doesn't exist.

""" + "x" * 250 + "\n"
    path = tmp_dir / "slide_invalid.md"
    path.write_text(content)
    return str(path)


@pytest.fixture
def sample_theme_file():
    """Return path to the project's SEMANTIC_THEME.yaml."""
    return str(PROJECT_ROOT / "engines" / "SEMANTIC_THEME.yaml")


@pytest.fixture
def sample_manifest(tmp_dir):
    """Create a sample lineage manifest."""
    manifest = {
        "version": "1.0.0",
        "last_updated": "2026-05-20T00:00:00Z",
        "assets": [
            {
                "filename": "test.pptx",
                "sha256": "a" * 64,
                "file_size": 1024,
                "mime_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                "ingested_at": "2026-05-20T00:00:00Z",
                "mock_file": "Input_Master/test.pptx.mock",
                "processing_status": "verified",
            }
        ],
        "lineage": [],
    }
    path = tmp_dir / "lineage_manifest.json"
    path.write_text(json.dumps(manifest, indent=2))
    return str(path)


@pytest.fixture
def sample_binary(tmp_dir):
    """Create a sample binary file for verification testing."""
    path = tmp_dir / "Input_Master"
    path.mkdir(exist_ok=True)
    binary_file = path / "test_asset.pptx"
    binary_file.write_bytes(b"PK\x03\x04" + b"\x00" * 100)  # Minimal zip header
    return str(binary_file)
