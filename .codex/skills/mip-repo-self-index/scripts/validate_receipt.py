#!/usr/bin/env python3
"""Validate sanitized MIP self-index producer and consumer receipts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def require(checks: dict[str, bool]) -> None:
    failed = sorted(name for name, passed in checks.items() if not passed)
    if failed:
        raise SystemExit("receipt validation failed: " + ", ".join(failed))


def validate_producer(data: dict[str, Any], expected_sha: str | None) -> str:
    head_sha = str(data.get("head_sha", ""))
    root = data.get("root_self_index") or {}
    checks = {
        "schema_version": data.get("schema_version") == "0.1",
        "program": data.get("program") == "MIP",
        "verification": data.get("verification") == "PASS",
        "repository": bool(data.get("repository")),
        "head_sha": bool(head_sha),
        "expected_sha": expected_sha is None or head_sha == expected_sha,
        "retention": data.get("raw_receipt_retention") == "transient_runner_only",
        "root_runs": isinstance(root, dict) and int(root.get("runs", 0)) >= 2,
        "root_repeatability": isinstance(root, dict)
        and root.get("normalized_equal") is True,
    }

    nested = data.get("nested_surface")
    if nested is not None:
        checks.update(
            {
                "nested_object": isinstance(nested, dict),
                "nested_path": isinstance(nested, dict) and bool(nested.get("path")),
                "nested_runs": isinstance(nested, dict)
                and int(nested.get("runs", 0)) >= 2,
                "nested_repeatability": isinstance(nested, dict)
                and nested.get("normalized_equal") is True,
            }
        )

    diagnostic = data.get("nested_diagnostic")
    if diagnostic is not None:
        checks.update(
            {
                "diagnostic_object": isinstance(diagnostic, dict),
                "diagnostic_pass": isinstance(diagnostic, dict)
                and diagnostic.get("verification") == "PASS",
                "diagnostic_sha": isinstance(diagnostic, dict)
                and diagnostic.get("parent_sha") == head_sha,
                "diagnostic_contract": isinstance(diagnostic, dict)
                and bool(diagnostic.get("source_contract")),
                "diagnostic_retention": isinstance(diagnostic, dict)
                and diagnostic.get("raw_receipt_retention")
                == "transient_runner_only",
            }
        )

    require(checks)
    return head_sha


def validate_consumer(
    data: dict[str, Any], producer_sha: str, producer_repo: str
) -> None:
    checks = {
        "consumer_schema_version": data.get("schema_version") == "0.1",
        "consumer_program": data.get("program") == "MIP",
        "consumer_verification": data.get("consumer_verification") == "PASS",
        "consumer_repository": data.get("repository") == producer_repo,
        "consumer_head_sha": data.get("head_sha") == producer_sha,
        "consumer_artifact": bool(data.get("producer_artifact")),
        "consumer_checks": isinstance(data.get("checks"), list)
        and bool(data.get("checks")),
        "consumer_retention": data.get("raw_receipt_retention")
        == "transient_runner_only",
    }
    require(checks)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("producer", type=Path)
    parser.add_argument("--consumer", type=Path)
    parser.add_argument("--expected-sha")
    args = parser.parse_args()

    producer = load(args.producer)
    head_sha = validate_producer(producer, args.expected_sha)
    if args.consumer:
        consumer = load(args.consumer)
        validate_consumer(consumer, head_sha, str(producer["repository"]))

    print(
        json.dumps(
            {
                "verification": "PASS",
                "head_sha": head_sha,
                "consumer_checked": bool(args.consumer),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
