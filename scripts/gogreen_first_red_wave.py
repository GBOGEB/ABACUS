"""GoGREEN N+1 first-red wave: observational PR-blocker and coverage telemetry.

Source-owner extension to the existing root leverage producer (PR #2080).
Consume explicit GitHub run/job/step metadata, NEVER workflow names as roots.
No network, writes, GitHub dispatch, promotion or security waiver.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

SCHEMA = "abacus.gogreen.first-red-wave.intake.v1"
OUTPUT = "abacus.gogreen.first-red-wave.observation.v1"
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
REPO = "GBOGEB/ABACUS"
DOWNSTREAM_JOBS = frozenset(
    {
        "Full Red Proof Summary",
        "Python proof completeness",
        "ABACUS compatibility gate",
        "Test Results Notification",
    }
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def positive(value: object) -> bool:
    return type(value) is int and value > 0


def nonnegative(value: object) -> bool:
    return type(value) is int and value >= 0


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _is_sha(value: object) -> bool:
    return isinstance(value, str) and HEX40.fullmatch(value) is not None


def _source_heads(payload: dict) -> dict[int, str]:
    entries = payload.get("source_heads")
    require(isinstance(entries, list) and bool(entries), "source_heads required")
    result = {}
    for row in entries:
        require(isinstance(row, dict), "invalid source head")
        pr, sha = row.get("pr"), row.get("head_sha")
        require(positive(pr) and _is_sha(sha), "invalid PR/head identity")
        require(pr not in result, "duplicate PR head")
        result[pr] = sha
    return result


def _check_observation(row: dict, heads: dict[int, str]) -> tuple:
    require(isinstance(row, dict), "invalid observation")
    pr, sha = row.get("pr"), row.get("head_sha")
    require(pr in heads and sha == heads[pr], "stale or foreign PR head")
    for key in ("run_id", "run_attempt", "job_id", "step_number"):
        require(positive(row.get(key)), f"invalid {key}")
    for key in ("workflow", "job", "first_red_step"):
        require(
            isinstance(row.get(key), str)
            and bool(row[key].strip())
            and len(row[key]) <= 200,
            f"invalid {key}",
        )
    require(row.get("job_conclusion") == "failure", "nonfailing job in red cohort")
    require(
        row.get("evidence_class") == "GITHUB_NATIVE_JOB_STEP_METADATA",
        "unqualified evidence class",
    )
    run_id = row["run_id"]
    require(
        row.get("run_url") == f"https://github.com/GBOGEB/ABACUS/actions/runs/{run_id}",
        "run URL not native or mismatched",
    )
    root_id = row.get("root_id")
    if root_id is not None:
        require(
            isinstance(root_id, str)
            and re.fullmatch(r"[A-Z][A-Z0-9_-]{2,79}", root_id) is not None,
            "invalid root ID",
        )
        require(
            row.get("owner_disposition") == "ACCEPTED"
            and isinstance(row.get("root_owner"), str)
            and bool(row["root_owner"].strip())
            and isinstance(row.get("root_evidence_url"), str)
            and row["root_evidence_url"].startswith("https://github.com/GBOGEB/"),
            "root is not independently owner accepted",
        )
        require(
            row.get("job") not in DOWNSTREAM_JOBS,
            "downstream summary cannot be accepted as an independent root",
        )
    else:
        require(
            all(
                row.get(key) is None
                for key in ("root_owner", "owner_disposition", "root_evidence_url")
            ),
            "unaccepted owner fields cannot promote root",
        )
    return (run_id, row["run_attempt"], row["job_id"])


def _coverage(record: dict, expected_sha: str) -> dict:
    require(
        isinstance(record, dict) and record.get("source_sha") == expected_sha,
        "coverage source/head mismatch",
    )
    require(record.get("branch_mode") is True, "coverage must use branch mode")
    for key in ("tool_version", "scope_id", "test_selection", "module_fingerprint"):
        require(
            isinstance(record.get(key), str) and bool(record[key]),
            f"coverage {key} missing",
        )
    for key in (
        "eligible_statements",
        "covered_statements",
        "eligible_branches",
        "covered_branches",
        "eligible_changed_lines",
        "covered_changed_lines",
    ):
        require(nonnegative(record.get(key)), f"coverage {key} invalid")
    require(
        record["eligible_statements"] > 0 and record["eligible_branches"] >= 0,
        "empty source coverage scope",
    )
    for a, b in (
        ("covered_statements", "eligible_statements"),
        ("covered_branches", "eligible_branches"),
        ("covered_changed_lines", "eligible_changed_lines"),
    ):
        require(record[a] <= record[b], "coverage numerator exceeds denominator")
    den = record["eligible_statements"] + record["eligible_branches"]
    return {
        "source_sha": expected_sha,
        "tool_version": record["tool_version"],
        "scope_id": record["scope_id"],
        "test_selection": record["test_selection"],
        "module_fingerprint": record["module_fingerprint"],
        "eligible_statements": record["eligible_statements"],
        "eligible_branches": record["eligible_branches"],
        "combined_covered": record["covered_statements"] + record["covered_branches"],
        "combined_eligible": den,
        "combined_pct": round(
            100 * (record["covered_statements"] + record["covered_branches"]) / den, 4
        ),
        "changed_line_pct": (
            round(
                100
                * record["covered_changed_lines"]
                / record["eligible_changed_lines"],
                4,
            )
            if record["eligible_changed_lines"] > 0
            else None
        ),
        "eligible_changed_lines": record["eligible_changed_lines"],
        "covered_changed_lines": record["covered_changed_lines"],
    }


def compare_coverage(previous: dict, current: dict) -> dict:
    """Reject incomparable cohorts instead of manufacturing coverage growth."""
    keys = (
        "tool_version",
        "scope_id",
        "test_selection",
        "module_fingerprint",
        "eligible_statements",
        "eligible_branches",
        "eligible_changed_lines",
    )
    comparable = all(previous.get(k) == current.get(k) for k in keys)
    return {
        "status": "MATCHED" if comparable else "INCOMPARABLE",
        "combined_delta_pp": (
            round(current["combined_pct"] - previous["combined_pct"], 4)
            if comparable
            else None
        ),
        "changed_line_delta_pp": (
            round(current["changed_line_pct"] - previous["changed_line_pct"], 4)
            if comparable
            and current["changed_line_pct"] is not None
            and previous["changed_line_pct"] is not None
            else None
        ),
    }


def analyze(payload: dict) -> dict:
    require(
        isinstance(payload, dict) and payload.get("schema") == SCHEMA,
        "invalid intake schema",
    )
    require(
        payload.get("repository") == REPO
        and payload.get("authority_transfer") is False
        and payload.get("merge_authorized") is False
        and payload.get("security_waiver") is False,
        "authority or repository mismatch",
    )
    heads = _source_heads(payload)
    rows = payload.get("observations")
    require(
        isinstance(rows, list) and len(rows) <= 512, "bounded observation list required"
    )
    identities, run_heads = {}, {}
    candidate, approved = (
        defaultdict(lambda: {"prs": set(), "jobs": set(), "observations": 0}),
        {},
    )
    downstream = 0
    for row in rows:
        key = _check_observation(row, heads)
        binding = (
            row["head_sha"],
            row["workflow"],
            row["job"],
            row["first_red_step"],
            row["step_number"],
            row.get("root_id"),
        )
        if key in identities:
            require(identities[key] == binding, "conflicting duplicate job identity")
            # Same native job may be associated with several PRs at one head.
            # Count that job once, but retain each affected PR for leverage.
            if row["job"] not in DOWNSTREAM_JOBS:
                label = (row["workflow"], row["job"], row["first_red_step"])
                candidate[label]["prs"].add(row["pr"])
                if row.get("root_id") is not None:
                    owner = (
                        row["root_id"],
                        row["root_owner"],
                        row["root_evidence_url"],
                    )
                    approved.setdefault(owner, set()).add(row["pr"])
            continue
        identities[key] = binding
        run_key = key[:2]
        require(
            run_key not in run_heads or run_heads[run_key] == row["head_sha"],
            "mixed source heads in one native run attempt",
        )
        run_heads[run_key] = row["head_sha"]
        if row["job"] in DOWNSTREAM_JOBS:
            downstream += 1
            continue
        # Stable observed signature only; never a causally established root.
        label = (row["workflow"], row["job"], row["first_red_step"])
        candidate[label]["prs"].add(row["pr"])
        candidate[label]["jobs"].add(key)
        candidate[label]["observations"] += 1
        if row.get("root_id") is not None:
            owner = (row["root_id"], row["root_owner"], row["root_evidence_url"])
            approved.setdefault(owner, set()).add(row["pr"])

    rank = []
    for (workflow, job, step), value in candidate.items():
        digest = hashlib.sha256(canonical([workflow, job, step]).encode()).hexdigest()[
            :16
        ]
        rank.append(
            {
                "candidate_id": "SIG-" + digest,
                "workflow": workflow,
                "job": job,
                "first_red_step": step,
                "pr_count": len(value["prs"]),
                "prs": sorted(value["prs"]),
                "distinct_failed_job_ids": len(value["jobs"]),
                "causal_root_id": None,
            }
        )
    rank.sort(
        key=lambda x: (-x["pr_count"], -x["distinct_failed_job_ids"], x["candidate_id"])
    )
    established = [
        {
            "root_id": key[0],
            "owner": key[1],
            "evidence_url": key[2],
            "prs": sorted(prs),
            "potential_pr_unblock_upper_bound": len(prs),
        }
        for key, prs in sorted(approved.items())
    ]
    cov_input = payload.get("coverage", [])
    require(isinstance(cov_input, list), "invalid coverage receipts")
    coverage = {}
    for item in cov_input:
        require(
            isinstance(item, dict) and item.get("pr") in heads, "coverage PR missing"
        )
        pr = item["pr"]
        require(pr not in coverage, "duplicate coverage PR")
        coverage[pr] = _coverage(item, heads[pr])
    comparisons = []
    for pair in payload.get("coverage_comparisons", []):
        require(
            isinstance(pair, dict)
            and positive(pair.get("baseline_pr"))
            and positive(pair.get("candidate_pr")),
            "invalid comparison",
        )
        a, b = pair["baseline_pr"], pair["candidate_pr"]
        require(a in coverage and b in coverage, "missing source-bound coverage")
        comparisons.append(
            {
                "baseline_pr": a,
                "candidate_pr": b,
                **compare_coverage(coverage[a], coverage[b]),
            }
        )
    # Non-acting, bounded work proposals: no path leases or forged worker IDs.
    packets = [
        {
            "candidate_id": x["candidate_id"],
            "affected_prs": x["prs"],
            "mode": "READ_ONLY_ROOT_SCOUT",
            "dispatch_authorized": False,
            "worker_state": "STAGED_NOT_LAUNCHED",
            "source_write_lease": None,
        }
        for x in rank[:4]
    ]
    return {
        "schema": OUTPUT,
        "repository": REPO,
        "source_heads_observed": len(heads),
        "observations_supplied": len(rows),
        "unique_native_failed_jobs": len(identities),
        "duplicates_deduplicated": len(rows) - len(identities),
        "downstream_summary_jobs": downstream,
        "candidate_signature_count": len(rank),
        "candidate_ranking": rank,
        "owner_accepted_roots": established,
        "accepted_root_count": len(established),
        "coverage": {str(k): v for k, v in sorted(coverage.items())},
        "coverage_comparisons": comparisons,
        "proposed_read_only_scouts": packets,
        "write_workers_without_owner_lease": 0,
        "globally_open_prs": None,
        "confirmed_roots_closed": None,
        "current_main_coverage": None,
        "forecast_verified_unblocked_prs": None,
        "merge_authorized": False,
        "authority_transfer": False,
        "security_waiver": False,
        "safety_admission": "HOLD",
        "evidence_class": "OBSERVED_NATIVE_METADATA_AND_OPTIONAL_SOURCE_BOUND_COVERAGE",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = analyze(json.loads(args.input.read_text(encoding="utf-8")))
    raw = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(raw, encoding="utf-8")
    else:
        print(raw, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
