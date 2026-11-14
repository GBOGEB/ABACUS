import json,subprocess,re,sys
from concurrent.futures import ThreadPoolExecutor
S=sys.argv[1]
def api(p,raw=False):
    o=subprocess.run(["gh","api",p],capture_output=True)
    if o.returncode: return None
    return o.stdout.decode("utf-8","replace") if raw else json.loads(o.stdout)
reds=[x for r in ["abacus","codex"] for x in json.load(open(f"{S}/wf_{r}.json")) if x["cls"] in("EVERRED","GREEN_TO_RED")]
PAT=re.compile(r"(##\[error\].*|.*\b(Error|ERROR|error:|Traceback|FAILED|ModuleNotFoundError|No such file|not found|exit code \d+|Permission|denied|403|404|Invalid workflow|startup_failure)\b.*)")
def one(x):
    run=api(f"repos/GBOGEB/{x['repo']}/actions/runs/{x['last_run']}")
    jobs=api(f"repos/GBOGEB/{x['repo']}/actions/runs/{x['last_run']}/jobs?per_page=100") or {"jobs":[]}
    fj=[j for j in jobs["jobs"] if j["conclusion"]=="failure"]
    x["n_jobs"]=len(jobs["jobs"]); x["n_failed_jobs"]=len(fj)
    x["failed"]=[]
    for j in fj[:3]:
        steps=[s["name"] for s in j.get("steps",[]) if s["conclusion"]=="failure"]
        log=api(f"repos/GBOGEB/{x['repo']}/actions/jobs/{j['id']}/logs",raw=True) or ""
        lines=[re.sub(r"^\S+Z ","",l) for l in log.splitlines()]
        hits=[l.strip()[:220] for l in lines if PAT.search(l)]
        x["failed"].append(dict(job=j["name"],steps=steps,err=hits[-6:]))
    if not jobs["jobs"]:
        x["failed"].append(dict(job="<none>",steps=[],err=[f"no jobs; run conclusion={run and run['conclusion']}"]))
    return x
with ThreadPoolExecutor(6) as ex: out=list(ex.map(one,reds))
json.dump(out,open(f"{S}/red_sig.json","w"),indent=1)
for x in out:
    print(f"\n### {x['repo']}/{x['path'].split('/')[-1]} [{x['cls']} {x['seq']}] jobs {x['n_failed_jobs']}/{x['n_jobs']} failed")
    for f in x["failed"]:
        print("  job:",f["job"]," steps:",f["steps"])
        for e in f["err"][-4:]: print("    ",e)
