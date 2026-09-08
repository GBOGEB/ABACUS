#!/usr/bin/env python3
"""W64 census P2 reverse-pressure analyzer.

Consumes the P1 census JSON and turns conservative inventory signals into
release-pressure findings. P2 does not migrate/delete anything; it separates
blockers from warnings so P3 can emit a defensible release receipt.

Usage:
    python tools/w64_total_repo_census.py --root . --out architecture/w64/receipts/W64_TOTAL_REPO_CENSUS_P1.json
    python tools/w64_census_reverse_pressure.py --census architecture/w64/receipts/W64_TOTAL_REPO_CENSUS_P1.json --out architecture/w64/receipts/W64_TOTAL_REPO_CENSUS_P2_REVERSE_PRESSURE.json
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Iterable

AUTHORITY_KEYWORDS = ("ssot", "authority", "contract", "schema", "resolver", "registry", "manifest")
STALE_TREE_COMPONENTS = {"legacy", "archive", "deprecated", "stale", "old"}
STALE_TREE_PREFIXES = ("abacus-v0", "abacus-v1", "abacus-v2", "abacus-v3")
GENERATED_KEYWORDS = ("generated", "dist/", "build/", "exports/")
RELEASE_CRITICAL_CATEGORIES = {"workflow", "ssot", "schema_or_config", "source_or_script", "binary_or_rendered_output"}


def load_census(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def as_assets(census: dict[str, object]) -> list[dict[str, object]]:
    raw = census.get("assets", [])
    if not isinstance(raw, list):
        raise TypeError("census assets must be a list")
    return [asset for asset in raw if isinstance(asset, dict)]


def path_text(asset: dict[str, object]) -> str:
    return str(asset.get("path", ""))


def is_authority_like(asset: dict[str, object]) -> bool:
    text = path_text(asset).lower()
    category = str(asset.get("category", ""))
    return category in {"ssot", "schema_or_config"} or any(keyword in text for keyword in AUTHORITY_KEYWORDS)


def is_generated_like(asset: dict[str, object]) -> bool:
    text = path_text(asset).lower()
    return str(asset.get("classification")) == "generated" or any(keyword in text for keyword in GENERATED_KEYWORDS)


def is_stale_tree_like(asset: dict[str, object]) -> bool:
    if str(asset.get("classification")) == "dormant":
        return True
    parts = [part.lower() for part in Path(path_text(asset)).parts]
    return any(part in STALE_TREE_COMPONENTS or part.startswith(STALE_TREE_PREFIXES) for part in parts)


def is_release_critical_unknown(asset: dict[str, object]) -> bool:
    if str(asset.get("classification")) != "unknown":
        return False
    category = str(asset.get("category", ""))
    return category in RELEASE_CRITICAL_CATEGORIES or is_authority_like(asset)


def duplicate_authority_findings(assets: list[dict[str, object]]) -> list[dict[str, object]]:
    families: dict[str, list[dict[str, object]]] = defaultdict(list)
    for asset in assets:
        family = asset.get("duplicate_family_candidate")
        if family and is_authority_like(asset):
            families[str(family)].append(asset)
    findings: list[dict[str, object]] = []
    for family, members in sorted(families.items()):
        if len(members) > 1:
            findings.append(
                {
                    "severity": "blocker",
                    "type": "duplicate_or_competing_authority",
                    "family": family,
                    "paths": sorted(path_text(member) for member in members),
                    "reason": "Multiple authority-like tracked assets share a duplicate family; consolidation decision required before release credit.",
                }
            )
    return findings


def stale_tree_findings(assets: list[dict[str, object]]) -> list[dict[str, object]]:
    paths = sorted(path_text(asset) for asset in assets if is_stale_tree_like(asset))
    if not paths:
        return []
    return [
        {
            "severity": "warning",
            "type": "stale_version_tree_or_legacy_material",
            "count": len(paths),
            "paths": paths[:250],
            "reason": "Legacy/stale paths must not inflate active architecture penetration.",
        }
    ]


def generated_inflation_findings(assets: list[dict[str, object]]) -> list[dict[str, object]]:
    generated = [asset for asset in assets if is_generated_like(asset)]
    authority_like_generated = [asset for asset in generated if is_authority_like(asset)]
    findings: list[dict[str, object]] = []
    if generated:
        findings.append(
            {
                "severity": "warning",
                "type": "generated_output_inflation_guard",
                "count": len(generated),
                "paths": sorted(path_text(asset) for asset in generated)[:250],
                "reason": "Generated outputs are inventory only unless separately lineaged to source authority and generator command.",
            }
        )
    if authority_like_generated:
        findings.append(
            {
                "severity": "blocker",
                "type": "generated_authority_collision",
                "count": len(authority_like_generated),
                "paths": sorted(path_text(asset) for asset in authority_like_generated)[:250],
                "reason": "Generated authority-like files cannot be counted as SSOT without explicit upstream lineage.",
            }
        )
    return findings


def unknown_blocker_findings(assets: list[dict[str, object]]) -> list[dict[str, object]]:
    unknowns = [asset for asset in assets if is_release_critical_unknown(asset)]
    if not unknowns:
        return []
    return [
        {
            "severity": "blocker",
            "type": "release_critical_unknown_assets",
            "count": len(unknowns),
            "paths": sorted(path_text(asset) for asset in unknowns)[:250],
            "reason": "Release-critical unknown assets must be classified before W64 DoV or release readiness credit.",
        }
    ]


def reverse_pressure(census: dict[str, object]) -> dict[str, object]:
    assets = as_assets(census)
    findings: list[dict[str, object]] = []
    findings.extend(duplicate_authority_findings(assets))
    findings.extend(stale_tree_findings(assets))
    findings.extend(generated_inflation_findings(assets))
    findings.extend(unknown_blocker_findings(assets))

    blocker_count = sum(1 for finding in findings if finding.get("severity") == "blocker")
    warning_count = sum(1 for finding in findings if finding.get("severity") == "warning")
    return {
        "schema_version": "W64-CENSUS-P2-1.0.0",
        "purpose": "Reverse-pressure census findings; no migration, deletion, or release credit.",
        "p1_asset_count": census.get("asset_count"),
        "finding_count": len(findings),
        "blocker_count": blocker_count,
        "warning_count": warning_count,
        "status": "blocked" if blocker_count else "candidate_no_blockers_detected",
        "findings": findings,
        "non_claims": [
            "Does not delete or migrate assets.",
            "Does not resolve duplicate authorities.",
            "Does not promote W64 DoV; P3 receipt remains required.",
        ],
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--census", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)

    census_path = Path(args.census).resolve()
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    report = reverse_pressure(load_census(census_path))
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"blocker_count": report["blocker_count"], "finding_count": report["finding_count"], "out": str(out)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
