#!/usr/bin/env python3
"""CODE PURPLE: exact-SHA, report-only baseline/security/coverage/LDAB census."""
from __future__ import annotations
import collections, datetime, hashlib, html, json, os, pathlib, re, subprocess, sys, tempfile, urllib.request, xml.etree.ElementTree as ET

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/"bd_receipts"/"extended_bd"
OUT.mkdir(parents=True,exist_ok=True)
BASE_SHA="dfd56456bf2b7ce14d48fe136b0800cb6c44f6c9"
def digest(raw): return hashlib.sha256(raw).hexdigest()
def run(cmd,cwd,tag,timeout=150):
    try:
        p=subprocess.run(cmd,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
        rc=p.returncode; raw=p.stdout
    except subprocess.TimeoutExpired as e:
        rc=124;raw=(e.stdout or b"")+b"\nTIMEOUT"
    dest=OUT/(tag+".log");dest.write_bytes(raw)
    return {"command":cmd,"exit_code":rc,"log":dest.name,"sha256":digest(raw),"bytes":len(raw)}
def coverage_info(root,tag):
    out=run([sys.executable,"-m","coverage","run","--data-file",str(OUT/(tag+".coverage")),"--source=ci.governance.pr_feedback_gate","-m","unittest","ci.governance.tests.test_pr_feedback_gate"],root,tag+"_tests")
    x=run([sys.executable,"-m","coverage","xml","--data-file",str(OUT/(tag+".coverage")),"--fail-under=0","-o",str(OUT/(tag+"_coverage.xml"))],root,tag+"_xml")
    p=OUT/(tag+"_coverage.xml")
    info={"test":out,"xml_command":x,"measured":False,"scope":"ci.governance.pr_feedback_gate_only"}
    if p.is_file() and x["exit_code"]==0:
        tree=ET.parse(p).getroot()
        info.update({"measured":int(tree.get("lines-valid","0"))>0,"lines_valid":int(tree.get("lines-valid","0")),"lines_covered":int(tree.get("lines-covered","0")),"line_rate":float(tree.get("line-rate","0"))})
        files=[]
        for elem in tree.findall(".//class"):
            denom=int(elem.get("lines-valid","0")) if elem.get("lines-valid") else len(elem.findall("./lines/line"))
            hit=sum(int(line.get("hits","0"))>0 for line in elem.findall("./lines/line"))
            files.append({"path":elem.get("filename"),"covered":hit,"total":denom,"missing":max(0,denom-hit)})
        info["files"]=sorted(files,key=lambda x:x["missing"],reverse=True)[:15]
        info["xml_sha256"]=digest(p.read_bytes())
    if not info["measured"]:
        info["reason"]="coverage_xml_absent_or_zero_denominator"
        info["test_exit"]=out["exit_code"]
        info["test_tail"]=(OUT/(tag+"_tests.log")).read_text(errors="replace")[-1800:]
        info["xml_tail"]=(OUT/(tag+"_xml.log")).read_text(errors="replace")[-800:]
        print(json.dumps({"coverage_failure":tag,"details":info},sort_keys=True))
    return info
def security(root,tag):
    cmds={"bandit":[sys.executable,"-m","bandit","-q","-r","ci/governance","-f","json"],"safety":[sys.executable,"-m","safety","check","--json"],"pip_audit":[sys.executable,"-m","pip_audit","--format","json"]}
    results={}
    for name,cmd in cmds.items():
        result=run(cmd,root,tag+"_"+name,timeout=120)
        body=(OUT/(tag+"_"+name+".log")).read_text(errors="replace")
        # Some scanners prefix JSON with warnings; never equate parse failure with zero findings.
        if name=="bandit" and "{" in body: body=body[body.find("{"): ]
        try:
            data=json.loads(body)
            if name=="bandit":
                result["finding_count"]=len(data.get("results",[]))
                result["findings"]=sorted([{"rule":v.get("test_id"),"path":str(v.get("filename","")).split("/ci/governance/")[-1],"line":v.get("line_number"),"severity":v.get("issue_severity")} for v in data.get("results",[])],key=lambda x:(str(x["rule"]),str(x["path"]),int(x["line"] or 0)))
            elif name=="pip_audit":result["finding_count"]=sum(len(d.get("vulns",[])) for d in data.get("dependencies",[]))
            else:result["finding_count"]=len(data.get("vulnerabilities",[])) if isinstance(data,dict) else None
        except (ValueError,TypeError,AttributeError):
            result["finding_count"]=None
            result["parse_status"]="unknown_or_tool_error"
        results[name]=result
    return results
def ldab_runs():
    token=os.getenv("GITHUB_TOKEN","")
    if not token:return {"status":"unavailable","reason":"GITHUB_TOKEN absent"}
    url="https://api.github.com/repos/GBOGEB/ABACUS/actions/runs?per_page=100"
    req=urllib.request.Request(url,headers={"Authorization":"Bearer "+token,"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"})
    try:
        with urllib.request.urlopen(req,timeout=15) as response:data=json.load(response)
    except Exception as exc:return {"status":"unavailable","reason":type(exc).__name__}
    runs=data.get("workflow_runs",[])
    classified=[]
    for run_ in runs:
        reason=run_.get("conclusion") or run_.get("status")
        if reason not in ("failure","cancelled","timed_out","action_required"):continue
        classified.append({"name":run_.get("name"),"run_id":run_.get("id"),"sha":run_.get("head_sha"),"status":reason,"created_at":run_.get("created_at")})
    counts=collections.Counter((r["name"],r["status"]) for r in classified)
    return {"status":"observed","sample_size":len(runs),"failed_or_cancelled":len(classified),"signature_class":"workflow_status_only_not_traceback","by_workflow":[{"workflow":k[0],"status":k[1],"count":v} for k,v in counts.most_common()],"runs":classified[:40]}
def table(rows):
    return "".join("<tr>"+ "".join("<td>"+html.escape(str(v))+"</td>" for v in row)+"</tr>" for row in rows)
def main():
    head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    baseline=pathlib.Path(tempfile.mkdtemp(prefix="purple-main-"))
    prep=run(["git","worktree","add","--detach",str(baseline),BASE_SHA],ROOT,"baseline_checkout")
    result={"schema":"code-purple-bd-census:v1","source_sha":head,"main_sha":BASE_SHA,"classification":"REPORT_ONLY_NOT_ADMISSION","checkout":prep,"started_utc":datetime.datetime.now(datetime.timezone.utc).isoformat()}
    if prep["exit_code"]==0:
        try:
            result["main"]={"coverage":coverage_info(baseline,"main"),"security":security(baseline,"main")}
        finally:run(["git","worktree","remove","--force",str(baseline)],ROOT,"baseline_remove")
    result["repair"]={"coverage":coverage_info(ROOT,"repair"),"security":security(ROOT,"repair")}
    result["ldab"]=ldab_runs()
    result["security_delta"]={}
    for scanner in ("bandit","pip_audit","safety"):
        old=result.get("main",{}).get("security",{}).get(scanner,{})
        new=result["repair"]["security"].get(scanner,{})
        if scanner=="bandit" and "findings" in old and "findings" in new:
            identify=lambda f:(f["rule"],f["path"])
            a={identify(f) for f in old["findings"]};b={identify(f) for f in new["findings"]}
            result["security_delta"][scanner]={"unchanged":len(a&b),"new":len(b-a),"removed":len(a-b)}
        else:result["security_delta"][scanner]={"status":"UNKNOWN","reason":"unparsed_or_unpinned_dependency_inventory"}
    result["coverage_delta"]=None
    m=result.get("main",{}).get("coverage",{});r=result["repair"]["coverage"]
    if m.get("measured") and r.get("measured") and m.get("scope")==r.get("scope") and m.get("lines_valid")==r.get("lines_valid"):
        result["coverage_delta"]=round(100*(r["line_rate"]-m["line_rate"]),3)
    else:result["coverage_delta_reason"]="denominator_or_scope_mismatch"
    result["finished_utc"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
    output=OUT/"census.json";output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    def status(n):return "GREEN" if n["exit_code"]==0 else ("ORANGE" if n["exit_code"] in (124,127) else "RED")
    items=[("Main Python gate",result.get("main",{}).get("coverage",{}).get("test",{})),("Branch Python gate",result["repair"]["coverage"]["test"])]
    rows=[(name,status(v) if v else "ORANGE",v.get("exit_code","unknown")) for name,v in items]
    for root in ("main","repair"):
        for tool,record in result.get(root,{}).get("security",{}).items():rows.append((root+" "+tool,status(record),record.get("finding_count","unknown")))
    document="""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>CODE PURPLE BD | exact-head evidence</title><style>body{font:16px system-ui;background:#101827;color:#e8edf5;max-width:1100px;margin:3rem auto;padding:0 1.5rem}table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #425067;padding:.8rem;text-align:left}h1{font-size:2.1rem}code{overflow-wrap:anywhere;color:#b9cafd}.warning{color:#ffba68}.red{color:#ff7f92}.green{color:#65dfb2}article{background:#1b2638;border:1px solid #3c4a60;border-radius:14px;padding:1.2rem;margin:1rem 0}</style><h1>CODE PURPLE | Measured BD</h1><p class="warning">REPORT ONLY · NO ADMISSION CREDIT · GOVERNANCE HOLD</p>"""
    document+="<article><h2>Exact identity</h2><p>Recovery: <code>"+html.escape(head)+"</code></p><p>Main: <code>"+BASE_SHA+"</code></p></article>"
    document+="<article><h2>Root execution census</h2><table><tr><th>Lane</th><th>Outcome</th><th>Exit / findings</th></tr>"+table(rows)+"</table></article>"
    document+="<article><h2>Coverage</h2><p>Baseline: "+str(m.get("lines_covered","?"))+"/"+str(m.get("lines_valid","?"))+" measured lines · Repair: "+str(r.get("lines_covered","?"))+"/"+str(r.get("lines_valid","?"))+"</p><p>Percentage-point change: "+str(result["coverage_delta"])+"</p><h3>Missing-line hotspots (repair)</h3><table>"+table([(f["path"],f["missing"],f["total"]) for f in r.get("files",[])])+"</table></article>"
    document+="<article><h2>LDAB runner signal census</h2><p>Scope: recent GitHub workflow status events; NOT full error-signature extraction.</p><table>"+table([(x["workflow"],x["status"],x["count"]) for x in result["ldab"].get("by_workflow",[])])+"</table></article>"
    document+="<p>Static HTML backed by census.json with SHA-256 file receipts. Security checks report measurement only, not vulnerability disposition.</p></html>"
    (OUT/"index.html").write_text(document)
    manifest={p.name:{"bytes":p.stat().st_size,"sha256":digest(p.read_bytes())} for p in OUT.iterdir() if p.is_file()}
    (OUT/"manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"head":head,"main":BASE_SHA,"coverage":{k:result.get(k,{}).get("coverage",{}).get("line_rate") for k in ("main","repair")},"delta_pp":result["coverage_delta"],"security":{k:{t:v.get("finding_count") for t,v in result.get(k,{}).get("security",{}).items()} for k in ("main","repair")},"ldab_events":result["ldab"].get("failed_or_cancelled"),"security_delta":result["security_delta"],"manifest":manifest},sort_keys=True))
    return 0
if __name__=="__main__":raise SystemExit(main())
