"""GOGREEN/EVERRED read-only, source-bound queue-pressure pulse comparisons.

Only GitHub status-filter total counts are population totals. Individual queue
IDs and age distributions require a complete, exact-SHA observation; any
incomplete census produces UNKNOWN for those coordinates, never a zero delta.
The module does not mark checks, cancel jobs, change trigger rules or approve PRs.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path

INPUT_SCHEMA = "abacus.feedback.queue-pressure.v1.receipt"
OUTPUT_SCHEMA = "abacus.feedback.queue-trends.v1"
SAFE_CONTROLS = {
    "admission": "HOLD",
    "authority_transfer": False,
    "skip_eligibility": "UNKNOWN_UNTIL_EXACT_OPEN_PR_LINKAGE_PROVEN",
    "remote_mutation_authorized": False,
    "security_waiver": False,
}


def canonical(data):
    return json.dumps(data, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def utc(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("UTC timestamp with Z suffix required")
    try:
        result = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid UTC timestamp") from exc
    return result


def nonneg(value, field):
    if type(value) is not int or value < 0:
        raise ValueError(field + " must be nonnegative integer")
    return value


def validate(p):
    if not isinstance(p, dict) or p.get("schema") != INPUT_SCHEMA:
        raise ValueError("unrecognized pressure receipt")
    if (
        not isinstance(p.get("source_repository"), str)
        or "/" not in p["source_repository"]
    ):
        raise ValueError("missing repository")
    sha = p.get("main_sha")
    if (
        not isinstance(sha, str)
        or len(sha) != 40
        or any(x not in "0123456789abcdef" for x in sha)
    ):
        raise ValueError("full lowercase 40-character main SHA required")
    timestamp = utc(p.get("observed_at"))
    repo = nonneg(p.get("repo_queued_total"), "repo_queued_total")
    main = nonneg(p.get("main_queued_total"), "main_queued_total")
    if main > repo:
        raise ValueError("main queue exceeds repository queue")
    if type(p.get("main_sample_complete")) is not bool:
        raise ValueError("explicit completeness required")
    sample_size = nonneg(p.get("main_sample_size"), "main_sample_size")
    if sample_size > main or (p["main_sample_complete"] != (sample_size == main)):
        raise ValueError("incorrect completeness/denominator")
    sample_feedback = nonneg(
        p.get("main_feedback_workflow_run_sample"), "feedback sample"
    )
    if sample_feedback > sample_size:
        raise ValueError("feedback sample exceeds sample size")
    actual_feedback = p.get("main_feedback_queued_total")
    if p["main_sample_complete"]:
        if nonneg(actual_feedback, "main_feedback_queued_total") != sample_feedback:
            raise ValueError("complete feedback count contradicts sample")
    elif actual_feedback is not None:
        raise ValueError("partial census cannot claim feedback population")
    feedback = p.get("feedback_runs")
    if not isinstance(feedback, list) or len(feedback) != sample_feedback:
        raise ValueError("feedback run list not aligned with sample")
    ids, runs = set(), []
    for entry in feedback:
        if not isinstance(entry, dict):
            raise ValueError("invalid feedback entry")
        ident = entry.get("id")
        if type(ident) is not int or ident <= 0 or ident in ids:
            raise ValueError("duplicate or invalid queued run ID")
        ids.add(ident)
        if (
            entry.get("head_sha") != sha
            or entry.get("name") != "PR Feedback Gate Evaluator"
            or entry.get("event") != "workflow_run"
        ):
            raise ValueError("unexpected identity / wrong source SHA")
        runs.append((ident, entry.get("created_at")))
    if (
        p.get("admission") != "HOLD"
        or p.get("authority_transfer") is not False
        or p.get("remote_mutation_authorized") is not False
    ):
        raise ValueError("pressure measurement cannot transfer authority")
    return {
        "at": timestamp,
        "repo": repo,
        "main": main,
        "complete": p["main_sample_complete"],
        "feedback": actual_feedback,
        "runs": runs,
    }


def qnearest(values, numerator, denominator):
    """Nearest-rank quantile with explicit rank (never interpolate run counts)."""
    if not values:
        return None
    index = math.ceil(len(values) * numerator / denominator) - 1
    return sorted(values)[index]


def queue_age_seconds(p, at):
    if not p["complete"]:
        return {
            "state": "UNKNOWN",
            "reason": "INCOMPLETE_QUEUE_SAMPLE",
            "p50_seconds": None,
            "p95_seconds": None,
        }
    ages = []
    for _, when in p["runs"]:
        if when is None:
            return {
                "state": "UNKNOWN",
                "reason": "MISSING_CREATED_AT",
                "p50_seconds": None,
                "p95_seconds": None,
            }
        age = (at - utc(when)).total_seconds()
        if age < 0:
            return {
                "state": "UNKNOWN",
                "reason": "FUTURE_CREATED_AT",
                "p50_seconds": None,
                "p95_seconds": None,
            }
        ages.append(age)
    # Zero feedback queue is an observed empty population; quantiles undefined.
    return {
        "state": "MEASURED" if ages else "NO_OBSERVATIONS",
        "p50_seconds": qnearest(ages, 1, 2),
        "p95_seconds": qnearest(ages, 95, 100),
    }


def compare(previous, current):
    a = validate(previous)
    b = validate(current)
    if previous["source_repository"] != current["source_repository"]:
        raise ValueError("different source repositories")
    if previous["main_sha"] != current["main_sha"]:
        raise ValueError("different main SHAs; no same-head queue comparison")
    seconds = (b["at"] - a["at"]).total_seconds()
    if seconds <= 0:
        raise ValueError("later pulse must have strictly greater UTC timestamp")
    exact = a["complete"] and b["complete"]
    old_ids, new_ids = ({v[0] for v in a["runs"]}, {v[0] for v in b["runs"]})
    return {
        "schema": OUTPUT_SCHEMA,
        "source_repository": previous["source_repository"],
        "main_sha": previous["main_sha"],
        "pulse_utc": [previous["observed_at"], current["observed_at"]],
        "interval_seconds": seconds,
        "queue_total_before": a["repo"],
        "queue_total_after": b["repo"],
        "queue_net_delta": b["repo"] - a["repo"],
        "queue_net_delta_per_minute": round(60 * (b["repo"] - a["repo"]) / seconds, 3),
        "main_queue_delta": b["main"] - a["main"],
        "main_feedback": {
            "state": "MEASURED" if exact else "UNKNOWN",
            "before": a["feedback"] if exact else None,
            "after": b["feedback"] if exact else None,
            "net_delta": b["feedback"] - a["feedback"] if exact else None,
            "observed_entered": len(new_ids - old_ids) if exact else None,
            "observed_exited": len(old_ids - new_ids) if exact else None,
            "churn_semantics": "snapshot_membership_only_not_completion_or_cancellation",
        },
        "age_feedback_at_latest_pulse": queue_age_seconds(b, b["at"]),
        "throughput": "UNKNOWN: queue exits are not terminal job outcomes",
        "root_closure": "UNKNOWN: queue reduction is not causal repair",
        **SAFE_CONTROLS,
    }


def emit(previous, current, output):
    result = compare(previous, current)
    output.mkdir(parents=True, exist_ok=True)
    encoded = (canonical(result) + "\n").encode("utf-8")
    (output / "trends.json").write_bytes(encoded)
    manifest = {
        "schema": OUTPUT_SCHEMA + ".manifest",
        "sha256": {"trends.json": hashlib.sha256(encoded).hexdigest()},
        "source_sha": result["main_sha"],
        "authority_transfer": False,
    }
    (output / "manifest.json").write_text(canonical(manifest) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous", required=True, type=Path)
    parser.add_argument("--current", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    print(
        canonical(
            emit(
                json.loads(args.previous.read_text()),
                json.loads(args.current.read_text()),
                args.out,
            )
        )
    )


if __name__ == "__main__":
    main()
