"""Validate bounded GitHub issue burndown without inventing causal-root credit."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCHEMA = "abacus.bd.four-repo-pulse2-20261017.v1"
REPOS = (
    "GBOGEB/ABACUS",
    "GBOGEB/CODEX",
    "GBOGEB/cryoplant-project",
    "GBOGEB/pipeline-automation-hub",
)


def validate(doc: dict) -> dict:
    if doc.get("schema") != SCHEMA:
        raise ValueError("unrecognized BD census schema")
    if (
        doc.get("merge_admission") != "HOLD"
        or doc.get("authority_transfer") is not False
    ):
        raise ValueError("unauthorized admission/authority promotion")
    start, end = doc["baseline"], doc["latest"]
    before = start.get("ABACUS_open_issues")
    after = end.get("scoped_repo_issue_open", {}).get("GBOGEB/ABACUS")
    if type(before) is not int or type(after) is not int:
        raise ValueError("missing numeric issue population")
    pools = end["scoped_repo_issue_open"]
    if set(pools) != set(REPOS) or any(
        type(v) is not int or v < 0 for v in pools.values()
    ):
        raise ValueError("incomplete or non-integer scoped population")
    if sum(pools.values()) != end.get("four_repo_total"):
        raise ValueError("four-repo population mismatch")
    if end.get("global_all_repo_total") is not None:
        raise ValueError("four repo scope cannot imply global completion")
    if (
        end.get("canonical_engineering_roots_open") is not None
        or end.get("canonical_engineering_roots_closed") is not None
    ):
        raise ValueError("GitHub issues cannot be certified causal roots")
    closed = doc["closure_evidence"]
    duplicates = closed["nine_this_pulse"]
    completed = closed["six_other_completed_today"]
    if len(duplicates) != 9 or len(completed) != 6:
        raise ValueError("nonreconciling issue closure classes")
    if len({x["issue"] for x in duplicates + completed}) != 15:
        raise ValueError("duplicate issue in closure proof")
    for x in duplicates:
        if x.get("state") != "closed" or x.get("state_reason") != "duplicate":
            raise ValueError("false duplicate ticket disposition")
        if (
            x.get("engineering_root_credit") != 0
            or x.get("canonical_issue") != 1885
            or x.get("source_root_status") != "OPEN"
        ):
            raise ValueError("duplicate ticket promoted to engineering fix")
        if x.get("historical_broken_hrefs") not in (16, 52):
            raise ValueError("unobserved historical scan regime")
        run = x.get("source_run_id")
        if type(run) is not int or run <= 0:
            raise ValueError("missing native run identity")
        if x.get("source_run_url") != (
            f"https://github.com/GBOGEB/ABACUS/actions/runs/{run}"
        ):
            raise ValueError("source-run URL mismatch")
    if sum(x["historical_broken_hrefs"] == 16 for x in duplicates) != 4:
        raise ValueError("lost historical 16-link regime")
    for x in completed:
        if (
            x.get("state_reason") != "completed"
            or x.get("proven_engineering_root_closure") is not None
        ):
            raise ValueError("completed issue promoted without RCA")
    if after - before != end["ABACUS_issue_count_delta"] or (
        before - after != len(duplicates) + len(completed)
    ):
        raise ValueError("issue-count change does not reconcile")
    ages = end["ABACUS_issue_ages"]
    if sum(ages.values()) != after or sum(start["ABACUS_age_bins"].values()) != before:
        raise ValueError("ageing cohort denominator mismatch")
    repair = closed["source_repair_head"]
    if len(repair) != 40 or not all(c in "0123456789abcdef" for c in repair):
        raise ValueError("source-repair SHA not pinned")
    if closed.get("source_repair_accepted") is not False:
        raise ValueError("unverified source repair promoted")
    return {
        "schema": "abacus.bd.pulse2-verification.v1",
        "open_issue_delta": after - before,
        "duplicate_ticket_closures": len(duplicates),
        "other_issue_completions": len(completed),
        "causal_root_closed_count": None,
        "scoped_four_repo_open": end["four_repo_total"],
        "global_total": None,
        "merge_admission": "HOLD",
    }


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    obj = json.loads(
        (root / "triage/ABACUS_BD_PULSE2_20261017.json").read_text(encoding="utf-8")
    )
    print(json.dumps(validate(obj), indent=2, sort_keys=True))
    sys.exit(0)
