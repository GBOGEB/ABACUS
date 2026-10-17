"""CBD! workflow manifestation -> candidate family / disjoint repair waves.

Observational only. Workflow names are *symptoms*, never causal root proof.
No runner launch, security waiver, authoritative BD mutation or main admission.
"""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

FAMILIES={
    "CI Workflow Governance":("GOVERNANCE_POLICY","ci/governance/","P0"),
    "a10-guard":("A10_SECURITY_REVIEW","ci/governance/","P0"),
    "Bandit Disjoint Census":("BANDIT_CENSUS","tools/everred_v3/","P0"),
    "CI/CD Test Suite":("INTEGRATED_TEST_SUITE","tests/","P1"),
    "ABACUS v032 - CI/CD Pipeline":("LEGACY_PIPELINE","ci/","P1"),
    "CI - ABACUS Matrix":("MATRIX_COMPATIBILITY","DMAIC_V3/","P1"),
    "Validate Docs (Markdown/YAML/JSON)":("DOCS_LINT","docs/","P2"),
    "EVERRED V3 Governed Control Plane":("EVERRED_CONTROL","tools/everred_v3/","P1"),
    "DOW + Recursive DMAIC - Enhanced CI":("DOW_TESTS","tests/","P1"),
    "DMAIC V3 Test Suite - Continuous Integration":("DMAIC_TESTS","DMAIC_V3/tests/","P1"),
    "DMAIC V3 Enterprise CI":("ENTERPRISE_MATRIX","DMAIC_V3/","P1"),
}
P0={"GOVERNANCE_POLICY","A10_SECURITY_REVIEW","BANDIT_CENSUS"}
def sha256(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()
def validate(d):
    if d.get("schema")!="cbd.pr_workflow_observations.v1" or d.get("repository")!="GBOGEB/ABACUS":
        raise ValueError("source schema or repository")
    if d.get("authority")!={"security_waiver":False,"authority_transfer":False,"merge_admission":"HOLD","dispatch":"STAGED_NOT_LAUNCHED"}:
        raise ValueError("authority")
    rows=d.get("observations")
    if not isinstance(rows,list) or not rows: raise ValueError("empty observations")
    seen=set()
    for r in rows:
        if type(r.get("pr")) is not int or r["pr"]<=0 or not isinstance(r.get("sha"),str) or len(r["sha"])!=40 or any(c not in "0123456789abcdef" for c in r["sha"]):
            raise ValueError("invalid source identity")
        if type(r.get("run_id")) is not int or r["run_id"]<=0 or "attempt" not in r or (r["attempt"] is not None and (type(r["attempt"]) is not int or r["attempt"]<=0)):
            raise ValueError("invalid run identity")
        if not isinstance(r.get("workflow"),str) or not r["workflow"].strip():raise ValueError("workflow")
        if r.get("conclusion") not in ("success","failure","cancelled",None):raise ValueError("conclusion")
        if r.get("url")!=f'https://github.com/GBOGEB/ABACUS/actions/runs/{r["run_id"]}':
            raise ValueError("source URL")
        key=(r["run_id"],r["attempt"])
        if key in seen:raise ValueError("duplicate run attempt")
        seen.add(key)
    return d
def produce(d):
    validate(d)
    families=defaultdict(lambda:{"prs":set(),"run_attempts":[],"first_red_verified":0})
    counts={"success":0,"failure":0,"cancelled":0,"nonterminal":0}
    prs=set()
    for r in d["observations"]:
        prs.add(r["pr"])
        result=r["conclusion"] or "nonterminal"
        counts[result]+=1
        if result!="failure":continue
        family,path,priority=FAMILIES.get(r["workflow"],("UNCLASSIFIED_WORKFLOW","UNOWNED","P1"))
        o=families[family];o["prs"].add(r["pr"]);o["run_attempts"].append({"pr":r["pr"],"sha":r["sha"],"run_id":r["run_id"],"attempt":r["attempt"],"workflow":r["workflow"],"url":r["url"]})
    ledger=[]
    for family,dv in families.items():
        path,priority=next(((p,s) for w,(f,p,s) in FAMILIES.items() if f==family),("UNOWNED","P1"))
        ledger.append({"candidate_family":family,"priority":priority,"candidate_path_lease":path,"unique_prs_affected":len(dv["prs"]),"failed_run_attempts":len(dv["run_attempts"]),"root_confirmed":False,"first_red_confirmed":False,"repair_committed":False,"independent_admission":False,"prs":sorted(dv["prs"]),"evidence":sorted(dv["run_attempts"],key=lambda x:(x["pr"],x["run_id"],x["attempt"]))})
    ledger.sort(key=lambda x:(x["priority"]!="P0",-x["unique_prs_affected"],-x["failed_run_attempts"],x["candidate_family"]))
    waves=[]
    leases=[]
    for f in ledger:
        if f["candidate_family"]=="UNCLASSIFIED_WORKFLOW":kind="READER"
        elif f["priority"]=="P0":kind="OWNER_SECURITY_OR_POLICY"
        else:kind="SOURCE_DIAGNOSTIC"
        path=f["candidate_path_lease"]
        collision=path!="UNOWNED" and any(path.startswith(a) or a.startswith(path) for a in leases)
        status="SERIALIZE_PATH_COLLISION" if collision else "READY_FOR_READER_DIAGNOSTIC"
        if f["priority"]=="P0":status="HOLD_INDEPENDENT_OWNER_REVIEW"
        if path!="UNOWNED" and not collision:leases.append(path)
        waves.append({"candidate_family":f["candidate_family"],"worker_type":kind,"path_lease_candidate":path,"scheduler_status":status,"source_mutation_authorized":False,"predicted_unblock_upper_bound_prs":f["unique_prs_affected"]})
    return {"schema":"cbd.failure_census_projection.v1","observation_scope":"PR_HEAD_ASSOCIATED_FIRST_PAGE_ONLY","input_digest":sha256(d),"source_sha_scope":"PR_HEAD_PER_OBSERVATION","authority":d["authority"],"observed":{"pr_count":len(prs),"run_attempt_count":(len(d["observations"]) if all(r["attempt"] is not None for r in d["observations"]) else None),"run_association_count":len(d["observations"]),"conclusions":counts,"candidate_family_count":len(ledger),"confirmed_causal_root_count":None,"accepted_closed_root_count":None,"matched_coverage_delta":None},"candidate_families":ledger,"candidate_disjoint_waves":waves,"safety_rules":["FAMILY_NAME_IS_SYMPTOM_NOT_CONFIRMED_ROOT","REUSE_CANONICAL_BD_LDAB_JOINER","NO_MERGE_OR_WAIVER","VERIFY_JOB_STEP_FIRST_RED_BEFORE_REPAIR","READ_ONLY_SCOUT_CAN_FAN_OUT_MUTATION_CANNOT_OVERLAP_PATH","EXACT_HEAD_AFTER_EACH_MUTATION"]}
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("source",type=Path);ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    out=produce(json.loads(a.source.read_text()))
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
    print(json.dumps(out["observed"],sort_keys=True))
if __name__=="__main__":main()
