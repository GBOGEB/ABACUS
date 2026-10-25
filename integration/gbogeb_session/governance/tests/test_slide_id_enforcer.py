"""Unit tests for SLIDE_ID_ENFORCER.py."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.SLIDE_ID_ENFORCER import (
    EnforcerResults,
    check_lineage_manifest,
    check_markdown_file,
    check_yaml_file,
    validate_slide_id,
)


class TestValidateSlideId:
    def test_valid_id(self):
        valid, msg = validate_slide_id("arch-overview-001")
        assert valid

    def test_valid_id_numeric(self):
        valid, msg = validate_slide_id("perf-metrics-012")
        assert valid

    def test_empty_string(self):
        valid, msg = validate_slide_id("")
        assert not valid

    def test_missing_sequence(self):
        valid, msg = validate_slide_id("arch-overview")
        assert not valid

    def test_non_numeric_sequence(self):
        valid, msg = validate_slide_id("arch-overview-abc")
        assert not valid

    def test_single_segment(self):
        valid, msg = validate_slide_id("architecture")
        assert not valid

    def test_special_characters(self):
        valid, msg = validate_slide_id("arch/overview-001")
        assert not valid

    def test_spaces(self):
        valid, msg = validate_slide_id("arch overview 001")
        assert not valid


class TestCheckMarkdownFile:
    def test_valid_front_matter(self, tmp_dir):
        content = '---\nslide_id: test-intro-001\n---\n# Hello\n'
        path = tmp_dir / "slide_test.md"
        path.write_text(content)
        findings = check_markdown_file(str(path))
        valid_findings = [f for f in findings if f.valid]
        assert len(valid_findings) >= 1

    def test_missing_slide_id(self, tmp_dir):
        content = '---\ntitle: "Test"\n---\n# Hello\n'
        path = tmp_dir / "slide_test.md"
        path.write_text(content)
        findings = check_markdown_file(str(path))
        invalid_findings = [f for f in findings if not f.valid]
        assert len(invalid_findings) >= 1

    def test_invalid_slide_id_format(self, tmp_dir):
        content = '---\nslide_id: "bad id format"\n---\n# Hello\n'
        path = tmp_dir / "slide_test.md"
        path.write_text(content)
        findings = check_markdown_file(str(path))
        invalid_findings = [f for f in findings if not f.valid]
        assert len(invalid_findings) >= 1


class TestCheckYamlFile:
    def test_yaml_with_slide_id(self, tmp_dir):
        import yaml
        content = {"slide_id": "test-overview-001", "title": "Test"}
        path = tmp_dir / "test.yaml"
        path.write_text(yaml.dump(content))
        findings = check_yaml_file(str(path))
        assert any(f.valid for f in findings)

    def test_yaml_with_slides_array(self, tmp_dir):
        import yaml
        content = {
            "slides": [
                {"slide_id": "test-one-001", "title": "First"},
                {"slide_id": "test-two-002", "title": "Second"},
            ]
        }
        path = tmp_dir / "test.yaml"
        path.write_text(yaml.dump(content))
        findings = check_yaml_file(str(path))
        valid_count = sum(1 for f in findings if f.valid)
        assert valid_count == 2

    def test_yaml_missing_slide_id_in_array(self, tmp_dir):
        import yaml
        content = {
            "slides": [
                {"title": "No ID"},
            ]
        }
        path = tmp_dir / "test.yaml"
        path.write_text(yaml.dump(content))
        findings = check_yaml_file(str(path))
        invalid_count = sum(1 for f in findings if not f.valid)
        assert invalid_count >= 1


class TestCheckLineageManifest:
    def test_valid_manifest(self, tmp_dir):
        manifest = {
            "version": "1.0.0",
            "assets": [],
            "lineage": [
                {"slide_id": "arch-overview-001", "derived_from": "test.yaml"}
            ],
        }
        path = tmp_dir / "lineage_manifest.json"
        path.write_text(json.dumps(manifest))
        findings = check_lineage_manifest(str(path))
        assert any(f.valid for f in findings)

    def test_nonexistent_manifest(self):
        findings = check_lineage_manifest("/nonexistent/manifest.json")
        assert len(findings) == 0


class TestEnforcerResults:
    def test_empty_results_pass(self):
        results = EnforcerResults()
        assert results.passed

    def test_results_with_violation(self):
        from engines.SLIDE_ID_ENFORCER import EnforcerFinding
        results = EnforcerResults()
        results.add(EnforcerFinding(
            file="test.md", slide_id=None, valid=False, message="Missing ID"
        ))
        assert not results.passed

    def test_json_output(self):
        results = EnforcerResults()
        output = results.to_json()
        data = json.loads(output)
        assert data["passed"] is True
