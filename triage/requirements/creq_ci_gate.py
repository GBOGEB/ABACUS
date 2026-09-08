#!/usr/bin/env python3
import argparse, hashlib, json, subprocess, sys
from datetime import date
from pathlib import Path

EXPECTED_REGISTRY_SHA256 = "541fbff68b298427ae8fc560efede6348ed7a8a27712b9e3c762225eb2de2eaa"
REQUIRED_ROLES = {"local_repo_owner","parent_cADR_or_cOCD_authority","global_CReq_authority"}

def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def repo_ns(repo): return repo.split("/")[-1].split("-")[0].upper()
def fail(msg): print("CReq federation CI: FAIL - " + msg); raise SystemExit(1)

def check_approval(item, root):
    if item.get("approval_state") != "APPROVED": return False
    receipt_path = item.get("approval_receipt")
    if not receipt_path: fail(item["id"] + ": approved override missing approval_receipt")
    p = root / receipt_path
    if not p.exists(): fail(item["id"] + ": approval receipt not found")
    receipt = load(p)
    if receipt.get("approval_state") != "APPROVED" and receipt.get("status") != "APPROVED": fail(item["id"] + ": approval receipt not approved")
    roles = {x.get("role") for x in receipt.get("approval_chain", item.get("approval_chain", [])) if x.get("state") == "APPROVED"}
    if not REQUIRED_ROLES.issubset(roles): fail(item["id"] + ": approval roles incomplete")
    expires = receipt.get("expires_at") or item.get("expires_at")
    if expires and date.fromisoformat(expires[:10]) < date.today(): fail(item["id"] + ": approval expired")
    return True

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--registry",required=True); ap.add_argument("--overlay",required=True); ap.add_argument("--resolver",required=True); ap.add_argument("--out",required=True); a=ap.parse_args()
    root=Path.cwd(); raw=Path(a.registry).read_bytes(); digest=hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_REGISTRY_SHA256: fail("global registry digest drift: " + digest)
    reg=load(a.registry); overlay=load(a.overlay); globals_={x["id"] for x in reg["requirements"]}; ns=repo_ns(overlay["repo"]); prefix=f"CReq_{ns}_"
    if len(globals_) != len(reg["requirements"]): fail("duplicate global IDs")
    for item in overlay.get("requirements",[]):
        if not item["id"].startswith(prefix): fail(item["id"] + ": local namespace shadowing/foreign prefix")
        mode=item.get("mode","addition"); parent=item.get("overrides") or item.get("parent_global_requirement")
        if not parent or parent not in globals_: fail(item["id"] + ": missing/unknown global parent")
        if mode == "override": check_approval(item, root)
        elif mode != "addition": fail(item["id"] + ": unknown mode")
    out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run([sys.executable,a.resolver,"--global-registry",a.registry,"--overlay",a.overlay,"--out",a.out],check=True)
    receipt=load(out); rows=receipt["effective_requirements"]; ids={r["effective_id"] for r in rows}
    for item in overlay.get("requirements",[]):
        mode=item.get("mode","addition"); parent=item.get("overrides") or item.get("parent_global_requirement"); approved=(mode=="override" and item.get("approval_state")=="APPROVED")
        if mode=="addition" and not ({item["id"],parent} <= ids): fail(item["id"] + ": addition precedence divergence")
        if mode=="override" and approved and (item["id"] not in ids or parent in ids): fail(item["id"] + ": approved override precedence divergence")
        if mode=="override" and not approved and (parent not in ids or item["id"] in ids): fail(item["id"] + ": fallback precedence divergence")
    gate={"status":"PASS","repo":overlay["repo"],"global_registry_sha256":digest,"global_count":len(globals_),"effective_count":len(ids),"checked_local_count":len(overlay.get("requirements",[])),"checks":["registry_digest","namespace_shadowing","approval_validity","approval_expiry","resolver_execution","precedence"]}
    Path(str(out).replace("RESOLUTION","GATE")).write_text(json.dumps(gate,indent=2)+"\n")
    print("CReq federation CI: PASS"); print(json.dumps(gate,sort_keys=True))
if __name__=="__main__": main()
