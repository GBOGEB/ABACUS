#!/usr/bin/env python3
"""Convert independently verified native metric receipts into MIP JSONL observations.

No external IO beyond explicit input/output files; absent metrics produce no numeric rows.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

FAMILIES = {
    "bd_burndown": {"root_transitions"},
    "coverage": {"statement_coverage", "branch_coverage", "changed_line_coverage"},
    "debug_ldab": {"attributed_session_rate"},
    "evidence_quality": {"receipt_completeness"},
    "repair_effectiveness": {"first_pass_acceptance"},
    "throughput": {"verified_root_hours_yield"},
}


def convert(payload):
    if (
        not isinstance(payload, dict)
        or payload.get("schema") != "mip.native.metric.receipts.v1"
    ):
        raise ValueError("native metric receipt schema required")
    rows = payload.get("receipts")
    if not isinstance(rows, list):
        raise ValueError("receipts list required")
    result = []
    for r in rows:
        if not isinstance(r, dict):
            raise ValueError("receipt must be object")
        family, metric = r.get("family"), r.get("metric")
        if family not in FAMILIES or metric not in FAMILIES[family]:
            raise ValueError("unknown family metric")
        if r.get("proposal_only") is True:
            continue
        n, d = r.get("numerator"), r.get("denominator")
        if n is not None or d is not None:
            if (
                type(n) is not int
                or type(d) is not int
                or d <= 0
                or n < 0
                or n > d
                or r.get("verified_native") is not True
            ):
                raise ValueError("numeric receipt requires verified native count pair")
        if family in (
            "bd_burndown",
            "debug_ldab",
            "repair_effectiveness",
            "throughput",
        ):
            if n is not None and not r.get("root_fingerprint"):
                raise ValueError("root-level metric needs fingerprint provenance")
        out = {
            "schema": "mip.stat.observation.v1",
            "repository": r.get("repository"),
            "family": family,
            "metric": metric,
            "metric_version": r.get("metric_version", "1.0"),
            "exact_sha": r.get("exact_sha"),
            "run_id": r.get("run_id"),
            "job_id": r.get("job_id"),
            "observed_at": r.get("observed_at"),
            "evidence_url": r.get("evidence_url"),
            "collection_quality": "NATIVE" if n is not None else "INCOMPLETE",
            "status": r.get("status") if n is not None else "UNKNOWN",
            "numerator": n,
            "denominator": d,
        }
        result.append(out)
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    rows = convert(json.loads(a.input.read_text(encoding="utf-8")))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
