"""Negative controls for exact-fixture coverage reporting guard."""
import importlib.util
import json
import tempfile
from pathlib import Path

import pytest
from coverage import CoverageData

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/ci/coverage_temp_source_guard.py"
spec = importlib.util.spec_from_file_location("coverage_temp_source_guard", SCRIPT)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


@pytest.fixture
def cohort(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "pyproject.toml").write_text("[tool.coverage.run]\n")
    temp = tmp_path / "temporary"
    temp.mkdir()
    real = root / "prod.py"
    real.write_text("x = 1\n")
    return root, temp, real, tmp_path / ".coverage", tmp_path / "receipt.json"


def run(cohort, paths):
    root, temp, _, database, receipt = cohort
    data = CoverageData(basename=str(database))
    data.add_lines({str(path): {1} for path in paths})
    data.write()
    return guard.reconcile(str(database), str(root), str(temp),
                           str(receipt), str(root / "coverage.xml"),
                           str(root / "coverage.json"))


def test_deleted_known_fixture_preserves_raw_data(cohort):
    root, temp, real, database, receipt = cohort
    gone = temp / "tmp12345" / "localpkg" / "__init__.py"
    result = run(cohort, [real, gone])
    assert result["status"] == "PASS"
    assert result["approved_deleted_fixture"] == [str(gone)]
    assert "localpkg" not in (root / "coverage.xml").read_text()
    raw = CoverageData(basename=str(database))
    raw.read()
    assert set(raw.measured_files()) == {str(real), str(gone)}


def test_missing_production_source_blocks(cohort):
    root, temp, real, database, receipt = cohort
    real.unlink()
    with pytest.raises(ValueError, match="missing non-fixture source"):
        run(cohort, [real])
    assert json.loads(receipt.read_text())["status"] == "HOLD"


@pytest.mark.parametrize("tail", [
    ("otherpkg", "__init__.py"),
    ("deep", "localpkg", "__init__.py"),
    ("localpkg", "other.py"),
])
def test_unrelated_missing_source_blocks(cohort, tail):
    root, temp, real, database, receipt = cohort
    gone = temp.joinpath("tmp12345", *tail)
    with pytest.raises(ValueError, match="missing non-fixture source"):
        run(cohort, [real, gone])


def test_existing_fixture_is_not_suppressed(cohort):
    root, temp, real, database, receipt = cohort
    existing = temp / "tmp12345" / "localpkg" / "__init__.py"
    existing.parent.mkdir(parents=True)
    existing.write_text("x = 1\n")
    result = run(cohort, [real, existing])
    assert result["approved_deleted_fixture"] == []
    assert result["measured_before"] == result["measured_after"] == 2


def test_outside_temp_prefix_blocks(cohort):
    root, temp, real, database, receipt = cohort
    gone = temp.parent / "temporary_fake" / "tmp12345" / "localpkg" / "__init__.py"
    with pytest.raises(ValueError, match="missing non-fixture source"):
        run(cohort, [real, gone])


def test_checkout_inside_temp_rejected(cohort):
    root, temp, real, database, receipt = cohort
    with pytest.raises(ValueError, match="checkout inside temp"):
        guard.reconcile(str(database), str(root), str(root.parent),
                        str(receipt), str(root / "coverage.xml"),
                        str(root / "coverage.json"))
