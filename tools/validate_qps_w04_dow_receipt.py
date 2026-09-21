#!/usr/bin/env python3
"""Validate fixture-wrapped or root W04 DOW receipts."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

CORR = "QPS-FED-W04-T10-SAFE-CTRL"
RUNTIME_REQUIRED = {
    "run_id",
    "artifact_id",
    "parent_repository",
    "parent_commit_sha",
    "child_source_ref",
    "authoritative_child_sha",
    "input_mode",
    "correlation_id",
    "input_hash",
    "input_snapshot_hash",
    "source_artifact_identities",
    "source_artifact_set_sha256",
    "prior_source_artifact_set_sha256",
    "trigger_semantics",
    "analysis_decision",
    "lineage_state_hash",
    "available_analysis_scope",
    "requested_analysis_scope",
    "semantic_trigger_scope",
    "executed_analysis_scope",
    "executed_stages",
    "stage_status",
    "fail_closed_status",
    "typed_findings",
    "child_disposition_placeholder",
    "authority_boundary",
    "output_hash",
}


def load(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(
        path.read_text(encoding="utf-8")
    )
    if not isinstance(data, dict):
        raise ValueError(
            "receipt must be a YAML mapping"
        )
    return data


def canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_trigger_contract(
    receipt: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    identities = receipt.get(
        "source_artifact_identities"
    )
    if not isinstance(identities, list) or not identities:
        errors.append(
            "source_artifact_identities must be a non-empty list"
        )
    else:
        for identity in identities:
            if not isinstance(identity, dict):
                errors.append(
                    "source artifact identity must be a mapping"
                )
                continue
            artifact = identity.get("artifact")
            digest = identity.get("sha256")
            if not artifact:
                errors.append(
                    "source artifact identity missing artifact"
                )
            if not re.fullmatch(
                r"[0-9a-f]{64}",
                str(digest or ""),
            ):
                errors.append(
                    "source artifact identity sha256 invalid"
                )
        if (
            canonical_sha256(identities)
            != receipt.get(
                "source_artifact_set_sha256"
            )
        ):
            errors.append(
                "source_artifact_set_sha256 mismatch"
            )

    prior = receipt.get(
        "prior_source_artifact_set_sha256"
    )
    if prior is not None and not re.fullmatch(
        r"[0-9a-f]{64}",
        str(prior),
    ):
        errors.append(
            "prior_source_artifact_set_sha256 invalid"
        )

    trigger = receipt.get("trigger_semantics")
    if not isinstance(trigger, dict):
        return errors + [
            "trigger_semantics must be a mapping"
        ]

    for key in (
        "semantic_change",
        "analysis_requested",
    ):
        if not isinstance(trigger.get(key), bool):
            errors.append(
                f"trigger_semantics.{key} must be bool"
            )

    artifact_hash_changed = trigger.get(
        "artifact_hash_changed"
    )
    if artifact_hash_changed not in {
        True,
        False,
        None,
    }:
        errors.append(
            "artifact_hash_changed must be bool or null"
        )

    current = receipt.get(
        "source_artifact_set_sha256"
    )
    if prior is None:
        if artifact_hash_changed is not None:
            errors.append(
                "artifact_hash_changed must be null "
                "without prior artifact identity"
            )
    elif re.fullmatch(
        r"[0-9a-f]{64}",
        str(current or ""),
    ):
        expected_changed = prior != current
        if artifact_hash_changed is not expected_changed:
            errors.append(
                "artifact_hash_changed does not match "
                "current/prior artifact identities"
            )

    semantic_change = trigger.get(
        "semantic_change"
    )
    analysis_requested = trigger.get(
        "analysis_requested"
    )
    decision = receipt.get("analysis_decision")

    if semantic_change or analysis_requested:
        expected_decision = "DOW_ANALYSIS"
    elif prior is None:
        expected_decision = (
            "INVALID_UNCOMPARED_NO_ANALYSIS"
        )
    elif artifact_hash_changed:
        expected_decision = (
            "LINEAGE_REFRESH_ONLY"
        )
    else:
        expected_decision = "IDEMPOTENT_NOOP"

    if decision != expected_decision:
        errors.append(
            "analysis_decision mismatch"
        )

    lineage_state = {
        "authoritative_child_sha": receipt.get(
            "authoritative_child_sha"
        ),
        "input_mode": receipt.get("input_mode"),
        "source_artifact_identities": identities,
        "source_artifact_set_sha256": current,
        "semantic_change": semantic_change,
        "analysis_requested": analysis_requested,
    }
    if (
        canonical_sha256(lineage_state)
        != receipt.get("lineage_state_hash")
    ):
        errors.append("lineage_state_hash mismatch")

    return errors


def validate(
    data: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    wrapped = "example_valid_receipt" in data
    receipt = (
        data.get("example_valid_receipt")
        if wrapped
        else data
    )
    if not isinstance(receipt, dict):
        return ["receipt missing or not a mapping"]

    if receipt.get("correlation_id") != CORR:
        errors.append("correlation_id mismatch")
    if "QPS_child_disposes" not in str(
        receipt.get("authority_boundary", "")
    ):
        errors.append(
            "child authority boundary missing"
        )

    if wrapped:
        required = set(
            data.get(
                "receipt_required_fields",
                [],
            )
        )
        missing = sorted(
            required - set(receipt)
        )
        if missing:
            errors.append(
                "fixture example missing fields: "
                + ", ".join(missing)
            )
        return errors

    missing = sorted(
        RUNTIME_REQUIRED - set(receipt)
    )
    if missing:
        errors.append(
            "missing runtime fields: "
            + ", ".join(missing)
        )

    if not re.fullmatch(
        r"[0-9a-f]{40}",
        str(
            receipt.get(
                "parent_commit_sha",
                "",
            )
        ),
    ):
        errors.append(
            "parent_commit_sha must be resolved"
        )

    if not re.fullmatch(
        r"[0-9a-f]{40}",
        str(
            receipt.get(
                "authoritative_child_sha",
                "",
            )
        ),
    ):
        errors.append(
            "authoritative_child_sha must be resolved"
        )

    errors.extend(
        validate_trigger_contract(receipt)
    )

    trigger = receipt.get(
        "trigger_semantics",
        {},
    )
    decision = receipt.get(
        "analysis_decision"
    )
    available = receipt.get(
        "available_analysis_scope"
    )
    requested = receipt.get(
        "requested_analysis_scope"
    )
    semantic_scope = receipt.get(
        "semantic_trigger_scope"
    )
    executed = receipt.get(
        "executed_analysis_scope"
    )
    stages = receipt.get("stage_status")
    findings = receipt.get("typed_findings")

    if not all(
        isinstance(value, list)
        for value in (
            available,
            requested,
            semantic_scope,
            executed,
        )
    ):
        errors.append(
            "analysis scopes must be lists"
        )
    elif decision == "DOW_ANALYSIS":
        if executed != available:
            errors.append(
                "DOW analysis must execute full "
                "available controlled scope"
            )
        if (
            trigger.get("analysis_requested")
            and requested != available
        ):
            errors.append(
                "explicit analysis request scope mismatch"
            )
        if (
            trigger.get("semantic_change")
            and semantic_scope != available
        ):
            errors.append(
                "semantic trigger scope mismatch"
            )
    else:
        if executed != []:
            errors.append(
                "non-analysis decision executed DOW scope"
            )
        if receipt.get("executed_stages") != []:
            errors.append(
                "non-analysis decision executed stages"
            )
        if stages != {}:
            errors.append(
                "non-analysis decision emitted stage status"
            )
        if findings != []:
            errors.append(
                "hash-only/noop decision emitted findings"
            )

        expected_status = {
            "LINEAGE_REFRESH_ONLY": (
                "PASS_HASH_ONLY_LINEAGE_REFRESH_NO_ANALYSIS"
            ),
            "IDEMPOTENT_NOOP": (
                "PASS_IDEMPOTENT_NOOP_NO_ANALYSIS"
            ),
        }.get(decision)
        if (
            expected_status is not None
            and receipt.get(
                "fail_closed_status"
            )
            != expected_status
        ):
            errors.append(
                "non-analysis fail_closed_status mismatch"
            )

    if decision == "DOW_ANALYSIS":
        if not isinstance(stages, dict):
            errors.append(
                "stage_status must be a mapping"
            )
        else:
            required_stage = {
                "stage_id",
                "mechanic_path",
                "executed",
                "status",
                "reason",
            }
            for key, value in stages.items():
                if (
                    not isinstance(value, dict)
                    or required_stage - set(value)
                ):
                    errors.append(
                        f"stage {key} lacks typed execution status"
                    )
                elif value.get("executed") is not True:
                    errors.append(
                        f"stage {key} was not executed"
                    )

        if not isinstance(findings, list):
            errors.append(
                "typed_findings must be a list"
            )
        else:
            for finding in findings:
                if (
                    not isinstance(finding, dict)
                    or finding.get(
                        "qps_authority"
                    )
                    is not False
                ):
                    errors.append(
                        "typed finding violates QPS authority boundary"
                    )

    payload = json.dumps(
        {
            key: value
            for key, value in receipt.items()
            if key != "output_hash"
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    if (
        hashlib.sha256(payload).hexdigest()
        != receipt.get("output_hash")
    ):
        errors.append("output_hash mismatch")

    return errors


def main(argv: list[str]) -> int:
    path = (
        Path(argv[1])
        if len(argv) > 1
        else Path(
            "tests/fixtures/"
            "qps_w04_dow_receipt_fixture.yaml"
        )
    )
    errors = validate(load(path))
    for error in errors:
        print(
            "ERROR: " + error,
            file=sys.stderr,
        )
    if not errors:
        print(
            f"OK: {path} satisfies "
            "QPS W04 DOW receipt contract"
        )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
