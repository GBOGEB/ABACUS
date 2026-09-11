#!/usr/bin/env python3
import datetime as dt,json,subprocess
K=["CG","RR","CR","SR","DR","PB","FE","QH","HK","BG","KR","EX","WD"]
def git(*a): return subprocess.check_output(["git",*a],text=True).strip()
def A(s="UNKNOWN",c="UNKNOWN",e="UNKNOWN",r="self",d=None):
 x={"state":s,"confidence":c,"evidence_class":e,"observed_at":dt.datetime.now(dt.timezone.utc).isoformat(),"source_ref":r};
 if d:x["detail"]=d
 return x
sha=git("rev-parse","HEAD"); D={k:A() for k in K}
D["CG"]=A("AMBER","HIGH","CANONICAL_SOURCE","architecture/w109/W109_MESH_EXECUTION_TAXONOMY_3PC_MIP.yaml","consume three repo vectors and select blocker")
D["RR"]=A("GREEN","HIGH","RUNTIME_RECEIPT",sha,"DOW emitter executed")
D["EX"]=A("GREEN","HIGH","RUNTIME_RECEIPT",sha,"emitter executed >0 steps")
D["DR"]=A("BLOCKED","HIGH","CANONICAL_SOURCE","architecture/w109/W109_MESH_EXECUTION_TAXONOMY_3PC_MIP.yaml","CODEX and cryoplant vectors required")
D["BG"]=A("BLOCKED","HIGH","CANONICAL_SOURCE","architecture/w109/W109_MESH_EXECUTION_TAXONOMY_3PC_MIP.yaml","three repo vector set incomplete")
D["WD"]=A("DEFER","HIGH","CANONICAL_SOURCE","architecture/w109/W109_MESH_EXECUTION_TAXONOMY_3PC_MIP.yaml","wait for vector set")
out={"schema_version":"1.0","repo":"GBOGEB/ABACUS","source_sha":sha,"freshness_timestamp":dt.datetime.now(dt.timezone.utc).isoformat(),"producer":"emit_mesh_status.py","dimensions":D,"next_action":"consume all three exact-SHA vectors and select BG/next-CG","blocking_atom":"three_repo_vector_set_incomplete"}
assert set(D)==set(K)
open("mesh-status.json","w").write(json.dumps(out,indent=2,sort_keys=True)+"\n")
print(f"PASS emitted {len(D)} dimensions for GBOGEB/ABACUS at {sha}")
