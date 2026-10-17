"""Additional isolated branch-path regression tests for existing #2099 coverage owner.

No real pipelines execute. The zero-tested historical modules are loaded by path,
subprocess calls are stubbed, and all writable files live under tmp_path.
"""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1] / "DMAIC_V3"


def load(name):
    spec = importlib.util.spec_from_file_location("_cbd_edge_" + name, ROOT / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_static_pylint_nonzero_without_error_and_mypy_warning_is_not_fabricated(monkeypatch):
    module = load("quick_error_fix")
    responses = iter([
        SimpleNamespace(returncode=2, stdout="fatal: tool unavailable\n"),
        SimpleNamespace(returncode=0, stdout="warning: not an error marker\n"),
    ])
    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: next(responses))
    errors, warnings = module.ErrorDetector().scan_for_errors()
    assert errors == [] and warnings == []


def test_mypy_multi_error_records_preserve_each_source_line(monkeypatch):
    module = load("quick_error_fix")
    responses = iter([
        SimpleNamespace(returncode=0, stdout="clean\n"),
        SimpleNamespace(returncode=1, stdout="a.py:2: error: mismatch\nb.py:9: error: unresolved\nnoise"),
    ])
    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: next(responses))
    errors, warnings = module.ErrorDetector().scan_for_errors()
    assert [row["type"] for row in errors] == ["type_error", "type_error"]
    assert [row["message"] for row in errors] == [
        "a.py:2: error: mismatch", "b.py:9: error: unresolved",
    ]
    assert warnings == []


def test_runtime_log_overlapping_context_and_boundary(tmp_path):
    module = load("quick_error_fix")
    path = tmp_path / "run.log"
    path.write_text("ERROR first\ncontext\nFAIL second\nquiet\nTraceback last\n")
    rows = module.ErrorDetector().detect_runtime_errors(path)
    assert [x["line_number"] for x in rows] == [1, 3, 5]
    assert "ERROR first" in rows[0]["context"]
    assert "Traceback last" in rows[-1]["context"]
    assert all(row["type"] == "runtime_error" for row in rows)


def test_categorization_multi_issue_partition_and_priority():
    module = load("quick_error_fix")
    inputs = [
        {"message": "type import conflict", "type": "runtime_error"},
        {"message": "module not found", "type": "runtime_error"},
        {"message": "attribute missing", "type": "runtime_error"},
        {"message": "bad syntax", "type": "runtime_error"},
        {"message": "unclassified panic", "type": "runtime_error"},
        {"message": "other", "type": "warning"},
    ]
    output = module.ErrorDetector().categorize_errors(inputs)
    assert {k: len(v) for k, v in output.items()} == {
        "type_errors": 1, "import_errors": 1, "attribute_errors": 1,
        "runtime_errors": 1, "syntax_errors": 1, "other": 1,
    }
    assert output["type_errors"][0] is inputs[0]


def test_multiple_type_hint_replacements_are_atomic_and_idempotent(tmp_path):
    module = load("quick_error_fix")
    target = tmp_path / "annotations.py"
    target.write_text("x: Dict[str, ] = {}\ny: List[Dict] = []\nz: Tuple[bool, Dict] = (True,{})\n")
    fixer = module.QuickFixer()
    assert fixer.fix_type_hints(target) is True
    contents = target.read_text()
    assert "Dict[str, Any]" in contents
    assert "List[Dict[str, Any]]" in contents
    assert "Tuple[bool, Dict[str, Any]]" in contents
    assert fixer.fix_type_hints(target) is False
    assert [r["status"] for r in fixer.fixes_applied] == ["SUCCESS"]


def test_report_suppresses_empty_categories_and_no_fake_fix(tmp_path):
    module = load("quick_error_fix")
    detector = module.ErrorDetector()
    detector.errors = [{"message": "type issue", "type": "type_error"}]
    report = tmp_path / "report.md"
    detector.generate_fix_report(report)
    contents = report.read_text()
    assert "Type Errors (1)" in contents
    assert "Fixes Applied:** 0" in contents
    assert "Import Errors (" not in contents


def test_main_repairs_existing_orchestrator_without_running_pipeline(tmp_path, monkeypatch):
    module = load("quick_error_fix")
    folder = tmp_path / "DMAIC_V3"
    folder.mkdir()
    orchestrator = folder / "full_pipeline_orchestrator.py"
    orchestrator.write_text("values: List[Dict] = []\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        module.ErrorDetector, "scan_for_errors",
        lambda self: ([], []),
    )
    assert module.main() == 0
    assert "List[Dict[str, Any]]" in orchestrator.read_text()
    assert "Fixes Applied:** 1" in (folder / "ERROR_DETECTION_REPORT.md").read_text()


def test_error_lister_multiple_issues_same_line_count_as_separate_findings(tmp_path, monkeypatch):
    module = load("quick_error_lister")
    folder = tmp_path / "DMAIC_V3"
    folder.mkdir()
    (folder / "ambiguous.py").write_text(
        "x: Dict[str, int] = {}; y: List[Dict] = []; z = config.workspace_root\n"
    )
    monkeypatch.chdir(tmp_path)
    rows = module.scan_python_files()
    assert len(rows) == 3
    assert [x["line"] for x in rows] == [1, 1, 1]
    assert [x["type"] for x in rows] == ["type_hint", "type_hint", "attribute"]


def test_error_lister_report_groups_distinct_issue_types(tmp_path):
    module = load("quick_error_lister")
    report = tmp_path / "report.md"
    count = module.generate_report(
        [{"line": 1, "message": "ERROR input", "type": "runtime"}],
        [
            {"type": "attribute", "file": "a.py", "line": 2, "message": "invalid path"},
            {"type": "type_hint", "file": "b.py", "line": 3, "message": "missing Any"},
        ],
        report,
    )
    body = report.read_text()
    assert count == 3
    assert "Attribute (1)" in body
    assert "Type Hint (1)" in body
    assert "Line 1: ERROR input" in body
