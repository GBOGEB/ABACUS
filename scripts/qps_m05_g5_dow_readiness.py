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
EXPECTED_H1 = {
    "run": 34730906661,
    "job": 103653394137,
    "runner_id": 1000260663,
    "artifact_id": 10309790070,
    "artifact_digest": (
        "sha256:9b71d43c2bafd913e9780174a92514e72511bb8a31fec2cfa065745b58effb9a"
    ),
    "projection_sha256": (
        "97be102020859048940cbe255224c36bb786ff19b31ea7483af2c9f898b4e450"
    ),
    "result": "PASS_EXECUTED_EXACT_PAYLOAD",
}


def fetch_json(url: str):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "QPS-M05-G5-DOW-readiness"},
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
        semantic["actual_numeric_cost_release"]
        == "WITHHELD_SOURCE_VALUES",
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
    for key, expected in EXPECTED_H1.items():
        require(execution.get(key) == expected, f"H1 {key} mismatch")

    out = {
        "schema": "qps.m05.g5.dow_readiness.v2",
        "consumer_mission": "MISSION_H3_DOW",
        "local_mission": "M05_PROVENANCE_ATTESTATION",
        "source_repo": "GBOGEB/CODEX",
        "source_head_sha": CODEX_HEAD,
        "source_contract_path": CONTRACT_PATH,
        "source_contract_sha256": digest,
        "h1_runtime": "PASS_EXACT_EXPECTED_IDENTITY",
        "h1_runner_id": EXPECTED_H1["runner_id"],
        "h2_contract_ingress": "DEFER_SUPERSEDED_V1_REPAIR_PENDING",
        "h2_observed_attestation": "PENDING_REPAIRED_V2",
        "dow_disposition": "DEFER_H2_REPAIRED_ATTESTATION_PENDING",
        "emit_for_child_disposition": False,
        "promotion_authority": False,
        "numeric_cost_release": "WITHHELD_SOURCE_VALUES",
        "source_value_gates": [974, 981],
        "status": "PASS_READINESS_ONLY_NO_H2_ACCEPT",
    }
    path = pathlib.Path("artifacts/m05/g5_dow_readiness_receipt.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(out, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    out_digest = hashlib.sha256(path.read_bytes()).hexdigest()
    print(json.dumps(out, sort_keys=True))
    print(f"G5_DOW_READINESS_RECEIPT_SHA256={out_digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
