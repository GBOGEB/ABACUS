#!/usr/bin/env python3
"""Read-only GitHub Actions collector; dry-run JSON by default, no implicit writes.

Requires GITHUB_TOKEN with Actions:read. --artifact-plan is a JSON array of
explicit job/artifact/member bindings and normalized scanner configurations.
"""

import argparse
import json
import pathlib
import sys

BASE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "src"))
from everred import append_events_batch
from native_ingest import GitHubReadOnly, collect_native


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--sha", required=True)
    p.add_argument("--run-id", required=True, type=int)
    p.add_argument("--artifact-plan")
    p.add_argument("--output", required=True)
    p.add_argument("--apply-ledger", action="store_true")
    p.add_argument("--ledger", default=str(BASE / "data/ledger.jsonl"))
    a = p.parse_args()
    plan = (
        json.loads(pathlib.Path(a.artifact_plan).read_text()) if a.artifact_plan else []
    )
    events = collect_native(a.repo, a.sha, a.run_id, plan, reader=GitHubReadOnly())
    path = pathlib.Path(a.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"schema": "abacus.everred.native.batch.v1", "events": events}, indent=2
        )
        + "\n"
    )
    if a.apply_ledger:
        # Each receipt is immutable; duplicate payloads are rejected rather than overwritten.
        # Operator is responsible for reconciling a partial interrupted batch.
        append_events_batch(pathlib.Path(a.ledger), events)
    print(
        f"Collected {len(events)} events at {a.sha}: "
        + ("LEDGER_APPLIED" if a.apply_ledger else "DRY_RUN_ONLY")
    )


if __name__ == "__main__":
    main()
