#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, re
from pathlib import Path

TEXT_SUFFIXES={'.py','.yml','.yaml','.json','.md','.toml','.txt','.ini','.cfg','.html','.js','.ts','.tsx','.jsx','.ps1','.sh'}
ID_RE=re.compile(r'\b[A-Z][A-Z0-9_-]{1,80}\b')

def read_text(p:Path)->str:
    try:return p.read_text(encoding='utf-8',errors='ignore')
    except Exception:return ''

def declared_ids(root:Path)->set[str]:
    return set(re.findall(r'^\s*-\s+id:\s*([^\s#]+)',read_text(root/'ssot/ssot_items.yaml'),flags=re.M))

def indexed_ids(root:Path)->tuple[set[str],dict[str,str]]:
    try:data=json.loads(read_text(root/'ssot/index.json') or '{}')
    except Exception:data={}
    ids=set(); paths={}
    for row in data.get('authorities',[]) if isinstance(data,dict) else []:
        if isinstance(row,dict) and row.get('logical_id'):
            lid=str(row['logical_id']); ids.add(lid)
            if row.get('path'):paths[lid]=str(row['path'])
    return ids,paths

def semantic_refs(root:Path)->set[str]:
    t=read_text(root/'ssot/semantic_traceability.yaml'); out=set()
    for m in re.finditer(r'\b(?:ssot|gaps):\s*(?:\[([^\]]*)\]|([^\s#]+))',t):
        raw=m.group(1) or m.group(2) or ''
        out.update(x.strip() for x in raw.split(',') if x.strip())
    return out

def consumer_hits(root:Path,known:set[str])->dict[str,set[str]]:
    hits={k:set() for k in known}; skip={'.git','.venv','venv','node_modules','dist','build','.pytest_cache'}
    for p in root.rglob('*'):
        if not p.is_file() or p.suffix.lower() not in TEXT_SUFFIXES:continue
        if any(part in skip for part in p.parts):continue
        rel=p.relative_to(root).as_posix()
        if rel.startswith('ssot/'):continue
        t=read_text(p)
        for k in known:
            if k in t:hits[k].add(rel)
    return hits

def pct(done,total):return round(100.0*done/total,2) if total else 100.0

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',default='.'); ap.add_argument('--out',required=True); a=ap.parse_args()
    root=Path(a.root).resolve(); out=Path(a.out); out=out if out.is_absolute() else root/out; out.mkdir(parents=True,exist_ok=True)
    declared=declared_ids(root); indexed,paths=indexed_ids(root); known=declared|indexed; refs=semantic_refs(root); hits=consumer_hits(root,known)
    reg_findings=sorted(declared-indexed)+sorted(indexed-declared); reg_total=len(known)+len(reg_findings); reg_open=len(reg_findings)
    unresolved=sorted(r for r in refs if r not in known and ID_RE.fullmatch(r)); ref_total=len(refs); ref_open=len(unresolved)
    unbound=sorted(k for k,v in hits.items() if not v); cons_total=len(known); cons_open=len(unbound)
    edges=[]
    for lid,p in paths.items():edges.append((lid,f'path:{p}'))
    for r in refs:
        if r in known:edges.append(('semantic',r))
    nodes=set(known)|set(refs)|{x for e in edges for x in e}; deg={n:0 for n in nodes}
    for x,y in edges:deg[x]=deg.get(x,0)+1;deg[y]=deg.get(y,0)+1
    isolated=sorted(n for n,d in deg.items() if d==0); graph_total=len(nodes); graph_open=len(isolated)
    unlineaged=sorted(lid for lid in known if not paths.get(lid) or not (root/paths[lid]).exists()); lin_total=len(known); lin_open=len(unlineaged)
    lane_defs={
      'A_registry_gap':(reg_total,reg_open,{'registry_mismatches':reg_findings}),
      'B_reference_gap':(ref_total,ref_open,{'unresolved_references':unresolved}),
      'C_consumer_penetration':(cons_total,cons_open,{'unbound_consumers':unbound}),
      'D_graph_orphan_drop':(graph_total,graph_open,{'isolated_nodes':isolated}),
      'E_lineage_evidence':(lin_total,lin_open,{'unlineaged_ids':unlineaged})}
    sha=os.getenv('SOURCE_SHA') or os.getenv('GITHUB_SHA','LOCAL')
    for lane,(total,open_,findings) in lane_defs.items():
        closed=max(0,total-open_)
        receipt={'schema_version':'W67-ID-MEASURED-1.0.0','repository':os.getenv('GITHUB_REPOSITORY','GBOGEB/ABACUS'),'source_sha':sha,'lane':lane,'state':'MEASURED','totals':{'total_population':total,'backlog_open':open_,'backlog_closed':closed,'completion_pct':pct(closed,total)},'findings':findings}
        (out/f'{lane}.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    row={'source_sha':sha,'registry_gap_rate':round(reg_open/max(reg_total,1),6),'unresolved_reference_rate':round(ref_open/max(ref_total,1),6),'consumer_penetration_rate':round((cons_total-cons_open)/max(cons_total,1),6),'graph_drop_rate':round(graph_open/max(graph_total,1),6),'lineage_gap_rate':round(lin_open/max(lin_total,1),6),'total_population':sum(v[0] for v in lane_defs.values()),'total_open_backlog':sum(v[1] for v in lane_defs.values())}
    (out/'FEATURE_ROW.json').write_text(json.dumps(row,indent=2,sort_keys=True)+'\n'); print(json.dumps(row,sort_keys=True))
if __name__=='__main__':main()
