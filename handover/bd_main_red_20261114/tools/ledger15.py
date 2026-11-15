import json,sys
from datetime import datetime,timezone
HD,S,OUT=sys.argv[1:4]
NOW=datetime(2026,11,15,14,30,tzinfo=timezone.utc)
d=lambda s: datetime.fromisoformat(s.replace("Z","+00:00"))
days=lambda s: (NOW-d(s)).days
H=json.load(open(f"{HD}/handover.json"))
reds={(x["repo"],x["path"].split("/")[-1]):x for x in json.load(open(f"{S}/reds_now.json"))}
c08={(r,x["path"].split("/")[-1]):x for r in ["abacus","codex"] for x in json.load(open(f"{HD}/census/wf_{r}_20261108.json"))}
c14={(r,x["path"].split("/")[-1]):x for r in ["abacus","codex"] for x in json.load(open(f"{HD}/census/wf_{r}_20261114.json"))}
RED=("EVERRED","GREEN_TO_RED")
def first_seen(k):
    if k in c08 and c08[k]["cls"] in RED: return "2026-11-08"
    if k in c14 and c14[k]["cls"] in RED: return "2026-11-14"
    return "2026-11-15"
UPD={ # state changes from today's evidence; keyed by workflow
 "bridge-ci.yml":("HOLD","Narrowed: standalone flake8 job now green (Black lanes #2747/#2748/#2750); only 'Full Deployment Test' red, which re-runs Static Analysis internally (re-baseline run 43700724441)","Owner: ratchet vs fix-all (BD-17)"),
 "ci.yml":("READY","mypy: single error DMAIC_V3/core/state.py:403 union-attr (re-baseline 43700728315)","BD-17a: None-guard, one PR"),
 "code-purple-quality-ratchet-proof.yml":("HOLD","Re-baselined 43700730809: still Traceback in 'Verify exact-head and producer wiring'","Owner: behaviour check vs literal restore (BD-23)"),
 "dow-sprint6-cicd.yml":("HOLD","#2704 merged 09:34Z; on main only SPEC job red: 'Step 1: Define [SPEC: ariana_trace_project/ + DOW_test_orchestrator.py never built]'","Owner: spec mode (BD-16)"),
 "spine-gate.yml":("HOLD","Confirmed same root: SPINE_GATE FAIL blocked=1 pca_engine/MATH_SSOT_BINDING.md [private_project]; the cp STAGE_RECEIPT line is noise (|| true)","Owner: reword vs allowlist (BD-18)"),
 "pages.yml":("HOLD","Still builds pre-pin commit: test_security_python39_stays_on_supported_ubuntu2404 fails ('ubuntu-latest' found)","Owner: commit selection (BD-05)"),
}
NEW={
 ("abacus","ci-governance.yml"):dict(root="BD-26a+BD-26b",family="F2 config / generated drift",state="ACTIVE",
   failure="Relapse of burned BD-25. policy: #2724 test_orchestrator_health.py imports yaml on bare setup-python (ModuleNotFoundError). inventory: #2704 left WORKFLOW_RATIONALIZATION.md stale (dow-sprint6 7->8 jobs)",
   next="Owner merge #2762 (BD-26a PyYAML==6.0.3) + #2761 (BD-26b regen); both needed",prs=[2762,2761]),
 ("abacus","validate_docs.yml"):dict(root="BD-27",family="F4 debt gate (changed-file lint)",state="HOLD",
   failure="Changed-file yamllint line-length>80 on SHA-pinned 'uses:' lines in bandit/codeql/reusable-security/semgrep.yml, touched by Dependabot #2683",
   next="Self-clears on next main push not touching those files; recurs on every pin bump. Owner: exempt 'uses:' pin lines from line-length vs wrap",prs=[]),
}
rows=[]
for x in H["live_red"]:
    k=(x["repo"],x["workflow"]); r=reds.get(k)
    row=dict(x); row["status"]="OPEN" if r else "CLOSED"
    if x["workflow"] in UPD: row["state"],row["failure"],row["next"]=UPD[x["workflow"]]
    if x["workflow"]=="release.yml": row["note"]="STALE launcher (zero-job May runs); not dispatched: publishes a release"
    rows.append(row)
for k,v in NEW.items(): rows.append(dict(repo=k[0],workflow=k[1],status="NEW",**v))
rows.append(dict(repo="abacus",workflow="dow-integration-ci-cd.yml",root="GHOST",family="registry",status="CLOSED",state="DONE",
  failure="File deleted in #1375 but GitHub still listed workflow 293888679 as active (stale launcher)",
  next="Disabled 2026-11-15 (PUT .../disable; reversible with /enable). Successor dow-integration.yml green"))
for row in rows:
    r=reds.get((row["repo"],row["workflow"]))
    row["first_seen_in_ledger"]=first_seen((row["repo"],row["workflow"]))
    row["ledger_age_d"]=days(row["first_seen_in_ledger"]+"T00:00:00Z")
    if r:
        row["seq"]=r["seq"]; row["last_run"]=r["last_run"]; row["last_at"]=r["last_at"]
        row["red_since"]=r["red_since"]; row["last_green"]=r["last_green"]
        row["red_age_d"]=days(r["red_since"]) if r["red_since"] else None
        row["red_age_is_floor"]=bool(r["red_since_bounded"] or (r["last_green"] is None))
        row["stale"]=r["stale"]; row["ghost"]=r["ghost"]
order={"NEW":0,"OPEN":1,"CLOSED":2}
rows.sort(key=lambda r:(order[r["status"]],-(r.get("red_age_d") or 0)))
L=dict(schema="bd-main-red-ledger-delta/1.0",as_of=NOW.isoformat().replace("+00:00","Z"),
  previous="handover.json as_of 2026-11-14T17:30:00Z",
  source_main_sha={"GBOGEB/ABACUS":"da5b6b7eef5657004575fa6588e32c556a29bb9f","GBOGEB/CODEX":"e4e28ae"},
  age_rule="red_age_d = now - oldest failure in the latest unbroken red streak (last 100 completed main runs). red_age_is_floor=true when no green exists in that window, so the true age is at least this. ledger_age_d = now - first census that listed it red (2026-11-08 / 2026-11-14 / 2026-11-15).",
  rebaseline="12 workflow_dispatch on main at 2026-11-15T09:44Z (all real failures, none zero-job); no merge after that touched their files",
  counts=dict(open=sum(r["status"]=="OPEN" for r in rows),new=sum(r["status"]=="NEW" for r in rows),closed=sum(r["status"]=="CLOSED" for r in rows)),
  live_red_now=sum(r["status"] in("OPEN","NEW") for r in rows),
  prs_opened=[{"pr":2761,"root":"BD-26b"},{"pr":2762,"root":"BD-26a"}],
  rows=rows)
json.dump(L,open(OUT,"w"),indent=1)
print(L["counts"],"live",L["live_red_now"])
for r in rows: print(f'{r["status"]:6} {r["repo"]:6} {r["workflow"]:40} {r["root"]:14} {r["state"]:7} red_age={r.get("red_age_d")}{"+" if r.get("red_age_is_floor") else ""}d ledger_age={r["ledger_age_d"]}d')
