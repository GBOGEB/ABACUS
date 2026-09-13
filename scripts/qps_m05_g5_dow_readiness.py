#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import urllib.request

CODEX_HEAD = "18598958a38c801e63c18d14490c27df426f7e1c"
CONTRACT_PATH = "docs/qps_m05/QPS_G5_KEB_CHALLENGE_v0.1.json"
CONTRACT_URL = (
    "https://raw.githubusercontent.com/GBOGEB/CODEX/"
    f"{CODEX_HEAD}/{CONTRACT_PATH}"
)

H1_RUN_ID = 34730906661
H1_JOB_ID = 103653394137
H1_RUNNER_ID = 1000260663

H2_REPO = "GBOGEB/Q_engineering_tools"
H2_HEAD = "840bac77fa54fd9701a0010321c5d710e081b2db"
H2_RUN_ID = 34760090016
H2_JOB_ID = 103731285019
H2_RUNNER_ID = 1000261441
H2_ARTIFACT_ID = 10318418865
H2_ARTIFACT_DIGEST = (
    "sha256:7b3d83e0c5a421801216f5e2737893a45e3a0f54f6981ffd4758313f390aacf7"
)


def fetch_json(url: str):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "QPS-M05-G5-DOW-independent-consumer"},
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read()
    return raw, json.loads(raw)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> int:
    raw, contract = fetch_json(CONTRACT_URL)
    digest = hashlib.sha256(raw).hexdigest()

    require(
        contract["schema"] == "qps.g5.keb_challenge.v1",
        "G5 KEB contract schema mismatch",
    )
    require(
        contract["mission"] == "MISSION_H2_KEB",
        "unexpected producer mission",
    )
    require(
        contract["local_mission"] == "M05_PROVENANCE_ATTESTATION",
        "unexpected local mission",
    )
    require(
        contract["authority"]
        == "SEMANTIC_PROVENANCE_CHALLENGE_ONLY_NOT_ENGINEERING_ACCEPTANCE",
        "KEB authority boundary mismatch",
    )
    require(
        contract["challenge_predicate"]["promotion_authority"] is False,
        "KEB contract may not grant child promotion authority",
    )

    semantic = contract["semantic_contract"]
    require(
        semantic["actual_numeric_cost_release"] == "WITHHELD_SOURCE_VALUES",
        "numeric-cost release overstated",
    )
    require(
        semantic["actual_numeric_cost_rows_ready"] == "0_of_3",
        "numeric-cost readiness overstated",
    )
    require(
        semantic["unknown_numeric_semantics"] == "NULL_NOT_ZERO",
        "unknown-value semantics drift",
    )
    require(
        semantic["source_value_gates"] == [974, 981],
        "source-value gate drift",
    )

    execution = contract["execution"]
    require(execution["run"] == H1_RUN_ID, "H1 run mismatch")
    require(execution["job"] == H1_JOB_ID, "H1 job mismatch")
    require(execution["runner_id"] == H1_RUNNER_ID, "H1 runner identity mismatch")
    require(
        execution["result"] == "PASS_EXECUTED_EXACT_PAYLOAD",
        "H1 runtime result mismatch",
    )

    api = "https://api.github.com/repos/GBOGEB/Q_engineering_tools/actions"
    _, h2_run = fetch_json(f"{api}/runs/{H2_RUN_ID}")
    require(
        h2_run["status"] == "completed" and h2_run["conclusion"] == "success",
        "H2 live run is not successful",
    )
    require(h2_run["head_sha"] == H2_HEAD, "H2 live head mismatch")
    require(
        h2_run["event"] == "push" and h2_run["head_branch"] == "main",
        "H2 live run is not an automatic main push",
    )

    _, jobs = fetch_json(f"{api}/runs/{H2_RUN_ID}/jobs")
    matches = [job for job in jobs.get("jobs", []) if job.get("id") == H2_JOB_ID]
    require(len(matches) == 1, "expected H2 job not found")
    job = matches[0]
    require(
        job["status"] == "completed" and job["conclusion"] == "success",
        "H2 live job is not successful",
    )
    require(job.get("runner_id") == H2_RUNNER_ID, "H2 runner identity mismatch")
    steps = job.get("steps") or []
    require(len(steps) > 0, "H2 zero-step execution rejected")
    require(
        all(step.get("conclusion") == "success" for step in steps),
        "not all H2 live steps passed",
    )

    _, artifacts = fetch_json(f"{api}/runs/{H2_RUN_ID}/artifacts")
    amatches = [
        item for item in artifacts.get("artifacts", [])
        if item.get("id") == H2_ARTIFACT_ID
    ]
    require(len(amatches) == 1, "expected H2 artifact not found")
    artifact = amatches[0]
    require(
        artifact.get("digest") == H2_ARTIFACT_DIGEST,
        "H2 artifact digest mismatch",
    )
    require(artifact.get("expired") is False, "H2 artifact already expired")
    require(
        artifact.get("workflow_run", {}).get("head_sha") == H2_HEAD,
        "H2 artifact head mismatch",
    )

    out = {
        "schema": "qps.m05.g5.dow_independent_consumer.v1",
        "consumer_mission": "MISSION_H3_DOW",
        "local_mission": "M05_PROVENANCE_ATTESTATION",
        "source_repo": "GBOGEB/CODEX",
        "source_head_sha": CODEX_HEAD,
        "source_contract_path": CONTRACT_PATH,
        "source_contract_sha256": digest,
        "h1_runtime": {
            "run_id": H1_RUN_ID,
            "job_id": H1_JOB_ID,
            "runner_id": H1_RUNNER_ID,
            "status": "PASS_EXECUTED_EXACT_PAYLOAD",
        },
        "h2_semantic_provenance": {
            "repo": H2_REPO,
            "head_sha": H2_HEAD,
            "run_id": H2_RUN_ID,
            "job_id": H2_JOB_ID,
            "runner_id": H2_RUNNER_ID,
            "steps_verified_gt_zero": len(steps),
            "artifact_id": H2_ARTIFACT_ID,
            "artifact_digest": H2_ARTIFACT_DIGEST,
            "status": "PASS_EXECUTED_EXACT_PAYLOAD",
        },
        "dow_disposition": "ACCEPT_SEMANTIC_PROVENANCE_ONLY",
        "emit_for_child_disposition": True,
        "promotion_authority": False,
        "numeric_cost_release": "WITHHELD_SOURCE_VALUES",
        "source_value_gates": [974, 981],
        "next_required_hop": "MISSION_H1_QPS_CHILD_DISPOSITION",
        "status": "PASS",
    }
    path = pathlib.Path("artifacts/m05/g5_dow_independent_consumer_receipt.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(out, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    out_digest = hashlib.sha256(path.read_bytes()).hexdigest()
    print(json.dumps(out, sort_keys=True))
    print(f"G5_DOW_INDEPENDENT_CONSUMER_SHA256={out_digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
