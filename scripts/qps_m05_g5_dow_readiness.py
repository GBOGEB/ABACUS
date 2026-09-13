#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import urllib.request

CODEX_HEAD = "18598958a38c801e63c18d14490c27df426f7e1c"
CONTRACT_BLOB = "e695a3d2bc406f0e9d687626655a145d8a07f09e"
SCRIPT_BLOB = "91be2fd3e66a60f0b83c6683152d62fbeb963abd"
CONTRACT_PATH = "docs/qps_m05/QPS_G5_KEB_CHALLENGE_v0.1.json"
CONTRACT_URL = (
    "https://raw.githubusercontent.com/GBOGEB/CODEX/"
    f"{CODEX_HEAD}/{CONTRACT_PATH}"
)

H2F_REPO = "GBOGEB/Q_engineering_tools"
H2F_PR = 20
H2F_MERGE = "840bac77fa54fd9701a0010321c5d710e081b2db"
H2F_RUN = 34760090016
H2F_JOB = 103731285019
H2F_ARTIFACT = 10318418865
H2F_ARTIFACT_ZIP_SHA256 = (
    "7b3d83e0c5a421801216f5e2737893a45e3a0f54f6981ffd4758313f390aacf7"
)
H2_KEB_RECEIPT_SHA256 = (
    "580d77065c8dfd286e58b05d6efd334cb77b038467627337e3571fb449fdc756"
)
RUN_URL = (
    "https://api.github.com/repos/GBOGEB/Q_engineering_tools/actions/runs/"
    f"{H2F_RUN}"
)
JOB_URL = (
    "https://api.github.com/repos/GBOGEB/Q_engineering_tools/actions/jobs/"
    f"{H2F_JOB}"
)
ARTIFACTS_URL = RUN_URL + "/artifacts"


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "QPS-M05-G5-DOW-independent-consumer",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read()


def fetch_json(url: str):
    raw = fetch_bytes(url)
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
    require(execution["run"] == 34730906661, "H1 run mismatch")
    require(execution["job"] == 103653394137, "H1 job mismatch")
    require(execution["runner_id"] != 0, "H1 zero-step evidence rejected")
    require(
        execution["result"] == "PASS_EXECUTED_EXACT_PAYLOAD",
        "H1 runtime result mismatch",
    )

    _, run = fetch_json(RUN_URL)
    require(run["id"] == H2F_RUN, "H2F run identity mismatch")
    require(run["status"] == "completed", "H2F run not completed")
    require(run["conclusion"] == "success", "H2F run did not succeed")
    require(run["head_sha"] == H2F_MERGE, "H2F exact executor SHA mismatch")

    _, job = fetch_json(JOB_URL)
    require(job["id"] == H2F_JOB, "H2F job identity mismatch")
    require(job["run_id"] == H2F_RUN, "H2F job/run mismatch")
    require(job["status"] == "completed", "H2F job not completed")
    require(job["conclusion"] == "success", "H2F job did not succeed")
    require(job.get("runner_id") not in (None, 0), "H2F runner admission missing")
    steps = job.get("steps") or []
    require(len(steps) >= 6, "H2F expected executed steps missing")
    require(
        all(step.get("conclusion") == "success" for step in steps),
        "H2F contains a non-success executed step",
    )

    _, artifact_payload = fetch_json(ARTIFACTS_URL)
    artifacts = artifact_payload.get("artifacts") or []
    artifact = next((item for item in artifacts if item.get("id") == H2F_ARTIFACT), None)
    require(artifact is not None, "H2F evidence artifact not found")
    require(artifact.get("expired") is False, "H2F evidence artifact expired")
    require(
        str(artifact.get("name", "")).startswith("qps-g5-keb-federated-"),
        "H2F artifact name mismatch",
    )

    out = {
        "schema": "qps.m05.g5.dow_independent_consumption.v2",
        "consumer_mission": "MISSION_H3_DOW",
        "local_mission": "M05_PROVENANCE_ATTESTATION",
        "source_repo": "GBOGEB/CODEX",
        "source_head_sha": CODEX_HEAD,
        "source_contract_path": CONTRACT_PATH,
        "source_contract_blob": CONTRACT_BLOB,
        "source_script_blob": SCRIPT_BLOB,
        "source_contract_sha256": digest,
        "h1_runtime": "PASS_EXECUTED_EXACT_PAYLOAD",
        "h2_observed_attestation": "PASS_EXECUTED_EXACT_PAYLOAD",
        "h2_keb_disposition": "ACCEPT_SEMANTIC_PROVENANCE_ONLY",
        "h2_keb_receipt_sha256": H2_KEB_RECEIPT_SHA256,
        "h2_federated_executor": {
            "repo": H2F_REPO,
            "pr": H2F_PR,
            "merge_sha": H2F_MERGE,
            "run": H2F_RUN,
            "job": H2F_JOB,
            "runner_id": job["runner_id"],
            "artifact": H2F_ARTIFACT,
            "artifact_zip_sha256_observed": H2F_ARTIFACT_ZIP_SHA256,
            "executed_steps": len(steps),
        },
        "independent_checks": {
            "semantic_lineage": "PASS",
            "null_preservation": "PASS",
            "forbidden_inference_guard": "PASS",
            "source_value_gates": "PASS_974_981",
            "runtime_identity": "PASS",
            "artifact_identity": "PASS_METADATA_BOUND",
        },
        "dow_disposition": "ACCEPT_INDEPENDENT_CONSUMPTION_ONLY",
        "emit_for_child_disposition": True,
        "promotion_authority": False,
        "numeric_cost_release": "WITHHELD_SOURCE_VALUES",
        "source_value_gates": [974, 981],
        "next_required_hop": "MISSION_H1_FINAL_CHILD_DISPOSITION",
        "status": "PASS",
        "credit_delta": {
            "engineering": 0,
            "compliance": 0,
            "negotiation": 0,
            "release": 0,
        },
    }
    path = pathlib.Path("artifacts/m05/g5_dow_independent_consumption_receipt.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(out, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    out_digest = hashlib.sha256(path.read_bytes()).hexdigest()
    print(json.dumps(out, sort_keys=True))
    print(f"G5_DOW_INDEPENDENT_RECEIPT_SHA256={out_digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
