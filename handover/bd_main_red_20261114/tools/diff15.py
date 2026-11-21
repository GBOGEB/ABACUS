import sys
import json,subprocess
from concurrent.futures import ThreadPoolExecutor
with open(sys.argv[1]) as f:
    H=json.load(f)
prev={(x["repo"],x["workflow"]):x for x in H["live_red"]}
RED=("EVERRED","GREEN_TO_RED")
def gh(p):
    o=subprocess.run(["gh","api",p],capture_output=True,text=True); return json.loads(o.stdout) if o.returncode==0 else None
out=[]
for r in ["abacus","codex"]:
    tree=set((subprocess.run(["gh","api",f"repos/GBOGEB/{r}/git/trees/main?recursive=1","--jq",'.tree[]|select(.path|startswith(".github/workflows/"))|.path'],capture_output=True,text=True).stdout).split())
    with open(f"{sys.argv[2]}/wf_{r}.json") as f:
        for x in json.load(f):
            if x["cls"] not in RED: continue
            x["ghost"]=x["path"] not in tree
            out.append(x)
def enrich(x):
    c=gh(f"repos/GBOGEB/{x['repo']}/commits?path={x['path']}&sha=main&per_page=1")
    x["file_edit"]=c[0]["commit"]["committer"]["date"] if c else "?"
    x["file_edit_sha"]=c[0]["sha"][:8] if c else ""
    x["stale"]= x["file_edit"]!="?" and x["file_edit"]>x["last_at"]
    j=gh(f"repos/GBOGEB/{x['repo']}/actions/runs/{x['last_run']}/jobs?per_page=100&page=1")
    x["njobs"]=j["total_count"] if j else -1
    # first red date in window (age floor)
    rr=gh(f"repos/GBOGEB/{x['repo']}/actions/workflows/{x['path'].split('/')[-1]}/runs?branch=main&status=completed&per_page=100&page=1")
    first=None; lastgreen=None
    for run in (rr or {}).get("workflow_runs",[]):
        if run["conclusion"]=="success": lastgreen=run["created_at"]; break
        if run["conclusion"]=="failure": first=run["created_at"]
    x["red_since"]=first; x["last_green"]=lastgreen
    x["red_since_bounded"]= lastgreen is None and len((rr or {}).get("workflow_runs",[]))==100
    return x
with ThreadPoolExecutor(8) as ex: out=list(ex.map(enrich,out))
with open(f"{sys.argv[2]}/reds_now.json","w") as f:
    json.dump(out,f,indent=1)
now={(x["repo"],x["path"].split("/")[-1]):x for x in out}
for k,x in sorted(now.items()):
    p=prev.get(k)
    print(f"{'OPEN' if p else 'NEW ':4} {k[0]:6} {k[1]:42} {x['cls']:12} {x['seq']} last {x['last_at'][:16]} edit {x['file_edit'][:16]} {'STALE' if x['stale'] else ''} {'GHOST' if x['ghost'] else ''} jobs={x['njobs']} since={str(x['red_since'])[:10]} lastgreen={str(x['last_green'])[:10]} root={p['root'] if p else '-'}")
print("\nCLOSED (in ledger, no longer red):")
for k,p in prev.items():
    if k not in now: print("  ",k,p["root"],p["state"])
