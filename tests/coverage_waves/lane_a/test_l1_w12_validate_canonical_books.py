"""Lane A wave 12: canonical knowledge books validator (books, registry, CI, imports)."""

import builtins
import json
from pathlib import Path

import pytest

from DMAIC_V3 import canonical_refactoring as cr
from DMAIC_V3 import validate_canonical_books as vcb

BOOK_DIRS = [
    "DMAIC",
    "Architecture",
    "Planning",
    "Reference",
    "Changelog",
    "Execution_Logs",
    "Assessment",
    "Uncategorized",
]
IMPORT_NAMES = (
    "DMAIC_V3.config",
    "DMAIC_V3.phases.phase6_knowledge",
    "master_document_system.core.temporal_tracker",
)


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def _populate(root, dmaic_text="Define Measure Analyze Improve Control"):
    canon = root / "CANONICAL_KNOWLEDGE"
    for name in BOOK_DIRS:
        _write(canon / name / (name + "_BOOK_1.md"), "book")
    _write(canon / "DMAIC" / "DMAIC_BOOK_1.md", dmaic_text)
    _write(canon / "MASTER_INDEX_1.md", "index")
    registry = {"documents": {"a": {}, "b": {}}, "version_history": {}}
    _write(canon / "document_registry.json", json.dumps(registry))
    _write(root / ".github" / "workflows" / "ci.yml", "on: push\njobs: {}\n")
    return canon


def _stub_imports(monkeypatch, behaviour):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name in behaviour:
            outcome = behaviour[name]
            if isinstance(outcome, Exception):
                raise outcome
            return None
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)


def _statuses(results):
    return {v["test"]: v["status"] for v in results["validations"]}


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_validate_all_passes_on_complete_workspace(workspace, monkeypatch, capsys):
    canon = _populate(workspace)
    _stub_imports(monkeypatch, {name: "ok" for name in IMPORT_NAMES})
    results = vcb.CanonicalBooksValidator(canon).validate_all()
    assert results["tests_failed"] == 0
    assert results["tests_passed"] == results["tests_run"] == 16
    statuses = _statuses(results)
    assert statuses["Document registry structure"] == "PASS"
    assert statuses["CI/CD config valid: ci.yml"] == "PASS"
    saved = json.loads((canon / "VALIDATION_REPORT.json").read_text(encoding="utf-8"))
    assert saved["tests_run"] == 16
    assert "Pass Rate:    100.0%" in capsys.readouterr().out


def test_main_returns_zero_when_everything_passes(workspace, monkeypatch):
    _populate(workspace)
    _stub_imports(monkeypatch, {name: "ok" for name in IMPORT_NAMES})
    assert vcb.main() == 0


def test_main_returns_one_on_empty_canonical_dir(workspace, monkeypatch):
    (workspace / "CANONICAL_KNOWLEDGE").mkdir()
    _stub_imports(
        monkeypatch,
        {
            IMPORT_NAMES[0]: ImportError("nope"),
            IMPORT_NAMES[1]: RuntimeError("boom"),
            IMPORT_NAMES[2]: "ok",
        },
    )
    validator = vcb.CanonicalBooksValidator()
    assert validator.canonical_dir == Path("CANONICAL_KNOWLEDGE")
    assert vcb.main() == 1


def test_failure_paths_are_recorded(workspace, monkeypatch):
    canon = workspace / "CANONICAL_KNOWLEDGE"
    canon.mkdir()
    _stub_imports(
        monkeypatch,
        {
            IMPORT_NAMES[0]: ImportError("nope"),
            IMPORT_NAMES[1]: RuntimeError("boom"),
            IMPORT_NAMES[2]: "ok",
        },
    )
    results = vcb.CanonicalBooksValidator(canon).validate_all()
    statuses = _statuses(results)
    assert statuses["Book missing: MASTER_INDEX_*.md"] == "FAIL"
    assert statuses["Document registry"] == "FAIL"
    assert statuses["DMAIC book"] == "FAIL"
    assert statuses["CI/CD configurations"] == "FAIL"
    assert statuses["Import: DMAIC_V3.config"] == "FAIL"
    assert statuses["Import: DMAIC_V3.phases.phase6_knowledge"] == "FAIL"
    assert statuses["Import: master_document_system.core.temporal_tracker"] == "PASS"
    details = {v["test"]: v["details"] for v in results["validations"]}
    assert details["Import: DMAIC_V3.config"].startswith("Import failed:")
    assert details["Import: DMAIC_V3.phases.phase6_knowledge"] == "Error: boom"
    assert results["tests_failed"] == results["tests_run"] - 1


