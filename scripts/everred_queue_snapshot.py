#!/usr/bin/env python3
"""Generate an offline, deterministic EVERRED queue snapshot from native run-list JSON."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

def normalize(queued: dict, running: dict) -> dict:
    rows = []
    seen = set()
    totals = {}
    for state, source in (("queued", queued), ("in_progress", running)):
        records = source.get("workflow_runs")
        total = source.get("total_count")
        if not isinstance(records, list) or type(total) is not int or total < len(records):
            raise ValueError("invalid Github Actions run-list response")
        totals[state] = {"api_total": total, "fetched": len(records), "partial": total > len(records)}
        for record in records:
            run_id = record.get("id")
            if type(run_id) is not int or run_id <= 0:
                raise ValueError("missing positive numeric run ID")
            if run_id in seen:
                continue
            seen.add(run_id)
            rows.append({"id": run_id, "status": state, "name": record.get("name") or "UNKNOWN",
                         "event": record.get("event") or "UNKNOWN", "head_sha": record.get("head_sha"),
                         "created_at": record.get("created_at"), "run_attempt": record.get("run_attempt")})
    rows.sort(key=lambda x: (x["status"], str(x["created_at"] or ""), x["id"]))
    return {"schema": "everred.queue.snapshot.v1", "source": "GitHub Actions native run-list",
            "scope": "GBOGEB/ABACUS", "counts": totals, "runs": rows,
            "partial": any(x["partial"] for x in totals.values())}

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queued", required=True, type=Path)
    ap.add_argument("--running", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    report = normalize(json.loads(args.queued.read_text()), json.loads(args.running.read_text()))
    payload = json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n"
    args.out.write_text(payload, encoding="utf-8")
    print(hashlib.sha256(payload.encode()).hexdigest())

if __name__ == "__main__":
    main()
