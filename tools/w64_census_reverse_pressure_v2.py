#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from tools.w64_census_reverse_pressure import load_census, as_assets, stale_tree_findings, generated_inflation_findings, unknown_blocker_findings, duplicate_authority_findings

RESOLVED_STATES={"non_competing_scoped","canonical_with_mirrors","immutable_run_series","template_or_staging_copy","generated_with_lineage","classified_non_authority","classified_active_reference","classified_rendered_output"}

def load_optional(path:str|None)->dict:
    if not path: return {}
    p=Path(path)
    if not p.exists(): return {}
    return json.loads(p.read_text())

def exact_path_set(finding:dict)->set[str]:
    return set(str(x) for x in finding.get('paths',[]))

def apply_duplicate_dispositions(findings:list[dict], registry:dict)->tuple[list[dict],list[dict]]:
    by_family={str(x.get('family')):x for x in registry.get('families',[]) if isinstance(x,dict)}
    keep=[]; resolved=[]
    for f in findings:
        fam=str(f.get('family','')); d=by_family.get(fam)
        if d and d.get('state') in RESOLVED_STATES and exact_path_set(f)==set(d.get('paths',[])):
            resolved.append({**f,'resolution_state':d.get('state'),'canonical':d.get('canonical'),'evidence_basis':d.get('evidence_basis')})
        else: keep.append(f)
    return keep,resolved

def apply_unknown_dispositions(finding:list[dict], registry:dict)->tuple[list[dict],list[dict]]:
    dispositions={str(x.get('path')):x for x in registry.get('assets',[]) if isinstance(x,dict)}
    keep=[]; resolved=[]
    for f in finding:
        if f.get('type')!='release_critical_unknown_assets': keep.append(f); continue
        unresolved=[]
        for p in f.get('paths',[]):
            d=dispositions.get(str(p))
            if d and d.get('state') in RESOLVED_STATES: resolved.append({'path':p,**d})
            else: unresolved.append(p)
        if unresolved: keep.append({**f,'count':len(unresolved),'paths':unresolved})
    return keep,resolved

def apply_generated_disposition(findings:list[dict], registry:dict)->tuple[list[dict],list[dict]]:
    entries={str(x.get('path')):x for x in registry.get('assets',[]) if isinstance(x,dict)}
    keep=[]; resolved=[]
    for f in findings:
        if f.get('type')!='generated_authority_collision': keep.append(f); continue
        unresolved=[]
        for p in f.get('paths',[]):
            d=entries.get(str(p))
            if d and d.get('state')=='generated_with_lineage' and d.get('source') and d.get('generator'):
                resolved.append({'path':p,**d})
            else: unresolved.append(p)
        if unresolved: keep.append({**f,'count':len(unresolved),'paths':unresolved})
    return keep,resolved

def reverse_pressure_v2(census:dict, dup:dict, unknown:dict, generated:dict)->dict:
    assets=as_assets(census)
    dup_raw=duplicate_authority_findings(assets); dup_keep,dup_resolved=apply_duplicate_dispositions(dup_raw,dup)
    findings=[]; findings.extend(dup_keep); findings.extend(stale_tree_findings(assets))
    gen_raw=generated_inflation_findings(assets); gen_keep,gen_resolved=apply_generated_disposition(gen_raw,generated); findings.extend(gen_keep)
    unk_raw=unknown_blocker_findings(assets); unk_keep,unk_resolved=apply_unknown_dispositions(unk_raw,unknown); findings.extend(unk_keep)
    blockers=sum(1 for f in findings if f.get('severity')=='blocker'); warnings=sum(1 for f in findings if f.get('severity')=='warning')
    return {'schema_version':'W64-CENSUS-P2-2.0.0','purpose':'Disposition-aware reverse-pressure census; explicit exact-path evidence required.','p1_asset_count':census.get('asset_count'),'finding_count':len(findings),'blocker_count':blockers,'warning_count':warnings,'status':'blocked' if blockers else 'candidate_no_blockers_detected','findings':findings,'resolved':{'duplicate_authority_families':dup_resolved,'unknown_assets':unk_resolved,'generated_authority_assets':gen_resolved},'non_claims':['Does not delete or migrate assets.','Disposition closes census ambiguity only; it does not grant engineering or negotiation credit.','P3 receipt remains required.']}

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--census',required=True); ap.add_argument('--duplicate-dispositions'); ap.add_argument('--unknown-dispositions'); ap.add_argument('--generated-lineage'); ap.add_argument('--out',required=True); a=ap.parse_args()
    report=reverse_pressure_v2(load_census(Path(a.census)),load_optional(a.duplicate_dispositions),load_optional(a.unknown_dispositions),load_optional(a.generated_lineage)); Path(a.out).write_text(json.dumps(report,indent=2,sort_keys=True)+'\n'); print(json.dumps({'blocker_count':report['blocker_count'],'warning_count':report['warning_count'],'resolved_duplicate_families':len(report['resolved']['duplicate_authority_families']),'resolved_unknown_assets':len(report['resolved']['unknown_assets']),'resolved_generated_assets':len(report['resolved']['generated_authority_assets'])},sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
