"""W29 branch/fault-injection coverage of fail-closed native temporal evidence."""

from __future__ import annotations

import json

import pytest

from scripts import cbd_coverage_temporal_gate as gate

HEAD = "a" * 40
STAMP = 'timestamp="2026-10-17T10:00:00+00:00" time="1"'


def case(name, *, classname="suite", outcome=""):
    tag = "" if not outcome else f"<{outcome}/>"
    return f'<testcase classname="{classname}" name="{name}">{tag}</testcase>'


def suite(cases, *, tests=None, failures=0, errors=0, skipped=0, stamp=STAMP):
    declared = len(cases) if tests is None else tests
    return (
        f'<testsuite tests="{declared}" failures="{failures}" errors="{errors}" '
        f'skipped="{skipped}" {stamp}>' + "".join(cases) + "</testsuite>"
    )


def coverage(*, stamp="2026-10-17T10:00:02Z"):
    return {
        "meta": {"branch_coverage": True, "timestamp": stamp},
        "files": {
            path: {
                "summary": {
                    "covered_lines": 2,
                    "num_statements": 4,
                    "covered_branches": 1,
                    "num_branches": 2,
                }
            }
            for path in gate.TARGETS
        },
    }


def check(junit, *, sample=None):
    return gate.measure(
        coverage() if sample is None else sample,
        junit,
        {"exact_sha": HEAD},
        {"exact_sha": HEAD},
        expected_sha=HEAD,
    )


def test_positive_two_distinct_executed_cases_are_eligible_for_review():
    report = check(suite([case("one"), case("two")]))
    assert report["status"] == "ELIGIBLE_FOR_MATCHED_COVERAGE_REVIEW"
    assert report["junit_count_integrity"] == "PASS"
    assert (
        report["junit_test_cases_declared"],
        report["junit_test_cases_observed"],
        report["junit_test_cases_executed"],
    ) == (2, 2, 2)
    assert report["junit_test_cases_skipped"] == 0
    assert report["merge_admission"] == "HOLD"
    assert report["accepted_coverage_uplift"] is None


@pytest.mark.parametrize("bad_tag", ["failure", "error"])
@pytest.mark.parametrize("declared_count", [0, 1])
def test_force_trip_failed_case_cannot_be_fresh_eligible(bad_tag, declared_count):
    kw = (
        {"failures": declared_count}
        if bad_tag == "failure"
        else {"errors": declared_count}
    )
    xml = suite([case("bad", outcome=bad_tag)], **kw)
    with pytest.raises(ValueError, match="failed or errored"):
        check(xml)


@pytest.mark.parametrize("kind", ["failures", "errors"])
def test_force_trip_false_failure_header_cannot_invent_success(kind):
    with pytest.raises(ValueError, match="failed or errored"):
        check(suite([case("clean")], **{kind: 1}))


@pytest.mark.parametrize(
    "manifest",
    [
        suite([], tests=0),
        "<testsuites/>",
        "<not-junit/>",
    ],
)
def test_force_trip_missing_suite_or_zero_cases_is_not_green(manifest):
    with pytest.raises(ValueError, match="zero test cases|testsuite missing"):
        check(manifest)


@pytest.mark.parametrize(
    "xml",
    [
        suite([case("one", outcome="skipped")], skipped=1),
        suite([case("a", outcome="skipped"), case("b", outcome="skipped")], skipped=2),
    ],
)
def test_force_trip_all_skipped_is_not_an_executed_suite(xml):
    with pytest.raises(ValueError, match="zero independently executed"):
        check(xml)


def test_reverse_mixed_skip_and_success_remains_accountable():
    report = check(
        suite([case("real"), case("deferred", outcome="skipped")], skipped=1)
    )
    assert report["status"] == "ELIGIBLE_FOR_MATCHED_COVERAGE_REVIEW"
    assert report["junit_test_cases_executed"] == 1
    assert report["junit_test_cases_skipped"] == 1


