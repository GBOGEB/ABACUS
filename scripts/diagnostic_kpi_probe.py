#!/usr/bin/env python3
"""Low-impact local diagnostic probe. Does not dispatch Actions work."""
import json, os, subprocess, time, urllib.request

def timed(name, fn):
    t=time.perf_counter(); ok=True; err=None
    try: value=fn()
    except Exception as e: ok=False; value=None; err=type(e).__name__
    return {'name':name,'ok':ok,'duration_ms':round((time.perf_counter()-t)*1000,2),'error':err,'value':value}

def cmd(c):
    p=subprocess.run(c,shell=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=120)
    if p.returncode: raise RuntimeError('nonzero')
    return p.returncode

def http():
    with urllib.request.urlopen(os.getenv('MCP_HEALTH_URL','http://127.0.0.1:8766/health'),timeout=2) as r: return r.status

checks=[timed('mcp_health',http)]
if os.path.exists('scripts/preflight.sh'): checks.append(timed('preflight',lambda:cmd('bash scripts/preflight.sh')))
checks.append(timed('git_status',lambda:cmd('git status --porcelain')))
checks.append(timed('python_compile',lambda:cmd("python -m compileall -q scripts")))
print(json.dumps({'schema':'ops-kpi-v1','authority':'operational_non_evidence','checks':checks},sort_keys=True))
