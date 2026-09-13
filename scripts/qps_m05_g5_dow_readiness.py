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
    require(execution["run"] == 34730906661, "H1 run mismatch")
    require(execution["job"] == 103653394137, "H1 job mismatch")
    require(execution["runner_id"] != 0, "H1 zero-step evidence rejected")
    require(
        execution["result"] == "PASS_EXECUTED_EXACT_PAYLOAD",
        "H1 runtime result mismatch",
    )

    out = {
        "schema": "qps.m05.g5.dow_readiness.v1",
        "consumer_mission": "MISSION_H3_DOW",
        "local_mission": "M05_PROVENANCE_ATTESTATION",
        "source_repo": "GBOGEB/CODEX",
        "source_head_sha": CODEX_HEAD,
        "source_contract_path": CONTRACT_PATH,
        "source_contract_sha256": digest,
        "h1_runtime": "PASS_EXECUTED_EXACT_PAYLOAD",
        "h2_contract_ingress": "PASS",
        "h2_observed_attestation": "PENDING",
        "dow_disposition": "DEFER_H2_ATTESTATION_PENDING",
        "emit_for_child_disposition": False,
        "promotion_authority": False,
        "numeric_cost_release": "WITHHELD_SOURCE_VALUES",
        "source_value_gates": [974, 981],
        "status": "PASS_READINESS_ONLY",
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
