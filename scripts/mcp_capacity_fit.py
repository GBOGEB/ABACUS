#!/usr/bin/env python3
"""Recommend a bounded worker count from queue/service observations.
Input JSON lines: {queued, active, completed, elapsed_s, workers}. Output JSON summary.
Operational optimisation only; not engineering evidence.
"""
import json, sys, statistics
rows=[json.loads(x) for x in sys.stdin if x.strip()]
if len(rows)<2: raise SystemExit('need >=2 observations')
first,last=rows[0],rows[-1]
elapsed=max(1.0,float(last.get('t',last.get('elapsed_s',0)))-float(first.get('t',0)))
if elapsed<=1 and last.get('elapsed_s'): elapsed=float(last['elapsed_s'])
q0,q1=float(first['queued']),float(last['queued'])
net_per_min=(q0-q1)/(elapsed/60.0)
completed=max(0,float(last.get('completed',0))-float(first.get('completed',0)))
worker_minutes=sum(float(r.get('workers',0)) for r in rows)/len(rows)*(elapsed/60.0)
eff=completed/worker_minutes if worker_minutes else 0.0
# Bounded candidate set keeps experiments interpretable.
candidates=[2,4,8]
# Prefer smallest count predicted to add >=10% of current drain; if drain <=0, start at 2.
if net_per_min<=0 or eff<=0: rec=2
else:
    target=max(0.1*net_per_min,0.25)
    rec=next((n for n in candidates if n*eff>=target),8)
print(json.dumps({'queue_delta':q1-q0,'net_drain_per_min':round(net_per_min,3),'jobs_per_worker_min':round(eff,4),'recommended_workers':rec,'candidates':candidates},sort_keys=True))
