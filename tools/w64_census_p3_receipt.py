#!/usr/bin/env python3
"""Emit a governed W64 P3 receipt from executed P1/P2 census outputs.

This tool does not rerun P1/P2 and does not create release credit by itself. It
summarizes the observed P2 blockers/warnings and records whether W64 remains
blocked or is a candidate for further release-readiness review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable


def load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_receipt(p1_path: Path, p2_path: Path) -> dict[str, object]:
    p1 = load(p1_path)
    p2 = load(p2_path)
    blocker_count = int(p2.get("blocker_count", 0))
    warning_count = int(p2.get("warning_count", 0))
    findings = p2.get("findings", [])
    finding_types = sorted(
        str(finding.get("type"))
        for finding in findings
        if isinstance(finding, dict) and finding.get("type")
    )
    return {
        "schema_version": "W64-CENSUS-P3-1.0.0",
        "purpose": "Executed W64 P1/P2 census receipt; no automatic release-credit promotion.",
        "p1": {
            "path": p1_path.as_posix(),
            "sha256": sha256(p1_path),
            "asset_count": p1.get("asset_count"),
            "by_category": p1.get("by_category", {}),
            "by_classification": p1.get("by_classification", {}),
        },
        "p2": {
            "path": p2_path.as_posix(),
            "sha256": sha256(p2_path),
            "blocker_count": blocker_count,
            "warning_count": warning_count,
            "finding_types": finding_types,
        },
        "status": "BLOCKED" if blocker_count else "CANDIDATE_NO_P2_BLOCKERS",
        "release_credit": "NOT_GRANTED",
        "w64_dov": "NOT_PROMOTED",
        "non_claims": [
            "Does not resolve any P2 finding.",
            "Does not migrate, delete, or consolidate assets.",
            "Does not grant release credit or W64 DoV.",
        ],
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--p1", required=True)
    parser.add_argument("--p2", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)

    p1_path = Path(args.p1)
    p2_path = Path(args.p2)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    receipt = build_receipt(p1_path, p2_path)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "out": str(out)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
