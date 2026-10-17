"""Adversarial denominator, timing and immutability tests for MIP telemetry.

These exercise the existing source-bound comparison implementation. They do not
certify merge admission, independent trials, or formal root closure.
"""

from datetime import datetime, timezone

import pytest

from tools.mip_ci_temporal_rollup import (
    check_coverage,
    check_forecast,
    compare,
    coverage_delta,
    integer,
    utc,
)

SHA_A = "a" * 40
SHA_B = "b" * 40
DIGEST = "c" * 64


def coverage(sha=SHA_A, *, lines=80, branches=30):
    return {
        "source_sha": sha,
        "scope_sha256": DIGEST,
        "config_sha256": DIGEST,
        "artifact_sha256": DIGEST,
        "tool_version": "coverage.py 7.x",
        "covered_lines": lines,
        "eligible_lines": 100,
        "covered_branches": branches,
        "eligible_branches": 40,
    }


def observation(wave, *, successes=20, n=20, terminal=True, samples=25):
    return {
        "wave": wave,
        "terminal": terminal,
        "workflow_count": n,
        "success_fraction": successes / n if terminal else None,
        "queue_basis": "job.created_at -> job.started_at",
        "queue_fallback_timestamp_samples": 0,
        "queue_samples": samples,
        "queue_p95_seconds": 60.0,
        "coverage": coverage(),
    }


@pytest.mark.parametrize("value", [True, False, -1, 1.0, "1", None])
def test_integer_identity_must_not_coerce_invalid_denominator(value):
    assert not integer(value, minimum=0)


@pytest.mark.parametrize(
    "value",
    [
        None,
        123,
        "2026-10-17T12:00:00+00:00",
        "2026-02-30T12:00:00Z",
        "2026-10-17T12:00:00+01:00Z",
    ],
)
def test_utc_rejects_missing_or_forged_timestamp(value):
    with pytest.raises(ValueError):
        utc(value)


def test_explicit_utc_timestamp_is_retained():
    assert utc("2026-10-17T12:00:00Z").utcoffset().total_seconds() == 0


@pytest.mark.parametrize(
    "key,value",
    [
        ("covered_lines", True),
        ("eligible_lines", -1),
        ("covered_lines", 101),
        ("eligible_branches", 10),
        ("source_sha", SHA_B),
        ("artifact_sha256", "bad-digest"),
        ("tool_version", "  "),
    ],
)
def test_bad_coverage_proof_never_creates_numerator(key, value):
    item = coverage()
    item[key] = value
    with pytest.raises(ValueError):
        check_coverage(item, SHA_A)


def test_missing_coverage_is_unknown_not_zero():
    assert check_coverage(None, SHA_A) is None
    before = observation(1)
    after = observation(2)
    after["coverage"] = None
    delta, reason = coverage_delta(before, after, "lines")
    assert delta is None
    assert "missing coverage" in reason


@pytest.mark.parametrize(
    "changed,expected_reason",
    [
        ({"scope_sha256": "d" * 64}, "scope_sha256"),
        ({"config_sha256": "d" * 64}, "config_sha256"),
        ({"tool_version": "coverage.py changed"}, "tool_version"),
        ({"eligible_lines": 101}, "denominator"),
        ({"eligible_lines": 0, "covered_lines": 0}, "denominator"),
    ],
)
def test_unmatched_cohort_cannot_claim_coverage_gain(changed, expected_reason):
    before = observation(1)
    after = observation(2)
    after["coverage"].update(changed)
    delta, reason = coverage_delta(before, after, "lines")
    assert delta is None
    assert expected_reason in reason


def test_negative_coverage_delta_remains_negative_not_clipped():
    before = observation(1)
    after = observation(2)
    after["coverage"]["covered_lines"] = 75
    delta, reason = coverage_delta(before, after, "lines")
    assert delta == -5.0
    assert reason is None
    assert compare(before, after)["accepted_main_coverage_delta_pp"] is None


@pytest.mark.parametrize("condition", ["pending", "denominator", "fallback", "small"])
def test_queue_gain_is_unqualified_when_evidence_is_weak(condition):
    before = observation(1)
    after = observation(2)
    if condition == "pending":
        after["terminal"] = False
        after["success_fraction"] = None
    elif condition == "denominator":
        after["workflow_count"] = 21
    elif condition == "fallback":
        after["queue_fallback_timestamp_samples"] = 1
    else:
        after["queue_samples"] = 19
    assert compare(before, after)["queue_p95_delta_seconds"] is None


def test_comparable_queue_is_descriptive_not_independent_proof():
    before = observation(1)
    after = observation(2)
    after["queue_p95_seconds"] = 35.0
    result = compare(before, after)
    assert result["queue_p95_delta_seconds"] == -25.0
    assert result["queue_comparability"] == "descriptive_only_not_independent"
    assert result["verified_formal_root_closures"] is None


def test_forecast_rejects_boolean_probability_without_fabricating_trial():
    by_wave = {
        1: {
            "source_sha": SHA_A,
            "timestamp": datetime(2026, 10, 17, 12, tzinfo=timezone.utc),
            "success_fraction": 1.0,
        }
    }
    row = {
        "method": "persistence-v1",
        "issued_wave": 1,
        "target_wave": 2,
        "issued_source_sha": SHA_A,
        "issued_at": "2026-10-17T12:01:00Z",
        "prediction": True,
    }
    with pytest.raises(ValueError):
        check_forecast(row, by_wave)
