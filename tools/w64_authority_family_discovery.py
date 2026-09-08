#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

GENERIC = {"action","config","manifest","package","schema","tasks","tsconfig","requirements","release","ci","dependabot","deploy-docs","update-docs","dmaic-commit-metrics","dashboard-health"}
LIFECYCLE_HINTS = ("workflows-pending/","docs/workflows/","workflows-to-install/","workflow_templates/")

def scope(path: str) -> str:
    p = Path(path)
    parts = p.parts
    if not parts:
        return "."
    if parts[0] == ".github" and len(parts) > 2:
        return "/".join(parts[:3])
    return "/".join(parts[:2]) if len(parts) > 1 else parts[0]

def relationship(family: str, paths: list[str]) -> str:
    suffixes = {Path(p).suffix.lower() for p in paths}
    scopes = {scope(p) for p in paths}
    if any(any(h in p for h in LIFECYCLE_HINTS) for p in paths):
        return "lifecycle_mirror_or_template"
    if family.startswith("_build_meta") or family in {"dow_receipt","roundtrip_payload"}:
        return "versioned_or_run_receipt_series"
    if len(suffixes) > 1 and len({Path(p).stem.lower() for p in paths}) == 1:
        return "multi_format_same_logical_name"
    if family in GENERIC and len(scopes) > 1:
        return "scope_blind_basename_false_positive_candidate"
    if len(scopes) > 1:
        return "cross_scope_same_name_requires_role_check"
    return "same_scope_competitor_requires_authority_decision"

def angle(rel: str) -> str:
    return {
        "lifecycle_mirror_or_template": "Declare one executable authority; classify pending/docs/install/template copies as lifecycle mirrors or templates.",
        "versioned_or_run_receipt_series": "Treat immutable version/run receipts as lineage history, not competing SSOT; bind each to parent SHA/run.",
        "multi_format_same_logical_name": "Declare canonical serialization and mark alternate serialization as generated/exported mirror with digest parity.",
        "scope_blind_basename_false_positive_candidate": "Refine duplicate-family key with semantic/path scope; retain blocker only when authority roles overlap.",
        "cross_scope_same_name_requires_role_check": "Classify donor/local/integration roles; block only if scopes claim the same authority boundary.",
        "same_scope_competitor_requires_authority_decision": "Select canonical authority or compatibility facade and mark superseded peer explicitly.",
    }[rel]

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument('--p2',required=True); ap.add_argument('--out',required=True)
    a=ap.parse_args(); p2=json.loads(Path(a.p2).read_text())
    rows=[]
    for f in p2.get('findings',[]):
        if f.get('type')!='duplicate_or_competing_authority': continue
        paths=list(f.get('paths',[])); fam=str(f.get('family','')); rel=relationship(fam,paths)
        rows.append({'family':fam,'member_count':len(paths),'paths':paths,'scopes':sorted({scope(p) for p in paths}),'relationship':rel,'closure_angle':angle(rel)})
    counts={}
    for r in rows: counts[r['relationship']]=counts.get(r['relationship'],0)+1
    out={'schema_version':'W64-AUTHORITY-DISCOVERY-1.0.0','family_count':len(rows),'by_relationship':dict(sorted(counts.items())),'families':rows,'non_claims':['Dry-run discovery only; does not reduce blocker count.','A blocker may be retired only after role/scope evidence is retained.']}
    Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'family_count':len(rows),'by_relationship':out['by_relationship']}))
    return 0
if __name__=='__main__': raise SystemExit(main())
