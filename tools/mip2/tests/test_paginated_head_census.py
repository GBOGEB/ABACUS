"""Synthetic pagination adversaries; no synthetic run is native closure evidence."""
from __future__ import annotations

import copy

import pytest

from tools.mip2.paginated_head_census import API, PAGE_SIZE, SCHEMA, analyze_head_pages

SHA = "a" * 40
ALT = "b" * 40


def row(rid, wf=10, event="push", state="queued", conclusion=None, sha=SHA):
    return {"id": rid, "workflow_id": wf, "run_attempt": 1,
            "head_sha": sha, "event": event, "status": state,
            "conclusion": conclusion}


def build(rows, sha=SHA, total=None):
    count = len(rows) if total is None else total
    pages = []
    for i in range(0, len(rows), PAGE_SIZE):
        page = i // PAGE_SIZE + 1
        pages.append({"page": page, "total_count": count,
                      "api_url": f"{API}?head_sha={sha}&per_page=100&page={page}",
                      "runs": rows[i:i + PAGE_SIZE]})
    return {"schema": SCHEMA, "repository": "GBOGEB/ABACUS",
            "source_role": "OBSERVED_DEFAULT_BRANCH_HEAD",
            "source_sha": sha, "pages": pages}


def n23_shape():
    # One head, 74 PR gate observations, five QPS, three W70, 28 others.
    rows = [row(i, 374064896, "workflow_run") for i in range(1, 61)]
    rows += [row(i, 374064896, "issue_comment") for i in range(61, 74)]
    rows += [row(74, 374064896, "schedule")]
    rows += [row(i, 350890474) for i in range(75, 80)]
    rows += [row(i, 352924517, "workflow_run") for i in range(80, 83)]
    rows += [row(83 + i, 10000 + i) for i in range(28)]
    return rows


def throws(doc, fragment):
    with pytest.raises(ValueError, match=fragment):
        analyze_head_pages(doc)


def test_positive_110_two_page_amplification_and_statuses():
    observed = analyze_head_pages(build(n23_shape()))
    assert (observed["observed_run_count"], observed["distinct_workflow_ids"]) == (110, 31)
    assert observed["repeat_run_excess"] == 79
    assert observed["pages_qualified_structurally"] == 2
    assert observed["event_counts"] == {
        "issue_comment": 13, "push": 33,
        "schedule": 1, "workflow_run": 63,
    }
    assert observed["status_counts"] == {"queued": 110}
    assert observed["manifest"][0]["event_counts"] == {
        "issue_comment": 13, "schedule": 1, "workflow_run": 60}


def test_positive_201_requires_three_pages():
    observed = analyze_head_pages(build([row(i) for i in range(1, 202)]))
    assert observed["pages_qualified_structurally"] == 3
    assert observed["repeat_run_excess"] == 200


def test_positive_100_exact_one_page():
    x = analyze_head_pages(build([row(i) for i in range(1, 101)]))
    assert x["pages_qualified_structurally"] == 1


def test_positive_terminal_rate_and_uncertainty_types():
    rows = [row(1, state="completed", conclusion="success"),
            row(2, state="completed", conclusion="failure"),
            row(3)]
    x = analyze_head_pages(build(rows))
    assert x["terminal_run_count"] == 2
    assert x["terminal_success_fraction"] == 0.5
    assert x["native_testcase_count"] is None
    assert x["independent_causal_root_count"] is None
    assert x["admission"] == "HOLD"


def test_positive_zero_terminal_rate_is_unknown():
    assert analyze_head_pages(build([row(1)]))["terminal_success_fraction"] is None


def test_reverse_shuffled_within_pages_same_counts():
    rows = n23_shape()
    original = analyze_head_pages(build(rows))
    reversed_page_rows = list(reversed(rows[:100])) + list(reversed(rows[100:]))
    changed = analyze_head_pages(build(reversed_page_rows))
    for key in ("event_counts", "status_counts", "repeat_run_excess",
                "distinct_workflow_ids", "manifest"):
        assert original[key] == changed[key]


