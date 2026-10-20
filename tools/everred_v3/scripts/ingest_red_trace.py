#!/usr/bin/env python3
"""Map GOGREEN red-trace reports (gogreen.red_trace.v1) onto EVERRED v3 events.

Producer: GBOGEB/pipeline-automation-hub mission-control/gogreen/red_trace (read-only
Actions metadata). EVERRED stays the consumer and the ledger owner; this adapter only
emits typed events, like ingest_bd_ldab_join.py.

Mapping (one deterministic event id per fact, so re-ingest is idempotent):
  * break (red now, green before)   -> occurrence at first red head + root_candidate
  * EVERRED (never green in window) -> occurrence at first red head + root_candidate
  * shared break root (1 SHA -> N)  -> ONE root_candidate, every workflow an occurrence
  * latest recovered red episode    -> verification at the recovery head (status PASS)
  * stale red (> 3 d, no replay)    -> note (state not asserted for current HEAD)
Never emits root_confirmed, closure or admission: metadata cannot confirm causes.
Candidate cause is only 'PINNED_HISTORICAL_EVIDENCE' when the workflow hard-codes a
historical run/artifact id; otherwise 'UNKNOWN'.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
import everred  # noqa: E402

SOURCE_SCHEMA = "gogreen.red_trace.v1"


def slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-")[:48]


def _ev(eid, kind, repo, at, sha, evidence, root_id=None):
    e = {"schema": everred.SCHEMA, "id": eid, "kind": kind, "repo": repo, "occurred_at": at,
         "provenance": "observed", "evidence": evidence}
    if sha:
        e["sha"] = sha
    if root_id:
        e["root_id"] = root_id
    return e


def events_from_report(rep: dict) -> list[dict]:
    if rep.get("schema") != SOURCE_SCHEMA:
        raise everred.InvalidEvidence("not a gogreen.red_trace.v1 report")
    if rep.get("authority", {}).get("merge_authorized") is not False:
        raise everred.InvalidEvidence("red-trace report must not carry merge authority")
    repo = rep["repository"]
    rshort = repo.split("/")[-1]
    base = f"https://github.com/{repo}/actions/runs/"
    out, roots = [], {}
    for w in rep["workflows"]:
        name, cls = w["name"], w["class"]
        pinned = bool(w.get("pinned_historical_ids"))
        t = w.get("break") or (dict(w["first_red"], first_red_sha=w["first_red"]["sha"],
                                    first_red_run=w["first_red"]["run_id"],
                                    first_red_at=w["first_red"]["at"]) if "first_red" in w else None)
        if cls in ("GREEN_TO_RED", "EVERRED") or (cls == "FLAKY" and w.get("current") == "RED"):
            if not t or not everred.valid_sha(t.get("first_red_sha")):
                continue
            rid = f"RT-ROOT-{slug(rshort)}-{t['first_red_sha'][:12]}"
            failing = [f"{f['job']}: {', '.join(f['steps'])}" for f in t.get("failing", [])]
            out.append(_ev(f"RT-OCC-{slug(rshort)}-{slug(name)}-{t['first_red_sha'][:12]}", "occurrence", repo,
                           t["first_red_at"], t["first_red_sha"],
                           {"workflow": name, "path": w["path"], "class": cls, "run_id": str(t["first_red_run"]),
                            "url": base + str(t["first_red_run"]), "last_green_sha": t.get("last_green_sha"),
                            "suspect_commit_count": t.get("suspect_commit_count"), "failing": failing,
                            "red_streak_runs": t.get("red_streak_runs"), "stale": bool(w.get("stale")),
                            "pinned_historical_ids": w.get("pinned_historical_ids", [])},
                           root_id=rid))
            r = roots.setdefault(rid, {"at": t["first_red_at"], "sha": t["first_red_sha"], "workflows": [],
                                       "pinned": True, "run": t["first_red_run"]})
            r["workflows"].append(name)
            r["pinned"] = r["pinned"] and pinned
        if w.get("stale") and w.get("current") == "RED":
            out.append(_ev(f"RT-STALE-{slug(rshort)}-{slug(name)}-{w['latest']['sha'][:12]}", "note", repo,
                           w["latest"]["at"], w["latest"]["sha"],
                           {"workflow": name, "state": "RED_AT_LAST_OBSERVATION_STALE",
                            "age_days": w.get("latest_age_days"), "action": "replay before asserting HEAD state"}))
        ep = (w.get("red_episodes") or [None])[-1]
        if ep and ep.get("recovery_sha") and everred.valid_sha(ep["recovery_sha"]):
            out.append(_ev(f"RT-VER-{slug(rshort)}-{slug(name)}-{ep['recovery_sha'][:12]}", "verification", repo,
                           ep["recovered_at"], ep["recovery_sha"],
                           {"name": name, "status": "PASS", "run_id": str(ep["recovery_run"]),
                            "url": base + str(ep["recovery_run"]), "recovers_first_red_sha": ep["first_red_sha"],
                            "red_hours": ep.get("red_hours"), "scope": "workflow_conclusion_only"}))
    for rid, r in sorted(roots.items()):
        cause = "PINNED_HISTORICAL_EVIDENCE" if r["pinned"] else "UNKNOWN"
        title = (f"Shared break root: {len(r['workflows'])} workflows red from {r['sha'][:8]}"
                 if len(r["workflows"]) > 1 else f"{r['workflows'][0]} red from {r['sha'][:8]}")
        out.append(_ev(rid, "root_candidate", repo, r["at"], r["sha"],
                       {"title": title, "owner": "UNASSIGNED", "cause": cause,
                        "cause_basis": "workflow hard-codes historical run/artifact ids" if r["pinned"] else None,
                        "applicable_consumers": sorted(r["workflows"]), "url": base + str(r["run"]),
                        "source_schema": SOURCE_SCHEMA, "source_digest": rep.get("digest_sha256")},
                       root_id=rid))
    for e in out:
        everred.validate_event(e)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=pathlib.Path, nargs="+", required=True, help="red_trace.json file(s)")
    ap.add_argument("--ledger", type=pathlib.Path, default=HERE.parent / "data" / "ledger.jsonl")
    ap.add_argument("--apply", action="store_true", help="append new events to the ledger")
    ap.add_argument("--output", type=pathlib.Path, help="write event batch JSON")
    a = ap.parse_args(argv)
    events = []
    for p in a.input:
        events += events_from_report(json.loads(p.read_text(encoding="utf-8")))
    existing = {e["id"] for e in everred.read_ledger(a.ledger)} if a.ledger.exists() else set()
    new = [e for e in events if e["id"] not in existing]
    if a.output:
        a.output.write_text(json.dumps(new, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if a.apply and new:
        everred.append_events_batch(a.ledger, new)
    kinds = {}
    for e in new:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    print(json.dumps({"status": "PASS", "events": len(events), "new": len(new),
                      "already_present": len(events) - len(new), "kinds": kinds, "applied": bool(a.apply and new)},
                     sort_keys=True))


if __name__ == "__main__":
    main()
