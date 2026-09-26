#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, pathlib, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "triage" / "GM_I_A_COOLPROP_RUNTIME_BRIDGE_P002_v1.json"

def canonical_bytes(value: dict) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")

def main() -> None:
    ap=argparse.ArgumentParser(); ap.add_argument("--receipt", required=True); args=ap.parse_args()
    m=json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert m["schema"]=="abacus.gm_i_a.coolprop_runtime_bridge.v1"
    assert m["pulse_id"]=="GM-I-A-MCLOCK-P002"
    assert m["authority_transfer"] is False
    p=m["provider"]
    url=f"https://raw.githubusercontent.com/GBOGEB/CoolProp/{p['attestation_commit_sha']}/{p['attestation_path']}"
    with urllib.request.urlopen(url, timeout=30) as response:
        raw=response.read()
    digest=hashlib.sha256(raw).hexdigest()
    assert digest==p["attestation_sha256"]
    d=json.loads(raw)
    assert d["pulse_id"]=="GM-I-A-MCLOCK-P002"
    assert d["source_head_sha"]==p["source_head_sha"]
    assert d["source_merge_sha"]==p["source_merge_sha"]
    assert d["workflow"]["run_id"]==p["workflow_run_id"]
    assert d["workflow"]["conclusion"]=="success"
    assert d["heavy"]["conclusion"]=="success"
    assert d["fast"]["conclusion"]=="success"
    assert d["heavy"]["artifact"]["digest"]==p["heavy_artifact_digest"]
    assert d["fast"]["artifact"]["digest"]==p["fast_artifact_digest"]
    assert d["fast"]["build_invoked"] is False
    assert d["fast"]["source_checkout_performed"] is False
    assert d["authority"]["authority_transfer"] is False
    receipt={
      "schema":"abacus.gm_i_a.coolprop_runtime_bridge_receipt.v1",
      "pulse_id":"GM-I-A-MCLOCK-P002",
      "consumer_repo":"GBOGEB/ABACUS",
      "provider_repo":"GBOGEB/CoolProp",
      "provider_source_head_sha":d["source_head_sha"],
      "provider_attestation_commit_sha":p["attestation_commit_sha"],
      "provider_attestation_sha256":digest,
      "provider_workflow_run_id":d["workflow"]["run_id"],
      "runtime_economics":d["runtime_economics"],
      "status":"PASS",
      "authority_transfer":False,
      "engineering_promotion_forbidden":True,
      "return_to":"GBOGEB/pipeline-automation-hub"
    }
    pathlib.Path(args.receipt).write_bytes(canonical_bytes(receipt))
if __name__=="__main__": main()
