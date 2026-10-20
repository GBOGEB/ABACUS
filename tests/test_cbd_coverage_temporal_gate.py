"""Adversarial tests for source-bound coverage freshness and counters."""
import json

import pytest

from scripts import cbd_coverage_temporal_gate as gate
SHA = "a" * 40


def coverage(at="2026-10-17T10:10:52Z", covered=(100, 80)):
    return {
        "meta": {"branch_coverage": True, "timestamp": at},
        "files": {
            path: {
                "summary": {
                    "covered_lines": covered[i],
                    "num_statements": (165, 104)[i],
                    "covered_branches": (30, 25)[i],
                    "num_branches": (56, 38)[i],
                }
            }
            for i, path in enumerate(gate.TARGETS)
        },
    }


def junit(at="2026-10-17T10:05:26.426899+00:00", elapsed="324.007"):
    return (
        '<testsuites><testsuite tests="2" failures="0" '
        f'timestamp="{at}" time="{elapsed}"><testcase classname="test_temporal" name="a"/>'
        '<testcase classname="test_temporal" name="b"/></testsuite></testsuites>'
    )


def evaluate(c=None, j=None, cover_sha=SHA, test_sha=SHA):
    return gate.measure(
        coverage() if c is None else c,
        junit() if j is None else j,
        {"exact_sha": cover_sha},
        {"exact_sha": test_sha},
        expected_sha=SHA,
    )


def test_github_snapshot_predates_junit_end_by_minutes():
    result = evaluate(c=coverage(at="2026-10-17T10:06:20.318184"))
    assert result["status"] == "HOLD"
    assert result["coverage_provenance"] == "STALE_BEFORE_TEST_COMPLETION"
    assert result["time_gap_seconds"] < -200
    assert result["accepted_coverage_uplift"] is None


def test_post_suite_evidence_is_eligible_only_for_review():
    result = evaluate()
    assert result["status"] == "ELIGIBLE_FOR_MATCHED_COVERAGE_REVIEW"
    assert result["covered_target_statements"] == 180
    assert result["eligible_target_statements"] == 269
    assert result["covered_target_branches"] == 55
    assert result["eligible_target_branches"] == 94
    assert result["merge_admission"] == "HOLD"
    assert result["root_closure_credit"] is None
    assert result["junit_test_cases_executed"] == 2
    assert result["junit_test_cases_skipped"] == 0


@pytest.mark.parametrize("which", ["coverage", "tests"])
def test_foreign_head_rejected(which):
    sha = "b" * 40
    with pytest.raises(ValueError, match="bound to exact head"):
        if which == "coverage":
            evaluate(cover_sha=sha)
        else:
            evaluate(test_sha=sha)


@pytest.mark.parametrize("bad", [True, -1, 166, "100", None])
def test_false_numerators_rejected(bad):
    c = coverage()
    c["files"][gate.TARGETS[0]]["summary"]["covered_lines"] = bad
    with pytest.raises(ValueError):
        evaluate(c=c)


def test_missing_source_or_branch_count_is_not_green():
    c = coverage()
    c["files"].pop(gate.TARGETS[0])
    with pytest.raises(ValueError, match="target coverage file missing"):
        evaluate(c=c)
    c = coverage()
    c["files"][gate.TARGETS[0]]["summary"].pop("covered_branches")
    with pytest.raises(ValueError, match="non-integer"):
        evaluate(c=c)


@pytest.mark.parametrize("elapsed", ["nan", "-1", "86400", "invalid"])
def test_invalid_junit_durations_rejected(elapsed):
    with pytest.raises(ValueError, match="invalid suite duration"):
        evaluate(j=junit(elapsed=elapsed))


def test_temporal_equality_boundary_is_eligible():
    result = evaluate(
        c=coverage(at="2026-10-17T10:06:00Z"),
        j=junit(at="2026-10-17T10:05:00Z", elapsed="60"),
    )
    assert result["time_gap_seconds"] == 0
    assert result["status"] == "ELIGIBLE_FOR_MATCHED_COVERAGE_REVIEW"


def test_zero_coverage_never_creates_derived_gain():
    result = evaluate(c=coverage(covered=(0, 0)))
    assert result["covered_target_statements"] == 0
    assert result["accepted_coverage_uplift"] is None


def test_missing_branch_instrumentation_and_fake_head_rejected():
    c = coverage()
    c["meta"]["branch_coverage"] = False
    with pytest.raises(ValueError, match="branch coverage"):
        evaluate(c=c)
    with pytest.raises(ValueError, match="invalid exact source head"):
        gate.measure(coverage(), junit(), {"exact_sha": SHA},
                     {"exact_sha": SHA}, expected_sha="deadbeef")


def test_cli_stale_receipt_exits_nonzero(tmp_path, capsys):
    documents = {
        "coverage": coverage(at="2026-10-17T10:06:20Z"),
        "coverage_binding": {"exact_sha": SHA},
        "test_binding": {"exact_sha": SHA},
    }
    for key, value in documents.items():
        (tmp_path / f"{key}.json").write_text(json.dumps(value))
    (tmp_path / "junit.xml").write_text(junit())
    output = tmp_path / "receipt.json"
    args = [
        "--coverage", str(tmp_path / "coverage.json"),
        "--coverage-binding", str(tmp_path / "coverage_binding.json"),
        "--test-binding", str(tmp_path / "test_binding.json"),
        "--junit", str(tmp_path / "junit.xml"),
        "--head", SHA, "--out", str(output),
    ]
    assert gate.main(args) == 2
    assert json.loads(output.read_text())["status"] == "HOLD"
    assert "HOLD" in capsys.readouterr().out


def test_inflated_junit_header_is_nonadmissible():
    bad = junit().replace('tests="2"', 'tests="14"')
    result = evaluate(j=bad)
    assert result["junit_count_integrity"] == "MISMATCH"
    assert result["status"] == "HOLD"
    assert result["accepted_coverage_uplift"] is None
