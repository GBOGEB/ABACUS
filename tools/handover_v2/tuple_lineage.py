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
