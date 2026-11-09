#!/usr/bin/env python3
"""Fail-closed read-only MIP U01-U16 backlog validator and roll-up."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

STATES = {"UNKNOWN", "PENDING", "VERIFIED_PASS", "VERIFIED_FAIL", "BLOCKED"}
PHASES = {"DEFINE", "MEASURE", "ANALYZE", "IMPROVE", "CONTROL"}


def rollup(backlog, as_of):
    if backlog.get("schema") != "code-purple.mip.unknown-backlog.v1":
        raise ValueError("unsupported backlog schema")
    date = dt.date.fromisoformat(as_of)
    items = backlog.get("items")
    if not isinstance(items, list) or len(items) != 16:
        raise ValueError("exactly U01-U16 required")
    ids = set()
    counts = {s: 0 for s in sorted(STATES)}
    aged = []
    for row in items:
        if not isinstance(row, dict):
            raise ValueError("invalid backlog row")
        key = row.get("id")
        if key not in {f"U{i:02d}" for i in range(1, 17)} or key in ids:
            raise ValueError("invalid or duplicate U-ID")
        ids.add(key)
        state = row.get("evidence_state")
        if state not in STATES or row.get("dmaic_phase") not in PHASES:
            raise ValueError("invalid state or DMAIC phase")
        for field in ("owner", "acceptance_target", "title"):
            if not isinstance(row.get(field), str) or not row[field]:
                raise ValueError("missing " + field)
        age = row.get("age")
        if not isinstance(age, dict):
            raise ValueError("age contract missing")
        first = dt.date.fromisoformat(age["first_observed"])
        days = (date - first).days
        if days < 0:
            raise ValueError("future observation")
        if age.get("days") is not None and age["days"] != days:
            raise ValueError("stale age days")
        if state.startswith("VERIFIED"):
            if not isinstance(row.get("proof_reference"), str) or not row[
                "proof_reference"
            ].startswith("https://github.com/"):
                raise ValueError("verified state requires native proof URL")
            if row.get("measurement_value") is None:
                raise ValueError("verified state requires measured value")
        elif row.get("measurement_value") is not None and state == "UNKNOWN":
            raise ValueError("UNKNOWN cannot claim a value")
        if (
            state == "VERIFIED_PASS"
            and row.get("root_id") is not None
            and not row.get("proof_reference")
        ):
            raise ValueError("unproven root")
        counts[state] += 1
        aged.append(
            {
                "id": key,
                "age_days": days,
                "state": state,
                "owner": row["owner"],
                "overflow": row.get("overflow") is True,
            }
        )
    if ids != {f"U{i:02d}" for i in range(1, 17)}:
        raise ValueError("missing U-ID")
    return {
        "schema": "code-purple.mip.unknown-kpi.v1",
        "as_of": as_of,
        "source_repository": backlog["source_repository"],
        "reference_head": backlog["reference_head"],
        "total": 16,
        "states": counts,
        "evidence_completeness": counts["VERIFIED_PASS"] + counts["VERIFIED_FAIL"],
        "evidence_completeness_pct": round(
            100 * (counts["VERIFIED_PASS"] + counts["VERIFIED_FAIL"]) / 16, 2
        ),
        "aged": aged,
        "overflow_count": sum(x["overflow"] for x in aged),
        "merge_admission": "HOLD",
        "authority_transfer": False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--as-of", required=True)
    a = p.parse_args()
    result = rollup(json.loads(a.input.read_text(encoding="utf-8")), a.as_of)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
