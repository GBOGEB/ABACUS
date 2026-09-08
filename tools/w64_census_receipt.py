#!/usr/bin/env python3
"""W64 census P3 receipt generator.

Consumes the W64 P1 census and P2 reverse-pressure reports and emits a
machine-readable receipt. P3 is a governance receipt only: it records whether
census reverse-pressure is clear or blocked, preserves source artifact digests,
and exposes queues for follow-up resolution without deleting, migrating, or
promoting assets.

Usage:
    python tools/w64_census_receipt.py \
      --census architecture/w64/receipts/W64_TOTAL_REPO_CENSUS_P1.json \
      --reverse-pressure architecture/w64/receipts/W64_TOTAL_REPO_CENSUS_P2_REVERSE_PRESSURE.json \
      --out architecture/w64/receipts/W64_TOTAL_REPO_CENSUS_P3_RECEIPT.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable

RECEIPT_SCHEMA_VERSION = "W64-CENSUS-P3-1.0.0"
DUPLICATE_AUTHORITY_TYPE = "duplicate_or_competing_authority"
FOLLOW_UP_TYPES = {
    "stale_version_tree_or_legacy_material",
    "generated_output_inflation_guard",
    "generated_authority_collision",
    "release_critical_unknown_assets",
}


def load_json(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return data


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def findings(reverse_pressure: dict[str, object]) -> list[dict[str, object]]:
    raw = reverse_pressure.get("findings", [])
    if not isinstance(raw, list):
        raise TypeError("reverse-pressure findings must be a list")
    return [finding for finding in raw if isinstance(finding, dict)]


def duplicate_authority_queue(items: list[dict[str, object]]) -> list[dict[str, object]]:
    queue: list[dict[str, object]] = []
    for item in items:
        if item.get("type") != DUPLICATE_AUTHORITY_TYPE:
            continue
        queue.append(
            {
                "family": item.get("family"),
                "paths": item.get("paths", []),
                "severity": item.get("severity"),
                "required_action": "Resolve or waive duplicate authority before release credit.",
            }
        )
    return queue


def follow_up_register(items: list[dict[str, object]]) -> list[dict[str, object]]:
    register: list[dict[str, object]] = []
    for item in items:
        finding_type = str(item.get("type", ""))
        if finding_type not in FOLLOW_UP_TYPES:
            continue
        register.append(
            {
                "type": finding_type,
                "severity": item.get("severity"),
                "count": item.get("count", len(item.get("paths", []) or [])),
                "paths": item.get("paths", []),
                "required_action": "Classify, lineage, resolve, or explicitly waive before downstream DoV credit.",
            }
        )
    return register


def build_receipt(
    census: dict[str, object],
    reverse_pressure: dict[str, object],
    census_path: Path,
    reverse_pressure_path: Path,
) -> dict[str, object]:
    items = findings(reverse_pressure)
    blocker_count = int(reverse_pressure.get("blocker_count", 0) or 0)
    warning_count = int(reverse_pressure.get("warning_count", 0) or 0)
    status = "blocked_pending_resolution" if blocker_count else "receipt_candidate_no_blockers"

    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "purpose": "W64 census P3 receipt; governance summary only, no migration or release promotion.",
        "status": status,
        "p1_asset_count": census.get("asset_count"),
        "p2_finding_count": reverse_pressure.get("finding_count", len(items)),
        "p2_blocker_count": blocker_count,
        "p2_warning_count": warning_count,
        "source_artifact_digests": {
            str(census_path): sha256_file(census_path),
            str(reverse_pressure_path): sha256_file(reverse_pressure_path),
        },
        "duplicate_authority_queue": duplicate_authority_queue(items),
        "stale_generated_unknown_register": follow_up_register(items),
        "downstream_gate": {
            "w64_census_lane": status,
            "binaries_release_regression_credit": "blocked" if blocker_count else "allowed_to_continue_to_next_receipt_gate",
            "requirement": "Downstream W64 DoV credit requires zero blockers or explicit source-bound waiver receipt.",
        },
        "non_claims": [
            "Does not delete, migrate, rename, or consolidate repository assets.",
            "Does not resolve duplicate SSOT or authority conflicts.",
            "Does not regenerate binaries, release packages, or deployment artifacts.",
            "Does not promote ABACUS 5.0 or W64 release DoV by itself.",
        ],
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--census", required=True)
    parser.add_argument("--reverse-pressure", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)

    census_path = Path(args.census).resolve()
    reverse_pressure_path = Path(args.reverse_pressure).resolve()
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    receipt = build_receipt(
        load_json(census_path),
        load_json(reverse_pressure_path),
        census_path,
        reverse_pressure_path,
    )
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "out": str(out),
                "status": receipt["status"],
                "p2_blocker_count": receipt["p2_blocker_count"],
                "p2_warning_count": receipt["p2_warning_count"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
