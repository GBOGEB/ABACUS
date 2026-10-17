"""Isolated tests for the zero-covered DMAIC quick-error detector and fixer.

Each subprocess call is stubbed and all filesystem changes occur in tmp_path.
"""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "DMAIC_V3" / "quick_error_fix.py"


def load():
    spec = importlib.util.spec_from_file_location("_cbd_quick_error_fix", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_scanners_retain_separate_pylint_and_mypy_findings(monkeypatch):
    module = load()
    calls = []

    def run(command, **options):
        calls.append((command, options))
        if "pylint" in command:
            return SimpleNamespace(returncode=1, stdout="error: syntax problem\nnoise\n")
        return SimpleNamespace(returncode=1, stdout="a.py:5: error: wrong type\n")

    monkeypatch.setattr(module.subprocess, "run", run)
    errors, warnings = module.ErrorDetector().scan_for_errors()
    assert [e["type"] for e in errors] == ["pylint_error", "type_error"]
    assert warnings == [] and len(calls) == 2
    assert all(kwargs.get("capture_output") and kwargs.get("text") for _, kwargs in calls)


def test_clean_scans_are_not_counted_as_failures(monkeypatch):
    module = load()
    monkeypatch.setattr(module.subprocess, "run", lambda *a, **kw:
                        SimpleNamespace(returncode=0, stdout="no errors here"))
    errors, warnings = module.ErrorDetector().scan_for_errors()
    assert errors == [] and warnings == []


def test_pylint_success_does_not_override_mypy_error(monkeypatch):
    module = load()
    results = iter([
        SimpleNamespace(returncode=0, stdout="error text but pylint is green"),
        SimpleNamespace(returncode=0, stdout="x.py:7: error: wrong type"),
    ])
    monkeypatch.setattr(module.subprocess, "run", lambda *a, **kw: next(results))
    errors, _ = module.ErrorDetector().scan_for_errors()
    assert [x["type"] for x in errors] == ["type_error"]


def test_missing_runtime_log_is_unknown_not_failure(tmp_path):
    assert load().ErrorDetector().detect_runtime_errors(tmp_path / "absent.log") == []


@pytest.mark.parametrize("marker", ["ERROR", "FAIL", "Exception", "Traceback"])
def test_runtime_error_line_and_context(marker, tmp_path):
    path = tmp_path / "run.log"
    path.write_text("one\ntwo\n" + marker + " root\nfour\nfive\n")
    result = load().ErrorDetector().detect_runtime_errors(path)
    assert len(result) == 1
    assert result[0]["line_number"] == 3
    assert "two" in result[0]["context"]
    assert "four" in result[0]["context"]


@pytest.mark.parametrize("message,bucket", [
    ("expected type str", "type_errors"),
    ("ImportError: module absent", "import_errors"),
    ("has no attribute", "attribute_errors"),
    ("syntax error", "syntax_errors"),
    ("plain runtime problem", "runtime_errors"),
    ("unclassified", "other"),
])
def test_classification_preserves_single_bucket(message, bucket):
    out = load().ErrorDetector().categorize_errors([
        {"message": message, "type": "runtime_error"}
    ])
    assert len(out[bucket]) == 1
    assert sum(len(rows) for rows in out.values()) == 1


def test_fix_report_retains_counts_and_fixes(tmp_path):
    module = load()
    d = module.ErrorDetector()
    d.errors = [{"message": "syntax problem " + str(n)} for n in range(7)]
    d.warnings = [{"message": "warning"}]
    d.fixes_applied = [{"file": "a.py", "issue": "bad type", "fix": "add Any", "status": "SUCCESS"}]
    out = tmp_path / "report.md"
    d.generate_fix_report(out)
    text = out.read_text()
    assert "Total Errors:** 7" in text
    assert "Total Warnings:** 1" in text
    assert "and 2 more" in text and "add Any" in text


def test_type_fix_is_idempotent_and_receipted(tmp_path):
    fixer = load().QuickFixer()
    path = tmp_path / "sample.py"
    path.write_text("items: List[Dict] = []\n")
    assert fixer.fix_type_hints(path) is True
    assert "List[Dict[str, Any]]" in path.read_text()
    assert fixer.fix_type_hints(path) is False
    assert len(fixer.fixes_applied) == 1


def test_missing_type_source_is_not_reported_as_fixed(tmp_path):
    fixer = load().QuickFixer()
    assert fixer.fix_type_hints(tmp_path / "missing.py") is False
    assert fixer.fixes_applied[-1]["status"] == "FAILED"


def test_add_import_to_existing_typing_line(tmp_path):
    fixer = load().QuickFixer()
    path = tmp_path / "sample.py"
    path.write_text("from typing import List\n")
    assert fixer.fix_missing_imports(path, "Any") is True
    assert path.read_text() == "from typing import List, Any\n"


def test_add_import_before_first_import(tmp_path):
    fixer = load().QuickFixer()
    path = tmp_path / "sample.py"
    path.write_text("import os\nvalue = 1\n")
    assert fixer.fix_missing_imports(path, "Any") is True
    assert path.read_text().startswith("from typing import Any\nimport os\n")


def test_missing_import_source_produces_failure_receipt(tmp_path):
    fixer = load().QuickFixer()
    assert fixer.fix_missing_imports(tmp_path / "missing.py", "Any") is False
    assert fixer.fixes_applied[-1]["status"] == "FAILED"


@pytest.mark.parametrize("has_error", [False, True])
def test_main_writes_report_and_preserves_exit_code(tmp_path, monkeypatch, has_error):
    module = load()
    (tmp_path / "DMAIC_V3").mkdir()
    monkeypatch.chdir(tmp_path)
    errors = [{"type": "type_error", "message": "wrong type"}] if has_error else []
    def fake_scan(self):
        self.errors = list(errors)
        self.warnings = []
        return self.errors, self.warnings

    monkeypatch.setattr(module.ErrorDetector, "scan_for_errors", fake_scan)
    assert module.main() == (1 if has_error else 0)
    report = (tmp_path / "DMAIC_V3" / "ERROR_DETECTION_REPORT.md")
    assert report.exists()
    assert ("wrong type" in report.read_text()) == has_error
