"""Bounded Phase 4 no-op and error-path coverage without production edits."""

from pathlib import Path

import pytest

from DMAIC_V3.phases.phase4_improve import CodeImprover


@pytest.mark.parametrize(
    "method",
    ["add_missing_docstrings", "fix_long_lines", "add_type_hints"],
)
def test_missing_source_is_reported_without_mutation(tmp_path: Path, method: str):
    improver = CodeImprover(tmp_path)
    missing = tmp_path / "missing.py"
    result = getattr(improver, method)(missing)
    assert result["success"] is False
    assert result["error"]
    assert improver.improvements_made == []
    assert not missing.exists()


def test_existing_docstrings_are_left_unchanged(tmp_path: Path):
    source = tmp_path / "module.py"
    original = '"""Module."""\n\ndef example():\n    """Documented."""\n    return 1\n'
    source.write_text(original, encoding="utf-8")
    improver = CodeImprover(tmp_path)
    result = improver.add_missing_docstrings(source)
    assert result == {"success": False, "reason": "No missing docstrings"}
    assert source.read_text(encoding="utf-8") == original
    assert improver.improvements_made == []


def test_short_lines_are_left_unchanged(tmp_path: Path):
    source = tmp_path / "module.py"
    original = "answer = 42\n"
    source.write_text(original, encoding="utf-8")
    improver = CodeImprover(tmp_path)
    result = improver.fix_long_lines(source)
    assert result == {"success": False, "reason": "No long lines found"}
    assert source.read_text(encoding="utf-8") == original
    assert improver.improvements_made == []
