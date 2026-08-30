#!/usr/bin/env python3
"""Local T0 diagnostics. Never dispatches GitHub Actions; operational metrics only."""
import glob,hashlib,json,os,shutil,subprocess,tempfile,time

def probe(name,cmd=None,fn=None):
 t=time.perf_counter(); status='ok'; detail=None
 try:
  if fn: detail=fn()
  elif cmd:
   p=subprocess.run(cmd,shell=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=180)
   if p.returncode: status='failed'; detail={'returncode':p.returncode}
 except Exception as e: status='failed'; detail={'error':type(e).__name__}
 return {'name':name,'status':status,'duration_ms':round((time.perf_counter()-t)*1000,2),'detail':detail}
def skip(name,why): return {'name':name,'status':'skipped','duration_ms':0,'detail':why}
def hash_pack():
 files=[p for p in glob.glob('**/*',recursive=True) if os.path.isfile(p) and '/.git/' not in '/'+p]
 files=files[:5000]; h=hashlib.sha256(); total=0
 for p in files:
  try:
   b=open(p,'rb').read();h.update(b);total+=len(b)
  except OSError:pass
 return {'files':len(files),'bytes':total,'sha256':h.hexdigest()}
r=[]
r.append(probe('artifact_hash_scan',fn=hash_pack))
yaml_files=glob.glob('**/*.yml',recursive=True)+glob.glob('**/*.yaml',recursive=True)
if yaml_files:r.append(probe('yaml_parse',cmd="python -c \"import glob,yaml; [yaml.safe_load(open(p,encoding='utf-8')) for p in glob.glob('**/*.y*ml',recursive=True)]\""))
else:r.append(skip('yaml_parse','no yaml'))
if shutil.which('npx') and (os.path.exists('playwright.config.js') or os.path.exists('playwright.config.ts')):r.append(probe('playwright_list',cmd='npx playwright test --list'))
else:r.append(skip('playwright_list','playwright config/tool unavailable'))
# DOW local contract validation is preferred over a full evidence-producing execution.
if os.path.exists('scripts/validate_qps_w04_dow_receipt.py'):r.append(probe('dow_contract_dry_run',cmd='python scripts/validate_qps_w04_dow_receipt.py --help'))
else:r.append(skip('dow_contract_dry_run','validator unavailable'))
print(json.dumps({'schema':'ops-kpi-v1','phase':'T0','repo':'ABACUS','authority':'operational_non_evidence','probes':r},sort_keys=True))
