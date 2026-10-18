#!/usr/bin/env python3
"""Exact-run/attempt N->N+1 telemetry delta with noncompensating comparability.

Offline by design: caller brings authenticated source receipts; no network,
GitHub mutations, worker launch, causal root closure, or admission decisions.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
from datetime import datetime
from pathlib import Path

SCHEMA='codepurple.g3cs.native-run-snapshot.v1'
SHA=re.compile(r'^[a-f0-9]{40}$')
HEX=re.compile(r'^[a-f0-9]{64}$')
TERMINAL=('success','failure','cancelled','skipped','timed_out','action_required','neutral','startup_failure')

def require(v,message):
    if not v:raise ValueError(message)
def date(s):
    require(type(s) is str and s.endswith('Z'),'UTC Z timestamp required')
    try:x=datetime.fromisoformat(s[:-1]+'+00:00')
    except ValueError as e:raise ValueError('invalid UTC time') from e
    return x

def validate(s):
    require(type(s) is dict and s.get('schema')==SCHEMA,'invalid schema')
    require(s.get('repository')=='GBOGEB/ABACUS','repository identity mismatch')
    require(bool(SHA.fullmatch(s.get('source_sha',''))),'invalid source SHA')
    require(bool(HEX.fullmatch(s.get('selection_sha256',''))),'missing selection hash')
    require(s.get('source_clock') in ('EXACT_PR_HEAD','CURRENT_MAIN'),'missing source clock')
    date(s.get('observed_at_utc'))
    require(s.get('admission')=='HOLD' and s.get('authority_transfer') is False,'unauthorized promotion')
    runs=s.get('runs');require(type(runs) is list and runs,'no native runs')
    seen=set()
    for x in runs:
        require(type(x) is dict,'invalid native run entry')
        rid=x.get('run_id');attempt=x.get('attempt')
        require(type(rid) is int and rid>0 and type(attempt) is int and attempt>0,'run/attempt must be positive integers')
        key=(rid,attempt);require(key not in seen,'duplicate run/attempt identity');seen.add(key)
        require(x.get('source_sha')==s['source_sha'],'cross-SHA run rejected')
        require(x.get('status') in ('queued','pending','in_progress','waiting','requested','completed'),'bad run status')
        done=x['status']=='completed'
        require((x.get('conclusion') in TERMINAL if done else x.get('conclusion') is None),'terminal status/conclusion mismatch')
        job=x.get('jobs',[]);require(type(job) is list,'jobs list required')
        jobids=set()
        for j in job:
            jid=j.get('job_id')
            require(type(jid) is int and jid>0 and jid not in jobids,'duplicate/malformed job id');jobids.add(jid)
            require(j.get('source_sha')==s['source_sha'],'job has wrong source SHA')
            require(j.get('status') in ('queued','pending','in_progress','completed'),'malformed job status')
            jt=j['status']=='completed'
            require((j.get('conclusion') in TERMINAL if jt else j.get('conclusion') is None),'malformed job outcome')
            for field in ('created_at','started_at','completed_at'):
                if j.get(field) is not None:date(j[field])
            if j.get('completed_at') is not None:require(jt,'nonterminal job completed timestamp')
            if j.get('created_at') and j.get('started_at'):
                require(date(j['started_at'])>=date(j['created_at']),'negative queue clock')
            if j.get('started_at') and j.get('completed_at'):
                require(date(j['completed_at'])>=date(j['started_at']),'negative runtime clock')
    return {(x['run_id'],x['attempt']):x for x in runs}

def pctile(values, p):
    if not values:return None
    a=sorted(values)
    pos=(len(a)-1)*p
    low=math.floor(pos);up=math.ceil(pos)
    return round(a[low]+(a[up]-a[low])*(pos-low),3)

def stats(s):
    validate(s)
    runs=s['runs']; terminal=[r for r in runs if r['status']=='completed']
    success=sum(r['conclusion']=='success' for r in terminal)
    fail=sum(r['conclusion']=='failure' for r in terminal)
    jobs=[j for r in runs for j in r.get('jobs',[])]
    q=[(date(j['started_at'])-date(j['created_at'])).total_seconds() for j in jobs if j.get('started_at') and j.get('created_at')]
    rt=[(date(j['completed_at'])-date(j['started_at'])).total_seconds() for j in jobs if j.get('started_at') and j.get('completed_at')]
    return {'observed':len(runs),'terminal':len(terminal),'success':success,'failed':fail,
        'nonterminal':len(runs)-len(terminal),'success_observed_pct':round(100*success/len(runs),4),
        'terminal_success_pct':round(100*success/len(terminal),4) if terminal else None,
        'jobs_observed':len(jobs),'failed_jobs':sum(j['conclusion']=='failure' for j in jobs),
        'queue_p50_seconds':pctile(q,.5),'queue_p95_seconds':pctile(q,.95),'queue_sample_n':len(q),
        'runtime_p50_seconds':pctile(rt,.5),'runtime_p95_seconds':pctile(rt,.95),'runtime_sample_n':len(rt),
        'queue_basis':'JOB_CREATED_AT_ONLY_NO_UNLABELLED_FALLBACK',
        'statistical_control':None,'causal_roots_closed':None}

def compare(before,after):
    b=validate(before);a=validate(after)
    basis={k:before[k] for k in ('repository','source_sha','selection_sha256','source_clock')}
    reasons=[]
    if any(before[k]!=after[k] for k in basis):reasons.append('DIFFERENT_SOURCE_OR_SELECTION_CONTEXT')
    if set(a)!=set(b):reasons.append('RUN_ATTEMPT_POPULATION_CHANGED')
    if not date(before['observed_at_utc'])<date(after['observed_at_utc']):reasons.append('NONMONOTONE_OBSERVATION_TIME')
    rb,ra=stats(before),stats(after)
    result={'schema':'codepurple.g3cs.native-run-delta.v1','before':rb,'after':ra,
        'before_observed_at_utc':before['observed_at_utc'],'after_observed_at_utc':after['observed_at_utc'],
        'basis':basis,'comparable':not reasons,'reasons':reasons,
        'successful_run_delta':None,'blocked_to_success_run_ids':None,
        'regressed_success_run_ids':None,'job_first_red_cleared':None,
        'native_coverage_delta':None,'causal_root_closure_credit':0,
        'governed_admission_credit':0,'authority_transfer':False}
    if reasons:return result
    result['successful_run_delta']=ra['success']-rb['success']
    result['blocked_to_success_run_ids']=sorted([k[0] for k in b if b[k]['status']!='completed' and a[k]['conclusion']=='success'])
    result['regressed_success_run_ids']=sorted([k[0] for k in b if b[k]['conclusion']=='success' and a[k]['conclusion']!='success'])
    cleared=[]
    for key in b:
        old={j['job_id']:j for j in b[key].get('jobs',[])}
        new={j['job_id']:j for j in a[key].get('jobs',[])}
        for jid in old.keys() & new.keys():
            if old[jid]['conclusion']=='failure' and new[jid]['conclusion']=='success':
                cleared.append((key[0],jid))
    result['job_first_red_cleared']=[{'run_id':run,'job_id':job} for run,job in sorted(cleared)]
    return result

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before',required=True,type=Path);p.add_argument('--after',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    args=p.parse_args(argv)
    b=json.loads(args.before.read_text());a=json.loads(args.after.read_text());result=compare(b,a)
    args.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'comparable':result['comparable'],'reasons':result['reasons'],
                      'delta':result['successful_run_delta']}))
if __name__=='__main__':main()
