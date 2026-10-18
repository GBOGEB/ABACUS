"""Negative/reverse controls for source-bound W27 native TestPilot testflight."""
from __future__ import annotations

from pathlib import Path

import yaml

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/w26-testpilot-matched-coverage.yml"


def _job():
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return workflow["jobs"]["matched-testpilot"]


def _step(name):
    matches = [step for step in _job()["steps"] if step.get("name") == name]
    assert len(matches) == 1, (name, len(matches))
    return matches[0]


def test_positive_four_real_os_python_matrix_cells():
    cells = _job()["strategy"]["matrix"]["include"]
    assert len(cells) == 4
    assert {(c["os"], c["python"]) for c in cells} == {
        ("ubuntu-latest", "3.10"),
        ("ubuntu-latest", "3.11"),
        ("ubuntu-latest", "3.12"),
        ("windows-latest", "3.11"),
    }


def test_force_trip_python_matrix_is_bound_to_setup_action():
    setup = _step("Set up matrix Python interpreter")
    assert setup["uses"] == "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97"
    assert setup["with"]["python-version"] == "${{ matrix.python }}"
    assert "sys.version_info[:2] == expected" in _step("Verify selected Python minor version")["run"]


def test_force_trip_pytest_conftest_numpy_dependency_is_pinned():
    install = _step("Install focused tools")["run"]
    assert "numpy==1.26.4" in install
    assert "pytest==9.1.1" in install
    assert "coverage==7.16.2" in install
    assert "defusedxml==0.7.1" in install


def test_force_trip_exact_checkout_and_revision_guard_retained():
    checkout = _step("Checkout source-owned exact head")
    expected = "${{ github.event.pull_request.head.sha || github.sha }}"
    assert checkout["with"]["ref"] == expected
    assert checkout["with"]["persist-credentials"] is False
    verify = _step("Verify exact head")
    assert verify["env"]["EXPECTED_SHA"] == expected
    assert 'git rev-parse HEAD' in verify["run"]
    assert '"$EXPECTED_SHA"' in verify["run"]


def test_force_trip_evidence_binds_run_attempt_and_fails_on_missing_files():
    upload = _step("Upload exact-head per-cell receipts")
    assert upload["with"]["if-no-files-found"] == "error"
    for ident in ("github.run_id", "github.run_attempt", "matrix.python", "matrix.os"):
        assert ident in upload["with"]["name"]
    assert "w26-*-junit.xml" in upload["with"]["path"]
    assert "w26-*-coverage.json" in upload["with"]["path"]


def test_positive_baseline_and_expanded_coverage_same_module():
    base = _step("Measure baseline on this same exact head")["run"]
    expand = _step("Measure expanded test family on identical source")["run"]
    for command in (base, expand):
        assert "coverage erase" in command
        assert "--source=scripts.testpilot_preflight" in command
        assert "--branch" in command
    assert "tests/test_testpilot_adversarial_coverage.py" not in base
    assert "tests/test_testpilot_adversarial_coverage.py" in expand


def test_reverse_denominator_and_head_guard_not_omitted():
    compare = _step("Fail closed on mismatched denominators or false uplift")["run"]
    assert "--exact-head" in compare
    assert '"$EXPECTED_SHA"' in compare
    assert "--base-junit" in compare
    assert "--expanded-junit" in compare
    assert "--output w26-matched-coverage.json" in compare
