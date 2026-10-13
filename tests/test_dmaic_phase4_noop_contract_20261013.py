"""Bounded Phase 4 no-op and error-path coverage without production edits."""

from pathlib import Path

import pytest

from DMAIC_V3.phases.phase4_improve import CodeImprover


@pytest.mark.parametrize(
    "method",
    [
        "add_missing_docstrings",
        "fix_long_lines",
        "add_type_hints",
        "remove_unused_imports",
    ],
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


@pytest.mark.parametrize(
    "method",
    ["add_missing_docstrings", "add_type_hints", "remove_unused_imports"],
)
def test_invalid_python_fails_closed_without_writing(
    tmp_path: Path, method: str
):
    source = tmp_path / "invalid.py"
    original = "def invalid(:\n"
    source.write_text(original, encoding="utf-8")
    improver = CodeImprover(tmp_path)

    result = getattr(improver, method)(source)

    assert result["success"] is False
    assert result["error"]
    assert source.read_text(encoding="utf-8") == original
    assert improver.improvements_made == []


def test_unused_import_removed_and_receipt_recorded(tmp_path: Path):
    source = tmp_path / "module.py"
    source.write_text("import os\n\nvalue = 1\n", encoding="utf-8")
    improver = CodeImprover(tmp_path)

    result = improver.remove_unused_imports(source)

    assert result["success"] is True
    assert result["modifications"] == 1
    assert "import os" not in source.read_text(encoding="utf-8")
    assert improver.improvements_made == [result]


def test_used_import_is_unchanged_and_uncredited(tmp_path: Path):
    source = tmp_path / "module.py"
    original = "import os\n\nname = os.name\n"
    source.write_text(original, encoding="utf-8")
    improver = CodeImprover(tmp_path)

    result = improver.remove_unused_imports(source)

    assert result == {"success": False, "reason": "No unused imports"}
    assert source.read_text(encoding="utf-8") == original
    assert improver.improvements_made == []


def test_type_annotated_function_is_unchanged(tmp_path: Path):
    source = tmp_path / "module.py"
    original = "def answer() -> int:\n    return 42\n"
    source.write_text(original, encoding="utf-8")
    improver = CodeImprover(tmp_path)

    result = improver.add_type_hints(source)

    assert result == {"success": False, "reason": "No missing type hints"}
    assert source.read_text(encoding="utf-8") == original
    assert improver.improvements_made == []


def test_noncomment_long_line_without_comma_is_unchanged(tmp_path: Path):
    source = tmp_path / "module.py"
    original = "message = " + repr("x" * 125) + "\n"
    source.write_text(original, encoding="utf-8")
    improver = CodeImprover(tmp_path)

    result = improver.fix_long_lines(source, max_length=60)

    assert result == {"success": False, "reason": "No long lines found"}
    assert source.read_text(encoding="utf-8") == original
    assert improver.improvements_made == []
