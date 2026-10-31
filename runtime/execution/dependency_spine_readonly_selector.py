#!/usr/bin/env python3
"""ABACUS DELTA_1 read-only proposal selector; no queued/remote execution.

Uses CODEX MYCELIUM stage receipt as *input evidence*, never as scheduling
authority. Missing exact-head authentication stays DEFER, not a successful hop.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

SHA = re.compile(r"^[0-9a-f]{40}$")
SCHEMA = "abacus.dow.dependency_spine.selector.v1"


def encode(value: dict) -> bytes:
    return (
        json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n"
    ).encode()


def checksum(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def owner_head(root: Path) -> str:
    p = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return p.stdout.strip() if p.returncode == 0 else ""


def contract(root: Path) -> None:
    p = root / "runtime" / "execution" / "federated-execution-scheduler.yaml"
    if not p.is_file():
        raise ValueError("CANONICAL_SCHEDULER_MISSING")
    text = p.read_text(encoding="utf-8")
    for expected in (
        "moniker: DELTA_1",
        "reconciliation_execution",
        "governance_execution",
    ):
        if expected not in text:
            raise ValueError("CANONICAL_SCHEDULER_CONTRACT_DRIFT")


def consume_codex(receipt: dict, expected_codex_sha: str) -> str:
    if not SHA.fullmatch(expected_codex_sha):
        raise ValueError("EXPECTED_CODEX_SHA_INVALID")
    val = {k: v for k, v in receipt.items() if k != "stage_digest_sha256"}
    claimed = receipt.get("stage_digest_sha256")
    if claimed != checksum(encode(val)):
        raise ValueError("CODEX_STAGE_DIGEST_BAD")
    if (
        receipt.get("schema") != "codex.mycelium.dependency_spine.stage.v1"
        or receipt.get("consumer_repo") != "GBOGEB/CODEX"
    ):
        raise ValueError("CODEX_STAGE_SCHEMA")
    if receipt.get("consumer_head_sha") != expected_codex_sha:
        raise ValueError("CODEX_STAGE_HEAD_MISMATCH")
    if (
        receipt.get("child_disposition") != "DEFER"
        or receipt.get("merge_admission") != "HOLD"
    ):
        raise ValueError("CODEX_FALSE_ACCEPT")
    for flag in (
        "authenticated_remote_execution",
        "native_producer_run_job_attempt_bound",
        "mutation_enabled",
        "dispatch_authorized",
        "authority_transfer",
    ):
        if receipt.get(flag) is not False:
            raise ValueError("CODEX_AUTHORITY_ESCALATION")
    if receipt.get("formal_credit_delta") != 0:
        raise ValueError("CODEX_FORMAL_CREDIT")
    return claimed


def select(
    head_sha: str, receipt: dict | None, expected_codex_sha: str | None = None
) -> dict:
    if not SHA.fullmatch(head_sha):
        raise ValueError("ABACUS_HEAD_INVALID")
    source_digest = None
    source_sha = None
    if receipt is not None:
        if expected_codex_sha is None:
            raise ValueError("CODEX_HEAD_REQUIRED")
        source_digest = consume_codex(receipt, expected_codex_sha)
        source_sha = receipt.get("source_head_sha")
    items = [
        {
            "id": "P0_GOVERNANCE",
            "priority": 0,
            "status": "OWNER_ACTION_REQUIRED",
            "predicate": "effective QPS branch rules + independent review + blocked RED canary",
        },
        {
            "id": "P1_PEER_SOURCE_PROOF",
            "priority": 1,
            "status": "AWAIT_NATIVE_PEER_RECEIPTS",
            "predicate": "four distinct native source-head scan artifacts",
        },
        {
            "id": "P1_FEDERATION",
            "priority": 1,
            "status": "DEFER_UNAUTHENTICATED_CONSUMER",
            "predicate": "CODEX/ABACUS run, job, attempt + artifact binding",
        },
    ]
    result = {
        "schema": SCHEMA,
        "owner_repo": "GBOGEB/ABACUS",
        "owner_head_sha": head_sha,
        "existing_scheduler": "runtime/execution/federated-execution-scheduler.yaml",
        "domain": "reconciliation_execution",
        "action_class": "STAGE_ONLY",
        "source_codex_head_sha": expected_codex_sha if source_digest else None,
        "source_stage_sha256": source_digest,
        "source_qps_head_sha": source_sha if source_digest else None,
        "selector_state": (
            "PROPOSAL_NOT_DISPATCHED" if source_digest else "DEFER_NO_CODEX_RECEIPT"
        ),
        "planned_actions": items,
        "observed_dispatches": 0,
        "successful_worker_returns": None,
        "authenticated_cross_repo_hops": 0,
        "engineering_credit_delta": 0,
        "formal_credit_delta": 0,
        "authority_transfer": False,
        "mutation_enabled": False,
        "worker_dispatch_authorized": False,
        "child_disposition": "DEFER",
        "merge_admission": "HOLD",
    }
    result["return_sha256"] = checksum(encode(result))
    return result


def verify(payload: dict) -> None:
    digest = payload.get("return_sha256")
    raw = {k: v for k, v in payload.items() if k != "return_sha256"}
    if digest != checksum(encode(raw)):
        raise ValueError("RETURN_HASH_DRIFT")
    if (
        payload.get("schema") != SCHEMA
        or payload.get("action_class") != "STAGE_ONLY"
        or payload.get("existing_scheduler")
        != "runtime/execution/federated-execution-scheduler.yaml"
        or payload.get("domain") != "reconciliation_execution"
        or payload.get("observed_dispatches") != 0
        or payload.get("authenticated_cross_repo_hops") != 0
        or payload.get("engineering_credit_delta") != 0
        or payload.get("formal_credit_delta") != 0
        or payload.get("worker_dispatch_authorized") is not False
        or payload.get("mutation_enabled") is not False
        or payload.get("authority_transfer") is not False
        or payload.get("child_disposition") != "DEFER"
        or payload.get("merge_admission") != "HOLD"
    ):
        raise ValueError("SCHEDULER_FALSE_DISPATCH_OR_ADMISSION")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--expected-head", required=True)
    p.add_argument("--codex-receipt", type=Path)
    p.add_argument("--expected-codex-head")
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if owner_head(a.root) != a.expected_head:
        raise SystemExit("OWNER_EXACT_HEAD_MISMATCH")
    contract(a.root)
    if a.codex_receipt and not a.codex_receipt.is_file():
        raise SystemExit("STAGED_CODEX_RECEIPT_MISSING")
    inbound = (
        json.loads(a.codex_receipt.read_text(encoding="utf-8"))
        if a.codex_receipt
        else None
    )
    candidate = select(a.expected_head, inbound, a.expected_codex_head)
    verify(candidate)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "ABACUS_DEPENDENCY_SPINE_DOW_RETURN.json").write_bytes(encode(candidate))
    print(
        json.dumps(
            {
                "selector_state": candidate["selector_state"],
                "observed_dispatches": 0,
                "merge_admission": "HOLD",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
