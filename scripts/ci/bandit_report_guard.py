#!/usr/bin/env python3
"""Fail closed on incomplete or erroneous Bandit JSON, independent of finding count.

A syntactically valid Bandit report with entries in "errors" is NOT a completed
security scan. This guard only qualifies scanner execution; Bandit's own exit
status and the existing full-red/new-debt admission controls remain authoritative.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def validate_report(payload: object) -> tuple[int, int]:
    if not isinstance(payload, dict):
        raise ValueError("Bandit report must be an object")
    findings = payload.get("results")
    errors = payload.get("errors")
    metrics = payload.get("metrics")
    if not isinstance(findings, list):
        raise ValueError("Bandit report is missing a results array")
    if not isinstance(errors, list):
        raise ValueError("Bandit report is missing an errors array")
    if errors:
        raise ValueError(f"Bandit left {len(errors)} source files unscanned")
    if not isinstance(metrics, dict) or not isinstance(metrics.get("_totals"), dict):
        raise ValueError("Bandit report is missing metrics totals")
    inspected = [key for key, value in metrics.items() if key != "_totals" and isinstance(value, dict)]
    if not inspected:
        raise ValueError("Bandit inspected zero source files")
    return len(inspected), len(findings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args(argv)
    try:
        inspected, findings = validate_report(
            json.loads(args.report.read_text(encoding="utf-8"))
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"BANDIT_RECEIPT_INVALID: {exc}", file=sys.stderr)
        return 2
    print(f"BANDIT_RECEIPT_VALID inspected_files={inspected} findings={findings} scan_errors=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
