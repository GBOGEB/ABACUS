"""N+13 targeted coverage and correctness for remaining quick-error branches."""

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name):
    source = ROOT / "DMAIC_V3" / name
    spec = importlib.util.spec_from_file_location("cbd_p13_" + name[:-3], source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fixer_inserts_missing_typing_import_in_source_without_imports(tmp_path):
    fixer = load("quick_error_fix.py").QuickFixer()
    source = tmp_path / "no_imports.py"
    source.write_text("value = 1\n")
    assert fixer.fix_missing_imports(source, "Any") is True
    assert source.read_text() == "from typing import Any\nvalue = 1\n"
    assert fixer.fixes_applied[-1]["status"] == "SUCCESS"


def test_fixer_keeps_preexisting_typing_import_unique(tmp_path):
    fixer = load("quick_error_fix.py").QuickFixer()
    source = tmp_path / "typed.py"
    original = "from typing import Any\nvalue: Any = 1\n"
    source.write_text(original)
    assert fixer.fix_missing_imports(source, "Any") is False
    assert source.read_text() == original
    assert fixer.fixes_applied == []
    assert source.read_text().count("from typing import Any") == 1


def test_fixer_main_existing_orchestrator_and_real_type_repair(tmp_path, monkeypatch):
    module = load("quick_error_fix.py")
    root = tmp_path / "DMAIC_V3"
    root.mkdir()
    orchestrator = root / "full_pipeline_orchestrator.py"
    orchestrator.write_text("items: List[Dict] = []\n")
    monkeypatch.chdir(tmp_path)

    def clean_scan(detector):
        detector.errors = []
        detector.warnings = []
        return detector.errors, detector.warnings

    monkeypatch.setattr(module.ErrorDetector, "scan_for_errors", clean_scan)
    assert module.main() == 0
    assert orchestrator.read_text() == "items: List[Dict[str, Any]] = []\n"
    assert "Fixed type hints" not in (root / "ERROR_DETECTION_REPORT.md").read_text()
    assert "Added type parameters" in (root / "ERROR_DETECTION_REPORT.md").read_text()


def test_lister_short_issue_group_exercises_nontruncation_branch(tmp_path):
    lister = load("quick_error_lister.py")
    result = tmp_path / "report.md"
    issues = [
        {"type": "type_hint", "file": "a.py", "line": 3, "message": "missing Any"},
        {"type": "attribute", "file": "b.py", "line": 4, "message": "missing property"},
    ]
    assert lister.generate_report([], issues, result) == 2
    text = result.read_text()
    assert "Type Hint (1)" in text
    assert "Attribute (1)" in text
    assert "and 1 more" not in text


def test_lister_exactly_ten_issues_is_not_truncated(tmp_path):
    lister = load("quick_error_lister.py")
    result = tmp_path / "report.md"
    issues = [
        {"type": "type_hint", "file": "a.py", "line": n, "message": "bad"}
        for n in range(10)
    ]
    assert lister.generate_report([], issues, result) == 10
    assert "and 0 more" not in result.read_text()


def test_similar_typing_identifier_is_not_a_false_import_match(tmp_path):
    fixer = load("quick_error_fix.py").QuickFixer()
    source = tmp_path / "similar.py"
    source.write_text("from typing import AnyStr\n")
    assert fixer.fix_missing_imports(source, "Any") is True
    assert source.read_text() == "from typing import AnyStr, Any\n"
    assert len(fixer.fixes_applied) == 1


def test_all_typing_lines_are_checked_for_existing_name(tmp_path):
    fixer = load("quick_error_fix.py").QuickFixer()
    source = tmp_path / "two_imports.py"
    original = "from typing import List\nfrom typing import Any\n"
    source.write_text(original)
    assert fixer.fix_missing_imports(source, "Any") is False
    assert source.read_text() == original
    assert fixer.fixes_applied == []


def test_type_import_after_future_import_keeps_file_valid(tmp_path):
    fixer = load("quick_error_fix.py").QuickFixer()
    source = tmp_path / "future.py"
    source.write_text("from __future__ import annotations\nvalue: 'Any' = 1\n")
    assert fixer.fix_missing_imports(source, "Any") is True
    content = source.read_text()
    assert content.startswith(
        "from __future__ import annotations\nfrom typing import Any\n"
    )
    compile(content, str(source), "exec")


def test_shebang_stays_first_when_inserting_typing_import(tmp_path):
    fixer = load("quick_error_fix.py").QuickFixer()
    source = tmp_path / "script.py"
    source.write_text("#!/usr/bin/env python3\nvalue = 1\n")
    assert fixer.fix_missing_imports(source, "Any") is True
    assert source.read_text().startswith(
        "#!/usr/bin/env python3\nfrom typing import Any\n"
    )
