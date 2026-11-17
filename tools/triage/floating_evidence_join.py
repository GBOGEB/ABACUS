"""Conservative evidence join: existing DAB measurement plus W104 candidate paths.

No claim of runtime reachability is made from a path or a missing static import.
All joins are exact-source-SHA gated. Missing provenance remains UNKNOWN.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def reconcile(
    dab: dict, floating: dict, *, source_sha: str, floating_sha: str | None
) -> dict:
    if dab.get("exact_sha") != source_sha:
        raise ValueError("DAB source SHA mismatch")
    if floating_sha != source_sha:
        raise ValueError("floating source SHA mismatch")
    candidates = set()
    for bucket in floating.get("floating_buckets", {}).values():
        candidates.update(bucket.get("paths", []))
    measured = {row["path"]: row for row in dab.get("rows", [])}
    rows = []
    for path in sorted(candidates | measured.keys()):
        measurement = measured.get(path)
        rows.append(
            {
                "path": path,
                "w104_floating_candidate": path in candidates,
                "coverage_evidence": (
                    "MEASURED" if measurement is not None else "UNKNOWN"
                ),
                "statements_covered": (
                    measurement.get("covered_statements") if measurement else None
                ),
                "statements_eligible": (
                    measurement.get("statements") if measurement else None
                ),
                "branches_covered": (
                    measurement.get("covered_branches") if measurement else None
                ),
                "branches_eligible": (
                    measurement.get("eligible_branches") if measurement else None
                ),
                "runtime_reachability": "UNKNOWN",
                "orphan": None,
                "prune_authorized": False,
            }
        )
    overlap = [
        r
        for r in rows
        if r["w104_floating_candidate"] and r["coverage_evidence"] == "MEASURED"
    ]
    return {
        "schema": "codepurple.floating-evidence-join.v1",
        "source_sha": source_sha,
        "candidate_paths": len(candidates),
        "measured_paths": len(measured),
        "candidate_measured_overlap": len(overlap),
        "candidate_unmeasured": len(candidates) - len(overlap),
        "rows": rows,
        "authority_transfer": False,
        "prune_authorized": False,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dab", type=Path, required=True)
    p.add_argument("--floating", type=Path, required=True)
    p.add_argument("--source-sha", required=True)
    p.add_argument("--floating-sha", required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    result = reconcile(
        json.loads(a.dab.read_text()),
        json.loads(a.floating.read_text()),
        source_sha=a.source_sha,
        floating_sha=a.floating_sha,
    )
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
