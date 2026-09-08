#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

# GitHub Actions invokes this file directly as `python tools/...py`.
# In that mode Python adds `tools/` (not the repository root) to sys.path,
# so package imports such as `from tools...` fail unless the root is explicit.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.w64_census_reverse_pressure import (
    as_assets,
    duplicate_authority_findings,
    generated_inflation_findings,
    load_census,
    stale_tree_findings,
    unknown_blocker_findings,
)

RESOLVED_STATES = {
    "non_competing_scoped",
    "canonical_with_mirrors",
    "immutable_run_series",
    "template_or_staging_copy",
    "generated_with_lineage",
    "classified_non_authority",
    "classified_active_reference",
    "classified_rendered_output",
}


def load_optional(path: str | None) -> dict:
    if not path:
        return {}
    candidate = Path(path)
    if not candidate.exists():
        return {}
    return json.loads(candidate.read_text())


def pathset_sha256(paths: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(str(x) for x in paths)).encode()).hexdigest()


def apply_duplicate_dispositions(findings: list[dict], registry: dict) -> tuple[list[dict], list[dict]]:
    by_family = {
        str(item.get("family")): item
        for item in registry.get("families", [])
        if isinstance(item, dict)
    }
    keep = []
    resolved = []
    for finding in findings:
        family = str(finding.get("family", ""))
        disposition = by_family.get(family)
        paths = list(finding.get("paths", []))
        exact = (
            (disposition or {}).get("pathset_sha256") == pathset_sha256(paths)
            and int((disposition or {}).get("member_count", -1)) == len(paths)
        )
        if disposition and disposition.get("state") in RESOLVED_STATES and exact:
            resolved.append(
                {
                    **finding,
                    "resolution_state": disposition.get("state"),
                    "canonical": disposition.get("canonical"),
                    "evidence_basis": disposition.get("evidence_basis"),
                    "pathset_sha256": disposition.get("pathset_sha256"),
                }
            )
        else:
            keep.append(finding)
    return keep, resolved


def apply_unknown_dispositions(findings: list[dict], registry: dict) -> tuple[list[dict], list[dict]]:
    dispositions = {
        str(item.get("path")): item
        for item in registry.get("assets", [])
        if isinstance(item, dict)
    }
    keep = []
    resolved = []
    for finding in findings:
        if finding.get("type") != "release_critical_unknown_assets":
            keep.append(finding)
            continue
        unresolved = []
        for path in finding.get("paths", []):
            disposition = dispositions.get(str(path))
            if disposition and disposition.get("state") in RESOLVED_STATES:
                resolved.append({"path": path, **disposition})
            else:
                unresolved.append(path)
        if unresolved:
            keep.append({**finding, "count": len(unresolved), "paths": unresolved})
    return keep, resolved


def apply_generated_disposition(findings: list[dict], registry: dict) -> tuple[list[dict], list[dict]]:
    entries = {
        str(item.get("path")): item
        for item in registry.get("assets", [])
        if isinstance(item, dict)
    }
    keep = []
    resolved = []
    for finding in findings:
        if finding.get("type") != "generated_authority_collision":
            keep.append(finding)
            continue
        unresolved = []
        for path in finding.get("paths", []):
            disposition = entries.get(str(path))
            if (
                disposition
                and disposition.get("state") == "generated_with_lineage"
                and disposition.get("source")
                and disposition.get("generator")
            ):
                resolved.append({"path": path, **disposition})
            else:
                unresolved.append(path)
        if unresolved:
            keep.append({**finding, "count": len(unresolved), "paths": unresolved})
    return keep, resolved


def reverse_pressure_v2(census: dict, duplicate: dict, unknown: dict, generated: dict) -> dict:
    assets = as_assets(census)
    duplicate_raw = duplicate_authority_findings(assets)
    duplicate_keep, duplicate_resolved = apply_duplicate_dispositions(duplicate_raw, duplicate)

    findings = []
    findings.extend(duplicate_keep)
    findings.extend(stale_tree_findings(assets))

    generated_raw = generated_inflation_findings(assets)
    generated_keep, generated_resolved = apply_generated_disposition(generated_raw, generated)
    findings.extend(generated_keep)

    unknown_raw = unknown_blocker_findings(assets)
    unknown_keep, unknown_resolved = apply_unknown_dispositions(unknown_raw, unknown)
    findings.extend(unknown_keep)

    blockers = sum(1 for finding in findings if finding.get("severity") == "blocker")
    warnings = sum(1 for finding in findings if finding.get("severity") == "warning")
    return {
        "schema_version": "W64-CENSUS-P2-2.2.0",
        "purpose": "Disposition-aware reverse-pressure census; explicit exact-path evidence required.",
        "p1_asset_count": census.get("asset_count"),
        "finding_count": len(findings),
        "blocker_count": blockers,
        "warning_count": warnings,
        "status": "blocked" if blockers else "candidate_no_blockers_detected",
        "findings": findings,
        "resolved": {
            "duplicate_authority_families": duplicate_resolved,
            "unknown_assets": unknown_resolved,
            "generated_authority_assets": generated_resolved,
        },
        "non_claims": [
            "Does not delete or migrate assets.",
            "Disposition closes census ambiguity only; it does not grant engineering or negotiation credit.",
            "P3 receipt remains required.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--census", required=True)
    parser.add_argument("--duplicate-dispositions")
    parser.add_argument("--unknown-dispositions")
    parser.add_argument("--generated-lineage")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    report = reverse_pressure_v2(
        load_census(Path(args.census)),
        load_optional(args.duplicate_dispositions),
        load_optional(args.unknown_dispositions),
        load_optional(args.generated_lineage),
    )
    Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "blocker_count": report["blocker_count"],
                "warning_count": report["warning_count"],
                "resolved_duplicate_families": len(report["resolved"]["duplicate_authority_families"]),
                "resolved_unknown_assets": len(report["resolved"]["unknown_assets"]),
                "resolved_generated_assets": len(report["resolved"]["generated_authority_assets"]),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
