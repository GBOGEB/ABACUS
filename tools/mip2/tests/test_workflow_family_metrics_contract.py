"""Bounded source-owned MIP2 qualification of repeat-aware workflow accounting."""
import pytest

from tools.mip2.workflow_family_metrics import summarize_families


def run(ident, workflow, status="completed", conclusion="success", attempt=1):
    return {"id": ident, "workflow_id": workflow, "run_attempt": attempt,
            "status": status, "conclusion": conclusion}


def test_twelve_qps_runs_are_one_family():
    rows = [run(i, 350890474) for i in range(1, 13)]
    rows.append(run(50, 1000, conclusion="failure"))
    x = summarize_families(rows)
    assert x["total_runs"] == 13
    assert x["distinct_workflows"] == 2
    assert x["repeated_executions"] == 11
    assert x["success_excess_from_repeat_runs"] == 11


def test_terminal_fraction_excludes_no_queued_in_denominator():
    rows = [run(1, 2), run(2, 3, "queued", None)]
    x = summarize_families(rows)
    assert x["success_over_all_runs"] == 0.5
    assert x["success_over_terminal_runs"] == 1.0
    assert x["run_nonterminal"] == 1
    assert x["family_clean_success"] == 1


def test_cancelled_is_not_a_failure_or_verified_root():
    x = summarize_families([run(1, 2, conclusion="cancelled")])
    assert x["run_failure"] == 0
    assert x["family_any_cancelled"] == 1
    assert x["verified_root_closure"] is None


def test_mixed_green_red_family_never_clean_green():
    x = summarize_families([run(1, 2), run(2, 2, conclusion="failure")])
    assert x["family_clean_success"] == 0
    assert x["family_any_failure"] == 1


def test_duplicate_run_id_fails_closed():
    with pytest.raises(ValueError, match="duplicate run"):
        summarize_families([run(1, 2), run(1, 2, attempt=2)])


def test_out_of_range_attempt_fails_closed():
    with pytest.raises(ValueError, match="positive integers"):
        summarize_families([run(1, 2, attempt=0)])


def test_sorted_manifest_preserves_native_run_identity():
    x = summarize_families([run(3, 20), run(1, 10), run(2, 20)])
    assert [r["workflow_id"] for r in x["manifest"]] == [10, 20]
    assert x["manifest"][1]["run_ids"] == [2, 3]


def test_no_merging_or_test_case_coverage_inference():
    x = summarize_families([run(1, 2)])
    assert x["workflow_testcase_count"] is None
    assert x["matched_statement_coverage"] is None
    assert x["merge_authority"] is False
