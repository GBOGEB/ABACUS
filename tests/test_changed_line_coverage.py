"""Positive and negative cases for source-bound changed-line coverage."""
from pathlib import Path

from scripts import measure_changed_line_coverage as diffcov


def _fixture(tmp_path: Path, hits: tuple[int, int]) -> Path:
    path = tmp_path / "coverage.xml"
    path.write_text(
        '<coverage><packages><package><classes>'
        '<class filename="scripts/sample.py"><lines>'
        f'<line number="10" hits="{hits[0]}"/>'
        f'<line number="11" hits="{hits[1]}"/>'
        '</lines></class></classes></package></packages></coverage>',
        encoding="utf-8",
    )
    return path


def test_changed_line_coverage_counts_executed_and_missed(tmp_path, monkeypatch):
    def fake_git(args, **kwargs):
        if args[1] == "rev-parse":
            return "a" * 40 + "\n"
        return "+++ b/scripts/sample.py\n@@ -9,0 +10,2 @@\n+first\n+second\n"
    monkeypatch.setattr(diffcov.subprocess, "check_output", fake_git)
    result = diffcov.measure(_fixture(tmp_path, (1, 0)), "b" * 40, tmp_path)
    assert result["exact_sha"] == "a" * 40
    assert result["eligible_lines"] == 2
    assert result["covered_lines"] == 1
    assert result["percent"] == 50.0
    assert result["uncovered"] == ["scripts/sample.py:11"]


def test_zero_changed_executable_lines_never_claims_full_coverage(tmp_path, monkeypatch):
    monkeypatch.setattr(
        diffcov.subprocess, "check_output",
        lambda args, **kwargs: "a" * 40 if args[1] == "rev-parse" else "",
    )
    result = diffcov.measure(_fixture(tmp_path, (1, 1)), "b" * 40, tmp_path)
    assert result["status"] == "NO_ELIGIBLE_CHANGED_LINES"
    assert result["percent"] is None
    assert result["eligible_lines"] == 0


def test_changed_line_coverage_accepts_src_prefix(tmp_path, monkeypatch):
    monkeypatch.setattr(
        diffcov.subprocess, "check_output",
        lambda args, **kwargs: "a" * 40 if args[1] == "rev-parse"
        else "+++ b/src/scripts/sample.py\n@@ -0,0 +10 @@\n+line\n",
    )
    result = diffcov.measure(_fixture(tmp_path, (1, 0)), "b" * 40, tmp_path)
    assert result["covered_lines"] == 1
    assert result["eligible_lines"] == 1
    assert result["percent"] == 100.0


def test_uninstrumented_changed_source_blocks_measured_percentage(tmp_path, monkeypatch):
    """Missing XML source must not silently disappear from denominator."""
    monkeypatch.setattr(
        diffcov.subprocess, "check_output",
        lambda args, **kwargs: "a" * 40 if args[1] == "rev-parse"
        else "+++ b/scripts/sample.py\n@@ -9,0 +10 @@\n+covered\n"
        "+++ b/scripts/unseen.py\n@@ -0,0 +1 @@\n+untested\n",
    )
    result = diffcov.measure(_fixture(tmp_path, (1, 1)), "b" * 40, tmp_path)
    assert result["status"] == "INCOMPLETE_INSTRUMENTATION"
    assert result["missing_source_files"] == ["scripts/unseen.py"]
    assert result["percent"] is None
    assert result["covered_lines"] == 1
