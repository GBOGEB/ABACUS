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
    if envelope.get("proposal_type") not in contract.get("proposal_types", []):
        errors.append("proposal_type")
    if envelope.get("mutation_mode") not in contract.get("mutation_modes", []):
        errors.append("mutation_mode")

    worker = envelope.get("worker_model", {})
    if not isinstance(worker, dict):
        errors.append("worker_model")
    else:
        worker_contract = contract.get("worker_model", {})
        proposal_workers = worker.get("proposal_workers")
        expected_workers = worker_contract.get("proposal_workers", {})
        if not isinstance(proposal_workers, dict):
            errors.append("proposal_workers")
        else:
            minimum = proposal_workers.get("min")
            maximum = proposal_workers.get("max")
            if (
                isinstance(minimum, bool)
                or not isinstance(minimum, int)
                or minimum < expected_workers.get("min", 1)
            ):
                errors.append("proposal_workers.min")
            if (
                isinstance(maximum, bool)
                or not isinstance(maximum, int)
                or maximum > expected_workers.get("max", 8)
            ):
                errors.append("proposal_workers.max")
            if (
                isinstance(minimum, int)
                and not isinstance(minimum, bool)
                and isinstance(maximum, int)
                and not isinstance(maximum, bool)
                and minimum > maximum
            ):
                errors.append("proposal_workers.range")
            if proposal_workers.get("mode") != expected_workers.get("mode"):
                errors.append("proposal_workers.mode")
            if proposal_workers.get("scalable") is not expected_workers.get(
                "scalable"
            ):
                errors.append("proposal_workers.scalable")

        mutation_writer = worker.get("mutation_writer")
        expected_writer = worker_contract.get("mutation_writer", {})
        if not isinstance(mutation_writer, dict):
            errors.append("mutation_writer")
        else:
            writer_count = mutation_writer.get("count")
            expected_count = expected_writer.get("count", 1)
            if (
                isinstance(writer_count, bool)
                or not isinstance(writer_count, int)
                or writer_count != expected_count
            ):
                errors.append("mutation_writer.count")
            if mutation_writer.get("required_for_mutation") is not expected_writer.get(
                "required_for_mutation", True
            ):
                errors.append("mutation_writer.required_for_mutation")

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


def iter_envelopes(payload: dict[str, Any]) -> list[Any]:
    proposals = payload.get("proposals")
    if isinstance(proposals, list):
        return proposals
    return [payload]


def valid_empty_queue(payload: dict[str, Any]) -> bool:
    if payload.get("schema_version") != "abacus-dab-proposal-queue/1.0.0":
        return False
    source_sha = payload.get("source_sha")
    if not isinstance(source_sha, str) or len(source_sha) != 40 or any(
        ch not in "0123456789abcdef" for ch in source_sha
    ):
        return False

    measurement = payload.get("measurement")
    if not isinstance(measurement, dict):
        return False
    total = measurement.get("total")
    families = measurement.get("families")
    holds = payload.get("protected_holds")
    if (
        isinstance(total, bool)
        or not isinstance(total, int)
        or total < 0
        or not isinstance(families, dict)
        or not isinstance(holds, dict)
    ):
        return False
    if any(
        isinstance(count, bool) or not isinstance(count, int) or count < 0
        for count in families.values()
    ):
        return False
    if sum(families.values()) != total:
        return False
    worker_model = payload.get("worker_model")
    if not isinstance(worker_model, dict):
        return False
    workers = worker_model.get("proposal_workers")
    writer_count = worker_model.get("mutation_writer_count")
    if (
        not isinstance(workers, dict)
        or workers.get("min") != 2
        or workers.get("max") != 8
        or workers.get("mode") != "READ_ONLY"
        or isinstance(writer_count, bool)
        or not isinstance(writer_count, int)
        or writer_count != 1
        or worker_model.get("parallel_proposals_allowed") is not True
        or worker_model.get("parallel_mutation_for_same_scope_allowed") is not False
    ):
        return False
    governance = payload.get("governance")
    if (
        not isinstance(governance, dict)
        or governance.get("authority_transfer") is not False
        or governance.get("formal_credit_delta") != 0
        or governance.get("engineering_credit_delta") != 0
    ):
        return False
    hold_counts = []
    for family, hold in holds.items():
        if not isinstance(hold, dict):
            return False
        count = hold.get("count")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            return False
        if count and families.get(family) != count:
            return False
        hold_counts.append(count)
    if sum(hold_counts) != sum(
        count for family, count in families.items() if family in holds
    ):
        return False
    if total == 0:
        return True

    for family, count in families.items():
        hold = holds.get(family)
        if not isinstance(hold, dict) or hold.get("count") != count:
            return False
    return bool(families)


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
            "proposal_workers": {
                "min": 2,
                "max": 8,
                "mode": "READ_ONLY",
                "scalable": True,
            },
            "mutation_writer": {"count": 1, "required_for_mutation": True},
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
    if not envelopes and not valid_empty_queue(payload):
        errors.append("empty_queue_receipt")
    for index, envelope in enumerate(envelopes):
        if not isinstance(envelope, dict):
            errors.append(f"{index}:not_object")
            continue
        for error in validate_envelope(envelope, contract):
            errors.append(f"{index}:{error}")
    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}, indent=2))
        return 1
    print(json.dumps({"status": "PASS", "proposals": len(envelopes)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
