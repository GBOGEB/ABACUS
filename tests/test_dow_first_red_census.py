"""Regression tests for DOW log provenance, fan-out and UNKNOWN semantics."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from dow_first_red_census import census, downstream_jobs

SHA = "a" * 40
WORKFLOW = """
jobs:
  lint-and-validate:
    name: Lint & Validate
    runs-on: ubuntu-latest
  ci-ubuntu:
    needs: lint-and-validate
  ci-rhel-8:
    needs: lint-and-validate
  ci-rhel-9:
    needs: lint-and-validate
  dmaic-full-cycle:
    needs: [ci-ubuntu, ci-rhel-8, ci-rhel-9]
  build-artifacts:
    needs: dmaic-full-cycle
  release:
    needs: build-artifacts
"""
LOG = """2026-10-14T12:27:36.10Z fix end of files.........................................Failed
2026-10-14T12:27:36.11Z - hook id: end-of-file-fixer
2026-10-14T12:27:36.12Z Fixing scripts/preview_diff.py
2026-10-14T12:27:37.01Z trim trailing whitespace....................................Failed
2026-10-14T12:27:37.02Z - hook id: trailing-whitespace
2026-10-14T12:27:37.03Z Fixing DMAIC_ITERATION_3_ERROR_ANALYSIS.md
2026-10-14T12:27:43.00Z ABACUS TestPilot fast preflight.............................Failed
2026-10-14T12:27:43.01Z - hook id: abacus-testpilot-fast
"""


def produce(log=LOG, workflow=WORKFLOW, sha=SHA):
    return census(log, workflow, source_sha=sha, run_id="38563034546", run_attempt="1")


def test_classifies_three_failed_hooks_with_exact_identity():
    result = produce()
    assert result["source"]["sha"] == SHA
    assert result["observation"]["failed_hook_signatures"] == 3
    assert result["observation"]["first_red"] == "end-of-file-fixer"
    assert {h["hook_id"] for h in result["observation"]["failed_hooks"]} == {
        "end-of-file-fixer", "trailing-whitespace", "abacus-testpilot-fast"}
    assert result["observation"]["unique_modified_files"] == 2


def test_reaches_six_downstream_but_does_not_fabricate_skips():
    result = produce()
    assert result["graph"]["potential_downstream_count"] == 6
    assert result["graph"]["observed_downstream_skipped"] is None
    assert result["admission"]["root_cause_closed_count"] is None
    assert result["admission"]["crew_launch_verified"] is None


def test_no_log_remains_unknown_not_zero():
    result = produce(log="GitHub checkout unavailable")
    assert result["observation"]["status"] == "UNKNOWN_INCOMPLETE_LOG"
    assert result["observation"]["failed_hook_signatures"] is None


def test_rejects_partial_sha_and_unknown_edges():
    with pytest.raises(ValueError, match="40-character"):
        produce(sha="deadbeef")
    with pytest.raises(ValueError, match="Unknown dependency"):
        downstream_jobs({"lint-and-validate": {}, "bad": {"needs": ["absent"]}}, "lint-and-validate")


def test_deterministic_repeated_receipt():
    assert produce() == produce()
