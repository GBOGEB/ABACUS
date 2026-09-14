#!/usr/bin/env python3
"""Finalize a QPS TRIAGE KEB receipt into a DOW contract receipt.

This is the contract-compliant H3_DOW boundary for QPS TRIAGE = QPS + DOW + KEB.
It validates an exact CODEX/KEB producer envelope, executes/records a bounded
independent DOW challenge, and emits the complete DOW_CONTRACT_v1 output tuple.
It never creates terminal QPS engineering, compliance, negotiation or acceptance
state; child re-entry into GBOGEB/cryoplant-project remains mandatory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


KEB_CONTRACT_VERSION = "qps-triage-keb-contract/1.0.0"
PRODUCER_REPO = "GBOGEB/CODEX"
CONSUMER_REPO = "GBOGEB/ABACUS"
CHILD_REENTRY_TARGET = "GBOGEB/cryoplant-project"


def canonical_digest(value: dict[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _is_sha(value: Any, length: int) -> bool:
    text = str(value or "").lower()
    return len(text) == length and all(ch in "0123456789abcdef" for ch in text)


def _positive_int(value: Any) -> bool:
    return type(value) is int and value > 0


def validate_keb_receipt(receipt: dict[str, Any]) -> list[str]:
    required = {
        "producer_repo",
        "producer_pr",
        "producer_head_sha",
        "source_object_ids",
        "contract_version",
        "workflow_or_validator",
        "executed_steps",
        "result",
        "receipt_sha256",
        "downstream_consumer",
        "child_reentry_target",
        "authority_transfer",
    }
    errors = sorted(required - set(receipt))

    if receipt.get("producer_repo") != PRODUCER_REPO:
        errors.append("producer_repo")
    if not _positive_int(receipt.get("producer_pr")):
        errors.append("producer_pr")
    if not _is_sha(receipt.get("producer_head_sha"), 40):
        errors.append("producer_head_sha")
    if receipt.get("contract_version") != KEB_CONTRACT_VERSION:
        errors.append("contract_version")
    if receipt.get("downstream_consumer") != CONSUMER_REPO:
        errors.append("downstream_consumer")
    if receipt.get("child_reentry_target") != CHILD_REENTRY_TARGET:
        errors.append("child_reentry_target")
    if receipt.get("authority_transfer") is not False:
        errors.append("authority_transfer")

    source_object_ids = receipt.get("source_object_ids")
    if not isinstance(source_object_ids, list) or not source_object_ids or not all(
        isinstance(item, str) and item.strip() for item in source_object_ids
    ):
        errors.append("source_object_ids")

    result = receipt.get("result")
    if result not in {"PASS", "FAIL", "DEFER"}:
        errors.append("result")
    if result == "PASS" and not _positive_int(receipt.get("executed_steps")):
        errors.append("executed_steps")

    digest = receipt.get("receipt_sha256")
    if not _is_sha(digest, 64):
        errors.append("receipt_sha256")
    else:
        basis = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
        if canonical_digest(basis) != str(digest).lower():
            errors.append("receipt_sha256_mismatch")

    return sorted(set(errors))


def validate_challenge(challenge: dict[str, Any], receipt: dict[str, Any]) -> list[str]:
    required = {
        "challenge_or_execution",
        "result",
        "executed_steps",
        "reason",
        "private_evidence_copied",
        "authority_transfer",
        "component_analytics_only",
        "system_consequence_withheld",
        "table10_rate_per_year",
        "first_red",
    }
    errors = sorted(required - set(challenge))

    if not isinstance(challenge.get("challenge_or_execution"), str) or not challenge.get(
        "challenge_or_execution", ""
    ).strip():
        errors.append("challenge_or_execution")
    result = challenge.get("result")
    if result not in {"PASS", "FAIL", "DEFER"}:
        errors.append("result")
    if result == "PASS" and not _positive_int(challenge.get("executed_steps")):
        errors.append("executed_steps")
    if not isinstance(challenge.get("reason"), str) or not challenge.get("reason", "").strip():
        errors.append("reason")

    if challenge.get("private_evidence_copied") is not False:
        errors.append("private_evidence_copied")
    if challenge.get("authority_transfer") is not False:
        errors.append("authority_transfer")

    if result == "PASS":
        if challenge.get("component_analytics_only") is not True:
            errors.append("component_analytics_only")
        if challenge.get("system_consequence_withheld") is not True:
            errors.append("system_consequence_withheld")
        if challenge.get("table10_rate_per_year") != 0.0:
            errors.append("table10_rate_per_year")
        if challenge.get("first_red") != "GHP03_N_MINUS_1_CAPACITY":
            errors.append("first_red")

    expected_merge = challenge.get("expected_producer_merge_sha")
    if expected_merge is not None and receipt.get("producer_merge_sha") != expected_merge:
        errors.append("expected_producer_merge_sha")

    expected_manifest = challenge.get("expected_source_manifest_sha256")
    if expected_manifest is not None and receipt.get("source_manifest_sha256") != expected_manifest:
        errors.append("expected_source_manifest_sha256")

    expected_objects = challenge.get("expected_source_object_ids")
    if expected_objects is not None:
        if not isinstance(expected_objects, list) or sorted(expected_objects) != sorted(
            receipt.get("source_object_ids") or []
        ):
            errors.append("expected_source_object_ids")

    return sorted(set(errors))


def finalize_dow_receipt(
    keb_receipt: dict[str, Any],
    challenge: dict[str, Any],
    *,
    consumer_pr: int,
    consumer_head_sha: str,
) -> dict[str, Any]:
    if not _positive_int(consumer_pr):
        raise ValueError("consumer_pr must be a positive integer")
    if not _is_sha(consumer_head_sha, 40):
        raise ValueError("consumer_head_sha must be an exact 40-hex SHA")

    keb_errors = validate_keb_receipt(keb_receipt)
    if keb_errors:
        raise ValueError("KEB_RECEIPT_CONTRACT: " + ",".join(keb_errors))

    challenge_errors = validate_challenge(challenge, keb_receipt)
    if challenge_errors:
        raise ValueError("DOW_CHALLENGE_CONTRACT: " + ",".join(challenge_errors))

    if keb_receipt["result"] == "PASS" and challenge["result"] == "PASS":
        disposition = "ACCEPT"
    elif keb_receipt["result"] == "FAIL" or challenge["result"] == "FAIL":
        disposition = "REJECT"
    else:
        disposition = "DEFER"

    value: dict[str, Any] = {
        "schema_version": "0.1",
        "consumer_repo": CONSUMER_REPO,
        "consumer_pr": consumer_pr,
        "consumer_head_sha": consumer_head_sha,
        "producer_repo": keb_receipt["producer_repo"],
        "producer_pr": keb_receipt["producer_pr"],
        "producer_head_sha": keb_receipt["producer_head_sha"],
        "producer_receipt_sha256": keb_receipt["receipt_sha256"],
        "challenge_or_execution": challenge["challenge_or_execution"],
        "executed_steps": challenge["executed_steps"],
        "disposition": disposition,
        "reason": challenge["reason"],
        "child_reentry_target": CHILD_REENTRY_TARGET,
        "authority_transfer": False,
        "scope": "COMPONENT_ANALYTICS_CONTRACT_ONLY",
        "system_consequence_withheld": bool(challenge.get("system_consequence_withheld")),
        "table10_rate_per_year": challenge.get("table10_rate_per_year"),
        "first_red": challenge.get("first_red"),
    }
    value["receipt_sha256"] = canonical_digest(value)
    return value


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keb-receipt", type=Path, required=True)
    parser.add_argument("--challenge", type=Path, required=True)
    parser.add_argument("--consumer-pr", type=int, required=True)
    parser.add_argument("--consumer-head-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        value = finalize_dow_receipt(
            load_json(args.keb_receipt),
            load_json(args.challenge),
            consumer_pr=args.consumer_pr,
            consumer_head_sha=args.consumer_head_sha,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
