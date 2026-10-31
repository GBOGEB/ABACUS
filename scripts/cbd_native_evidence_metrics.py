"""Read-only replayer for frozen, non-atomic CBD GitHub job evidence.

This is a validation/projection worker, not the canonical BD ledger or a
GitHub-origin attestation. Raw native API capture remains source-bound.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SOURCE = (
    Path(__file__).resolve().parents[1] / "docs/ci/CBD_W2_NATIVE_EVIDENCE_20261017.json"
)
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
    if (
        snapshot.get("observation_scope")
        != ("NONATOMIC_FROZEN_COHORT_AND_LATEST_RUN_ATTEMPTS")
        or snapshot.get("source_snapshot_rate_eligible") is not False
    ):
        raise ValueError("false atomic or fleet-rate inference")
    gate = snapshot.get("authority", {})
    if (
        gate.get("merge_admission") != "HOLD"
        or gate.get("security_waiver") is not False
        or gate.get("source_mutation_authorized") is not False
    ):
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
        if (
            not isinstance(jobs, dict)
            or jobs.get("complete") is not True
            or jobs.get("job_attempt_verified") is not True
        ):
            raise ValueError("missing exact-attempt job proof")
        if not (
            _integer(jobs.get("jobs_returned"))
            and jobs.get("jobs_returned")
            == jobs.get("jobs_reported")
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
                    "Install tooling",
                    "Install canonical dependencies",
                ):
                    raise ValueError("unsupported resolver step")
                if not any(
                    "No matching distribution found for matplotlib"
                    in ex.get("value", "")
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
        if not all(
            isinstance(h.get(k), str) and _SHA.fullmatch(h[k])
            for k in ("source_sha", "current_sha")
        ):
            raise ValueError("malformed head SHA")
        if h.get("head_matches") is not (h["source_sha"] == h["current_sha"]):
            raise ValueError("false current-head indication")
        if not h["head_matches"]:
            stale_heads.append(h["pr"])
    if not all(
        _integer(metrics.get(key))
        for key in (
            "declared_source_rows",
            "unique_runs",
            "aliases",
            "manifest_prs",
            "heads_matching",
            "native_latest_failure",
            "latest_nonterminal",
            "fully_aligned_jobsets",
            "failed_jobs",
            "failed_steps",
            "observed_first_failed_step",
            "downloaded_logs",
            "matplotlib_signature_runs",
            "accepted_closed_roots",
        )
    ):
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
        or sorted(metrics.get("matplotlib_affected_prs", [])) != sorted(signature_prs)
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
        return {
            "numerator": num,
            "denominator": denominator,
            "percent": round(100 * num / denominator, 3) if denominator else None,
        }

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
        "dag": [
            "cohort",
            "native_run_attempt",
            "job",
            "first_red_step",
            "sampled_log",
            "source_owner",
            "native_retest",
            "admission",
        ],
        "sipoc": {
            "supplier": "GitHub Actions",
            "input": "source SHA/run/attempt",
            "process": "observe/classify/retest",
            "output": "non-admitting receipt",
            "customer": "canonical BD-LDAB issue 1929",
        },
        "matched_statement_coverage": None,
        "matched_branch_coverage": None,
        "queue_p95_seconds": None,
        "accepted_closures": 0,
        "admission": "HOLD",
    }


SUPPLEMENT = (
    Path(__file__).resolve().parents[1]
    / "docs/ci/CBD_W3_NATIVE_LOG_SUPPLEMENT_20261017.json"
)


def classify_supplement_first_red(record: dict) -> str:
    """Classify only step-bound, witnessed failures, never incidental tool names."""
    text = "\n".join(record.get("diagnostic_tail_sanitized", []))
    step = record.get("first_failed_step")
    if (
        step == "Fail closed on governance red"
        and "policy_outcome=failure" in text
        and "inventory_outcome=failure" in text
    ):
        return "GOVERNANCE_POLICY_INVENTORY"
    if (
        step == "Generate governance inventory as evidence"
        and "CI governance failed: unclassified workflows" in text
    ):
        return "GOVERNANCE_UNCLASSIFIED_WORKFLOW"
    if step == "Enforce security red roots" and "##[error]Safety is red." in text:
        return "SAFETY_NONZERO"
    if (
        step == "Tender guard (new or changed files only)"
        and "restricted term in content" in text
    ):
        return "A10_RESTRICTED"
    if (
        step == "Run canonical exact-head coverage surface"
        and "test_change_detector_legacy_windows_snapshot_does_not_create_phantom_change"
        in text
    ):
        return "TEST_PATH_NORMALIZATION"
    if (
        step == "Install dependencies"
        and "No matching distribution found for matplotlib" in text
    ):
        return "MATPLOTLIB_RESOLVER"
    if step == "Verify committed Black and isort styles" and "would reformat" in text:
        return "BLACK_REFORMAT"
    if step == "Validate changed docs" and "error MD013/line-length" in text:
        return "MARKDOWN_MD013"
    if (
        step == "Upload to code-scanning"
        and "API rate limit exceeded for installation" in text
    ):
        return "GITHUB_API_RATE_LIMIT"
    if (
        step == "Enforce code-quality red roots"
        and "Required BLACK full scan failed." in text
        and "Required ISORT full scan failed." in text
    ):
        return "QUALITY_BLACK_ISORT"
    return "UNCLASSIFIED_REQUIRES_REVIEW"


def replay_supplement(snapshot: dict, supplement: dict) -> dict:
    """Join nonoverlapping, targeted log evidence without creating new authority."""
    baseline = replay(snapshot)
    if (
        not isinstance(supplement, dict)
        or supplement.get("schema") != ("cbd.native_log_supplement.v2")
        or supplement.get("repository") != "GBOGEB/ABACUS"
    ):
        raise ValueError("supplement source schema or repository")
    if supplement.get("source_snapshot_sha") != snapshot.get("source_ref"):
        raise ValueError("wrong evidence checkpoint")
    if (
        supplement.get("selection_bias")
        != "TARGETED_STRATA_NOT_RANDOM_FREQUENCY_SAMPLE"
        or supplement.get("untrusted_search_hits_are_not_root_categories") is not True
        or supplement.get("admission") != "HOLD"
        or supplement.get("accepted_root_closures") != 0
    ):
        raise ValueError("non-atomic classification authority violated")
    records = supplement.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("missing supplementary job logs")
    base_runs = {r["run_id"]: r for r in snapshot["run_evidence"]}
    classified = {}
    seen = set()
    supplemental_matplotlib = 0
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("invalid supplementary record")
        run_id = record.get("run_id")
        if not _integer(run_id, minimum=1) or run_id not in base_runs or run_id in seen:
            raise ValueError("duplicate or unbound supplemental run")
        seen.add(run_id)
        original = base_runs[run_id]
        first = original["jobs"]["first_failed_step"]
        if original.get("log_evidence") is not None or first is None:
            raise ValueError("supplement duplicates previously sampled first-red")
        if not (
            record.get("head_sha") == original["source_sha"]
            and record.get("attempt") == original["attempt"]
            and record.get("pr") == original["pr"]
            and record.get("job_id") == first["job_id"]
            and record.get("first_failed_step") == first["step_name"]
            and record.get("failed_step_number") == first["step_number"]
            and record.get("workflow") == original["workflow"]
            and record.get("log_retrieved") is True
        ):
            raise ValueError("supplement run/job/step source mismatch")
        if not isinstance(record.get("diagnostic_tail_sanitized"), list):
            raise ValueError("missing log witness snippets")
        identity = classify_supplement_first_red(record)
        if (
            identity != record.get("validated_signature")
            or identity == ("UNCLASSIFIED_REQUIRES_REVIEW")
            or record.get("signature_grounded_in_sanitized_witness") is not True
        ):
            raise ValueError("unsupported first-red root signature")
        if (
            record.get("causal_root_admission") is not False
            or record.get("rerun_admission") is not False
        ):
            raise ValueError("false root or rerun acceptance")
        classified[identity] = classified.get(identity, 0) + 1
        if identity == "MATPLOTLIB_RESOLVER":
            supplemental_matplotlib += 1
    if (
        supplement.get("new_log_rows") != len(records)
        or supplement.get("new_logs_downloaded") != len(records)
        or supplement.get("baseline_logged_runs")
        != baseline["log_sampling_reach"]["numerator"]
        or supplement.get("baseline_unique_runs") != len(base_runs)
        or supplement.get("uniquely_new") is not True
        or supplement.get("all_records_have_witness") is not True
        or supplement.get("validated_signature_counts") != classified
    ):
        raise ValueError("false supplemental denominators or classes")
    combined = baseline["log_sampling_reach"]["numerator"] + len(records)
    baseline["log_sampling_reach"] = {
        "numerator": combined,
        "denominator": len(base_runs),
        "percent": round(100.0 * combined / len(base_runs), 3),
    }
    baseline["supplemental_logs"] = len(records)
    baseline["classified_first_red_supplement"] = dict(sorted(classified.items()))
    baseline["resolver_attribution"]["signature_runs"] += supplemental_matplotlib
    baseline["resolver_attribution"]["accepted_root_closures"] = 0
    baseline["selection_bias"] = "TARGETED_NOT_INFERENTIAL"
    baseline["historical_first_red_proof_only"] = True
    baseline["admission"] = "HOLD"
    return baseline


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--supplement", type=Path)
    args = parser.parse_args()
    source = json.loads(args.source.read_text(encoding="utf-8"))
    result = (
        replay_supplement(
            source, json.loads(args.supplement.read_text(encoding="utf-8"))
        )
        if args.supplement
        else replay(source)
    )
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


if __name__ == "__main__":
    main()
