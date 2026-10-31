"""Fail-closed triage metrics over source-bound GitHub issue/PR snapshots.

A GitHub issue count is not a causal root denominator. This module performs no
remote requests, issue changes, PR merging or admission decisions.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

SOURCE_SCHEMA = "abacus.triage.issue-age-census.v1"
PR_SCHEMA = "abacus.triage.pr-head-register.v1"
SHA40 = re.compile(r"[0-9a-f]{40}")
BANDS = ("0_to_6", "7_to_13", "14_to_29", "30_plus")


class CensusError(ValueError):
    pass


def _count(v, label):
    if type(v) is not int or v < 0:
        raise CensusError(f"invalid {label}")
    return v


def summarize(issue_census, pr_register):
    if (
        issue_census.get("schema") != SOURCE_SCHEMA
        or pr_register.get("schema") != PR_SCHEMA
    ):
        raise CensusError("unknown evidence schema")
    if (
        issue_census.get("repository") != "GBOGEB/ABACUS"
        or pr_register.get("repository") != "GBOGEB/ABACUS"
    ):
        raise CensusError("mismatched source repository")
    if (
        issue_census.get("authority_transfer") is not False
        or pr_register.get("authority_transfer") is not False
        or issue_census.get("pr_admission") != "HOLD"
        or pr_register.get("merge_admission") != "HOLD"
    ):
        raise CensusError("unsafe authority or admission promotion")

    rows = issue_census["issue_records"]
    counts = issue_census["live"]
    if not isinstance(rows, list) or not rows:
        raise CensusError("open issue evidence missing")
    ids = []
    for r in rows:
        ident = _count(r.get("issue"), "issue")
        ids.append(ident)
        if (
            r.get("status") != "OPEN_OBSERVED"
            or r.get("root_resolution") != "UNKNOWN"
            or r.get("engineering_closure_credit") is not None
        ):
            raise CensusError("observed issue incorrectly admitted or closed")
        if r.get("age_band") not in BANDS:
            raise CensusError("unknown ageing cohort")
        if r.get("age_days") is not None:
            age = _count(r["age_days"], "age_days")
            low, high = {
                "0_to_6": (0, 6),
                "7_to_13": (7, 13),
                "14_to_29": (14, 29),
                "30_plus": (30, 10**6),
            }[r["age_band"]]
            if not low <= age <= high:
                raise CensusError("age incompatible with band")
        if r.get("url") != f"https://github.com/GBOGEB/ABACUS/issues/{ident}":
            raise CensusError("issue reference mismatch")
    if len(ids) != len(set(ids)):
        raise CensusError("duplicate issue record")
    if len(rows) != _count(counts.get("ordinary_open_issues"), "open issues"):
        raise CensusError("issue denominator mismatch")
    actual = Counter(r["age_band"] for r in rows)
    if any(actual.get(k, 0) != _count(counts["age_cohorts"][k], k) for k in BANDS):
        raise CensusError("age cohorts do not partition population")
    older = _count(counts.get("open_pr_created_before_oct17"), "old PR")
    newer = _count(counts.get("open_pr_created_on_oct17"), "new PR")
    if older + newer != _count(counts.get("open_pr_total"), "open PR"):
        raise CensusError("PR population mismatch")
    dashboard = sum(r["family"] == "DASHBOARD_HEALTH_ALERT" for r in rows)
    if dashboard != counts["open_dashboard_tickets"]:
        raise CensusError("dashboard issue count mismatch")
    if 1885 not in ids:
        raise CensusError("canonical dashboard root issue not open")
    closed = issue_census["closed_housekeeping"]
    if len(closed) != _count(
        counts["recent_closed_duplicate_issues"], "duplicate closure count"
    ):
        raise CensusError("closed cohort mismatch")
    closed_ids = set()
    for row in closed:
        n = _count(row["issue"], "closed issue")
        if n in closed_ids or n in ids:
            raise CensusError("duplicate closed ID or still open")
        closed_ids.add(n)
        if (
            row.get("reason") != "duplicate"
            or row.get("canonical_survivor") != 1885
            or row.get("classification")
            != "HOUSEKEEPING_DUPLICATE_NOT_ENGINEERING_REPAIR"
        ):
            raise CensusError("non-housekeeping closed issue")
    if counts.get("root_open_count") is not None or (
        counts.get("root_closed_count") is not None
    ):
        raise CensusError("root counts cannot be derived from GitHub issues")
    if counts.get("current_main_sha") != ("54da377cf82a358ac97903ecde0270c975b8fcc1"):
        raise CensusError("unverified main baseline movement")

    prs = pr_register["primary_source_heads"]
    seen_prs = set()
    for row in prs:
        n = _count(row["pr"], "PR")
        if n in seen_prs:
            raise CensusError("duplicate PR")
        seen_prs.add(n)
        if not SHA40.fullmatch(row.get("head_sha", "")):
            raise CensusError("missing native PR head SHA")
        if row.get("state") != "open" or row.get("merged") is not False:
            raise CensusError("head snapshot no longer open/unmerged")
    if not {2135, 2026, 2027}.issubset(seen_prs):
        raise CensusError("required owner PR absent")
    match = pr_register["bseries_source_matched"]
    if match["pr"] != 2135 or not SHA40.fullmatch(match["verified_source_sha"]):
        raise CensusError("B-series source/PR not bound")
    a, b = match["statement_before"], match["statement_after"]
    c, d = match["branches_before"], match["branches_after"]
    for pair in (a, b, c, d):
        if (
            not isinstance(pair, list)
            or len(pair) != 2
            or any(type(v) is not int or v < 0 for v in pair)
        ):
            raise CensusError("invalid matched numerator/denominator")
        if pair[1] <= 0 or pair[0] > pair[1]:
            raise CensusError("invalid matched coverage ratio")
    if a[1] != b[1] or c[1] != d[1]:
        raise CensusError("coverage denominators changed")
    if match["new_head"] != next(p["head_sha"] for p in prs if p["pr"] == 2135):
        raise CensusError("different head recorded within snapshot")

    ages_old = actual["30_plus"] + actual["14_to_29"]
    return {
        "schema": "abacus.triage.ageing-metrics.v1",
        "source_date_utc": issue_census["calendar_cutoff_utc"],
        "scope": "GBOGEB/ABACUS",
        "age_distribution": {x: actual[x] for x in BANDS},
        "age_14plus_fraction": ages_old / len(rows),
        "open_issues": len(rows),
        "open_prs": older + newer,
        "dashboard_open_alerts": dashboard,
        "closed_duplicate_tickets": len(closed),
        "closed_ticket_type": "HOUSEKEEPING_ONLY",
        "closed_issue_duplicate_latency_median_days": (
            counts.get("recent_duplicate_close_median_days")
        ),
        "source_matched_statement_gain": b[0] - a[0],
        "source_matched_branch_gain": d[0] - c[0],
        "source_matched_statement_denominator": b[1],
        "source_matched_branch_denominator": d[1],
        "engineering_root_open": None,
        "engineering_root_closed": None,
        "time_to_engineering_root_closure": None,
        "survival_hazard": None,
        "survival_hazard_reason": "INCOMPLETE_COHORT_AND_NO_VERIFIED_CAUSAL_CLOSURES",
        "merges_to_main_since_baseline": 0,
        "PR_head_freshness_later_than_snapshot": None,
        "P0": "HOLD",
        "authority_transfer": False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--issues", type=Path, required=True)
    p.add_argument("--heads", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    result = summarize(
        json.loads(args.issues.read_text(encoding="utf-8")),
        json.loads(args.heads.read_text(encoding="utf-8")),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "open_issues": result["open_issues"],
                "open_prs": result["open_prs"],
                "P0": "HOLD",
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
