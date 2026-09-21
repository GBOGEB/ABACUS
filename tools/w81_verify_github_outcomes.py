#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import urllib.request
from pathlib import Path

API = "https://api.github.com"
REPO = "GBOGEB/ABACUS"

def get_json(url: str) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ABACUS-W81",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)

def verify_observation(source_sha: str, obs: dict) -> dict:
    run = get_json(f"{API}/repos/{REPO}/actions/runs/{int(obs['run_id'])}")
    if run.get("head_sha") != source_sha:
        raise ValueError(f"run {obs['run_id']} head SHA mismatch")
    if run.get("name") != obs["workflow"]:
        raise ValueError(f"run {obs['run_id']} workflow mismatch")
    if run.get("event") != obs["event"]:
        raise ValueError(f"run {obs['run_id']} event mismatch")
    if run.get("status") != "completed" or run.get("conclusion") != obs["conclusion"]:
        raise ValueError(f"run {obs['run_id']} conclusion/status mismatch")

    jobs = get_json(
        f"{API}/repos/{REPO}/actions/runs/{int(obs['run_id'])}/jobs?per_page=100"
    ).get("jobs", [])
    job = next((x for x in jobs if int(x.get("id", 0)) == int(obs["job_id"])), None)
    if job is None:
        raise ValueError(f"job {obs['job_id']} missing from run {obs['run_id']}")
    if job.get("name") != obs["job_name"]:
        raise ValueError(f"job {obs['job_id']} name mismatch")
    if job.get("status") != "completed" or job.get("conclusion") != obs["conclusion"]:
        raise ValueError(f"job {obs['job_id']} conclusion/status mismatch")
    steps = list(job.get("steps") or [])
    executed = [s for s in steps if s.get("status") == "completed"]
    if len(executed) <= 2:
        raise ValueError(f"job {obs['job_id']} did not execute substantive steps")
    return {
        "run_id": int(obs["run_id"]),
        "job_id": int(obs["job_id"]),
        "source_sha": source_sha,
        "workflow": obs["workflow"],
        "job_name": obs["job_name"],
        "event": obs["event"],
        "conclusion": obs["conclusion"],
        "executed_step_count": len(executed),
        "verified": True,
    }

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))

    missing = []
    for state in contract["primary_frontier_check"]["states"]:
        data = get_json(
            f"{API}/repos/{REPO}/actions/runs?head_sha={state['source_sha']}&per_page=1"
        )
        actual = int(data.get("total_count", -1))
        expected = int(state["expected_actions_run_count"])
        if actual != expected:
            raise ValueError(
                f"{state['label']} Actions count changed: expected {expected}, got {actual}"
            )
        missing.append({
            "label": state["label"],
            "source_sha": state["source_sha"],
            "actions_run_count": actual,
            "status": "NO_ACTIONS_EVIDENCE" if actual == 0 else "OBSERVED",
        })

    observations = []
    for episode in contract["episodes"]:
        for phase, source_key, obs_key in (
            ("failure", "failure_source_sha", "observed_failure"),
            ("repair", "repair_source_sha", "observed_repair"),
        ):
            for obs in episode[obs_key]:
                row = verify_observation(episode[source_key], obs)
                row["episode_id"] = episode["episode_id"]
                row["phase"] = phase
                observations.append(row)

    receipt = {
        "schema_version": "MC2-W81-GITHUB-OUTCOME-VERIFICATION-0.1.0",
        "repository": REPO,
        "result": "PASS",
        "primary_frontier": {
            "result": "EXHAUSTED_NO_ACTIONS_EVIDENCE",
            "states": missing,
        },
        "repair_episode_semantics": contract["repair_episode_semantics"],
        "verified_observations": observations,
        "authority_transfer": False,
        "formal_credit_delta": 0,
    }
    Path(args.out).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
