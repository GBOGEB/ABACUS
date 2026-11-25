import json,subprocess,sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
repo,S=sys.argv[1],sys.argv[2]
def api(p):
    return json.loads(subprocess.check_output(["gh","api",p],stderr=subprocess.DEVNULL))
wfs=[];page=1
while True:
    d=api(f"repos/GBOGEB/{repo}/actions/workflows?per_page=100&page={page}")
    wfs+=d["workflows"]
    if len(d["workflows"])<100: break
    page+=1
wfs=[w for w in wfs if w["state"]=="active"]
fname=lambda w: w["path"].split("/")[-1]
def one(w):
    try: r=api(f"repos/GBOGEB/{repo}/actions/workflows/{fname(w)}/runs?branch=main&per_page=10&status=completed")
    except Exception as e: return None
    runs=r["workflow_runs"]
    if not runs: return dict(repo=repo,name=w["name"],path=w["path"],cls="NO_MAIN_RUNS")
    cs=[x["conclusion"] for x in runs]; nf=sum(c=="failure" for c in cs); ns=sum(c=="success" for c in cs)
    # Only a success is evidence of green; neutral conclusions (cancelled,
    # skipped, action_required, ...) are ignored, never counted as green.
    if ns==0: cls="EVERRED" if nf else "NO_SUCCESS"
    elif cs[0]=="failure": cls="GREEN_TO_RED"
    elif nf: cls="FLAKY"
    else: cls="GREEN"
    first_red=None
    if cls=="GREEN_TO_RED":
        for x in runs:
            if x["conclusion"]=="success": break
            if x["conclusion"]=="failure": first_red=x
    return dict(repo=repo,name=w["name"],path=w["path"],cls=cls,nfail=nf,n=len(cs),seq="".join("R" if c=="failure" else ("G" if c=="success" else "-") for c in cs),
        last_run=runs[0]["id"],last_sha=runs[0]["head_sha"][:8],last_at=runs[0]["created_at"],
        first_red_sha=(first_red or {}).get("head_sha","")[:8],first_red_run=(first_red or {}).get("id"),first_red_title=(first_red or {}).get("display_title"))
with ThreadPoolExecutor(8) as ex: rows=[x for x in ex.map(one,wfs) if x]
with open(f"{S}/wf_{repo}.json","w") as f:
    json.dump(rows,f,indent=1)
print(repo,len(wfs),"active",Counter(x["cls"] for x in rows))
