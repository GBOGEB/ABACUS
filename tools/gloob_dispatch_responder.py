#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAPS = ROOT / "gloob_dispatch" / "capabilities.json"


def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def dump(path, value):
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
def digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
def fetch_json(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def validate(ticket, envelope, capabilities, repo):
    errors = []
    if ticket.get("schema") != "gloob-dispatch-ticket/0.1": errors.append("TICKET_SCHEMA_MISMATCH")
    if envelope.get("schema") != "gloob-dispatch-envelope/0.1": errors.append("ENVELOPE_SCHEMA_MISMATCH")
    unsigned = dict(envelope); claimed = unsigned.pop("envelope_digest", None)
    if not claimed or claimed != digest(unsigned): errors.append("ENVELOPE_DIGEST_MISMATCH")
    for key in ("dispatch_id", "route_id", "assignment_digest", "target_repo", "crew"):
        if ticket.get("expected_" + key) != envelope.get(key): errors.append("EXPECTED_" + key.upper() + "_MISMATCH")
    if ticket.get("expected_envelope_digest") != claimed: errors.append("EXPECTED_ENVELOPE_DIGEST_MISMATCH")
    if envelope.get("target_repo") != repo: errors.append("TARGET_REPO_MISMATCH")
    cap = capabilities.get("capabilities", {}).get(envelope.get("crew"), {})
    if not cap.get("eligible"): errors.append("CREW_NOT_ELIGIBLE")
    if cap.get("authority") != "DOW_POINTER_ONLY": errors.append("AUTHORITY_BOUNDARY_MISMATCH")
    return errors


def process(ticket_path, source_sha, run_id, repo):
    ticket = load(ticket_path); envelope = fetch_json(ticket["dispatch_url"]); caps = load(CAPS)
    dispatch_id = envelope.get("dispatch_id", ticket.get("expected_dispatch_id", "UNKNOWN"))
    accepted_path = ROOT / "gloob_dispatch" / "accepted" / f"{dispatch_id}.json"
    if accepted_path.exists(): raise SystemExit("REPLAY_REJECTED: dispatch already accepted")
    errors = validate(ticket, envelope, caps, repo)
    if errors: raise SystemExit("DISPATCH_REJECTED: " + ",".join(errors))
    if len(source_sha) != 40 or any(c not in "0123456789abcdef" for c in source_sha): raise SystemExit("INVALID_SOURCE_SHA")
    outdir = ROOT / "gloob_dispatch" / "outbox" / dispatch_id
    ack = {
      "schema":"gloob-dispatch-ack/0.1", "dispatch_id":dispatch_id, "route_id":envelope["route_id"],
      "assignment_digest":envelope["assignment_digest"], "repo":repo, "crew":envelope["crew"], "state":"ACCEPTED",
      "source_commit":source_sha, "run_id":str(run_id), "receiver_disposition":"ACCEPT_POINTER_ONLY", "control_credit":False
    }
    ret = {
      "schema":"gloob-causal-return/0.1", "route_id":envelope["route_id"], "assignment_digest":envelope["assignment_digest"],
      "repo":repo, "crew":envelope["crew"], "outcome":"RESOLVED",
      "evidence":{"source_commit":source_sha,"runner_commit":source_sha,"run_id":str(run_id),"steps":4,"conclusion":"success"},
      "dispatch":{"dispatch_id":dispatch_id,"envelope_digest":envelope["envelope_digest"],"receiver_disposition":"ACCEPT_POINTER_ONLY"},
      "control_credit":False,"engineering_acceptance_credit":False,"commercial_credit":False
    }
    ledger = {
      "schema":"gloob-dispatch-acceptance-ledger/0.1", "dispatch_id":dispatch_id, "route_id":envelope["route_id"],
      "assignment_digest":envelope["assignment_digest"], "source_commit":source_sha, "run_id":str(run_id),
      "state":"RETURN_EMITTED", "authority":"DOW_POINTER_ONLY", "control_credit":False,
      "engineering_acceptance_credit":False,"commercial_credit":False
    }
    dump(outdir / "delivery-ack.json", ack); dump(outdir / "gloob-causal-return.json", ret); dump(accepted_path, ledger)
    print(json.dumps({"dispatch_id":dispatch_id,"route_id":envelope["route_id"],"state":"RETURN_EMITTED","source_commit":source_sha,"run_id":str(run_id)}, sort_keys=True))


def self_test():
    env={"schema":"gloob-dispatch-envelope/0.1","dispatch_id":"D","route_id":"R","assignment_digest":"A","target_repo":"GBOGEB/ABACUS","crew":"FEDERATION_AMBASSADOR","transport":{"mode":"IMMUTABLE_GLOOB_POINTER"}}
    env["envelope_digest"]=digest(env)
    ticket={"schema":"gloob-dispatch-ticket/0.1", **{"expected_"+k:env[k] for k in ("dispatch_id","route_id","assignment_digest","target_repo","crew")}, "expected_envelope_digest":env["envelope_digest"]}
    assert validate(ticket,env,load(CAPS),"GBOGEB/ABACUS")==[]
    bad=dict(env); bad["crew"]="UNKNOWN"
    assert "ENVELOPE_DIGEST_MISMATCH" in validate(ticket,bad,load(CAPS),"GBOGEB/ABACUS")
    print("ABACUS Gloob dispatch responder self-test PASS")


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("ticket",nargs="?"); ap.add_argument("--self-test",action="store_true"); a=ap.parse_args()
    if a.self_test: return self_test()
    if not a.ticket: raise SystemExit("ticket required")
    process(a.ticket,os.environ.get("GITHUB_SHA",""),os.environ.get("GITHUB_RUN_ID",""),os.environ.get("GITHUB_REPOSITORY",""))
if __name__=="__main__": main()
