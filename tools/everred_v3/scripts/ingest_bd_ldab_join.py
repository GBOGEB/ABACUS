#!/usr/bin/env python3
"""Read a current ABACUS bd.ldab.joined.census.v1 output as UNVERIFIED evidence.

This bridge deliberately does not promote BD-* fingerprint groups to causal roots.
It appends an immutable observation-only event. Source producer remains authoritative.
"""

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import sys

P = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(P / "src"))
from everred import SCHEMA, InvalidEvidence, append_event, valid_sha


def to_event(obj):
    if not isinstance(obj, dict) or obj.get("schema") != "bd.ldab.joined.census.v1":
        raise InvalidEvidence("expected bd.ldab.joined.census.v1")
    scope = obj.get("scope")
    if not isinstance(scope, dict):
        raise InvalidEvidence("missing source scope")
    repo = scope.get("repository")
    sha = scope.get("head_sha")
    url = scope.get("evidence_url")
    run = scope.get("run_id")
    job = scope.get("job_id")
    if not isinstance(repo, str) or "/" not in repo or not valid_sha(sha):
        raise InvalidEvidence("invalid joined source repository/SHA")
    if (
        not isinstance(url, str)
        or not url.startswith("https://github.com/")
        or type(run) is not int
        or run <= 0
        or type(job) is not int
        or job <= 0
    ):
        raise InvalidEvidence("unbound source run/job/URL")
    if (
        obj.get("merge_admission") != "HOLD"
        or obj.get("authority_transfer") is not False
        or obj.get("security_waiver") is not False
    ):
        raise InvalidEvidence("joined census admission/authority violation")
    rows = obj.get("roots")
    metrics = obj.get("metrics")
    dbg = obj.get("unlinked_debug_receipts")
    if (
        not isinstance(rows, list)
        or not isinstance(metrics, dict)
        or not isinstance(dbg, list)
    ):
        raise InvalidEvidence("joined census arrays required")
    if len(rows) != len({r.get("root_id") for r in rows if isinstance(r, dict)}):
        raise InvalidEvidence("duplicate or invalid joined group ids")
    if not all(
        isinstance(r, dict)
        and isinstance(r.get("root_id"), str)
        and r["root_id"].startswith(("BD-", "CI-"))
        for r in rows
    ):
        raise InvalidEvidence("unsupported joined alias row")
    if (
        type(metrics.get("full_bandit_unique")) is not int
        or metrics["full_bandit_unique"] < 0
    ):
        raise InvalidEvidence("missing bandit denominator")
    dg = hashlib.sha256(
        json.dumps(
            obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()
    ingestion_time = dt.datetime.now(dt.timezone.utc).isoformat()
    return {
        "schema": SCHEMA,
        "id": "BDLDAB-" + dg[:24],
        "kind": "note",
        "repo": repo,
        "sha": sha,
        "occurred_at": ingestion_time,
        "provenance": "manual",
        "evidence": {
            "producer_schema": obj["schema"],
            "source_binding": {
                "repository": repo, "source_sha": sha, "run_id": run,
                "job_id": job, "run_url": url,
            },
            "ingested_at": ingestion_time,
            "evidence_trust": "MANUAL_UNVERIFIED",
            "producer_sha256": dg,
            "head_sha": sha,
            "run_id": run,
            "job_id": job,
            "url": url,
            "bandit_fingerprint_observations": metrics["full_bandit_unique"],
            "join_groups": len(rows),
            "debug_receipts": metrics.get("debug_receipts"),
            "unlinked_debug_receipts": len(dbg),
            "compare": metrics.get("comparable_delta"),
            "root_causality": "UNCONFIRMED",
            "admission": "HOLD",
            "note": "Fingerprint/CI group identifiers remain taxonomic candidates, never confirmed causal root IDs.",
        },
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--ledger", default="data/ledger.jsonl")
    a = p.parse_args()
    e = to_event(json.loads(pathlib.Path(a.input).read_text(encoding="utf-8")))
    append_event(pathlib.Path(a.ledger), e)
    print("Appended observation-only BD/LDAB join receipt", e["id"])


if __name__ == "__main__":
    main()
