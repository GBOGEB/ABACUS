"""Prove canonical coverage excludes only a disposable lint fixture.

The temp package belongs to a test-created Git snapshot, not the repository's
source inventory. Missing unrelated source must continue to fail closed.
"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from coverage import Coverage
from coverage.exceptions import NoSource
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
OMIT = "/tmp/tmp*/localpkg/__init__.py"
WORKFLOWS = (
    ".github/workflows/ci-abacus.yml",
    ".github/workflows/mip-coverage-evidence.yml",
)


def coverage_with_deleted_fixture(root: Path, extra_missing: bool = False):
    source = root / "governed.py"
    source.write_text("value = 42\n", encoding="utf-8")
    transient = root / "localpkg" / "__init__.py"
    missing = {str(transient): {1}}
    if extra_missing:
        missing[str(root / "otherpkg" / "__init__.py")] = {1}
    cov = Coverage(data_file=str(root / ".coverage"), config_file=False)
    cov.get_data().add_lines({str(source): {1}, **missing})
    cov.save()
    return cov, source, transient


def test_deleted_lint_fixture_can_be_omitted_without_losing_governed_source():
    with TemporaryDirectory() as td:
        root = Path(td)
        cov, source, transient = coverage_with_deleted_fixture(root)
        with pytest.raises(NoSource, match="localpkg"):
            cov.json_report(outfile=str(root / "unqualified.json"))
        cov.json_report(outfile=str(root / "qualified.json"), omit=[str(transient)])
        report = json.loads((root / "qualified.json").read_text(encoding="utf-8"))
        assert report["totals"]["num_statements"] == 1
        assert len(report["files"]) == 1
        assert next(iter(report["files"])).endswith(source.name)


def test_omission_does_not_hide_other_missing_source():
    with TemporaryDirectory() as td:
        root = Path(td)
        cov, _, transient = coverage_with_deleted_fixture(root, extra_missing=True)
        with pytest.raises(NoSource, match="otherpkg"):
            cov.json_report(
                outfile=str(root / "must-stay-red.json"), omit=[str(transient)]
            )


def test_native_workflows_keep_narrow_scope_without_ignore_errors():
    for relative in WORKFLOWS:
        workflow = (REPO_ROOT / relative).read_text(encoding="utf-8")
        assert f"--omit='{OMIT}'" in workflow
        assert "python -m coverage json" in workflow
        assert "--ignore-errors" not in workflow