def test_registry_missing_fields_and_bad_json(workspace):
    canon = workspace / "CANONICAL_KNOWLEDGE"
    validator = vcb.CanonicalBooksValidator(canon)
    _write(canon / "document_registry.json", json.dumps({"documents": {}}))
    validator._test_document_registry()
    _write(canon / "document_registry.json", "{not json")
    validator._test_document_registry()
    tests = [(v["test"], v["status"]) for v in validator.results["validations"]]
    assert tests == [
        ("Document registry structure", "FAIL"),
        ("Document registry parsing", "FAIL"),
    ]


def test_dmaic_book_with_few_phases_fails(workspace):
    canon = _populate(workspace, dmaic_text="only define here")
    validator = vcb.CanonicalBooksValidator(canon)
    validator._test_dmaic_references()
    entry = validator.results["validations"][-1]
    assert entry["status"] == "FAIL"
    assert entry["details"] == "Only found 1/5 phases"


def test_dmaic_book_read_error_is_recorded(workspace, monkeypatch):
    canon = _populate(workspace)
    real_open = builtins.open

    def fake_open(file, *args, **kwargs):
        if str(file).endswith("DMAIC_BOOK_1.md"):
            raise OSError("locked")
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)
    validator = vcb.CanonicalBooksValidator(canon)
    validator._test_dmaic_references()
    entry = validator.results["validations"][-1]
    assert entry["test"] == "DMAIC book reading"
    assert entry["details"] == "locked"


def test_invalid_yaml_config_is_flagged(workspace):
    _write(workspace / ".github" / "workflows" / "bad.yaml", "key: [unclosed\n")
    _write(workspace / ".gitlab-ci.yml", "stages: [a]\n")
    validator = vcb.CanonicalBooksValidator(workspace / "CANONICAL_KNOWLEDGE")
    validator._test_cicd_configs()
    statuses = _statuses(validator.results)
    assert statuses["CI/CD configurations"] == "PASS"
    assert statuses["CI/CD config invalid: bad.yaml"] == "FAIL"
    assert statuses["CI/CD config valid: .gitlab-ci.yml"] == "PASS"


def test_report_without_tests_skips_pass_rate(workspace, capsys):
    (workspace / "CANONICAL_KNOWLEDGE").mkdir()
    validator = vcb.CanonicalBooksValidator()
    validator._generate_report()
    assert "Pass Rate" not in capsys.readouterr().out
    report = workspace / "CANONICAL_KNOWLEDGE" / "VALIDATION_REPORT.json"
    assert json.loads(report.read_text(encoding="utf-8"))["tests_run"] == 0


def check_production_defect_registry_key_mismatch(workspace):
    # Pins a production_defect (validate_canonical_books.py:93): the validator
    # requires a "documents" key, but CanonicalDocumentRefactorer.save_registry
    # writes "registry", so a freshly generated registry is always reported as
    # invalid. This check will fail once the defect is fixed.
    doc = workspace / "DMAIC_a.md"
    _write(doc, "Define")
    refactorer = cr.CanonicalDocumentRefactorer(workspace)
    refactorer._register_document(doc, "DMAIC")
    refactorer.save_registry()
    validator = vcb.CanonicalBooksValidator(refactorer.canonical_root)
    validator._test_document_registry()
    entry = validator.results["validations"][-1]
    assert entry["status"] == "FAIL"
    assert entry["details"] == "Missing required fields"


def check_production_defect_report_ignores_canonical_dir(tmp_path, monkeypatch):
    # Pins a production_defect (validate_canonical_books.py:218): the report path is
    # hard-coded to ./CANONICAL_KNOWLEDGE instead of self.canonical_dir, so a
    # validator pointed at another directory crashes when writing its report.
    # This check will fail once the defect is fixed.
    monkeypatch.chdir(tmp_path)
    custom = tmp_path / "custom_books"
    custom.mkdir()
    validator = vcb.CanonicalBooksValidator(custom)
    with pytest.raises(FileNotFoundError):
        validator._generate_report()
