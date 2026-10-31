#!/usr/bin/env python3
"""Read-only normalized CI/SUT evidence producer (not a merge admission gate).

Python stdlib only; refuses silently incomplete evidence. Intentional strict separation:
CONFIGURED -> EXECUTED -> SOURCE_BOUND -> CAUSAL/ADMISSION_VERIFIED.
No guessed pairwise Bradley-Terry wins from unrelated workflow successes.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import statistics
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

SCHEMA = 'code-purple.test-observability.v1'
SHA = re.compile(r'^[a-f0-9]{40}$')
CATEGORIES = (
    ('runtime', re.compile(r'(docker|container|rhel|ubi[89]?|lldb|ldab|debugger|deployment|podman)',re.I)),
    ('security', re.compile(r'(bandit|safety|semgrep|codeql|osv|dependabot|dependency.review|vulnerab|sast)',re.I)),
    ('static', re.compile(r'(flake8|ruff|format|isort|black|lint|yaml.validate|markdownlint|mypy|pylint)',re.I)),
    ('unit_integration', re.compile(r'(pytest|unittest|unit.test|matrix|ci.?cd|test.suite|testpilot|regression|smoke|coverage|mip.b0)',re.I)),
    ('governance', re.compile(r'(govern|policy|admission|ruleset|review|pr.feedback|protection)',re.I)),
    ('observability', re.compile(r'(census|metrics|telemetry|evidence|everred|recovery|burndown|dmaic|proof|3p)',re.I)),
)
STATUS = {'success','failure','cancelled','skipped','timed_out','action_required','neutral','stale','unknown','queued','pending','requested','waiting','in_progress'}


def category(name):
    text = str(name or '')
    return next((key for key, pattern in CATEGORIES if pattern.search(text)), 'unclassified')


def stable(o):
    return json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def sha256(o):
    return hashlib.sha256(stable(o).encode()).hexdigest()


def utc_seconds(value):
    if not isinstance(value,str): return None
    try:
        obj = dt.datetime.fromisoformat(value.replace('Z','+00:00'))
        return obj.timestamp() if obj.utcoffset() is not None else None
    except (ValueError, OverflowError):return None


def is_sha(value):
    return isinstance(value,str) and bool(SHA.fullmatch(value))


def state(run):
    if run.get('status')!='completed':
        return run.get('status') if run.get('status') in STATUS else 'unknown'
    return run.get('conclusion') if run.get('conclusion') in STATUS else 'unknown'


def pca_2d(jobs):
    # Workflow scheduling and job duration are *observational* times;
    # no independence or causal interpretation is assumed.
    obs=[]
    for j in jobs:
        q=utc_seconds(j.get('created_at'))
        s=utc_seconds(j.get('started_at'))
        e=utc_seconds(j.get('completed_at'))
        if q is not None and s is not None and e is not None and 0<=s-q<=86400 and 0<=e-s<=86400:
            obs.append((round(s-q,3),round(e-s,3)))
    result={'object':'PCA', 'variables':['queue_seconds','execution_seconds'], 'n_complete':len(obs),
            'minimum_n_heuristic':30, 'readiness':'NOT_QUALIFIED', 'pc1_evr':None,
            'correlation':None,'uncertainty':'UNKNOWN', 'causal':False,'sample_unit':'job (may be correlated within runs)'}
    if len(obs)<30: result['reason']='Insufficient complete timing pairs; no PCA fit';return result
    x=[p[0] for p in obs];y=[p[1] for p in obs]
    mx,my=statistics.mean(x),statistics.mean(y)
    sx,sy=statistics.stdev(x),statistics.stdev(y)
    if sx<=0 or sy<=0: result['reason']='Constant variable / zero variance';return result
    n=len(obs);cov=sum((a-mx)*(b-my) for a,b in obs)/(n-1)
    rho=max(-1,min(1,cov/sx/sy))
    result.update(readiness='DESCRIPTIVE_ONLY',pc1_evr=round((1+abs(rho))/2,6),
                  correlation=round(rho,6), reason='Exploratory 2D correlation PCA. Clustered runs/temporal dependence untested; do not infer causation or admission.')
    return result


def graph_reachable(start,edges):
    seen={start}; todo=[start]
    while todo:
        for nxt in edges.get(todo.pop(),set()):
            if nxt not in seen:seen.add(nxt);todo.append(nxt)
    return seen


def bt_pairs(records, *, sha):
    """Only explicit independent, comparable head-to-head TEST-EXECUTION trial receipts.

    Each independent trial must explicitly bind source_sha, test_contract_digest,
    pair context, compared candidates and winner. No implicit wins from unrelated
    GitHub workflow PASS/FAIL. Ties are not automatically converted into wins.
    """
    report={'object':'BRADLEY_TERRY', 'status':'UNKNOWN', 'fit':False, 'items':[],
            'usable_pairs':0, 'sample_minimum_heuristic':30, 'ranking':None,
            'confidence_intervals':None, 'authority_transfer':False}
    if records is None:report['reason']='No native matched pairwise test-outcome producer';return report
    if not isinstance(records,list):report['reason']='Bad pairwise producer schema';return report
    edges=defaultdict(set); outcomes=Counter(); units=set(); items=set();bad=0
    for r in records:
        if not isinstance(r,dict):bad+=1;continue
        a,b,w=(r.get('candidate_a'),r.get('candidate_b'),r.get('winner'))
        tr=r.get('trial_id'); digest=r.get('test_contract_digest')
        if (not all(isinstance(q,str) and q for q in (a,b,tr,digest))
            or a==b or w not in (a,b) or r.get('source_sha')!=sha
            or (tr,digest) in units or r.get('comparable') is not True
            or not re.fullmatch('[a-f0-9]{64}',digest)):
            bad+=1;continue
        units.add((tr,digest));items.update((a,b));loser=b if w==a else a
        outcomes[(w,loser)]+=1;edges[w].add(loser)
    report.update(items=sorted(items),usable_pairs=sum(outcomes.values()),rejected_records=bad)
    if bad: report['reason']='Rejected mismatched/duplicate/noncomparable pair records';return report
    if len(items)<2 or sum(outcomes.values())<30: report['reason']='Insufficient matched independent outcome records';return report
    if not all(len(graph_reachable(x,edges))==len(items) for x in items):
        report['reason']='Directed winning graph not strongly connected; unpenalized MLE may diverge';return report
    # Classic MM scheme for unpenalized Bradley-Terry, normalized strengths.
    strength={k:1/len(items) for k in items}
    for step in range(3000):
        next_s={}
        for a in items:
            wins=sum(v for (w,l),v in outcomes.items() if w==a)
            denom=0.0
            for b in items:
                if a==b:continue
                n_ab=outcomes.get((a,b),0)+outcomes.get((b,a),0)
                denom+=n_ab/(strength[a]+strength[b]) if n_ab else 0
            next_s[a]=wins/denom if denom else 0.0
        z=sum(next_s.values())
        if z<=0:break
        next_s={x:next_s[x]/z for x in items}
        delta=max(abs(next_s[x]-strength[x]) for x in items)
        strength=next_s
        if delta<1e-11:break
    else:
        report['reason']='MLE iteration did not converge';return report
    report.update(status='DESCRIPTIVE_FIT_ONLY',fit=True,
                  ranking=[{'candidate':k,'strength':round(strength[k],7)} for k in sorted(items,key=lambda k:-strength[k])],
                  reason='Observed paired outcomes only. No confidence intervals, trial clustering or calibration: not an actionable ranking or merge authority.')
    return report


def workflow_taxonomy(workflows):
    names=[]; seen=set()
    for w in workflows:
        if not isinstance(w,dict):continue
        name=w.get('name') or w.get('path')
        path=w.get('path') or ''
        if not name or path in seen:continue
        seen.add(path);names.append({'name':str(name),'path':path,'family':category(name+' '+path),
                                     'layer':'CONFIGURED_ONLY','execution_proven':False})
    return sorted(names,key=lambda x:(x['family'],x['name']))


def normalize(repo,sha,workflows,runs,jobs,*,expected_runs=None,pair_records=None,observed_at=None):
    if not re.fullmatch(r'^[\w.-]+/[\w.-]+$',repo) or not is_sha(sha):raise ValueError('repo / exact SHA required')
    if not isinstance(workflows,list) or not isinstance(runs,list) or not isinstance(jobs,list):raise ValueError('missing list')
    raw=[]
    for r in runs:
        if not isinstance(r,dict) or r.get('head_sha')!=sha: continue
        k=state(r)
        raw.append({'id':r.get('id'),'name':r.get('name') or 'UNKNOWN','family':category(r.get('name')),
                    'status':k,'head_sha':sha,'created_at':r.get('created_at'),
                    'updated_at':r.get('updated_at'),'html_url':r.get('html_url'),
                    'run_attempt':r.get('run_attempt'),
                    'event':r.get('event')})
    stat=Counter(r['status'] for r in raw)
    decisive=stat['success']+stat['failure']
    observed=len(raw)
    grouped={k:Counter(x['status'] for x in raw if x['family']==k) for k in sorted({x['family'] for x in raw})}
    errors=[];scopedjobs=[]
    for j in jobs:
        if not isinstance(j,dict):continue
        if j.get('head_sha') not in (None,sha):errors.append('Job head SHA mismatch');continue
        runid=j.get('run_id')
        if runid not in {r['id'] for r in raw}:errors.append('Job run outside selected source cohort');continue
        scopedjobs.append(j)
    failed_jobs=[{'run_id':j.get('run_id'),'job_id':j.get('id'),'job':j.get('name'),
                  'step':(next((s.get('name') for s in (j.get('steps') or []) if s.get('conclusion')=='failure'),None))}
                 for j in scopedjobs if j.get('conclusion')=='failure']
    classified=workflow_taxonomy(workflows)
    fam_config=Counter(x['family'] for x in classified)
    complete= type(expected_runs) is int and expected_runs==observed
    fact={'schema':SCHEMA,'repo':repo,'source_sha':sha,'observed_at':observed_at or dt.datetime.now(dt.timezone.utc).isoformat(),
          'provenance':'DECLARED_SOURCE_SCOPE_UNVERIFIED',
          'catalog':{'workflows_count':len(classified),'families':dict(fam_config),'scope':'workflow definitions, not successful executions',
                     'items':classified},
          'runs':{'expected':expected_runs,'observed':observed,'complete':complete,
                  'statuses':dict(stat),'families':{k:dict(v) for k,v in grouped.items()},
                  'success_decisive_pct':round(100*stat['success']/decisive,2) if decisive else None,
                  'failure_decisive_pct':round(100*stat['failure']/decisive,2) if decisive else None,
                  'cancelled_observed_pct':round(100*stat['cancelled']/observed,2) if observed else None,
                  'queue_observed_pct':round(100*sum(stat[x] for x in ('queued','pending','requested','waiting'))/observed,2) if observed else None,
                  'items':sorted(raw,key=lambda j:j['created_at'] or '')},
          'jobs':{'observed':len(scopedjobs), 'failed_jobs':failed_jobs, 'complete':False,
                  'note':'Job inventory intentionally bounded; does not assert completeness, JUnit cases or actual runner capacity'},
          'models':{'pca':pca_2d(scopedjobs),'bt':bt_pairs(pair_records,sha=sha)},
          'dmaic':{'Define':{'status':'OBSERVED','measurement':'exact repository + SHA identity'},
                   'Measure':{'status':'SOURCE_BOUND' if complete else 'PARTIAL','measurement':f'{observed}/{expected_runs if expected_runs is not None else "UNKNOWN"} workflow runs enumerated'},
                   'Analyze':{'status':'UNCONFIRMED','measurement':f'{len(failed_jobs)} first-red job locations; independent causal roots UNKNOWN'},
                   'Improve':{'status':'UNKNOWN','measurement':'matched repair attribution and post-fix regression not connected'},
                   'Control':{'status':'HOLD','measurement':'effective branch policy and independent review not accepted from CI outcomes'}},
          'runtime':{'docker':'CAPABILITY_DEPENDS_ON_WORKFLOW','rhel':'CAPABILITY_DEPENDS_ON_WORKFLOW',
                     'lldb':'AUTHENTICATED_SESSION_UNKNOWN','ldab':'AUTHENTICATED_SESSION_UNKNOWN'},
          'errors':errors, 'limitations':['GitHub metadata does not contain JUnit test case denominator or comparable Bandit finding set',
              'No equal-significance assumption across heterogeneous workflows',
              'Native run and job identities are observations, not causal roots',
              'Pairwise BT requires genuine matched test contracts; unrelated green/red workflows are excluded',
              'PCA uses correlated observational timing samples; engineering authority remains withheld'],
          'authority_transfer':False,'merge_authorized':False}
    fact['semantic_sha256']=sha256({k:v for k,v in fact.items() if k!='semantic_sha256'})
    return fact


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        raise ValueError('Redirect refused for authorization-bearing GitHub API requests')


class Github:
    def __init__(self,token=None):
        self.token=token or os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
        self.opener=urllib.request.build_opener(NoRedirect)
    def get(self,route):
        if not route.startswith('/repos/') or '..' in route or '\\' in route:raise ValueError('Unsafe route')
        headers={'Accept':'application/vnd.github+json','User-Agent':'CODE-PURPLE-READONLY-CENSUS/1.0','X-GitHub-Api-Version':'2022-11-28'}
        if self.token:headers['Authorization']='Bearer '+self.token
        req=urllib.request.Request('https://api.github.com'+route,headers=headers)
        with self.opener.open(req,timeout=18) as res:
            if res.status!=200:raise ValueError('Unexpected HTTP response')
            data=res.read(4*1024*1024+1)
            if len(data)>4*1024*1024:raise ValueError('Oversized native response')
        return json.loads(data)


def collect(repo,sha,client,*,run_limit=100,job_limit=20,pairs=None):
    if not is_sha(sha):raise ValueError('Exact SHA required')
    def paginate(route,field,max_records):
        records=[];page=1;expected=None
        while len(records)<max_records:
            result=client.get(route+('&' if '?' in route else '?')+f'per_page=100&page={page}')
            if isinstance(result,list):items=result
            else:items=result.get(field,[]);expected=result.get('total_count',expected)
            if not isinstance(items,list):raise ValueError('API list missing')
            records+=items[:max_records-len(records)]
            if len(items)<100 or len(records)>=max_records:break
            page+=1
        return records,expected
    wf,_=paginate(f'/repos/{repo}/actions/workflows','workflows',500)
    runs,expected=paginate(f'/repos/{repo}/actions/runs?head_sha={sha}','workflow_runs',run_limit)
    jobs=[]
    for r in runs[:job_limit]:
        rid=r.get('id')
        if type(rid) is not int:continue
        doc=client.get(f'/repos/{repo}/actions/runs/{rid}/jobs?per_page=100')
        if not isinstance(doc.get('jobs'),list):continue
        # Mark identity explicitly: job SHA is not always returned by GitHub.
        for j in doc['jobs']:
            q=dict(j);q['head_sha']=q.get('head_sha') or r.get('head_sha');jobs.append(q)
    result = normalize(repo,sha,wf,runs,jobs,expected_runs=expected,pair_records=pairs,observed_at=dt.datetime.now(dt.timezone.utc).isoformat())
    result['provenance']='GITHUB_API_METADATA_ONLY'
    result['semantic_sha256']=sha256({k:v for k,v in result.items() if k!='semantic_sha256'})
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',default='GBOGEB/ABACUS');p.add_argument('--sha',required=True)
    p.add_argument('--run-limit',type=int,default=100);p.add_argument('--job-limit',type=int,default=20)
    p.add_argument('--pair-input',type=Path);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    if not 1<=args.run_limit<=300 or not 0<=args.job_limit<=50: p.error('Invalid safe collection bounds')
    pairs=json.loads(args.pair_input.read_text()) if args.pair_input else None
    result=collect(args.repo,args.sha,Github(),run_limit=args.run_limit,job_limit=args.job_limit,pairs=pairs)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(stable({'out':str(args.out),'sha':result['source_sha'],'run_count':result['runs']['observed'],'semantic_sha256':result['semantic_sha256']}))


if __name__=='__main__':main()
