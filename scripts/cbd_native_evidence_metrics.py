"""Read-only replayer for frozen, non-atomic CBD GitHub job evidence.

This is a validation/projection worker, not the canonical BD ledger or a
GitHub-origin attestation. Raw native API capture remains source-bound.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "docs/ci/CBD_W2_NATIVE_EVIDENCE_20261017.json"
_SHA = re.compile(r"[0-9a-f]{40}\Z")


def _integer(value: object, *, minimum: int = 0) -> bool:
    return type(value) is int and value >= minimum


def replay(snapshot: dict) -> dict:
    """Check evidence identities, rebuild denominators and output a safe DAG."""
    if not isinstance(snapshot, dict) or snapshot.get("schema") != (
        "cbd.native-triage-dashboard-snapshot.v1"
    ):
        raise ValueError("native snapshot schema")
    if snapshot.get("repository") != "GBOGEB/ABACUS":
        raise ValueError("foreign repository")
    if snapshot.get("observation_scope") != (
        "NONATOMIC_FROZEN_COHORT_AND_LATEST_RUN_ATTEMPTS"
    ) or snapshot.get("source_snapshot_rate_eligible") is not False:
        raise ValueError("false atomic or fleet-rate inference")
    gate = snapshot.get("authority", {})
    if gate.get("merge_admission") != "HOLD" or gate.get(
        "security_waiver"
    ) is not False or gate.get("source_mutation_authorized") is not False:
        raise ValueError("unauthorized merge, waiver or mutation")

    metrics = snapshot.get("metrics")
    rows = snapshot.get("run_evidence")
    heads = snapshot.get("head_readbacks")
    if not isinstance(metrics, dict) or not isinstance(rows, list) or not rows:
        raise ValueError("missing native observations")
    if not isinstance(heads, list) or not heads:
        raise ValueError("missing PR head census")

    seen_runs = set()
    failed_latest = 0
    nonterminal = 0
    failed_jobs = 0
    failed_steps = 0
    first_reds = 0
    logs = 0
    signature_prs = set()
    signature_runs = 0
    symptom_buckets = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("invalid native row")
        rid = row.get("run_id")
        if not _integer(rid, minimum=1) or rid in seen_runs:
            raise ValueError("duplicate or invalid run ID")
        seen_runs.add(rid)
        sha = row.get("source_sha")
        if not isinstance(sha, str) or not _SHA.fullmatch(sha):
            raise ValueError("invalid source SHA")
        if not (
            row.get("head") == sha
            and row.get("event") == "pull_request"
            and row.get("native_workflow") == row.get("workflow")
            and row.get("pr_link") is True
            and _integer(row.get("pr"), minimum=1)
            and _integer(row.get("attempt"), minimum=1)
        ):
            raise ValueError("run/head/attempt provenance mismatch")
        if row.get("authenticated") is True and row.get("result") == "failure":
            failed_latest += 1
        elif row.get("authenticated") is False and row.get("result") is None:
            nonterminal += 1
        else:
            raise ValueError("unsupported latest-attempt verdict")

        jobs = row.get("jobs")
        if not isinstance(jobs, dict) or jobs.get("complete") is not True or jobs.get(
            "job_attempt_verified"
        ) is not True:
            raise ValueError("missing exact-attempt job proof")
        if not (
            _integer(jobs.get("jobs_returned"))
            and jobs.get("jobs_returned") == jobs.get("jobs_reported")
            == jobs.get("provenance_aligned_jobs")
        ):
            raise ValueError("incomplete job denominator")
        n_failed = jobs.get("failed_jobs")
        n_steps = jobs.get("failed_steps")
        if not _integer(n_failed) or not _integer(n_steps) or n_steps < n_failed:
            raise ValueError("invalid failed job/step denominator")
        failed_jobs += n_failed
        failed_steps += n_steps
        first = jobs.get("first_failed_step")
        if first is not None:
            if not isinstance(first, dict) or not (
                _integer(first.get("job_id"), minimum=1)
                and _integer(first.get("step_number"), minimum=1)
                and isinstance(first.get("step_name"), str)
                and first["step_name"].strip()
            ):
                raise ValueError("unattributed first-red step")
            first_reds += 1
            bucket = first["step_name"]
            symptom_buckets[bucket] = symptom_buckets.get(bucket, 0) + 1
        else:
            symptom_buckets["NO_TERMINAL_FAILED_STEP"] = (
                symptom_buckets.get("NO_TERMINAL_FAILED_STEP", 0) + 1
            )
        log = row.get("log_evidence")
        if log is not None:
            if not isinstance(log, dict) or log.get("downloaded") is not True:
                raise ValueError("unverified log evidence")
            if first is None or log.get("job_id") != first["job_id"]:
                raise ValueError("log/first-red attribution mismatch")
            logs += 1
            signals = log.get("signals", [])
            if not isinstance(signals, list):
                raise ValueError("invalid log signals")
            if "MATPLOTLIB_RESOLVER" in signals:
                if first["step_name"] not in (
                    "Install tooling", "Install canonical dependencies"
                ):
                    raise ValueError("unsupported resolver step")
                if not any(
                    "No matching distribution found for matplotlib" in ex.get("value", "")
                    for ex in log.get("excerpt", [])
                ):
                    raise ValueError("resolver signal without supporting log text")
                signature_runs += 1
                signature_prs.add(row["pr"])

    manifest_ids = set()
    stale_heads = []
    for h in heads:
        if not isinstance(h, dict) or not _integer(h.get("pr"), minimum=1):
            raise ValueError("invalid head census")
        if h["pr"] in manifest_ids:
            raise ValueError("duplicate head manifest")
        manifest_ids.add(h["pr"])
        if not all(isinstance(h.get(k), str) and _SHA.fullmatch(h[k]) for k in (
            "source_sha", "current_sha"
        )):
            raise ValueError("malformed head SHA")
        if h.get("head_matches") is not (h["source_sha"] == h["current_sha"]):
            raise ValueError("false current-head indication")
        if not h["head_matches"]:
            stale_heads.append(h["pr"])
    if not all(_integer(metrics.get(key)) for key in (
        "declared_source_rows", "unique_runs", "aliases", "manifest_prs",
        "heads_matching", "native_latest_failure", "latest_nonterminal",
        "fully_aligned_jobsets", "failed_jobs", "failed_steps",
        "observed_first_failed_step", "downloaded_logs",
        "matplotlib_signature_runs", "accepted_closed_roots",
    )):
        raise ValueError("noninteger metric denominator")
    measured = {
        "unique_runs": len(seen_runs),
        "manifest_prs": len(manifest_ids),
        "heads_matching": len(heads) - len(stale_heads),
        "native_latest_failure": failed_latest,
        "latest_nonterminal": nonterminal,
        "fully_aligned_jobsets": len(rows),
        "failed_jobs": failed_jobs,
        "failed_steps": failed_steps,
        "observed_first_failed_step": first_reds,
        "downloaded_logs": logs,
        "matplotlib_signature_runs": signature_runs,
    }
    if any(metrics[k] != v for k, v in measured.items()):
        raise ValueError("metric numerator/denominator mismatch")
    if (
        metrics["declared_source_rows"] != len(rows) + metrics["aliases"]
        or sorted(metrics.get("heads_stale", [])) != sorted(stale_heads)
        or sorted(metrics.get("matplotlib_affected_prs", []))
        != sorted(signature_prs)
    ):
        raise ValueError("inconsistent aliases, stale heads or signature reach")
    root = snapshot.get("root_assessment", {})
    if (
        metrics["accepted_closed_roots"] != 0
        or metrics.get("validated_main_coverage_delta") is not None
        or root.get("closure") != 0
        or root.get("first_red_runs") != signature_runs
        or sorted(root.get("affected_prs", [])) != sorted(signature_prs)
    ):
        raise ValueError("unverified closure, coverage or repair credit")
    if snapshot.get("source_manifest_workflow_total_nonatomic") != 533:
        raise ValueError("unmatched frozen manifest denominator")

    def fraction(num: int, denominator: int) -> dict:
        return {"numerator": num, "denominator": denominator,
                "percent": round(100 * num / denominator, 3) if denominator else None}

    return {
        "schema": "cbd.read_only_native_pulse.v1",
        "repository": "GBOGEB/ABACUS",
        "observation_kind": "NONATOMIC_LATEST_ATTEMPT_CENSUS",
        "run_binding": fraction(len(rows), len(rows)),
        "first_red_step_reach": fraction(first_reds, len(rows)),
        "log_sampling_reach": fraction(logs, len(rows)),
        "terminal_failed_latest_attempts": fraction(failed_latest, len(rows)),
        "head_currentness": fraction(len(heads) - len(stale_heads), len(heads)),
        "resolver_attribution": {
            "signature_runs": signature_runs,
            "pr_upper_bound": len(signature_prs),
            "affected_prs": sorted(signature_prs),
            "accepted_root_closures": 0,
        },
        "failed_jobs": failed_jobs,
        "failed_steps": failed_steps,
        "candidate_symptom_buckets": dict(sorted(symptom_buckets.items())),
        "dag": ["cohort", "native_run_attempt", "job", "first_red_step",
                "sampled_log", "source_owner", "native_retest", "admission"],
        "sipoc": {"supplier": "GitHub Actions", "input": "source SHA/run/attempt",
                  "process": "observe/classify/retest",
                  "output": "non-admitting receipt",
                  "customer": "canonical BD-LDAB issue 1929"},
        "matched_statement_coverage": None,
        "matched_branch_coverage": None,
        "queue_p95_seconds": None,
        "accepted_closures": 0,
        "admission": "HOLD",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = replay(json.loads(args.source.read_text(encoding="utf-8")))
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


if __name__ == "__main__":
    main()
