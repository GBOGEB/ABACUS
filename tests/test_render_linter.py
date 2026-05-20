"""Unit tests for RENDER_LINTER.py."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.RENDER_LINTER import (
    LintResults,
    Severity,
    lint_file,
    rule_no_orphan_bullets,
    rule_no_overflow,
    rule_stable_heading_hierarchy,
    rule_figure_reference_required,
    rule_semantic_card_required,
    rule_speaker_notes_required,
)


class TestNoOverflow:
    def test_long_line_triggers_warning(self, tmp_dir):
        content = "x" * 250 + "\n"
        path = tmp_dir / "test.md"
        path.write_text(content)
        results = LintResults()
        rule_no_overflow(content, str(path), results)
        assert len(results.warnings) >= 1
        assert "overflow" in results.warnings[0].message.lower() or "200" in results.warnings[0].message

    def test_overflow_hidden_triggers_error(self, tmp_dir):
        content = "div { overflow: hidden; }\n"
        path = tmp_dir / "test.css"
        path.write_text(content)
        results = LintResults()
        rule_no_overflow(content, str(path), results)
        assert len(results.errors) >= 1

    def test_normal_line_passes(self, tmp_dir):
        content = "Normal line of text.\n"
        results = LintResults()
        rule_no_overflow(content, "test.md", results)
        assert results.passed


class TestNoOrphanBullets:
    def test_single_bullet_flagged(self):
        content = "Some text\n\n- Only item\n\nMore text\n"
        results = LintResults()
        rule_no_orphan_bullets(content, "test.md", results)
        assert len(results.warnings) >= 1

    def test_multiple_bullets_pass(self):
        content = "- Item one\n- Item two\n- Item three\n"
        results = LintResults()
        rule_no_orphan_bullets(content, "test.md", results)
        assert results.passed

    def test_single_numbered_item_flagged(self):
        content = "1. Only numbered item\n\nMore text\n"
        results = LintResults()
        rule_no_orphan_bullets(content, "test.md", results)
        assert len(results.warnings) >= 1


class TestStableHeadingHierarchy:
    def test_sequential_headings_pass(self):
        content = "# H1\n## H2\n### H3\n"
        results = LintResults()
        rule_stable_heading_hierarchy(content, "test.md", results)
        # Should have no errors (info about H1 count is ok)
        assert len(results.errors) == 0

    def test_skipped_level_triggers_error(self):
        content = "# H1\n### H3 Skipped\n"
        results = LintResults()
        rule_stable_heading_hierarchy(content, "test.md", results)
        assert len(results.errors) >= 1
        assert "skipped" in results.errors[0].message.lower()

    def test_h2_to_h4_skip_detected(self):
        content = "# H1\n## H2\n#### H4 Skipped\n"
        results = LintResults()
        rule_stable_heading_hierarchy(content, "test.md", results)
        assert len(results.errors) >= 1


class TestFigureReferenceRequired:
    def test_referenced_figure_passes(self):
        content = "![diagram](img.png)\n\nSee Figure diagram for details.\n"
        results = LintResults()
        rule_figure_reference_required(content, "test.md", results)
        # No errors expected
        assert len(results.errors) == 0

    def test_unreferenced_figure_flagged(self):
        content = 'fig-id: "myFigure"\n\nNo reference in text.\n'
        results = LintResults()
        rule_figure_reference_required(content, "test.md", results)
        assert len(results.findings) >= 1


class TestSemanticCardRequired:
    def test_complete_card_passes(self):
        content = '---\nslide_id: test-intro-001\npurpose: "Test"\naudience: "All"\n---\n# Slide\n'
        results = LintResults()
        rule_semantic_card_required(content, "slide_test.md", results)
        assert len(results.errors) == 0

    def test_missing_fields_flagged(self):
        content = '---\nslide_id: test-intro-001\n---\n# Slide\n'
        results = LintResults()
        rule_semantic_card_required(content, "slide_test.md", results)
        assert len(results.errors) >= 1
        assert "purpose" in results.errors[0].message or "audience" in results.errors[0].message


class TestSpeakerNotesRequired:
    def test_sufficient_notes_pass(self):
        content = '---\nspeaker_notes: "' + 'x' * 60 + '"\n---\n# Slide\n'
        results = LintResults()
        rule_speaker_notes_required(content, "test.md", results)
        assert len(results.warnings) == 0

    def test_short_notes_flagged(self):
        content = '---\nspeaker_notes: "Short"\n---\n# Slide\n'
        results = LintResults()
        rule_speaker_notes_required(content, "test.md", results)
        assert len(results.warnings) >= 1


class TestLintFile:
    def test_valid_file(self, sample_md_valid):
        results = lint_file(sample_md_valid)
        # Valid file may have warnings but should not block (check structure works)
        assert isinstance(results, LintResults)
        assert results.summary()  # Ensure summary can be generated

    def test_invalid_file(self, sample_md_invalid):
        results = lint_file(sample_md_invalid)
        assert len(results.findings) > 0

    def test_nonexistent_file(self):
        results = lint_file("/nonexistent/path.md")
        assert len(results.errors) >= 1

    def test_non_lintable_extension(self, tmp_dir):
        path = tmp_dir / "test.py"
        path.write_text("print('hello')")
        results = lint_file(str(path))
        assert len(results.findings) == 0  # .py not linted


class TestLintResults:
    def test_passed_with_no_errors(self):
        results = LintResults()
        assert results.passed

    def test_failed_with_errors(self):
        from engines.RENDER_LINTER import LintFinding
        results = LintResults()
        results.add(LintFinding(
            rule="test", severity=Severity.ERROR,
            file="test.md", line=1, message="test error",
        ))
        assert not results.passed

    def test_json_output(self):
        results = LintResults()
        output = results.to_json()
        import json
        data = json.loads(output)
        assert data["passed"] is True
        assert data["total"] == 0
