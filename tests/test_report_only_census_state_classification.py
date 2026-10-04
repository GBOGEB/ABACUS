"""Regression tests for report-only MIP state classification."""

from pathlib import Path

from scripts.test_admission_census import (
    classify_report_only_state,
    junit_counts_and_states,
)


def _write_junit(path: Path, cases: str) -> Path:
    path.write_text(
        '<?xml version="1.0" encoding="utf-8"?>'
        '<testsuites><testsuite name="synthetic">'
        f"{cases}"
        "</testsuite></testsuites>",
        encoding="utf-8",
    )
    return path


def test_all_config_blocked_skips_preserve_governed_state(tmp_path):
    junit = _write_junit(
        tmp_path / "config.xml",
        (
            '<testcase name="a"><properties>'
            '<property name="test_state" value="TEST_BLOCKED_CONFIG"/>'
            '</properties><skipped message="disabled"/></testcase>'
            '<testcase name="b"><properties>'
            '<property name="test_state" value="TEST_BLOCKED_CONFIG"/>'
            '</properties><skipped message="disabled"/></testcase>'
        ),
    )

    counts, states = junit_counts_and_states(junit)

    assert counts == {"pass": 0, "fail": 0, "error": 0, "skip": 2}
    assert states == {"TEST_BLOCKED_CONFIG": 2}
    assert classify_report_only_state(counts, states, 0) == "TEST_BLOCKED_CONFIG"


def test_skip_message_fallback_preserves_governed_state(tmp_path):
    junit = _write_junit(
        tmp_path / "source.xml",
        (
            '<testcase name="a">'
            '<skipped message="TEST_BLOCKED_SOURCE_MISSING: fixture absent"/>'
            "</testcase>"
        ),
    )

    counts, states = junit_counts_and_states(junit)

    assert states == {"TEST_BLOCKED_SOURCE_MISSING": 1}
    assert (
        classify_report_only_state(counts, states, 0)
        == "TEST_BLOCKED_SOURCE_MISSING"
    )


def test_unclassified_skip_remains_uncollected(tmp_path):
    junit = _write_junit(
        tmp_path / "unclassified.xml",
        '<testcase name="a"><skipped message="not classified"/></testcase>',
    )

    counts, states = junit_counts_and_states(junit)

    assert states == {}
    assert classify_report_only_state(counts, states, 0) == "TEST_EXISTS_UNCOLLECTED"


def test_any_passing_case_makes_report_only_file_green(tmp_path):
    junit = _write_junit(
        tmp_path / "mixed.xml",
        (
            '<testcase name="pass"/>'
            '<testcase name="skip"><properties>'
            '<property name="test_state" value="TEST_BLOCKED_CONFIG"/>'
            '</properties><skipped message="disabled"/></testcase>'
        ),
    )

    counts, states = junit_counts_and_states(junit)

    assert counts["pass"] == 1
    assert counts["skip"] == 1
    assert classify_report_only_state(counts, states, 0) == "TEST_GREEN"
