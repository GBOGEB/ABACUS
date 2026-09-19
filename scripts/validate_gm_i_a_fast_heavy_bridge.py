#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
M=ROOT/"triage"/"receipts"/"GM_I_A_FAST_HEAVY_PROVIDER_MANIFEST.json"
R=ROOT/"triage"/"receipts"/"GM_I_A_FAST_HEAVY_PROVIDER_RECEIPT.json"
EXPECTED_M="5cb23495c4950d3052b4f298784462ea679cc402462a9b3f49d33f63331346b7"
EXPECTED_R="8ad81a9862bae0376d0ab755b84f7c63553933d64c2d45976e93a49d8a2a7cef"
EXPECTED_SOURCE="47cc8dced9278d50714ac39ef0a2edab7458c6a0"

def sha256(path: Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    assert sha256(M)==EXPECTED_M
    assert sha256(R)==EXPECTED_R
    m=json.loads(M.read_text())
    r=json.loads(R.read_text())
    assert m["source_sha"]==r["source_sha"]==EXPECTED_SOURCE
    assert m["wheel_sha256"]==r["wheel_sha256"]
    assert m["producer_class"]=="HEAVY"
    assert r["consumer_class"]=="FAST"
    assert m["build_seconds"]>0
    assert r["probe_elapsed_ms"]>0
    assert r["build_invoked"] is False
    assert r["source_checkout_performed"] is False
    assert r["status"]=="PASS" and r["calculations_passed"]>0
    assert m["engineering_promotion"]=="WITHHELD"
    assert r["engineering_promotion"]=="WITHHELD"
    for row in r["calculations"]:
        assert all(math.isfinite(float(row[k])) for k in ("T_K","P_Pa","h_J_kg","rho_kg_m3"))
    build_ms=m["build_seconds"]*1000
    probe_ms=r["probe_elapsed_ms"]
    out={
      "schema":"abacus.gm_i_a_fast_heavy_consumption.v1",
      "status":"PASS",
      "provider_repo":"GBOGEB/CoolProp",
      "provider_source_sha":EXPECTED_SOURCE,
      "provider_manifest_sha256":EXPECTED_M,
      "provider_fast_receipt_sha256":EXPECTED_R,
      "wheel_sha256":m["wheel_sha256"],
      "heavy_build_seconds":m["build_seconds"],
      "fast_probe_elapsed_ms":probe_ms,
      "build_to_probe_ratio":build_ms/probe_ms,
      "fast_calculations_consumed":r["calculations_passed"],
      "authority_scope":"RUNTIME_ECONOMICS_ONLY",
      "authority_transfer":False,
      "formal_credit_delta":0,
      "engineering_promotion_forbidden":True,
      "next_bridge":"MISSIONCONTROL_ATTESTATION"
    }
    print(json.dumps(out,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
