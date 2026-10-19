#!/usr/bin/env python3
"""Fail-closed read-only publication telemetry for CODE PURPLE / DMAIC.

A workflow success with a SKIPPED publish job is not a published metrics PR.
Unlike a workflow conclusion this classifier uses exact run/attempt and job
identity; a successful publish step needs a separate source-bound receipt.
No GitHub API mutation, credentials, owner approval or coverage transfer.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SHA = re.compile(r"[0-9a-f]{40}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
JOB_NAME = "Publish DMAIC Metrics Through Governed PR"


def qualify(run: dict, jobs: list[dict], receipt: dict | None = None) -> dict:
    if not isinstance(run, dict) or not isinstance(jobs, list):
        raise ValueError("METRICS_PROOF_HOLD: invalid native data")
    sha = run.get("head_sha")
    rid, attempt = run.get("id"), run.get("run_attempt")
    if (not isinstance(sha, str) or SHA.fullmatch(sha) is None or
            type(rid) is not int or rid < 1 or
            type(attempt) is not int or attempt < 1):
        raise ValueError("METRICS_PROOF_HOLD: exact SHA/run/attempt")
    identities = [j.get("id") for j in jobs if isinstance(j, dict)]
    if (len(identities) != len(jobs) or
            any(type(i) is not int or i < 1 for i in identities) or
            len(identities) != len(set(identities))):
        raise ValueError("METRICS_PROOF_HOLD: incomplete/duplicate job identity")
    found = [j for j in jobs if j.get("name") == JOB_NAME]
    if len(found) != 1:
        raise ValueError("METRICS_PROOF_HOLD: missing/duplicate publication job")
    job = found[0]
    if job.get("run_id") != rid:
        raise ValueError("METRICS_PROOF_HOLD: job from another native run")
    if run.get("status") != "completed" or job.get("status") != "completed":
        state = "NONTERMINAL_NO_CREDIT"
    elif job.get("conclusion") == "skipped":
        state = "DEFERRED_SKIPPED_NO_PUBLICATION"
    elif job.get("conclusion") == "failure":
        state = "NATIVE_PUBLICATION_FAILED"
    elif job.get("conclusion") != "success":
        state = "UNKNOWN_TERMINAL_NO_CREDIT"
    elif run.get("conclusion") != "success":
        state = "JOB_SUCCESS_BUT_WORKFLOW_NOT_SUCCESS"
    else:
        state = "SUCCESS_WITHOUT_BOUND_RECEIPT"
        if receipt is not None:
            if (not isinstance(receipt, dict) or
                    receipt.get("source_sha") != sha or
                    receipt.get("run_id") != rid or
                    receipt.get("run_attempt") != attempt or
                    receipt.get("job_id") != job["id"] or
                    type(receipt.get("destination_pr_number")) is not int or
                    receipt["destination_pr_number"] <= 0 or
                    not isinstance(receipt.get("artifact_sha256"), str) or
                    not DIGEST.fullmatch(receipt["artifact_sha256"])):
                raise ValueError("METRICS_PROOF_HOLD: forged/unbound receipt")
            state = "SOURCE_BOUND_RECEIPT_SUPPLIED_REVIEW_REQUIRED"
    return {
        "schema": "abacus.g3g.metrics_publication.v1",
        "source_sha": sha, "run_id": rid, "attempt": attempt,
        "publication_job_id": job["id"],
        "publication_job_conclusion": job.get("conclusion"),
        "qualifier": state,
        "proof_of_native_publication": state ==
             "SOURCE_BOUND_RECEIPT_SUPPLIED_REVIEW_REQUIRED",
        "proof_of_human_acceptance": False,
        "proof_of_required_status_admission": False,
        "credential_evidence": None,
        "formal_causal_root_closure": None,
        "fresh_federation_coverage": None,
        "merge_admission": "HOLD",
        "security_waiver": False,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, type=Path)
    ap.add_argument("--jobs", required=True, type=Path)
    ap.add_argument("--receipt", type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    run = json.loads(args.run.read_text(encoding="utf-8"))
    jobs = json.loads(args.jobs.read_text(encoding="utf-8"))
    receipt = (json.loads(args.receipt.read_text(encoding="utf-8"))
               if args.receipt else None)
    result = qualify(run, jobs, receipt)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n",
                        encoding="utf-8")
    print("METRICS_PUBLICATION=" + result["qualifier"] +
          "; INDEPENDENT_ADMISSION=HOLD")


if __name__ == "__main__":
    main()
