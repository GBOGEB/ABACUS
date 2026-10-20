"""W12 fail-closed, source-reported N+i trigger-edge event census.

A source-reported record does NOT authenticate GitHub job identity or create
security, worker/REX, admission or causal-root closure authority. Independent
wave-cluster denominators require a separate native readback and owner audit.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import importlib.util
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA = 'codepurple.spine.w12.trigger-events.v1'
HEX = re.compile(r'^[0-9a-f]{40}$')
UTC = re.compile(r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$')


def fail(ok, message):
    if not ok:
        raise ValueError(message)


def positive(value, label):
    fail(type(value) is int and value>0,label+' requires positive integer')
    return value


def parse_utc(value):
    fail(isinstance(value,str) and UTC.fullmatch(value),'canonical UTC timestamp required')
    try:
        dt=datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError as err:
        raise ValueError('invalid UTC timestamp') from err
    return dt


def graph_edges(graph):
    spec=importlib.util.spec_from_file_location('w12_spine_schema',HERE/'spine_contract.py')
    fail(spec is not None and spec.loader is not None,'typed source DAG provider absent')
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.topological_order(graph)
    return {(edge['from'],edge['to'],edge['type']) for edge in graph['edges']}


def reduce_events(packet, graph):
    fail(isinstance(packet,dict) and packet.get('schema')==SCHEMA,'unsupported event schema')
    fail(packet.get('repository')=='GBOGEB/ABACUS','event source owner mismatch')
    gov=packet.get('governance') or {}
    fail(gov.get('merge_admission')=='HOLD' and gov.get('security_waiver') is False
         and gov.get('authority_transfer') is False, 'unsafe event authority')
    fail(gov.get('accepted_rex') is None and gov.get('crew_worker_id') is None,
         'unverified REX or remote worker not accepted')
    pairs=graph_edges(graph)
    waves=packet.get('waves')
    fail(isinstance(waves,list),'waves must be list')
    seen_waves=set();seen_run_attempt=set(); per_wave=[]; fired_by_type={}
    all_latencies=[]
    for w in waves:
        fail(isinstance(w,dict),'wave must be object')
        label=w.get('wave_id')
        fail(isinstance(label,str) and re.fullmatch(r'N\+[0-9]{1,4}',label),'invalid N+i wave label')
        fail(label not in seen_waves,'duplicate wave ID')
        seen_waves.add(label)
        sha=w.get('source_sha')
        fail(isinstance(sha,str) and HEX.fullmatch(sha),'invalid source SHA')
        run=positive(w.get('run_id'),'native run')
        attempt=positive(w.get('attempt'),'native attempt')
        fail((run,attempt) not in seen_run_attempt,'duplicate run/attempt across wave clusters')
        seen_run_attempt.add((run,attempt))
        fail(w.get('source_clock') in ('EXACT_PR_HEAD','SERIAL_MAIN'),'unknown source clock')
        jobs=w.get('jobs')
        fail(isinstance(jobs,list) and bool(jobs),'native job identities required')
        seen_jobs=set(); fired_count=0; observed_count=0; failures=0
        for job in jobs:
            fail(isinstance(job,dict),'job must be object')
            job_id=positive(job.get('job_id'),'native job')
            fail(job_id not in seen_jobs,'duplicate native job in a wave')
            seen_jobs.add(job_id)
            steps=job.get('steps')
            fail(isinstance(steps,list),'job steps must be list')
            seen_steps=set()
            for event in steps:
                fail(isinstance(event,dict),'event must be object')
                step_id=positive(event.get('step_id'),'step ID')
                fail(step_id not in seen_steps,'duplicate job step event')
                seen_steps.add(step_id)
                name=(event.get('from'),event.get('to'),event.get('type'))
                fail(name in pairs,'unbound or forged typed trigger edge')
                fired=event.get('fired')
                fail(type(fired) is bool,'edge fired requires boolean')
                t0=parse_utc(event.get('started_at'))
                t1=parse_utc(event.get('completed_at'))
                fail(t1>=t0,'negative observed edge duration')
                duration=(t1-t0).total_seconds()
                status=event.get('conclusion')
                fail(status in ('success','failure','skipped'),'event conclusion absent or invalid')
                if not fired:
                    fail(status=='skipped','unfired event cannot count as attempted success/failure')
                if name[2] in ('OWNS','OBSERVATION_ONLY'):
                    fail(not fired,'repo/observation edge cannot be declared an executed mutation')
                first_red=event.get('first_red_signature')
                fail(first_red is None or (isinstance(first_red,str) and 1<=len(first_red)<=200),
                     'invalid first-red signature')
                if status!='failure':
                    fail(first_red is None,'first-red signature without failed event')
                observed_count+=1
                if fired:
                    fired_count+=1
                    fired_by_type[name[2]]=fired_by_type.get(name[2],0)+1
                    all_latencies.append(duration)
                if status=='failure':failures+=1
        per_wave.append({'wave_id':label,'source_sha':sha,'run_id':run,'attempt':attempt,
                         'observed_step_edges':observed_count,'fired_step_edges':fired_count,
                         'failed_steps':failures,'jobs_observed':len(jobs),
                         'native_authentication':'SOURCE_REPORTED_UNVERIFIED'})
    return {'schema':'codepurple.spine.w12.trigger-census.v1',
            'design_graph_nodes':len(graph['nodes']),'design_graph_edges':len(pairs),
            'wave_clusters_reported':len(per_wave),'independent_wave_clusters':None,
            'observed_step_events':sum(x['observed_step_edges'] for x in per_wave),
            'fired_step_events':sum(x['fired_step_edges'] for x in per_wave),
            'fired_by_type':dict(sorted(fired_by_type.items())),
            'p95_edge_latency_seconds':None,  # only after native verification and >=20 wave clusters
            'observed_edge_latencies_seconds':all_latencies,
            'wave_receipts':per_wave,'source_clock_comparability':None,
            'DNN_or_inferential_validity':False,'external_crew_authenticated':None,
            'accepted_rex':None,'formal_root_closures':None,
            'merge_admission':'HOLD','security_waiver':False,'authority_transfer':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--events',type=Path,required=True)
    parser.add_argument('--graph',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    arg=parser.parse_args()
    report=reduce_events(json.loads(arg.events.read_text(encoding='utf-8')),
                         json.loads(arg.graph.read_text(encoding='utf-8')))
    arg.output.parent.mkdir(parents=True,exist_ok=True)
    arg.output.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n',encoding='utf-8')


if __name__ == '__main__':
    main()