def test_reverse_failure_in_repeated_family_not_clean_success():
    rows = [row(1, state="completed", conclusion="success"),
            row(2, state="completed", conclusion="failure")]
    x = analyze_head_pages(build(rows))
    assert x["manifest"][0]["terminal_failure"] == 1
    assert x["manifest"][0]["terminal_success"] == 1
    assert x["admission"] == "HOLD"


def test_negative_missing_last_page():
    doc = build(n23_shape())
    doc["pages"].pop()
    throws(doc, "truncated or excess")


def test_negative_empty_pages():
    throws({"schema": SCHEMA, "repository": "GBOGEB/ABACUS",
            "source_role": "OBSERVED_DEFAULT_BRANCH_HEAD", "source_sha": SHA,
            "pages": []}, "missing API pages")


def test_negative_wrong_source_repository():
    d = build([row(1)])
    d["repository"] = "GBOGEB/CODEX"
    throws(d, "foreign")


def test_negative_wrong_source_role():
    d = build([row(1)])
    d["source_role"] = "synthetic_merge"
    throws(d, "source identity role")


def test_negative_wrong_schema():
    d = build([row(1)])
    d["schema"] = "unknown"
    throws(d, "source schema")


def test_negative_duplicate_run_id_on_separate_pages():
    rows = n23_shape()
    rows[103]["id"] = 1
    throws(build(rows), "duplicate native run")


def test_negative_mixed_sha_on_last_page():
    rows = n23_shape()
    rows[-1]["head_sha"] = ALT
    throws(build(rows), "mixed head")


def test_negative_missing_page_rows():
    d = build(n23_shape())
    d["pages"][0]["runs"].pop()
    throws(d, "missing or excess native rows")


def test_negative_unstable_page_total():
    d = build(n23_shape())
    d["pages"][1]["total_count"] = 111
    throws(d, "unstable API total")


def test_negative_reversed_page_order():
    d = build(n23_shape())
    d["pages"].reverse()
    throws(d, "out-of-order API")


def test_negative_wrong_api_url():
    d = build(n23_shape())
    d["pages"][1]["api_url"] += "&event=push"
    throws(d, "unbound API")


def test_negative_out_of_range_total():
    d = build([row(1)])
    d["pages"][0]["total_count"] = 999999
    throws(d, "excessive native")


def test_negative_boolean_run_identity():
    d = build([row(1)])
    d["pages"][0]["runs"][0]["id"] = True
    throws(d, "invalid native run")


def test_negative_noninteger_page_number():
    d = build([row(1)])
    d["pages"][0]["page"] = True
    throws(d, "out-of-order API")


def test_negative_invalid_event():
    d = build([row(1, event="push; attack")])
    throws(d, "triggering event")


def test_force_trip_premature_green_for_queued():
    d = build([row(1, state="queued", conclusion="success")])
    throws(d, "premature terminal")


def test_force_trip_completed_unknown_conclusion():
    d = build([row(1, state="completed", conclusion="unknown")])
    throws(d, "nonqualifying terminal")


def test_force_trip_unrecognized_status():
    d = build([row(1, state="evil")])
    throws(d, "unrecognized nonterminal")


def test_force_trip_forged_attempt_zero():
    d = build([row(1)])
    d["pages"][0]["runs"][0]["run_attempt"] = 0
    throws(d, "invalid native run")


def test_force_trip_partial_page_count_inflation():
    d = build(n23_shape())
    d["pages"][0]["total_count"] = 120
    d["pages"][1]["total_count"] = 120
    throws(d, "missing or excess native rows")


def test_force_trip_adds_extra_tail_page():
    d = build(n23_shape())
    d["pages"].append(copy.deepcopy(d["pages"][1]))
    throws(d, "truncated or excess")


def test_force_trip_nonobject_run():
    d = build([row(1)])
    d["pages"][0]["runs"][0] = "forged"
    throws(d, "nonobject native")


def test_force_trip_nonobject_first_page():
    d = build([row(1)])
    d["pages"][0] = "bad"
    throws(d, "invalid first API page")
