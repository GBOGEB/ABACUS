#!/usr/bin/env python3
"""Validate the QPS W04 DOW receipt fixture contract.

This validator is intentionally schema/authority focused. It does not run QPS
engineering analysis and it does not promote ABACUS findings into QPS authority.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required to run this validator") from exc

EXPECTED_CORRELATION = "QPS-FED-W04-T10-SAFE-CTRL"
REQUIRED_FIELDS = {
    "run_id",
    "artifact_id",
    "parent_commit_sha",
    "correlation_id",
    "input_hash",
    "output_hash",
    "executed_stages",
    "stage_status",
    "fail_closed_status",
    "typed_findings",
    "authority_boundary",
}


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} did not parse as a YAML mapping")
    return data


def validate_fixture(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("correlation_id") != EXPECTED_CORRELATION:
        errors.append("fixture correlation_id does not match W04 correlation")

    receipt = data.get("example_valid_receipt")
    if not isinstance(receipt, dict):
        return errors + ["example_valid_receipt missing or not a mapping"]

    missing = sorted(REQUIRED_FIELDS - set(receipt))
    if missing:
        errors.append(f"example_valid_receipt missing required fields: {', '.join(missing)}")

    if receipt.get("correlation_id") != EXPECTED_CORRELATION:
        errors.append("receipt correlation_id does not match W04 correlation")

    executed_stages = receipt.get("executed_stages")
    stage_status = receipt.get("stage_status")
    if not isinstance(executed_stages, list) or not executed_stages:
        errors.append("executed_stages must be a non-empty list")
    if not isinstance(stage_status, dict):
        errors.append("stage_status must be a mapping")
    elif isinstance(executed_stages, list):
        missing_status = [stage for stage in executed_stages if stage not in stage_status]
        if missing_status:
            errors.append(f"stage_status missing entries for: {', '.join(missing_status)}")

    typed_findings = receipt.get("typed_findings")
    if not isinstance(typed_findings, list):
        errors.append("typed_findings must be a list")

    boundary = str(receipt.get("authority_boundary", ""))
    if "QPS_child_disposes" not in boundary:
        errors.append("authority_boundary must state that QPS child disposes findings")

    return errors


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else Path("tests/fixtures/qps_w04_dow_receipt_fixture.yaml")
    errors = validate_fixture(load_yaml(path))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"OK: {path} satisfies QPS W04 DOW receipt fixture contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
