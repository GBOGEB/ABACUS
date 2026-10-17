"""Fail-closed, source-bound coverage receipt for the DMAIC bridge.

This receipt covers one named Python module; it is not a fleet-wide estimate.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict


def _count(summary: Dict[str, Any], name: str) -> int:
    value = summary.get(name)
    if type(value) is not int or value < 0:
        raise ValueError(f"missing or invalid coverage count: {name}")
    return value


def _measured(summary: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    statements = _count(summary, "num_statements")
    lines = _count(summary, "covered_lines")
    branches = _count(summary, "num_branches")
    covered_branches = _count(summary, "covered_branches")
    if not statements or not branches:
        raise ValueError("source must have positive statement and branch denominators")
    if lines > statements or covered_branches > branches:
        raise ValueError("coverage numerator exceeds denominator")
    for missing_key, total, covered in (
        ("missing_lines", statements, lines),
        ("missing_branches", branches, covered_branches),
    ):
        if missing_key in summary and _count(summary, missing_key) != total - covered:
            raise ValueError(f"inconsistent coverage denominator: {missing_key}")
    return {
        "statements": {
            "covered": lines,
            "total": statements,
            "percent": round(100 * lines / statements, 2),
        },
        "branches": {
            "covered": covered_branches,
            "total": branches,
            "percent": round(100 * covered_branches / branches, 2),
        },
    }


def build_receipt(
    coverage_path: Path, source_path: Path, head_sha: str
) -> Dict[str, Any]:
    """Reject absent/malformed measurements; bind the counts to exact source bytes."""
    if not re.fullmatch(r"[0-9a-f]{40}", head_sha):
        raise ValueError("head SHA must be a complete lowercase Git object ID")
    raw = coverage_path.read_bytes()
    report = json.loads(raw)
    if not isinstance(report, dict) or not isinstance(report.get("files"), dict):
        raise ValueError("missing coverage.py file-level measurement")
    if not isinstance(report.get("totals"), dict):
        raise ValueError("missing coverage.py overall measurement")

    source_id = source_path.as_posix()
    candidates = [
        k
        for k in report["files"]
        if isinstance(k, str)
        and (k == source_id or k.endswith("/" + source_id.lstrip("/")))
    ]
    if len(candidates) != 1:
        raise ValueError("missing or ambiguous source module coverage")
    record = report["files"][candidates[0]]
    if not isinstance(record, dict) or not isinstance(record.get("summary"), dict):
        raise ValueError("missing source module summary")

    measured = _measured(record["summary"])
    overall = _measured(report["totals"])
    for metric in ("statements", "branches"):
        if measured[metric]["total"] > overall[metric]["total"]:
            raise ValueError("module denominator exceeds global denominator")
        if measured[metric]["covered"] > overall[metric]["covered"]:
            raise ValueError("module numerator exceeds global numerator")
        if len(report["files"]) == 1 and measured[metric] != overall[metric]:
            raise ValueError("one-file global totals differ from source measurement")

    return {
        "schema": "abacus.bridge.coverage.receipt.v1",
        "head_sha": head_sha,
        "scope": "one_python_module",
        "source_path": source_id,
        "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "coverage_report_sha256": hashlib.sha256(raw).hexdigest(),
        **measured,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--head", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        receipt = build_receipt(args.coverage, args.source, args.head)
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(2, f"bridge coverage proof failed: {exc}\n")
    args.output.write_text(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
