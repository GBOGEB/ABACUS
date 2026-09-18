#!/usr/bin/env python3
"""Independent DOW recomputation of QPS W285 federation depth."""
from __future__ import annotations
import hashlib, json, math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DEPTH=ROOT/"federation/w285/source/QPS_W285_FEDERATION_FUNCTION_DEPTH_v0.1.json"
TOPO=ROOT/"federation/w285/source/QPS_REPO_FUNCTION_TOPOLOGY_v1.yaml"
EXPECTED_DEPTH="691680cdf11289142b402a0ae02c95d46a246473"
EXPECTED_TOPO="df0ee845697578cd644691b81eafb2465249d772"

def git_blob(path):
    b=path.read_bytes()
    return hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest()

def current_use(text):
    out={}; fn=None; inside=False
    for line in text.splitlines():
        if line.startswith("  - repo:"):
            fn=None; inside=False
        elif line.startswith("    function:"):
            fn=line.split(":",1)[1].strip(); inside=False
            if fn!="NONE": out.setdefault(fn,[])
        elif line=="    current_use:":
            inside=fn in out
        elif inside and line.startswith("      - "):
            out[fn].append(line[8:].strip())
        elif inside and line.startswith("    ") and not line.startswith("      "):
            inside=False
    return out

def recompute():
    assert git_blob(DEPTH)==EXPECTED_DEPTH
    assert git_blob(TOPO)==EXPECTED_TOPO
    d=json.loads(DEPTH.read_text())
    uses=current_use(TOPO.read_text())
    per=[]; cred=den=0
    for f in d["covered_functions"]:
        atoms=f["atoms"]
        assert [a["text"] for a in atoms]==uses[f["function"]]
        n=sum(bool(a["credited"]) for a in atoms); m=len(atoms)
        assert n==f["numerator"] and m==f["denominator"]
        per.append(n/m); cred+=n; den+=m
    D=sum(per)/len(per); pooled=cred/den
    B=len(d["covered_functions"])/(len(d["covered_functions"])+len(d["uncovered_functions"]))
    PEN=B*D
    assert math.isclose(B,1/3,abs_tol=1e-12)
    assert math.isclose(D,0.6,abs_tol=1e-12)
    assert math.isclose(pooled,9/16,abs_tol=1e-12)
    assert math.isclose(PEN,0.2,abs_tol=1e-12)
    return {"status":"PASS_INDEPENDENT_RECOMPUTE","B":B,"D_equal_function":D,"pooled_atom_ratio":pooled,"PEN":PEN,"credited_atoms":cred,"atom_denominator":den}

if __name__=="__main__":
    print(json.dumps(recompute(),sort_keys=True))
