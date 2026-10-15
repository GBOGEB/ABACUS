#!/usr/bin/env python3
"""Read-only semantic tuple receipt verifier. NOT a full V2 capsule seal."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

def h(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def check(ledger_bytes: bytes, narrative_bytes: bytes, manifest_bytes: bytes) -> dict:
    s=json.loads(ledger_bytes)
    m=json.loads(manifest_bytes)
    if (s.get("schema")!="ABACUS_CHAT_TUPLE_DELTA_V1" or
        s.get("fidelity")!="SEMANTIC_NOT_VERBATIM" or
        s.get("session_lossless_certified") is not False):
        raise ValueError("Unproven verbatim fidelity")
    if (s["parent"]["pr"]!=2006 or
        s["parent"]["v2_protocol"]!="tools/handover_v2/process_spec.json"):
        raise ValueError("Canonical V2 parent changed")
    for name,data in (("CHAT_TUPLE_LEDGER.json",ledger_bytes),
                      ("GOLDEN_THREAD.md",narrative_bytes)):
        if m["files"].get(name)!=h(data):
            raise ValueError("Manifest byte mismatch: "+name)
    turns=s["tuples"]
    todo=s["todo_records"]
    ids=[x["id"] for x in turns]
    tasks=[x["id"] for x in todo]
    if not turns or not todo or len(set(ids))!=len(ids) or len(set(tasks))!=len(tasks):
        raise ValueError("Missing or duplicate tuple/TODO")
    ancestor=s["parent"]["head_at_last_readback"]
    if len(ancestor)!=40:
        raise ValueError("Unpinned ancestor")
    prev="GENESIS:"+ancestor
    for i,x in enumerate(turns,1):
        if (x["id"]!=f"T{i:02}" or x["raw_user_sha256"] is not None or
            x["raw_assistant_sha256"] is not None or
            x["status"]!="SEMANTIC_SUMMARY" or
            x["evidence_class"]!="CHAT_REPORTED_UNLESS_RECHECKED"):
            raise ValueError("Unverifiable tuple promoted")
        fields={k:v for k,v in x.items() if k!="cumulative_sha256"}
        digest=h(json.dumps(fields,sort_keys=True).encode("utf-8"))
        prev=h((prev+"|"+digest).encode("utf-8"))
        if prev!=x["cumulative_sha256"]:
            raise ValueError("Tuple chain tampered: "+x["id"])
    if prev!=m["tuple_chain_tip_sha256"]:
        raise ValueError("Manifest chain-tip mismatch")
    for item in todo:
        if (not item["source_tuple_ids"] or
            not set(item["source_tuple_ids"]).issubset(ids) or
            item["root_signature"] is not None or
            item["closure_receipt"] is not None or
            item["operational_root_credit"]!="WITHHELD"):
            raise ValueError("Orphan TODO or fabricated root credit")
        if item["state"] not in ("BLOCKED","HOLD","VERIFY","UNKNOWN"):
            raise ValueError("Invalid TODO disposition")
    for key in ("operational_roots_opened","operational_roots_closed",
                "accepted_rex_count","crew_launch_count"):
        if s[key] is not None:
            raise ValueError("UNKNOWN promoted to numeric: "+key)
    for cohort in s["coverage_reference"]:
        if cohort["n"] is not None or cohort["d"] is not None:
            raise ValueError("Historical percentage lacks source-bound obligation counts")
    if len(turns)!=m["tuple_count"] or len(todo)!=m["todo_count"]:
        raise ValueError("Census/manifest mismatch")
    if m.get("certification")!="SEMANTIC_ONLY":
        raise ValueError("Unsupported completeness certification")
    return {"result":"PASS","fidelity":"SEMANTIC_ONLY",
            "tuples":len(turns),"todos":len(todo),
            "operational_bd_opened":None,"operational_bd_closed":None,
            "chain_tip":prev}


def pulse_metrics(ledger: dict, *, head_sha: str, observed_ci: dict) -> dict:
    """Only count verified exact-head terminal CI; operational roots stay unknown.

    observed_ci maps workflow run IDs to {source_sha, conclusion, url}.
    A source-linked instrumented run is not proof of executed Crew workers.
    """
    if len(head_sha) != 40 or any(c not in "0123456789abcdef" for c in head_sha):
        raise ValueError("A complete exact-head SHA is required")
    allowed = {"success", "failure", "cancelled", "skipped"}
    ci = {"success": 0, "failure": 0, "cancelled": 0, "skipped": 0}
    observed = []
    for run_id, item in sorted(observed_ci.items(), key=lambda kv: int(kv[0])):
        if item["source_sha"] != head_sha:
            raise ValueError("CI source SHA mismatch: " + str(run_id))
        if item["conclusion"] not in allowed:
            raise ValueError("Nonterminal run cannot be credited: " + str(run_id))
        if not item["url"].startswith(
            "https://github.com/GBOGEB/ABACUS/actions/runs/"
        ):
            raise ValueError("Untrusted CI URL")
        ci[item["conclusion"]] += 1
        observed.append({"id": int(run_id), **item})
    states = {"BLOCKED": 0, "HOLD": 0, "VERIFY": 0, "UNKNOWN": 0}
    for task in ledger["todo_records"]:
        states[task["state"]] += 1
    if sum(states.values()) != len(ledger["todo_records"]):
        raise ValueError("TODO census is incomplete")
    n = len(observed)
    return {
        "schema": "handover.bd_tuple_pulse.v1",
        "head_sha": head_sha,
        "metric_basis": "EXACT_HEAD_TERMINAL_WORKFLOW_RUN_CONCLUSIONS",
        "workflow_terminal": n,
        "workflow_pass": ci["success"],
        "workflow_fail": ci["failure"],
        "workflow_cancelled": ci["cancelled"],
        "workflow_skipped": ci["skipped"],
        "workflow_pass_pct": round(100 * ci["success"] / n, 4) if n else None,
        "workflow_receipts": observed,
        "tuple_population": len(ledger["tuples"]),
        "todo_population": len(ledger["todo_records"]),
        "todo_state_count": states,
        "todo_closed": None,
        "operational_roots_opened": None,
        "operational_roots_closed": None,
        "crew_launches": None,
        "accepted_rex": None,
        "canonical_coverage": None,
        "changed_line_coverage": None,
        "admission": "HOLD",
    }


def compare_pulses(before: dict, after: dict) -> dict:
    """Compare only same-source-metric instruments and declared populations."""
    if before["schema"] != after["schema"]:
        raise ValueError("Different telemetry schema")
    if before["metric_basis"] != after["metric_basis"]:
        raise ValueError("Different CI metric basis")
    scope_same = (
        before["head_sha"] == after["head_sha"]
        and {x["id"] for x in before["workflow_receipts"]} ==
        {x["id"] for x in after["workflow_receipts"]}
    )
    return {
        "schema": "handover.bd_tuple_pulse_delta.v1",
        "same_exact_head_and_run_set": scope_same,
        "workflow_pass_delta": (
            after["workflow_pass"] - before["workflow_pass"] if scope_same else None
        ),
        "workflow_pass_pp": (
            round(after["workflow_pass_pct"] - before["workflow_pass_pct"], 4)
            if scope_same and before["workflow_pass_pct"] is not None
            and after["workflow_pass_pct"] is not None else None
        ),
        "observed_run_set_growth": (
            len(after["workflow_receipts"]) - len(before["workflow_receipts"])
        ),
        "new_terminal_scope_is_not_coverage_improvement": True,
        "operational_root_closure_delta": None,
        "coverage_delta": None,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--folder",type=Path,default=Path(__file__).resolve().parents[2]/"handover/mip_20261015")
    a=p.parse_args()
    f=a.folder
    print(json.dumps(check((f/"CHAT_TUPLE_LEDGER_v1.json").read_bytes(),
                           (f/"GOLDEN_THREAD_TUPLES_v1.md").read_bytes(),
                           (f/"TUPLE_MANIFEST_v1.json").read_bytes()),
                     sort_keys=True))

if __name__=="__main__":
    main()
