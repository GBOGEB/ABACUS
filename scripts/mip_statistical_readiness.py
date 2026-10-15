#!/usr/bin/env python3
"""Read-only MIP statistical evidence validator and M1/M2/M3 maturity evaluator."""

from __future__ import annotations

import argparse
import datetime as dt
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
    if status == "UNKNOWN" and n is not None:
        raise ValueError("UNKNOWN must remain null")
    return row


def evaluate(rows, minimum=20, holdout=5):
    if minimum < 5 or holdout < 2:
        raise ValueError("invalid maturity thresholds")
    by_family = defaultdict(list)
    identities = set()
    for row in rows:
        check(row)
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
            # Multiple jobs within one run are not independent observations.
            distinct = len({x["run_id"] for x in comparable})
            valid = len(comparable) == len(obs) and distinct == len(comparable)
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
                    "native_comparable": len(comparable),
                    "independent_runs": distinct,
                    "missing": len(obs) - len(comparable),
                    "denominator_stable": denominator_stable,
                    "lag1_autocorrelation": autocorr,
                    "MEASUREMENT_VALID": valid and bool(obs),
                    "STABILITY_ASSESSABLE": enough,
                    "PROCESS_STABLE": process_stable,
                    "CAPABILITY_ASSESSABLE": cap,
                    "BACKTEST_ELIGIBLE": bt is not None,
                    "backtest": bt,
                }
            )
    return {
        "schema": "mip.statistical.readiness.v1",
        "repository": "GBOGEB/ABACUS",
        "minimum_independent_observations": minimum,
        "holdout": holdout,
        "series": results,
        "missing_families": [
            f for f in FAMILIES if f not in by_family_names(by_family)
        ],
        "merge_admission": "HOLD",
        "authority_transfer": False,
    }


def by_family_names(groups):
    return {key[0] for key in groups}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--minimum", type=int, default=20)
    p.add_argument("--holdout", type=int, default=5)
    a = p.parse_args()
    rows = [
        json.loads(x)
        for x in a.input.read_text(encoding="utf-8").splitlines()
        if x.strip()
    ]
    result = evaluate(rows, a.minimum, a.holdout)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
