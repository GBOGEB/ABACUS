"""W29 independent negative controls for same-head branch-coverage acceptance."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from tools.recovery import w29_temporal_native_compare as m

SHA = "a" * 40
T0 = datetime(2026, 10, 17, 10, 0, 0, tzinfo=timezone.utc)
OLD = {
    "num_statements": 120,
    "covered_lines": 95,
    "num_branches": 80,
    "covered_branches": 45,
}
NEW = {
    "num_statements": 120,
    "covered_lines": 99,
    "num_branches": 80,
    "covered_branches": 60,
}
TEST_OLD = {"declared": 14, "observed": 14, "executed": 14, "skipped": 0}
TEST_NEW = {"declared": 40, "observed": 40, "executed": 40, "skipped": 0}


def metrics(
    before=OLD,
    after=NEW,
    old_tests=TEST_OLD,
    new_tests=TEST_NEW,
    *,
    old_time=None,
    new_time=None,
    old_finished=None,
    new_finished=None,
    sha=SHA,
):
    left = (before, old_time or T0 + timedelta(seconds=10), "1" * 64)
    right = (after, new_time or T0 + timedelta(seconds=20), "2" * 64)
    jleft = (old_tests, old_finished or T0, "3" * 64)
    jright = (new_tests, new_finished or T0, "4" * 64)
    return m.compare(left, right, jleft, jright, exact_head=sha)


def native_cov(
    tmp_path, *, totals=OLD, source=m.SOURCE, branch=True, stamp="2026-10-17T10:00:20Z"
):
    doc = {
        "meta": {"branch_coverage": branch, "timestamp": stamp},
        "files": {source: {"summary": dict(totals)}},
        "totals": dict(totals),
    }
    p = tmp_path / "c.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    return p


def native_junit(tmp_path, *, cases=2, declared=None, failed=False):
    count = cases if declared is None else declared
    entries = "".join(
        f'<testcase classname="suite" name="test_{i}"/>' for i in range(cases)
    )
    if failed:
        entries = '<testcase classname="suite" name="failed"><failure/></testcase>'
    p = tmp_path / "j.xml"
    p.write_text(
        '<testsuite timestamp="2026-10-17T10:00:00+00:00" time="1" '
        f'tests="{count}" failures="{1 if failed else 0}" errors="0" skipped="0">'
        + entries
        + "</testsuite>",
        encoding="utf-8",
    )
    return p


def test_positive_matched_growth_retains_true_denominators_and_sha():
    receipt = metrics()
    assert receipt["delta"]["covered_statements"] == 4
    assert receipt["delta"]["covered_branches"] == 15
    assert receipt["delta"]["new_executed_test_cases"] == 26
    assert receipt["delta"]["combined_eligible"] == 200
    assert receipt["delta"]["combined_delta_pp"] == 9.5
    assert receipt["exact_head"] == SHA
    assert receipt["global_main_coverage_delta"] is None
    assert receipt["pr_changed_line_coverage_delta"] is None
    assert receipt["merge_admission"] == "HOLD"


@pytest.mark.parametrize("head", ["", "garbage", "a" * 39, "a" * 41, "A" * 40])
def test_force_trip_unpinned_head_not_admissible(head):
    with pytest.raises(ValueError, match="head"):
        metrics(sha=head)


@pytest.mark.parametrize(
    "path",
    [
        "elsewhere/file.py",
        "./scripts/cbd_coverage_temporal_gate.py",
        "../scripts/cbd_coverage_temporal_gate.py",
        "scripts/../scripts/cbd_coverage_temporal_gate.py",
    ],
)
def test_force_trip_coverage_path_alias_or_escape_rejected(tmp_path, path):
    with pytest.raises(ValueError, match="unexpected source"):
        m.coverage_from(native_cov(tmp_path, source=path))


@pytest.mark.parametrize(
    "changed",
    [
        {"num_statements": 121},
        {"num_branches": 81},
    ],
)
def test_reverse_denominator_drift_cannot_inflate_growth(changed):
    with pytest.raises(ValueError, match="unmatched"):
        metrics(after={**NEW, **changed})


@pytest.mark.parametrize("bad", [None, -1, False, "60", 201])
def test_negative_corrupt_branch_population_fails_closed(tmp_path, bad):
    data = dict(OLD, covered_branches=bad)
    with pytest.raises(ValueError, match="counter|exceeds"):
        m.coverage_from(native_cov(tmp_path, totals=data))


def test_negative_source_global_counter_divergence(tmp_path):
    file = native_cov(tmp_path)
    doc = json.loads(file.read_text())
    doc["files"][m.SOURCE]["summary"]["covered_branches"] -= 1
    file.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match="source/global"):
        m.coverage_from(file)


def test_reverse_coverage_windows_native_exact_module_path(tmp_path):
    filename = m.SOURCE.replace("/", "\\")
    values, when, digest = m.coverage_from(native_cov(tmp_path, source=filename))
    assert values == OLD and when.tzinfo is not None and len(digest) == 64


def test_force_trip_no_new_branch_coverage_fails():
    with pytest.raises(ValueError, match="no measured branch"):
        metrics(after={**NEW, "covered_branches": OLD["covered_branches"]})


def test_force_trip_branch_regression_fails_even_if_statement_gain():
    with pytest.raises(ValueError, match="coverage regression"):
        metrics(after={**NEW, "covered_branches": OLD["covered_branches"] - 1})


def test_force_trip_same_executed_test_denominator_not_uplift():
    with pytest.raises(ValueError, match="no independently executed"):
        metrics(new_tests=TEST_OLD)


def test_force_trip_stale_coverage_json_rejected():
    with pytest.raises(ValueError, match="predates"):
        metrics(new_time=T0, new_finished=T0 + timedelta(seconds=2))


@pytest.mark.parametrize(
    "tamper",
    [
        {"meta": {"branch_coverage": False}},
        {"meta": {}},
        {"files": {}},
        {"files": []},
        {"totals": {"num_statements": False}},
    ],
)
def test_force_trip_invalid_coverage_shape_rejected(tmp_path, tamper):
    p = native_cov(tmp_path)
    d = json.loads(p.read_text(encoding="utf-8"))
    d.update(tamper)
    p.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(ValueError):
        m.coverage_from(p)


def test_positive_native_junit_census_and_sha256(tmp_path):
    rows, ended, digest = m.junit_from(native_junit(tmp_path))
    assert rows["executed"] == 2 and rows["skipped"] == 0
    assert ended.tzinfo is not None and len(digest) == 64


def test_force_trip_fake_junit_header_cannot_claim_extra_tests(tmp_path):
    with pytest.raises(ValueError, match="identity/case counts"):
        m.junit_from(native_junit(tmp_path, declared=25))


def test_force_trip_failed_junit_is_not_an_accepted_coverage_sample(tmp_path):
    with pytest.raises(ValueError, match="failed or errored"):
        m.junit_from(native_junit(tmp_path, cases=1, failed=True))
