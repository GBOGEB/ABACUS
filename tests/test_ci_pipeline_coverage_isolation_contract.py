"""#2669: ci-pipeline unit-tests coverage data must be isolated and xdist-safe.

The Run Tests step intermittently failed with ``coverage.exceptions.DataError:
... no such table: file`` under ``-n auto --cov``. The step therefore keeps its
coverage data outside the workspace and runs without the pyproject
``dynamic_context = "test_function"`` setting, which pytest-cov documents as
unsafe under xdist (pytest-cov#604).
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ci-pipeline.yml"
PYPROJECT = ROOT / "pyproject.toml"


def _unit_job() -> str:
    source = WORKFLOW.read_text(encoding="utf-8")
    return source.split("  unit-tests:", 1)[1].split("\n  integration-tests:", 1)[0]


def _run_tests_step() -> str:
    job = _unit_job()
    return job.split("- name: Run Tests", 1)[1].split("\n      - name:", 1)[0]


def test_coverage_file_lives_outside_the_workspace():
    step = _run_tests_step()
    assert 'mkdir -p "$RUNNER_TEMP/cov"' in step
    assert 'export COVERAGE_FILE="$RUNNER_TEMP/cov/.coverage"' in step
    export = step.index("export COVERAGE_FILE=")
    assert export < step.index("python -m coverage erase")
    assert export < step.index("pytest --benchmark-disable tests/")


def test_xdist_run_uses_a_config_without_dynamic_context():
    step = _run_tests_step()
    assert 'cov_config="$RUNNER_TEMP/cov/coverage-xdist.toml"' in step
    assert "sed '/^dynamic_context = /d' pyproject.toml > \"$cov_config\"" in step
    assert "grep -q '^dynamic_context' \"$cov_config\"" in step
    pytest_cmd = step[step.index("pytest --benchmark-disable tests/") :]
    assert '--cov-config="$cov_config"' in pytest_cmd
    assert "--cov-branch" in pytest_cmd
    assert '-n "$PYTEST_WORKERS"' in pytest_cmd


def test_coverage_errors_still_fail_the_step():
    step = _run_tests_step()
    assert "set -euo pipefail" in step
    assert "python -m coverage erase" in step
    for line in step.splitlines():
        if "pytest --benchmark-disable" in line:
            assert "|| true" not in line
            assert "|| echo" not in line
            assert "--no-cov" not in line


def test_matrix_does_not_cancel_the_sibling_cell():
    job = _unit_job()
    assert re.search(r"^      fail-fast: false$", job, re.MULTILINE)


def test_sed_filter_drops_dynamic_context_and_keeps_branch(tmp_path):
    """Apply the step's sed filter in Python and load the result with coverage."""
    coverage = pytest.importorskip("coverage")
    lines = PYPROJECT.read_text(encoding="utf-8").splitlines(keepends=True)
    filtered = [ln for ln in lines if not re.match(r"dynamic_context = ", ln)]
    assert not any(ln.startswith("dynamic_context") for ln in filtered)
    config = tmp_path / "coverage-xdist.toml"
    config.write_text("".join(filtered), encoding="utf-8")

    cov = coverage.Coverage(
        config_file=str(config), data_file=str(tmp_path / ".coverage")
    )
    assert not cov.config.dynamic_context
    assert cov.config.branch is True
    full = coverage.Coverage(
        config_file=str(PYPROJECT), data_file=str(tmp_path / ".coverage-full")
    )
    assert cov.config.run_omit == full.config.run_omit
    assert cov.config.report_omit == full.config.report_omit
    assert cov.config.exclude_list == full.config.exclude_list
