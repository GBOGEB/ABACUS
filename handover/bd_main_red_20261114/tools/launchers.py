import yaml,json,os,re,sys,glob
# usage: launchers.py <census_dir> <abacus_checkout> <codex_checkout>
if len(sys.argv)!=4: sys.exit("usage: launchers.py <census_dir> <abacus_checkout> <codex_checkout>")
S=sys.argv[1]
ROOTS=[("abacus",sys.argv[2]),("codex",sys.argv[3])]
for repo,root in ROOTS:
    if not glob.glob(f"{root}/.github/workflows/*.y*ml"):
        sys.exit(f"{repo}: no workflows under {root}/.github/workflows; pass a checkout root")
out=[]
for repo,root in ROOTS:
    with open(f"{S}/wf_{repo}.json", encoding="utf-8") as wf_fp:
        cls={x["path"].split("/")[-1]:x for x in json.load(wf_fp)}
    for p in sorted(glob.glob(f"{root}/.github/workflows/*.y*ml")):
        f=os.path.basename(p)
        with open(p,encoding="utf-8",errors="replace") as wf_txt_fp:
            txt=wf_txt_fp.read()
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
with open(f"{S}/launchers.json","w",encoding="utf-8") as out_fp:
    json.dump(out,out_fp)
from collections import Counter
for repo in ["abacus","codex"]:
    rows=[r for r in out if r[0]==repo]
    print(repo,"workflows",len(rows),Counter(r[2] for r in rows))
    print("  auto-triggered:",sum(1 for r in rows if r[3]),"| with schedule:",sum(1 for r in rows if "schedule" in r[3]))
    print("  auto-triggered AND references missing paths:",sum(1 for r in rows if r[3] and r[5]))
print("\n# auto-triggered, red or never-run, with missing paths")
for r in out:
    if r[3] and r[5] and r[2] in("EVERRED","GREEN_TO_RED","NO_MAIN_RUNS","?","FLAKY"): print("\t".join(r))
