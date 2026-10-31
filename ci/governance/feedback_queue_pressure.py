"""Read-only PR Feedback Gate queue-pressure receipt; never an admission gate.

Historical totals, current queue totals and sampled workflow names have distinct
denominators. Default-branch completions are NOT assumed to be no-ops.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
from pathlib import Path

REPO = "GBOGEB/ABACUS"
SHA = re.compile(r"[0-9a-f]{40}\Z")
SCHEMA = "abacus.feedback.queue-pressure.v1"
FEEDBACK = "PR Feedback Gate Evaluator"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def valid_stamp(s):
    if not isinstance(s, str):
        raise ValueError("observed_at must be UTC ISO 8601")
    try:
        t = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid observed_at") from exc
    if t.utcoffset() != dt.timedelta():
        raise ValueError("observation must be UTC")


def _queue(name, payload, expected_sha=None):
    if not isinstance(payload, dict):
        raise ValueError(name + " query missing")
    total = payload.get("total_count")
    runs = payload.get("workflow_runs")
    if type(total) is not int or total < 0 or not isinstance(runs, list):
        raise ValueError(name + " invalid run count")
    if len(runs) > total:
        raise ValueError(name + " sample exceeds total")
    ids, clean = set(), []
    for run in runs:
        if not isinstance(run, dict):
            raise ValueError(name + " invalid run row")
        ident = run.get("id")
        if type(ident) is not int or ident <= 0 or ident in ids:
            raise ValueError(name + " invalid or repeated run ID")
        ids.add(ident)
        if run.get("status") != "queued":
            raise ValueError(name + " contains a non-queued run")
        if not isinstance(run.get("name"), str) or not run["name"]:
            raise ValueError(name + " workflow identity missing")
        if expected_sha is not None and run.get("head_sha") != expected_sha:
            raise ValueError(name + " source SHA mismatch")
        clean.append(
            {
                "id": ident,
                "name": run["name"],
                "event": run.get("event", "UNKNOWN"),
                "head_sha": run.get("head_sha"),
                "head_branch": run.get("head_branch"),
                "created_at": run.get("created_at"),
            }
        )
    clean.sort(key=lambda r: r["id"])
    return {
        "total": total,
        "sampled": len(clean),
        "complete": len(clean) == total,
        "runs": clean,
    }


def analyze(data):
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise ValueError("unknown pressure input schema")
    if data.get("repository") != REPO or not isinstance(data.get("main_sha"), str):
        raise ValueError("wrong repository")
    sha = data["main_sha"]
    if not SHA.fullmatch(sha):
        raise ValueError("exact 40-character SHA required")
    valid_stamp(data.get("observed_at"))
    repository = _queue("repository", data.get("repository_queued"))
    main = _queue("main", data.get("main_queued"), sha)
    if main["total"] > repository["total"]:
        raise ValueError("main queue cannot exceed repository queue")
    sampled_feedback = [
        r
        for r in main["runs"]
        if r["name"] == FEEDBACK and r["event"] == "workflow_run"
    ]
    return {
        "schema": SCHEMA + ".receipt",
        "source_repository": REPO,
        "main_sha": sha,
        "observed_at": data["observed_at"],
        "repo_queued_total": repository["total"],
        "main_queued_total": main["total"],
        "main_feedback_workflow_run_sample": len(sampled_feedback),
        "main_sample_size": main["sampled"],
        "main_sample_complete": main["complete"],
        "main_feedback_queued_total": (
            len(sampled_feedback) if main["complete"] else None
        ),
        "feedback_fraction_of_main_queued_pct": (
            round(100 * len(sampled_feedback) / main["total"], 2)
            if main["complete"] and main["total"]
            else (0.0 if main["complete"] else None)
        ),
        "feedback_runs": sampled_feedback,
        "skip_eligibility": "UNKNOWN_UNTIL_EXACT_OPEN_PR_LINKAGE_PROVEN",
        "root_closures": 0,
        "admission": "HOLD",
        "authority_transfer": False,
        "remote_mutation_authorized": False,
        "security_waiver": False,
        "note": "Queued counts are exact to the API query, breakdown is sample-only unless complete; no effect or causality is inferred from status.",
    }


def emit(data, output):
    result = analyze(data)
    output.mkdir(parents=True, exist_ok=True)
    # Hash and write the same bytes: text-mode writes translate "\n" to "\r\n"
    # on Windows, so the manifest would not bind the receipt on disk.
    report = (canonical(result) + "\n").encode("utf-8")
    (output / "pressure.json").write_bytes(report)
    manifest = {
        "schema": SCHEMA + ".manifest",
        "sha256": {"pressure.json": hashlib.sha256(report).hexdigest()},
        "source_sha": result["main_sha"],
        "authority_transfer": False,
    }
    (output / "manifest.json").write_bytes((canonical(manifest) + "\n").encode("utf-8"))
    return result


def collect_live(expected_sha, observed_at):
    # Reuse the repository's existing GitHub HTTP client; do not introduce
    # another token/authentication implementation. Calls here are GET only.
    from ci.governance.pr_feedback_gate import GitHub

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise ValueError("read-only GITHUB_TOKEN is required")
    github = GitHub(token, REPO)
    branch = github.request("GET", "/repos/" + REPO + "/branches/main")
    if (branch.get("commit") or {}).get("sha") != expected_sha:
        raise ValueError("source main HEAD moved; recensus instead of mixing refs")
    suffix = "&per_page=100"
    base = "/repos/" + REPO + "/actions/runs?status=queued"
    repository = github.request("GET", base + suffix)
    main = github.request("GET", base + "&head_sha=" + expected_sha + suffix)
    return {
        "schema": SCHEMA,
        "repository": REPO,
        "main_sha": expected_sha,
        "observed_at": observed_at,
        "repository_queued": repository,
        "main_queued": main,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--observed-at", required=True)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    input_data = (
        json.loads(args.fixture.read_text(encoding="utf-8"))
        if args.fixture
        else collect_live(args.sha, args.observed_at)
    )
    if input_data["main_sha"] != args.sha:
        raise ValueError("expected SHA differs from input")
    print(canonical(emit(input_data, args.output)))


if __name__ == "__main__":
    main()
