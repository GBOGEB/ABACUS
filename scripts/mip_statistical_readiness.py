#!/usr/bin/env python3
"""Read-only MIP statistical evidence validator and M1/M2/M3 maturity evaluator."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path

FAMILIES = (
    "ci_reliability",
    "bd_burndown",
    "coverage",
    "debug_ldab",
    "evidence_quality",
    "repair_effectiveness",
    "throughput",
)
SHA_CHARS = set("0123456789abcdef")


def check(row):
    if not isinstance(row, dict) or row.get("schema") != "mip.stat.observation.v1":
        raise ValueError("invalid observation schema")
    if row.get("repository") != "GBOGEB/ABACUS" or row.get("family") not in FAMILIES:
        raise ValueError("invalid repository/family")
    for k in ("metric", "metric_version", "evidence_url", "collection_quality"):
        if not isinstance(row.get(k), str) or not row[k]:
            raise ValueError("missing " + k)
    if not row["evidence_url"].startswith("https://github.com/GBOGEB/ABACUS/"):
        raise ValueError("untrusted evidence URL")
    if row["collection_quality"] not in ("NATIVE", "INCOMPLETE", "UNVERIFIED"):
        raise ValueError("invalid quality")
    sha = row.get("exact_sha")
    if (
        not isinstance(sha, str)
        or len(sha) != 40
        or any(c not in SHA_CHARS for c in sha)
    ):
        raise ValueError("invalid exact SHA")
    for key in ("run_id", "job_id"):
        if type(row.get(key)) is not int or row[key] <= 0:
            raise ValueError("invalid " + key)
    expected_url = "https://github.com/GBOGEB/ABACUS/actions/runs/" + str(row["run_id"])
    if row["evidence_url"] != expected_url:
        raise ValueError("evidence URL does not match run identity")
    timestamp = row.get("observed_at")
    if not isinstance(timestamp, str) or not timestamp.endswith("Z"):
        raise ValueError("invalid UTC timestamp")
    dt.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    status = row.get("status")
    if status not in ("PASS", "FAIL", "UNKNOWN"):
        raise ValueError("invalid status")
    n, d = row.get("numerator"), row.get("denominator")
    if (n is None) != (d is None):
        raise ValueError("partial numerator/denominator")
    if n is not None:
        if type(n) is not int or type(d) is not int or d <= 0 or n < 0 or n > d:
            raise ValueError("invalid count pair")
        if status == "UNKNOWN" or row["collection_quality"] != "NATIVE":
            raise ValueError("unverified numerator")
    if row["metric"] == "workflow_failure_rate" and n is not None:
        if d != 1 or n != int(status == "FAIL"):
            raise ValueError("workflow outcome/count mismatch")
    return row


def match_native(row, evidence):
    """Match a selected receipt to a caller-supplied GitHub API snapshot.

    Offline matching cannot authenticate the snapshot's acquisition. Callers
    must retain its digest and independently acquire it from GitHub. A match
    establishes neither a complete sampling frame nor process independence.
    """
    if evidence is None:
        return False
    if (
        not isinstance(evidence, dict)
        or evidence.get("schema") != "mip.github.snapshot.v1"
    ):
        raise ValueError("invalid native evidence schema")
    runs, jobs = evidence.get("runs"), evidence.get("jobs")
    if not isinstance(runs, list) or not isinstance(jobs, list):
        raise ValueError("invalid native evidence collections")
    for collection in (runs, jobs):
        if any(not isinstance(item, dict) for item in collection):
            raise ValueError("invalid native evidence item")
        ids = [item.get("id") for item in collection]
        if any(type(i) is not int or i <= 0 for i in ids) or len(set(ids)) != len(ids):
            raise ValueError("invalid or duplicate native identity")
    run = next((item for item in runs if item["id"] == row["run_id"]), None)
    job = next((item for item in jobs if item["id"] == row["job_id"]), None)
    if run is None or job is None:
        return False
    if row["family"] != "ci_reliability" or row["metric"] != "workflow_failure_rate":
        return False  # Other metrics require their own native artifact evidence.
    completed = job.get("completed_at")
    if not isinstance(completed, str) or not completed.endswith("Z"):
        return False
    try:
        completed_at = dt.datetime.fromisoformat(completed.replace("Z", "+00:00"))
    except ValueError:
        return False
    observed_at = dt.datetime.fromisoformat(row["observed_at"].replace("Z", "+00:00"))
    expected = {"PASS": "success", "FAIL": "failure"}.get(row["status"])
    return bool(
        expected
        and run.get("html_url") == row["evidence_url"]
        and isinstance(run.get("repository"), dict)
        and run["repository"].get("full_name") == row["repository"]
        and run.get("head_sha") == job.get("head_sha") == row["exact_sha"]
        and job.get("run_id") == run["id"]
        and type(run.get("run_attempt")) is int
        and run["run_attempt"] > 0
        and type(job.get("run_attempt")) is int
        and job.get("run_attempt") == run["run_attempt"]
        and run.get("status") == job.get("status") == "completed"
        and run.get("conclusion") == expected
        and run.get("updated_at") == row["observed_at"]
        and completed_at <= observed_at
        and isinstance(run.get("path"), str)
        and run["path"].startswith(".github/workflows/")
    )


def evaluate(rows, minimum=20, holdout=5, native_evidence=None):
    if minimum < 5 or holdout < 2:
        raise ValueError("invalid maturity thresholds")
    by_family = defaultdict(list)
    identities = set()
    source_identities = {}
    for row in rows:
        check(row)
        for kind in ("run_id", "job_id"):
            identity = (kind, row[kind])
            source = (row["exact_sha"], row["run_id"])
            if identity in source_identities and source_identities[identity] != source:
                raise ValueError("conflicting native source identity")
            source_identities[identity] = source
        key = (
            row["repository"],
            row["exact_sha"],
            row["run_id"],
            row["job_id"],
            row["family"],
            row["metric"],
            row["metric_version"],
        )
        if key in identities:
            raise ValueError("duplicate observation")
        identities.add(key)
        by_family[(row["family"], row["metric"], row["metric_version"])].append(row)
    results = []
    for family in FAMILIES:
        for (f, metric, version), obs in sorted(by_family.items()):
            if f != family:
                continue
            obs.sort(key=lambda x: (x["observed_at"], x["run_id"], x["job_id"]))
            comparable = [
                x
                for x in obs
                if x["collection_quality"] == "NATIVE"
                and x["numerator"] is not None
                and x["status"] != "UNKNOWN"
            ]
            # Distinct run IDs are a count, not a proof of independence.
            distinct = len({x["run_id"] for x in comparable})
            valid = len(comparable) == len(obs) and distinct == len(comparable)
            matched = sum(match_native(x, native_evidence) for x in comparable)
            measurement_valid = valid and bool(obs) and matched == len(obs)
            values = [x["numerator"] / x["denominator"] for x in comparable]
            enough = valid and distinct >= minimum and len(values) >= minimum
            # A preliminary lag-1 check cannot certify stability.
            autocorr = None
            if enough and len(set(values)) > 1:
                mean = statistics.fmean(values)
                denom = sum((x - mean) ** 2 for x in values)
                if denom:
                    autocorr = (
                        sum(
                            (values[i] - mean) * (values[i - 1] - mean)
                            for i in range(1, len(values))
                        )
                        / denom
                    )
            denominator_stable = (
                len({x["denominator"] for x in comparable}) == 1
                if comparable
                else False
            )
            # Explicit conservative hold until adequate process-specific control chart / spec.
            process_stable = False
            cap = False
            # Forward-only previous-observation baseline scored on a reserved final window.
            bt = None
            if (
                enough
                and len(values) >= minimum + holdout
                and denominator_stable
                and not (autocorr is not None and abs(autocorr) >= 0.3)
            ):
                train, test = values[:-holdout], values[-holdout:]
                forecasts = [train[-1]] + test[:-1]
                bt = {
                    "holdout": len(test),
                    "method": "walk_forward_last_observation",
                    "mae": round(
                        statistics.fmean(abs(a - b) for a, b in zip(forecasts, test)), 8
                    ),
                    "forecast_count": len(test),
                    "predictive_authority": "DIAGNOSTIC_ONLY",
                }
            results.append(
                {
                    "family": f,
                    "metric": metric,
                    "metric_version": version,
                    "observations": len(obs),
                    "native_marked_records": len(comparable),
                    "distinct_runs": distinct,
                    "distinct_source_shas": len({x["exact_sha"] for x in obs}),
                    "native_snapshot_matches": matched,
                    "independent_runs": None,
                    "comparability": "UNKNOWN",
                    "independence": "UNKNOWN",
                    "measurement_scope": "SELECTED_RECEIPTS_ONLY",
                    "provenance_basis": (
                        "SUPPLIED_SNAPSHOT"
                        if native_evidence is not None
                        else "MISSING"
                    ),
                    "STRUCTURE_VALID": valid and bool(obs),
                    "missing": len(obs) - len(comparable),
                    "denominator_stable": denominator_stable,
                    "lag1_autocorrelation": autocorr,
                    "MEASUREMENT_VALID": measurement_valid,
                    "M1_DECISION": "PASS" if measurement_valid else "HOLD",
                    "PROCESS_SERIES_DECISION": "HOLD",
                    "STABILITY_ASSESSABLE": False,
                    "PROCESS_STABLE": process_stable,
                    "CAPABILITY_ASSESSABLE": cap,
                    "BACKTEST_ELIGIBLE": False,
                    "backtest": None,
                    "diagnostic_sample_threshold_met": enough,
                    "diagnostic_backtest": bt,
                    "status_counts": {
                        s: sum(x["status"] == s for x in obs)
                        for s in ("PASS", "FAIL", "UNKNOWN")
                    },
                }
            )
    return {
        "schema": "mip.statistical.readiness.v2",
        "repository": "GBOGEB/ABACUS",
        "minimum_independent_observations": minimum,
        "holdout": holdout,
        "series": results,
        "missing_families": [
            f for f in FAMILIES if f not in by_family_names(by_family)
        ],
        "merge_admission": "HOLD",
        "authority_transfer": False,
        "family_states": {
            f: "OBSERVED" if f in by_family_names(by_family) else "UNKNOWN"
            for f in FAMILIES
        },
    }


def by_family_names(groups):
    return {key[0] for key in groups}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--minimum", type=int, default=20)
    p.add_argument("--holdout", type=int, default=5)
    p.add_argument("--native-evidence", type=Path)
    a = p.parse_args()
    input_bytes = a.input.read_bytes()
    rows = [
        json.loads(x) for x in input_bytes.decode("utf-8").splitlines() if x.strip()
    ]
    evidence_bytes = a.native_evidence.read_bytes() if a.native_evidence else None
    evidence = json.loads(evidence_bytes) if evidence_bytes is not None else None
    result = evaluate(rows, a.minimum, a.holdout, evidence)
    result["input_sha256"] = hashlib.sha256(input_bytes).hexdigest()
    result["producer_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result["native_evidence_sha256"] = (
        hashlib.sha256(evidence_bytes).hexdigest()
        if evidence_bytes is not None
        else None
    )
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
