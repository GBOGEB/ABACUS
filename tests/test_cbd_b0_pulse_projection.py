"""Five-run source-bound three-pulse burndown validation and negatives."""
import copy
import json
from pathlib import Path

import pytest

from scripts import cbd_b0_pulse_projection as b0

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "docs/ci/CBD_B0_THREE_PULSE_NATIVE_CENSUS_20261017.json"
)


@pytest.fixture
def evidence():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_five_workflows_65_native_jobs_have_fixed_denominators(evidence):
    result = b0.project(evidence)
    assert result["sampled_runs"] == 5
    assert result["sampled_native_jobs"] == 65
    assert result["native_successful_jobs"] == 59
    assert result["native_failed_jobs"] == 6
    assert result["workflow_successes"] == 2
    assert result["workflow_failures"] == 3


def test_first_red_producer_is_not_same_as_summary_failure(evidence):
    result = b0.project(evidence)
    assert result["failed_first_red_producer_jobs"] == 3
    assert result["downstream_summary_failures"] == 3
    assert result["distinct_failing_test_signatures"] == 1
    assert result["failing_test_manifestations"] == 3
    assert list(result["first_red_cases"]) == [b0.FIRST_RED]


def test_cross_source_fix_verified_but_not_an_independent_trial(evidence):
    before_after = b0.project(evidence)["baseline_to_owned_repair"]
    assert before_after["old_pr"] == 2104
    assert before_after["new_pr"] == 2107
    assert before_after["old_success_jobs"] == 11
    assert before_after["new_success_jobs"] == 13
    assert before_after["workflow_result_changed_to_pass"]
    assert before_after["same_head_trial"] is False
    assert before_after["population_effect_size"] is None
    assert before_after["main_merge"] is False


def test_coverage_closure_queue_and_merge_unproven(evidence):
    result = b0.project(evidence)
    assert result["changed_line_coverage_percent"] is None
    assert result["branch_coverage_percent"] is None
    assert result["statement_coverage_percent"] is None
    assert result["independent_causal_root_count"] is None
    assert result["fresh_clone_parity_proven"] is None
    assert result["security_governance_a10_admission"] == "HOLD"
    assert result["statistical_validity"][
        "different_heads_not_independent_trials"
    ] is True
    assert all(entry["actual_queue_wait_ms"] is None
               for entry in result["timeline"])


def test_read_only_projection_deterministic(evidence):
    prior = copy.deepcopy(evidence)
    assert b0.project(evidence) == b0.project(evidence)
    assert evidence == prior


def test_duplicate_native_run_rejected(evidence):
    evidence["records"][1]["run_id"] = evidence["records"][0]["run_id"]
    with pytest.raises(ValueError, match="duplicate run"):
        b0.project(evidence)


def test_head_sha_rejected_when_malformed(evidence):
    evidence["records"][0]["source_sha"] = "a" * 39
    with pytest.raises(ValueError, match="exact source head"):
        b0.project(evidence)


def test_boolean_attempt_fails_closed(evidence):
    evidence["records"][0]["run_attempt"] = True
    with pytest.raises(ValueError, match="run attempt"):
        b0.project(evidence)


def test_unknown_or_incomplete_jobs_rejected(evidence):
    evidence["records"][0]["job_total"] = 12
    with pytest.raises(ValueError, match="job denominator"):
        b0.project(evidence)


def test_forged_merge_authority_rejected(evidence):
    evidence["authority"]["merge_admission"] = "PASS"
    with pytest.raises(ValueError, match="authority"):
        b0.project(evidence)


def test_forged_new_first_red_case_rejected(evidence):
    row = next(r for r in evidence["records"] if r["conclusion"] == "failure")
    row["first_red_case"] = "tests/test_fake.py::test_fake"
    with pytest.raises(ValueError, match="first-red"):
        b0.project(evidence)


def test_summary_job_cannot_be_marked_upstream(evidence):
    row = next(r for r in evidence["records"] if r["conclusion"] == "failure")
    row["failed_jobs"][1]["name"] = "B0 canonical coverage producer"
    with pytest.raises(ValueError, match="downstream summary"):
        b0.project(evidence)


def test_successful_workflow_cannot_lose_failed_job_denominator(evidence):
    row = next(r for r in evidence["records"] if r["conclusion"] == "success")
    row["success_jobs"] -= 1
    with pytest.raises(ValueError, match="job denominator"):
        b0.project(evidence)


def test_invalid_test_summary_does_not_promote_counts(evidence):
    row = next(r for r in evidence["records"] if r["conclusion"] == "failure")
    row["test_summary"]["failed"] = 0
    with pytest.raises(ValueError, match="outcome contradicts"):
        b0.project(evidence)


@pytest.mark.parametrize("date", ["2026-10-17T10:20:52", "not-a-time", None])
def test_bad_utc_timestamp_denied(date, evidence):
    evidence["records"][0]["created_at"] = date
    with pytest.raises(ValueError, match="timestamp"):
        b0.project(evidence)


def test_negative_elapsed_time_denied(evidence):
    evidence["records"][0]["updated_at"] = "2026-01-01T00:00:00Z"
    with pytest.raises(ValueError, match="inverted workflow timestamps"):
        b0.project(evidence)


def test_missing_first_red_identity_fails_closed(evidence):
    row = next(r for r in evidence["records"] if r["conclusion"] == "failure")
    row["first_red_case"] = None
    with pytest.raises(ValueError, match="first-red"):
        b0.project(evidence)
