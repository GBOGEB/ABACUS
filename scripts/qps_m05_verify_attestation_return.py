#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import urllib.request

CODEX_RECEIPT_SHA = "49fb7c132c3689cf83f85b4afe997b9ad0810bee"
CODEX_RECEIPT_PATH = "federation/qps/m05/M05_ATTESTATION_RETURN_RECEIPT_v0.1.json"
RECEIPT_URL = f"https://raw.githubusercontent.com/GBOGEB/CODEX/{CODEX_RECEIPT_SHA}/{CODEX_RECEIPT_PATH}"
RUN_ID = 34684810640
EXPECTED_HEAD = "077b7a39ef091eb47b30d6134d70d95bc945ad97"
EXPECTED_JOB_ID = 103529841527
EXPECTED_ARTIFACT_ID = 10295112538
EXPECTED_ARTIFACT_DIGEST = "sha256:e08a1ff6ff3040f27416efab50ae82f4f335eea7094f2ee11fc27769c3f73101"
EXPECTED_SUBJECT_SHA256 = "d9dc8945622cd0be5dca76e2f98ad66844ad6eaf755509500d8081c6fd03358c"
EXPECTED_ATTESTATION_ID = 47037742
EXPECTED_ACTION_SHA = "1e69f48acb82d1966a394da916b4c1698aa569d6"
AUTHORITY = "PROVENANCE_ONLY_NOT_ENGINEERING_ACCEPTANCE"


def fetch_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "QPS-M05-DOW-independent-consumer"})
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read()
    return raw, json.loads(raw)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> int:
    receipt_bytes, receipt = fetch_json(RECEIPT_URL)
    receipt_digest = hashlib.sha256(receipt_bytes).hexdigest()

    require(receipt["schema"] == "qps.m05.attestation_return_receipt.v1", "receipt schema mismatch")
    require(receipt["authority"] == AUTHORITY, "authority boundary mismatch")
    require(receipt["action"]["sha"] == EXPECTED_ACTION_SHA, "attest action SHA mismatch")
    vector = receipt["automatic_control_vector"]
    require(vector["run_id"] == RUN_ID, "run id mismatch")
    require(vector["job_id"] == EXPECTED_JOB_ID, "job id mismatch")
    require(vector["source_head_sha"] == EXPECTED_HEAD, "source head mismatch")
    require(vector["carrier_sha"] == EXPECTED_HEAD, "carrier head mismatch")
    require(vector["subject_sha256"] == EXPECTED_SUBJECT_SHA256, "subject digest mismatch")
    require(vector["attestation_id"] == EXPECTED_ATTESTATION_ID, "attestation id mismatch")
    require(vector["artifact"]["id"] == EXPECTED_ARTIFACT_ID, "artifact id mismatch")
    require(vector["artifact"]["digest"] == EXPECTED_ARTIFACT_DIGEST, "artifact digest mismatch")
    require(vector["result"] == "PASS", "source-owner result is not PASS")

    _, run = fetch_json(f"https://api.github.com/repos/GBOGEB/CODEX/actions/runs/{RUN_ID}")
    require(run["status"] == "completed" and run["conclusion"] == "success", "live run is not successful")
    require(run["head_sha"] == EXPECTED_HEAD, "live run head mismatch")
    require(run["event"] == "push" and run["head_branch"] == "main", "live run is not automatic main push")

    _, jobs = fetch_json(f"https://api.github.com/repos/GBOGEB/CODEX/actions/runs/{RUN_ID}/jobs")
    matches = [job for job in jobs.get("jobs", []) if job.get("id") == EXPECTED_JOB_ID]
    require(len(matches) == 1, "expected job not found")
    job = matches[0]
    require(job["status"] == "completed" and job["conclusion"] == "success", "live job is not successful")
    steps = job.get("steps") or []
    require(len(steps) > 0, "zero-step execution cannot earn credit")
    require(all(step.get("conclusion") == "success" for step in steps), "not all live steps passed")

    _, artifacts = fetch_json(f"https://api.github.com/repos/GBOGEB/CODEX/actions/runs/{RUN_ID}/artifacts")
    amatches = [item for item in artifacts.get("artifacts", []) if item.get("id") == EXPECTED_ARTIFACT_ID]
    require(len(amatches) == 1, "expected artifact not found")
    artifact = amatches[0]
    require(artifact.get("digest") == EXPECTED_ARTIFACT_DIGEST, "live artifact digest mismatch")
    require(artifact.get("expired") is False, "source artifact already expired")

    out = {
        "schema": "qps.m05.dow_independent_consumer.v1",
        "consumer_repo": "GBOGEB/ABACUS",
        "source_repo": "GBOGEB/CODEX",
        "source_receipt_commit": CODEX_RECEIPT_SHA,
        "source_receipt_path": CODEX_RECEIPT_PATH,
        "source_receipt_sha256": receipt_digest,
        "source_run_id": RUN_ID,
        "source_job_id": EXPECTED_JOB_ID,
        "source_head_sha": EXPECTED_HEAD,
        "source_subject_sha256": EXPECTED_SUBJECT_SHA256,
        "source_attestation_id": EXPECTED_ATTESTATION_ID,
        "source_artifact_id": EXPECTED_ARTIFACT_ID,
        "source_artifact_digest": EXPECTED_ARTIFACT_DIGEST,
        "live_run_verified": True,
        "live_job_steps_verified_gt_zero": len(steps),
        "live_artifact_verified": True,
        "claim_mutated": False,
        "claim_resigned": False,
        "authority": AUTHORITY,
        "dow_disposition": "ACCEPT_PROVENANCE_INTEGRITY_ONLY",
        "status": "PASS",
    }
    path = pathlib.Path("artifacts/m05/dow_m05_consumer_receipt.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    pathlib.Path("artifacts/m05/dow_m05_consumer_receipt.sha256").write_text(digest + "\n", encoding="utf-8")
    print(json.dumps(out, sort_keys=True))
    print(f"DOW_M05_CONSUMER_RECEIPT_SHA256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
