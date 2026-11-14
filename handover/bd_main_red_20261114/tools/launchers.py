import yaml,json,os,re,sys,glob
S=sys.argv[1]
out=[]
for repo,root in [("abacus","/home/claude/w2a3/abacus"),("codex","/home/claude/w1c1/codex")]:
    cls={x["path"].split("/")[-1]:x for x in json.load(open(f"{S}/wf_{repo}.json"))}
    for p in sorted(glob.glob(f"{root}/.github/workflows/*.y*ml")):
        f=os.path.basename(p); txt=open(p,encoding="utf-8",errors="replace").read()
        try: d=yaml.safe_load(txt) or {}
        except Exception as e: out.append((repo,f,"YAML_ERROR","","",""));continue
        on=d.get(True,d.get("on")) if isinstance(d,dict) else None
        keys=list(on) if isinstance(on,dict) else ([on] if isinstance(on,str) else (on or []))
        auto=[k for k in keys if k in("schedule","push","pull_request","workflow_run","pull_request_target","repository_dispatch","merge_group")]
        # referenced local paths that don't exist
        refs=set(re.findall(r"(?:python3?|bash|sh|pwsh|cd|-r|pytest)\s+(?:-m\s+)?([A-Za-z0-9_./-]+\.(?:py|sh|ps1|txt)|[A-Za-z0-9_][A-Za-z0-9_.-]*/[A-Za-z0-9_./-]+)",txt))
        missing=[r for r in refs if not r.startswith(("-","$","/","http")) and "${" not in r and not os.path.exists(os.path.join(root,r))]
        c=cls.get(f,{})
        out.append((repo,f,c.get("cls","?"),",".join(auto),c.get("seq",""),";".join(sorted(missing))[:160]))
json.dump(out,open(f"{S}/launchers.json","w"))
from collections import Counter
for repo in ["abacus","codex"]:
    rows=[r for r in out if r[0]==repo]
    print(repo,"workflows",len(rows),Counter(r[2] for r in rows))
    print("  auto-triggered:",sum(1 for r in rows if r[3]),"| with schedule:",sum(1 for r in rows if "schedule" in r[3]))
    print("  auto-triggered AND references missing paths:",sum(1 for r in rows if r[3] and r[5]))
print("\n# auto-triggered, red or never-run, with missing paths")
for r in out:
    if r[3] and r[5] and r[2] in("EVERRED","GREEN_TO_RED","NO_MAIN_RUNS","?","FLAKY"): print("\t".join(r))