@pytest.mark.parametrize(
    "xml",
    [
        suite([case("one")], tests=5),
        suite([case("one"), case("one")]),
        suite([case("one", classname="")]),
        suite([case("", classname="x")]),
        suite([case("one", outcome="skipped"), case("two")], skipped=0),
        suite([case("one"), case("two")], skipped=1),
    ],
)
def test_negative_untrustworthy_junit_identity_or_counts_are_held(xml):
    result = check(xml)
    assert result["status"] == "HOLD"
    assert result["junit_count_integrity"] == "MISMATCH"
    assert result["accepted_coverage_uplift"] is None


def test_force_trip_duplicate_ids_across_suites_cannot_gain_count():
    xml = (
        "<testsuites>"
        + suite([case("repeat")])
        + suite([case("repeat")])
        + "</testsuites>"
    )
    assert check(xml)["status"] == "HOLD"


def test_reverse_multisuite_distinct_ids_retains_total_executed_count():
    xml = (
        "<testsuites>"
        + suite([case("first")])
        + suite([case("second")])
        + "</testsuites>"
    )
    report = check(xml)
    assert report["status"] == "ELIGIBLE_FOR_MATCHED_COVERAGE_REVIEW"
    assert report["junit_test_cases_executed"] == 2


@pytest.mark.parametrize(
    "metadata", [None, [], {}, {"branch_coverage": False}, {"branch_coverage": 1}]
)
def test_force_trip_coverage_missing_branch_metadata(metadata):
    value = coverage()
    value["meta"] = metadata
    with pytest.raises(ValueError, match="metadata|branch coverage"):
        check(suite([case("one")]), sample=value)


@pytest.mark.parametrize(
    "broken",
    [
        '<!DOCTYPE testsuite [<!ENTITY x "expansion">]>'
        '<testsuite tests="1" failures="0" errors="0" skipped="0" '
        + STAMP
        + '><testcase classname="s" name="&x;"/></testsuite>',
        "<testsuite",
        "<testsuites><testsuite/></testsuites>",
    ],
)
def test_force_trip_xml_entity_or_structure_not_eligible(broken):
    with pytest.raises(Exception):
        check(broken)


def test_reverse_timezone_offset_and_equal_timestamp_remain_eligible():
    same = suite(
        [case("boundary")], stamp='timestamp="2026-10-17T12:00:00+02:00" time="0"'
    )
    result = check(same, sample=coverage(stamp="2026-10-17T10:00:00Z"))
    assert result["time_gap_seconds"] == 0
    assert result["status"] == "ELIGIBLE_FOR_MATCHED_COVERAGE_REVIEW"


def test_negative_stale_coverage_preserves_hold_even_with_all_clean_tests():
    report = check(
        suite([case("clean")]), sample=coverage(stamp="2026-10-17T09:59:59Z")
    )
    assert report["status"] == "HOLD"
    assert report["coverage_provenance"] == "STALE_BEFORE_TEST_COMPLETION"


def test_cli_failed_suite_refuses_to_publish_eligible_receipt(tmp_path):
    c = tmp_path / "coverage.json"
    j = tmp_path / "junit.xml"
    bind1 = tmp_path / "cov-bind.json"
    bind2 = tmp_path / "tests-bind.json"
    output = tmp_path / "no-receipt.json"
    c.write_text(json.dumps(coverage()), encoding="utf-8")
    j.write_text(
        suite([case("failed", outcome="failure")], failures=1), encoding="utf-8"
    )
    for path in (bind1, bind2):
        path.write_text(json.dumps({"exact_sha": HEAD}), encoding="utf-8")
    args = [
        "--coverage",
        str(c),
        "--junit",
        str(j),
        "--coverage-binding",
        str(bind1),
        "--test-binding",
        str(bind2),
        "--head",
        HEAD,
        "--out",
        str(output),
    ]
    with pytest.raises(ValueError, match="failed or errored"):
        gate.main(args)
    assert not output.exists()
