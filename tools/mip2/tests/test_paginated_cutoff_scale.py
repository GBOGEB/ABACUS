"""Synthetic creation-cutoff and 5000-run pagination scale adversaries.

These scenarios exercise parser reach. They never attest 5000 native GitHub
runs, reproduce an independent failure, or confer release/merge authority.
"""

from __future__ import annotations

from urllib.parse import quote

from tools.mip2.paginated_head_census import API, analyze_head_pages
from tools.mip2.tests.test_paginated_head_census import build as raw_build
from tools.mip2.tests.test_paginated_head_census import row, throws


def build(rows, *, cutoff, sha="a" * 40, total=None):
    doc = raw_build(rows, sha=sha, total=total)
    doc["created_cutoff_utc"] = cutoff
    for page in doc["pages"]:
        page["api_url"] += "&created=" + quote("<=" + cutoff, safe="")
    return doc


# N+2: actual creation-window and 50-page *synthetic* scale controls.
CUTOFF = "2026-10-18T17:50:00Z"
EARLIER = "2026-10-18T17:40:00Z"
LATER = "2026-10-18T17:55:00Z"


def cutoff_rows(n, *, wf=10):
    return [{**row(i, wf=wf), "created_at": EARLIER} for i in range(1, n + 1)]


def test_positive_creation_cutoff_six_pages_and_repeat_denominator():
    rows = cutoff_rows(503)
    for i in range(443):
        rows[i]["workflow_id"] = 374064896
        rows[i]["event"] = (
            "workflow_run" if i < 407 else ("issue_comment" if i < 438 else "schedule")
        )
    for i in range(443, 464):
        rows[i]["workflow_id"] = 352924517
    for i in range(464, 473):
        rows[i]["workflow_id"] = 350890474
    for i in range(473, 503):
        rows[i]["workflow_id"] = 1000 + ((i - 473) % 28)
    result = analyze_head_pages(build(rows, cutoff=CUTOFF))
    assert (result["observed_run_count"], result["distinct_workflow_ids"]) == (503, 31)
    assert result["repeat_run_excess"] == 472
    assert result["pages_qualified_structurally"] == 6
    assert result["manifest"][0]["observed_run_count"] == 443
    assert result["created_cutoff_utc"] == CUTOFF
    assert result["snapshot_population"] == "FROZEN_CREATION_WINDOW_STATUS_AS_OBSERVED"
    assert result["artifact_byte_attestation"] == "NOT_PROVEN_BY_API_STRUCTURAL_CENSUS"


def test_positive_maximum_fifty_page_synthetic_scaling():
    rows = cutoff_rows(5000)
    for i, item in enumerate(rows):
        item["workflow_id"] = 100 + i // 100
    x = analyze_head_pages(build(rows, cutoff=CUTOFF))
    assert x["pages_qualified_structurally"] == 50
    assert x["observed_run_count"] == 5000
    assert x["distinct_workflow_ids"] == 50
    assert x["repeat_run_excess"] == 4950
    assert sum(g["repeat_excess"] for g in x["manifest"]) == 4950


def test_positive_exact_page_boundaries_101_and_200_and_4999():
    for n, p in ((101, 2), (200, 2), (4999, 50)):
        x = analyze_head_pages(build(cutoff_rows(n), cutoff=CUTOFF))
        assert x["pages_qualified_structurally"] == p
        assert x["observed_run_count"] == n


def test_positive_boundary_timestamp_equals_cutoff():
    rows = cutoff_rows(1)
    rows[0]["created_at"] = CUTOFF
    x = analyze_head_pages(build(rows, cutoff=CUTOFF))
    assert x["observed_run_count"] == 1


def test_negative_missing_created_at_for_frozen_window():
    throws(build([row(1)], cutoff=CUTOFF), "canonical UTC")


def test_negative_created_after_cutoff_fails_closed():
    rows = cutoff_rows(1)
    rows[0]["created_at"] = LATER
    throws(build(rows, cutoff=CUTOFF), "after frozen UTC cutoff")


def test_negative_bad_calendar_day_in_cutoff():
    throws(build(cutoff_rows(1), cutoff="2026-02-30T17:50:00Z"), "canonical UTC")


def test_negative_cutoff_with_query_injection():
    throws(build(cutoff_rows(1), cutoff=CUTOFF + "&per_page=200"), "canonical UTC")


def test_negative_wrong_cutoff_query_binding():
    payload = build(cutoff_rows(1), cutoff=CUTOFF)
    payload["pages"][0]["api_url"] = payload["pages"][0]["api_url"].replace(
        "%3C%3D", ""
    )
    throws(payload, "unbound API page URL")


def test_reverse_cross_page_boundary_cutoff_older_head_conclusion_not_promoted():
    rows = cutoff_rows(101)
    rows[-1]["status"] = "completed"
    rows[-1]["conclusion"] = "cancelled"
    x = analyze_head_pages(build(rows, cutoff=CUTOFF))
    assert x["terminal_run_count"] == 1
    assert x["terminal_success_fraction"] == 0
    assert x["admission"] == "HOLD"


def test_reverse_status_change_on_same_creation_window_not_false_independent_run():
    rows = cutoff_rows(101)
    previous = analyze_head_pages(build(rows, cutoff=CUTOFF))
    rows[0]["status"] = "completed"
    rows[0]["conclusion"] = "success"
    subsequent = analyze_head_pages(build(rows, cutoff=CUTOFF))
    assert previous["observed_run_count"] == subsequent["observed_run_count"]
    assert previous["repeat_run_excess"] == subsequent["repeat_run_excess"]
    assert subsequent["terminal_run_count"] == 1
    assert subsequent["admission"] == "HOLD"


def test_force_trip_new_run_after_cutoff_cannot_enter_same_population():
    rows = cutoff_rows(101)
    rows[-1]["created_at"] = LATER
    throws(build(rows, cutoff=CUTOFF), "after frozen UTC cutoff")


def test_force_trip_5001_rows_over_capacity_rejected():
    rows = cutoff_rows(5001)
    throws(build(rows, cutoff=CUTOFF), "page-count cap")


def test_force_trip_last_page_total_change_rejected():
    doc = build(cutoff_rows(503), cutoff=CUTOFF)
    doc["pages"][-1]["total_count"] = 504
    throws(doc, "unstable API total denominator")


def test_force_trip_forged_completed_status_in_created_window():
    rows = cutoff_rows(1)
    rows[0]["conclusion"] = "success"
    throws(build(rows, cutoff=CUTOFF), "premature terminal result")
