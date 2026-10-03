#!/usr/bin/env python3
"""Emit and validate cross-method proposal compatibility envelopes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

DEFAULT_CONTRACT = Path("governance/proposals/PROPOSAL_COMPATIBILITY_CONTRACT.json")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_envelope(
    envelope: dict[str, Any],
    contract: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    for field in contract.get("required_fields", []):
        if field not in envelope:
            errors.append(f"missing:{field}")

    method = envelope.get("method")
    if method not in contract.get("compatible_methods", []):
        errors.append("method")

    sha = str(envelope.get("source_sha", ""))
    if len(sha) != 40 or any(ch not in "0123456789abcdef" for ch in sha):
        errors.append("source_sha")

    if envelope.get("risk_class") not in contract.get("risk_classes", []):
        errors.append("risk_class")
    if envelope.get("mutation_mode") not in contract.get("mutation_modes", []):
        errors.append("mutation_mode")

    worker = envelope.get("worker_model", {})
    if not isinstance(worker, dict):
        errors.append("worker_model")
    elif int(worker.get("mutation_writer_count", 0) or 0) != 1:
        errors.append("mutation_writer_count")

    authority = envelope.get("authority", {})
    if authority.get("authority_transfer") is not False:
        errors.append("authority_transfer")
    if int(authority.get("formal_credit_delta", 1) or 0) != 0:
        errors.append("formal_credit_delta")
    if int(authority.get("engineering_credit_delta", 1) or 0) != 0:
        errors.append("engineering_credit_delta")

    coverage = envelope.get("coverage_growth", {})
    for field in contract.get("coverage_growth", {}).get("required_fields", []):
        if field not in coverage:
            errors.append(f"coverage_growth:{field}")

    return sorted(set(errors))


def iter_envelopes(payload: dict[str, Any]) -> list[dict[str, Any]]:
    proposals = payload.get("proposals")
    if isinstance(proposals, list):
        return [value for value in proposals if isinstance(value, dict)]
    return [payload]


def emit_mip(source_sha: str, evidence: Path) -> dict[str, Any]:
    return {
        "schema_version": "abacus-proposal-envelope/1.0.0",
        "proposal_id": f"MIP-{source_sha[:12]}",
        "method": "MIP",
        "source_sha": source_sha,
        "proposal_type": "PRESSURE_QUEUE",
        "risk_class": "MEASURED",
        "scope": {"paths": [], "finding_count": 0},
        "mutation_mode": "READ_ONLY_PROPOSAL",
        "worker_model": {
            "proposal_workers": "SCALABLE_READ_ONLY",
            "mutation_writer_count": 1,
        },
        "protected_holds": {"source_bound_holds": "PRESERVE"},
        "evidence_receipts": [
            {
                "path": str(evidence),
                "sha256": file_digest(evidence),
            }
        ],
        "admission": {
            "exact_head_required": True,
            "first_completed_attributable_red_only": True,
            "post_merge_recensus_required": True,
        },
        "coverage_growth": {
            "applicability": "MEASURED_COVERAGE_PRESSURE",
            "baseline_receipt": str(evidence),
            "target": "INCREASE_EXECUTED_TEST_CHECK_COVERAGE",
            "result": "PENDING",
        },
        "authority": {
            "authority_transfer": False,
            "formal_credit_delta": 0,
            "engineering_credit_delta": 0,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate")
    validate.add_argument("--input", type=Path, required=True)

    mip = sub.add_parser("emit-mip")
    mip.add_argument("--source-sha", required=True)
    mip.add_argument("--evidence", type=Path, required=True)
    mip.add_argument("--out", type=Path, required=True)

    args = parser.parse_args()
    contract = load_json(args.contract)

    if args.command == "emit-mip":
        if len(args.source_sha) != 40:
            raise SystemExit("MIP proposal envelope requires exact SHA")
        envelope = emit_mip(args.source_sha, args.evidence)
        errors = validate_envelope(envelope, contract)
        if errors:
            raise SystemExit("invalid emitted MIP envelope: " + ",".join(errors))
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(envelope, indent=2, sort_keys=True))
        return 0

    payload = load_json(args.input)
    errors: list[str] = []
    envelopes = iter_envelopes(payload)
    if not envelopes:
        errors.append("no_proposals")
    for index, envelope in enumerate(envelopes):
        for error in validate_envelope(envelope, contract):
            errors.append(f"{index}:{error}")
    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}, indent=2))
        return 1
    print(json.dumps({"status": "PASS", "proposals": len(envelopes)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
