"""Regression tests for Phase 9 fail-closed output prerequisites."""

import json
from pathlib import Path

import pytest

from DMAIC_V3.phases.phase9_documentation_generation import (
    Phase9_DocumentationGeneration,
)


@pytest.mark.parametrize("present", [(), ("phase1_define",), ("phase2_measure",)])
def test_missing_required_phase_prevents_documentation(tmp_path: Path, present):
    phase = Phase9_DocumentationGeneration()
    phase.output_dir = tmp_path / "output"
    iteration_dir = phase.output_dir / "iteration_7"
    for name in present:
        directory = iteration_dir / name
        directory.mkdir(parents=True)
        (directory / f"{name}.json").write_text("{}", encoding="utf-8")

    assert phase._verify_execution_success(7) is False
    ok, receipt = phase.execute(7)
    assert ok is False
    assert receipt["status"] == "skipped"
    assert receipt["reason"] == "execution_not_successful"
    saved = iteration_dir / "phase9_documentation_generation" / "phase9_documentation_generation.json"
    assert json.loads(saved.read_text(encoding="utf-8"))["reason"] == receipt["reason"]


def test_both_required_phase_receipts_allow_prerequisite(tmp_path: Path):
    phase = Phase9_DocumentationGeneration()
    phase.output_dir = tmp_path / "output"
    iteration_dir = phase.output_dir / "iteration_3"
    for name in ("phase1_define", "phase2_measure"):
        directory = iteration_dir / name
        directory.mkdir(parents=True)
        (directory / f"{name}.json").write_text("{}", encoding="utf-8")

    assert phase._verify_execution_success(3) is True
