#!/usr/bin/env python3
"""Fail-closed Pulse-3 PCA promotion gate.
Input: JSON feature rows. Promotion requires >=3 numeric comparable observations and >=3 distinct SHAs.
No third-party dependency: covariance + power iteration are sufficient for the promotion receipt.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
FEATURES=['registry_gap_rate','unresolved_reference_rate','consumer_penetration_rate','graph_drop_rate','lineage_gap_rate']

def numeric(row): return all(isinstance(row.get(k),(int,float)) and math.isfinite(float(row[k])) for k in FEATURES)
def standardize(rows):
    cols=[[float(r[k]) for r in rows] for k in FEATURES]; means=[sum(c)/len(c) for c in cols]
    sds=[]
    for c,m in zip(cols,means): sds.append(math.sqrt(sum((x-m)**2 for x in c)/max(len(c)-1,1)))
    return [[0.0 if sds[j]==0 else (float(r[FEATURES[j]])-means[j])/sds[j] for j in range(len(FEATURES))] for r in rows]
def covariance(z):
    n=len(z); p=len(FEATURES)
    return [[sum(z[i][a]*z[i][b] for i in range(n))/max(n-1,1) for b in range(p)] for a in range(p)]
def power(cov,iters=100):
    p=len(cov); v=[1/math.sqrt(p)]*p
    for _ in range(iters):
        w=[sum(cov[i][j]*v[j] for j in range(p)) for i in range(p)]; norm=math.sqrt(sum(x*x for x in w)) or 1
        v=[x/norm for x in w]
    eig=sum(v[i]*sum(cov[i][j]*v[j] for j in range(p)) for i in range(p))
    return eig,v
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('rows',nargs='+'); ap.add_argument('--out',required=True); a=ap.parse_args()
    rows=[json.loads(Path(p).read_text()) for p in a.rows]; good=[r for r in rows if numeric(r)]
    shas={str(r.get('source_sha','')) for r in good if r.get('source_sha')}
    comparable=len(good)>=3 and len(shas)>=3
    receipt={'schema_version':'W67-PCA-PROMOTION-1.0.0','rows_seen':len(rows),'numeric_comparable_rows':len(good),'distinct_source_shas':len(shas),'required_rows':3,'required_distinct_shas':3,'promotion':'WITHHELD','within_lane_pca':'WITHHELD','cross_lane_pca':'WITHHELD','worker_allocation_mode':'RULE_BASED'}
    if comparable:
        z=standardize(good); cov=covariance(z); eig,v=power(cov); total=sum(cov[i][i] for i in range(len(FEATURES)))
        loads=dict(zip(FEATURES,[round(x,6) for x in v])); ranked=sorted(loads.items(),key=lambda kv:abs(kv[1]),reverse=True)
        receipt.update({'promotion':'PASS','within_lane_pca':'ELIGIBLE','cross_lane_pca':'MEASURED_PC1','worker_allocation_mode':'PCA_REVERSE_LOADING','pc1_explained_variance_ratio':round(eig/total,6) if total else 0.0,'pc1_loadings':loads,'reverse_loading_rank':[k for k,_ in ranked]})
    Path(a.out).write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps(receipt,sort_keys=True))
if __name__=='__main__': main()
