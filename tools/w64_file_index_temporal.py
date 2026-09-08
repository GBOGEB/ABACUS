#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

def git(args:list[str], root:Path)->str:
    return subprocess.check_output(['git',*args],cwd=root,text=True,stderr=subprocess.DEVNULL)

def tracked(root:Path)->list[str]:
    return [x for x in git(['ls-files'],root).splitlines() if x.strip()]

def last_commit(root:Path,path:str)->dict[str,object]:
    try:
        raw=git(['log','-1','--format=%H%x09%ct%x09%an%x09%ae','--',path],root).strip()
        if not raw: return {'commit':None,'epoch':None,'iso':None,'author':None,'email':None}
        sha,epoch,author,email=raw.split('\t',3); ts=int(epoch)
        return {'commit':sha,'epoch':ts,'iso':datetime.fromtimestamp(ts,timezone.utc).isoformat(),'author':author,'email':email}
    except Exception:
        return {'commit':None,'epoch':None,'iso':None,'author':None,'email':None}

def ext(path:str)->str:
    e=Path(path).suffix.lower(); return e or '[no_ext]'

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--root',default='.'); ap.add_argument('--out',required=True); ap.add_argument('--window-seconds',type=int,default=300)
    a=ap.parse_args(); root=Path(a.root).resolve(); rows=[]
    for p in tracked(root):
        full=root/p; st=full.stat() if full.exists() else None; meta=last_commit(root,p)
        rows.append({'path':p,'name':Path(p).name,'extension':ext(p),'size_bytes':st.st_size if st else None,**meta})
    by_ext=Counter(r['extension'] for r in rows); by_name=Counter(r['name'] for r in rows)
    dated=sorted((r for r in rows if r['epoch'] is not None), key=lambda r:(r['epoch'],r['path']))
    clusters=[]; current=[]; last=None
    for r in dated:
        if last is None or r['epoch']-last <= a.window_seconds: current.append(r)
        else:
            if len(current)>1: clusters.append(current)
            current=[r]
        last=r['epoch']
    if len(current)>1: clusters.append(current)
    out={'schema_version':'W64-FILE-INDEX-TEMPORAL-1.0.0','asset_count':len(rows),'window_seconds':a.window_seconds,'by_extension':dict(by_ext.most_common()),'duplicate_name_counts':{k:v for k,v in sorted(by_name.items()) if v>1},'temporal_clusters':[{'start':c[0]['iso'],'end':c[-1]['iso'],'span_seconds':c[-1]['epoch']-c[0]['epoch'],'member_count':len(c),'paths':[x['path'] for x in c]} for c in clusters],'files':rows}
    Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'asset_count':len(rows),'extension_types':len(by_ext),'temporal_cluster_count':len(clusters)}))
    return 0
if __name__=='__main__': raise SystemExit(main())
