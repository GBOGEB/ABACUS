"""CODE PURPLE W35 read-only census and G3P decision adapter.

The dashboard projection is not an SSOT, native receipt, security verdict,
review authorization or engine for launching/displacing GitHub workflows.
Pure stdlib, deterministic.  Missing source populations remain null.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

SHA40 = re.compile(r'^[0-9a-f]{40}$')
EXPECTED = {'ABACUS', 'CODEX', 'cryoplant-project', 'pipeline-automation-hub', 'gg_MATH'}


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def valid_sha(value: Any) -> bool:
    return isinstance(value, str) and SHA40.fullmatch(value) is not None


def _count_pair(node: dict, passed_key: str, total_key: str) -> tuple[int, int]:
    a, b = node.get(passed_key), node.get(total_key)
    require(type(a) is int and type(b) is int and 0 <= a <= b and b > 0,
            'invalid pair: '+passed_key+'/'+total_key)
    return a, b


def qualified_coverage_delta(before: dict, after: dict) -> dict:
    """Deny comparison unless method, instrumentor, path/blob and denominator match."""
    required = ('scope_sha256', 'instrumentor_version', 'config_sha256',
                'eligible_statements', 'eligible_branches', 'source_blob_sha256')
    for k in required:
        require(k in before and k in after, 'missing matched scope identity: '+k)
        require(before[k] == after[k], 'unmatched scope/instrumentor: '+k)
    for value in (before, after):
        for a,b in (('covered_statements','eligible_statements'),
                    ('covered_branches','eligible_branches')):
            require(type(value[a]) is int and type(value[b]) is int
                    and 0 <= value[a] <= value[b], 'invalid coverage counters')
    est = before['eligible_statements'] + before['eligible_branches']
    require(est > 0, 'empty eligible opportunity denominator')
    before_covered = before['covered_statements'] + before['covered_branches']
    after_covered = after['covered_statements'] + after['covered_branches']
    return {'comparison':'MATCHED_SCOPE','opportunities':est,
            'uncovered_before':est-before_covered,
            'uncovered_after':est-after_covered,
            'covered_delta':after_covered-before_covered,
            'delta_pp':round(100*(after_covered-before_covered)/est,6),
            'main_coverage_claim':False,
            'merge_admission':'HOLD'}


def decision(waves: list[dict], queue_nonterminal: int | None,
             protections_qualified: bool) -> dict:
    require(queue_nonterminal is None or (type(queue_nonterminal) is int and queue_nonterminal >= 0),
            'invalid nonterminal population')
    require(type(protections_qualified) is bool, 'invalid protections status')
    if not protections_qualified:
        return {'state':'HOLD_GOVERNANCE','max_new_native_cells':0,'stable':False}
    if queue_nonterminal is None or queue_nonterminal > 0:
        return {'state':'HOLD_QUEUE_UNKNOWN_OR_ACTIVE','max_new_native_cells':0,'stable':False}
    require(isinstance(waves,list), 'waves not a collection')
    if not waves:
        return {'state':'HOLD_NO_TERMINAL_PROOF','max_new_native_cells':0,'stable':False}
    seen=set()
    for w in waves:
        require(isinstance(w,dict) and valid_sha(w.get('head_sha')),
                'invalid temporal source SHA')
        ident=w.get('wave_id')
        require(isinstance(ident,str) and bool(ident) and ident not in seen,
                'duplicated/invalid wave identity')
        seen.add(ident)
        require(type(w.get('terminal')) is bool and type(w.get('bytes_verified')) is bool,
                'unverified temporal status')
        require(w.get('scope_id') and isinstance(w.get('scope_id'),str),
                'missing temporal scope')
        require(type(w.get('marginal_covered_delta')) is int,
                'missing comparable delta')
    if not all(w['terminal'] and w['bytes_verified'] for w in waves[-4:]):
        return {'state':'HOLD_NO_TERMINAL_PROOF','max_new_native_cells':0,'stable':False}
    recent=waves[-4:]
    comparable=len(recent)==4 and len({w['scope_id'] for w in recent})==1
    plateau=comparable and all(w['marginal_covered_delta']==0 for w in recent[1:])
    if plateau:
        return {'state':'STOP_LOCAL_PLATEAU_CANDIDATE','max_new_native_cells':0,
                'stable':False,'six_sigma_capability_qualified':False}
    if not comparable and len(waves)>1:
        return {'state':'RESET_UNMATCHED_SCOPE','max_new_native_cells':0,'stable':False}
    return {'state':'ALLOW_BOUNDED_SOURCE_DISJOINT_PROBE','max_new_native_cells':6,
            'stable':False,'six_sigma_capability_qualified':False}


def rollup(data: dict) -> dict:
    require(isinstance(data,dict) and data.get('schema')=='codepurple.w35.dashboard-ledger.v1',
            'unsupported ledger schema')
    require(data.get('merge_admission')=='HOLD' and data.get('readonly') is True,
            'ledger cannot confer merge authority')
    require(valid_sha(data.get('main_sha')), 'invalid main SHA')
    repos=data.get('repositories')
    require(isinstance(repos,list) and len(repos)==5, 'invalid repo census')
    require({r.get('repo') for r in repos}==EXPECTED, 'incomplete or duplicate repo IDs')
    for r in repos:
        require(valid_sha(r.get('sha')), 'unknown repository exact SHA')
        require(r.get('level')=='HEAD_OBSERVED', 'foreign repo authority claim')
    rule=data.get('governance',{})
    require(type(rule.get('required_approval_count')) is int and
            type(rule.get('required_status_rules')) is int and
            type(rule.get('always_bypass_actors')) is int,
            'missing effective-rule denominator')
    require(rule.get('security_waiver') is False and rule.get('authority_transfer') is False,
            'unauthorized security exception')
    cohorts=data.get('cohorts',{})
    b0=cohorts.get('w34_canonical_b0_jobs',{})
    successful,total=_count_pair(b0,'passed','total')
    require(type(b0.get('failed')) is int and
            successful+b0['failed']==total, 'B0 job population mismatch')
    require(b0.get('source_sha')==data.get('baseline_main_sha', data['main_sha']) and
            type(b0.get('run_id')) is int and b0['run_id']>0 and
            type(b0.get('run_attempt')) is int and b0['run_attempt']>0,
            'B0 exact run/attempt/source mismatch')
    cases=cohorts.get('w34_canonical_pytest',{})
    for key in ('passed','failed','skipped','total'):
        require(type(cases.get(key)) is int and cases[key]>=0,
                'unknown pytest denominator')
    require(sum(cases[k] for k in ('passed','failed','skipped'))==cases['total'],
            'pytest case population inconsistent')
    slices=cohorts.get('w34_staged_lanes',{})
    assert_implemented,elig=_count_pair(slices,'implemented','eligible')
    require(0<=slices.get('native_qualified',-1)<=assert_implemented and
            0<=slices.get('accepted',-1)<=slices['native_qualified'],
            'unqualified native/admitted lane')
    local_pass,local_total=_count_pair(slices,'local_synthetic_passed','local_synthetic_total')
    roots=data.get('root_families')
    require(isinstance(roots,list) and roots, 'missing root census')
    roots_seen=set();manifestations=0;confirmed=0;unknown=0
    for r in roots:
        name=r.get('id');n=r.get('observed_manifestations');count=r.get('confirmed_distinct_roots')
        require(isinstance(name,str) and name and name not in roots_seen,
                'duplicate root ID')
        roots_seen.add(name)
        require(type(n) is int and n>=0, 'invalid root manifestation count')
        require(count is None or(type(count) is int and 0<=count<=n),
                'invalid confirmed distinct roots')
        manifestations+=n
        if count is None: unknown+=1
        else: confirmed+=count
    w27=cohorts.get('w27_matched_testpilot',{})
    require(w27.get('historical') is True and w27.get('code_global_coverage') is None,
            'false global W27 coverage claim')
    before=w27.get('before');after=w27.get('after');unit=w27.get('eligible_per_cell')
    require(isinstance(before,list) and isinstance(after,list) and len(before)==len(after)==4,
            'W27 cohort size mismatch')
    require(type(unit) is int and unit>0,'invalid W27 scope')
    diffs=[]
    for pre,post in zip(before,after):
        require(type(pre) is int and type(post) is int and 0<=pre<=unit and 0<=post<=unit,
                'W27 impossible cell coverage')
        diffs.append(round(100*(post-pre)/unit,6))
    w38=cohorts.get('w38_focused',{})
    require(valid_sha(w38.get('source_head')), 'missing W38 producer exact SHA')
    require(type(w38.get('run_id')) is int and w38['run_id']>0 and
            type(w38.get('job_id')) is int and w38['job_id']>0 and
            type(w38.get('run_attempt')) is int and w38['run_attempt']>0,
            'invalid W38 run/job/attempt identity')
    require(type(w38.get('tests_passed')) is int and w38['tests_passed']>0 and
            w38.get('tests_failed')==0 and w38.get('tests_skipped')==0 and
            w38['interpreter']=='3.12', 'unqualified W38 Python case proof')
    families=w38.get('families')
    require(isinstance(families,list) and len(families)==4 and
            len({v.get('family') for v in families})==4, 'duplicate or incomplete W38 family')
    covered=eligible=0
    for row in families:
        c,e=row.get('covered'),row.get('eligible')
        require(type(c) is int and type(e) is int and 0<=c<=e and e>0,
                'invalid W38 family opportunity denominator')
        covered+=c; eligible+=e
    require((covered,eligible)==(w38.get('after_covered'),w38.get('eligible')),
            'W38 scope numerator/denominator mismatch')
    require(type(w38.get('before_covered')) is int and
            0<=w38['before_covered']<=eligible,'invalid W38 predecessor denominator')
    # No aggregation across OS cells: reused statement/branch opportunities.
    return {
        'schema':'codepurple.w35.readonly-rollup.v1',
        'exact_main':data['main_sha'],
        'repository_head_observed':{'numerator':len(repos),'denominator':5},
        'source_implementation':{'numerator':assert_implemented,'denominator':elig},
        'native_qualified_lanes':{'numerator':slices['native_qualified'],'denominator':elig,
                                  'meaning':'proof-count; unobserved is not a measured failure'},
        'admitted_lanes':{'numerator':slices['accepted'],'denominator':elig},
        'historical_w34_b0':{'numerator':successful,'denominator':total,'status':'FAIL',
                           'run_id':b0['run_id'],'attempt':b0['run_attempt'],
                           'source_sha':b0['source_sha']},
        'current_main_b0':{'run_id':data.get('w35_live_transition',{}).get('current_main_b0_run_id'),
                           'terminal':False,'numerator':None,'denominator':None,
                           'source_sha':data['main_sha']},
        'canonical_pytest':{k:cases[k] for k in ('passed','failed','skipped','total')},
        'root_census':{'manifestations':manifestations,'source_classified_roots':confirmed,
                       'unknown_root_groups':unknown,'formal_closures':None},
        'local_synthetic':{'numerator':local_pass,'denominator':local_total,
                           'native_qualification':None},
        'historical_w27_cell_delta_pp':diffs,
        'w27_whole_repo_delta':None,
        'w38_focused':{'covered':covered,'eligible':eligible,
            'before_covered':w38['before_covered'],
            'delta_pp':round(100*(covered-w38['before_covered'])/eligible,6),
            'tested_python':w38['interpreter'],
            'native_passed':w38['tests_passed'],'run_id':w38['run_id'],
            'job_id':w38['job_id'],'artifact_bytes_verified':None,
            'broad_main_coverage':None},
        'current_main_coverage':None,
        'stable_sigma':False,
        'merge_admission':'HOLD',
        'security_waiver':False,
        'authority_transfer':False}


def main() -> None:
    p=argparse.ArgumentParser(description='Read-only proof-grade rollup; NO GitHub write')
    p.add_argument('--input',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    opts=p.parse_args()
    payload=rollup(json.loads(opts.input.read_text(encoding='utf-8')))
    opts.output.parent.mkdir(parents=True,exist_ok=True)
    opts.output.write_text(json.dumps(payload,sort_keys=True,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__': main()
