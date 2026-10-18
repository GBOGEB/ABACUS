"""Read-only, source-reported serial-main comparison for G3C-S.

This comparator never authenticates GitHub receipts, closes causal roots,
grants admission, or treats two main samples as statistical convergence.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re

INPUT_SCHEMA = "codepurple.g3cs.serial-main-pair-input.v1"
OUTPUT_SCHEMA = "codepurple.g3cs.serial-main-pair-result.v1"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA64 = re.compile(r"^[0-9a-f]{64}$")
ROOT_STATES = {"OPEN", "REPAIRED", "VERIFIED", "CLOSURE_CLAIMED"}
TERMINAL = {"success", "failure", "cancelled", "skipped", "timed_out"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def instant(value):
    require(isinstance(value, str), "timestamp must be a string")
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        result = datetime.fromisoformat(value)
        require(result.tzinfo is not None and result.utcoffset() is not None,
                "timestamp must have timezone offset")
        return result.astimezone(timezone.utc)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid offset-aware timestamp") from exc


def coverage(item, sha, name):
    require(item is None or isinstance(item, dict), f"invalid {name} coverage")
    if item is None:
        return
    for key in ("scope_sha256", "tool_sha256", "selection_sha256"):
        require(isinstance(item.get(key), str) and SHA64.fullmatch(item[key]),
                f"invalid {name} {key}")
    require(item.get("source_sha") == sha, f"{name} coverage not source-bound")
    covered, eligible = item.get("covered"), item.get("eligible")
    require(type(covered) is int and type(eligible) is int and
            0 <= covered <= eligible and eligible > 0,
            f"invalid {name} numerator/denominator")


def validate(payload):
    require(isinstance(payload, dict) and payload.get("schema") == INPUT_SCHEMA,
            "bad paired-main schema")
    require(payload.get("repository") == "GBOGEB/ABACUS" and
            payload.get("clock") == "SERIAL_MERGED_MAIN", "non-main or wrong repo")
    require(payload.get("receipt_authentication") == "NOT_INDEPENDENTLY_VERIFIED",
            "unproven native attestation")
    pair = payload.get("observations")
    require(isinstance(pair, list) and len(pair) == 2, "exactly two serial main samples required")
    seen_jobs = set()
    for i, item in enumerate(pair):
        sha = item.get("main_sha")
        require(isinstance(sha, str) and SHA40.fullmatch(sha), "invalid main SHA")
        if i == 1:
            require(sha != pair[0]["main_sha"] and
                    item.get("parent_main_sha") == pair[0]["main_sha"],
                    "main SHA chain is not contiguous")
            require(instant(item["captured_at"]) > instant(pair[0]["captured_at"]),
                    "nonmonotonic observation clock")
        else:
            instant(item["captured_at"])
        values = item.get("coverage")
        require(isinstance(values, dict), "invalid coverage mapping")
        for name in ("statement", "branch", "diff"):
            coverage(values.get(name), sha, name)
        reds = item.get("first_red_fingerprints")
        require(isinstance(reds, list) and len(reds) == len(set(reds)) and
                all(isinstance(x, str) and SHA64.fullmatch(x) for x in reds),
                "invalid or duplicated first-red fingerprint")
        roots = item.get("roots")
        require(isinstance(roots, dict) and all(
            isinstance(k, str) and SHA64.fullmatch(k) and v in ROOT_STATES
            for k, v in roots.items()), "invalid causal-root status")
        jobs = item.get("jobs")
        require(isinstance(jobs, list), "missing native job observation")
        job_names = set()
        for job in jobs:
            require(job.get("source_sha") == sha, "job not bound to main SHA")
            require(all(type(job.get(k)) is int and job[k] > 0
                        for k in ("run_id", "attempt", "job_id")),
                    "bad native run/job/attempt")
            key = (job["run_id"], job["attempt"], job["job_id"])
            require(key not in seen_jobs, "reused native job identity")
            seen_jobs.add(key)
            name = job.get("cohort_key")
            require(isinstance(name, str) and name and name not in job_names,
                    "missing or duplicate job cohort key")
            job_names.add(name)
            status = job.get("status")
            conclusion = job.get("conclusion")
            require(status in ("completed", "queued", "in_progress"), "bad job status")
            if status == "completed":
                require(conclusion in TERMINAL, "terminal job missing conclusion")
                if conclusion not in {"skipped", "cancelled"}:
                    require(job.get("started_at") is not None and
                            job.get("completed_at") is not None,
                            "terminal job missing execution clock")
            else:
                require(conclusion is None and job.get("completed_at") is None,
                        "nonterminal job falsely complete")
            created = instant(job["created_at"])
            started = instant(job["started_at"]) if job.get("started_at") else None
            finished = instant(job["completed_at"]) if job.get("completed_at") else None
            require(status != "queued" or started is None, "queued job has start clock")
            require(status != "in_progress" or started is not None,
                    "in-progress job missing start clock")
            require(started is None or created <= started, "negative queue clock")
            require(finished is None or (started is not None and started <= finished),
                    "negative execution clock")
            captured = instant(item["captured_at"])
            require(created <= captured and (finished is None or finished <= captured),
                    "observation precedes native job evidence")
    return pair


def paired_coverage(before, after):
    result = {}
    for name in ("statement", "branch", "diff"):
        a, b = before.get("coverage", {}).get(name), after.get("coverage", {}).get(name)
        if a is None or b is None:
            result[name] = {"status": "UNKNOWN", "delta_pp": None}
            continue
        if any(a[k] != b[k] for k in
               ("scope_sha256", "tool_sha256", "selection_sha256", "eligible")):
            result[name] = {"status": "NONCOMPARABLE", "delta_pp": None,
                            "reason": "SCOPE_TOOL_SELECTION_OR_DENOMINATOR_DRIFT"}
            continue
        denom = a["eligible"]
        result[name] = {
            "status": "PAIRED_SOURCE_REPORTED", "covered_before": a["covered"],
            "covered_after": b["covered"], "eligible": denom,
            "numerator_delta": b["covered"] - a["covered"],
            "delta_pp": round(100 * (b["covered"] - a["covered"]) / denom, 6),
        }
    return result


def percentile95(values):
    values = sorted(values)
    if len(values) < 5:
        return None
    position = (len(values) - 1) * 0.95
    low = math.floor(position)
    return round(values[low] + (values[math.ceil(position)] - values[low]) *
                 (position - low), 3)


def timing(before, after):
    indexed = [{j["cohort_key"]: j for j in x["jobs"]} for x in (before, after)]
    names = sorted(set(indexed[0]) & set(indexed[1]))
    groups = {"before_queue": [], "after_queue": [],
              "before_execution": [], "after_execution": []}
    for name in names:
        a, b = indexed[0][name], indexed[1][name]
        if any(job["status"] != "completed" or
               job["conclusion"] in {"skipped", "cancelled"} or
               job.get("started_at") is None or job.get("completed_at") is None
               for job in (a, b)):
            continue
        for label, job in (("before", a), ("after", b)):
            created, started, ended = (instant(job[k]) for k in
                                       ("created_at", "started_at", "completed_at"))
            groups[label + "_queue"].append((started - created).total_seconds())
            groups[label + "_execution"].append((ended - started).total_seconds())
    return {"matched_terminal_jobs": len(groups["before_queue"]),
            "minimum_for_descriptive_p95": 5,
            "queue_p95_before_seconds": percentile95(groups["before_queue"]),
            "queue_p95_after_seconds": percentile95(groups["after_queue"]),
            "execution_p95_before_seconds": percentile95(groups["before_execution"]),
            "execution_p95_after_seconds": percentile95(groups["after_execution"]),
            "provenance": "SOURCE_REPORTED_NOT_NATIVE_AUTHENTICATED"}


def compare(payload):
    before, after = validate(payload)
    first, last = (set(x["first_red_fingerprints"]) for x in (before, after))
    roots_before, roots_after = before["roots"], after["roots"]
    transitions = [
        {"fingerprint": k, "before": roots_before.get(k), "after": roots_after.get(k)}
        for k in sorted(set(roots_before) | set(roots_after))
        if roots_before.get(k) != roots_after.get(k)
    ]
    return {
        "schema": OUTPUT_SCHEMA,
        "repository": payload["repository"],
        "lineage": {"clock": "CLAIMED_SERIAL_MERGED_MAIN",
                    "before_sha": before["main_sha"], "after_sha": after["main_sha"],
                    "edge_type": "MAIN_PARENT_CLAIM_NOT_INDEPENDENTLY_AUTHENTICATED"},
        "coverage": paired_coverage(before, after),
        "first_reds": {"new": sorted(last - first),
                       "nonreproduced_candidates": sorted(first - last),
                       "persistent": sorted(first & last),
                       "closure_credit": 0},
        "roots": {"status_transitions_source_reported": transitions,
                  "verified_closed": None},
        "telemetry": timing(before, after),
        "sipoc_process": "MIP / gg_MATH matched-cohort measurement",
        "dag_joins": ["main", "matrix", "coverage", "roots", "dmaic", "dashboard"],
        "statistics": {"regime": "DESCRIPTIVE_PAIR_ONLY",
                       "stability": None, "pca": None, "bradley_terry": None,
                       "six_sigma": None, "predictive_interval": None},
        "admission": "HOLD",
        "evidence_level": "SOURCE_REPORTED_NOT_INDEPENDENTLY_VERIFIED",
        "authority_transfer": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = compare(json.loads(args.input.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print("G3CS_SERIAL_PAIR SOURCE_REPORTED; ADMISSION HOLD;", args.output)


if __name__ == "__main__":
    main()
