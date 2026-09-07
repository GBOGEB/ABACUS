from __future__ import annotations
import hashlib,json,re,subprocess
from collections import Counter,defaultdict
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1];TRIAGE=ROOT/'triage';OUT=TRIAGE/'generated';REGISTRY=TRIAGE/'REPO_CENSUS.yaml';ACTIVE={'CANONICAL_ACTIVE','ACTIVE_COMPATIBILITY'}
RULES=[('workflow',lambda p:p.startswith('.github/workflows/')),('test',lambda p:'/test' in p.lower() or p.lower().startswith('tests/')),('runtime',lambda p:p.endswith(('.py','.ts','.js','.mjs','.cjs','.ps1','.sh'))),('governance',lambda p:any(x in p.lower() for x in ('control','govern','schema','zod','contract','rtm','adr','ocd'))),('federation',lambda p:any(x in p.lower() for x in ('federat','keb','dow','abacus','codex'))),('evidence',lambda p:any(x in p.lower() for x in ('evidence','receipt','provenance','manifest','checksum','sha256'))),('binary_output',lambda p:p.endswith(('.xlsx','.pptx','.pdf','.docx','.html'))),('documentation',lambda p:p.endswith(('.md','.rst','.txt'))),('structured_data',lambda p:p.endswith(('.yaml','.yml','.json','.csv','.tsv'))),('ssot',lambda p:'ssot' in p.lower()),('zod',lambda p:'zod' in p.lower() or (p.endswith('.ts') and 'schema' in p.lower())),('agentic',lambda p:any(x in p.lower() for x in ('agent','mcp','orchestrat'))),('bridge_adapter',lambda p:any(x in p.lower() for x in ('bridge','adapter'))),('deployment',lambda p:any(x in p.lower() for x in ('docker','compose','k8s','kubernetes','devcontainer','runner')))]
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT,text=True).strip()
def pref(r,k):return [(str(i['path']).rstrip('/'),str(i.get('state','UNKNOWN'))) for i in (r.get(k,[]) or []) if isinstance(i,dict) and i.get('path')]
def state(p,r):
 m=[]
 for k in ('canonical_roots','generated_roots','reference_roots','historical_roots','documentation_roots','dormant_roots'):m += [(x,s) for x,s in pref(r,k) if p==x or p.startswith(x+'/')]
 if m:return max(m,key=lambda x:len(x[0]))[1]
 low=p.lower();top=p.split('/',1)[0].lower()
 if re.match(r'^(abacus[-_]?v\d|v\d+|archive|archives|legacy|historical)',top) or any(x in low for x in ('/archive/','/legacy/','/historical/','deprecated')):return 'HISTORICAL'
 if any(x in low for x in ('/generated/','artifacts/','outputs/','dist/','build/')):return 'GENERATED'
 if low.startswith('docs/') and not p.endswith(('.py','.ts','.js','.ps1','.sh')):return 'DOCUMENTATION_ONLY'
 return 'UNKNOWN'
def main():
 r=yaml.safe_load(REGISTRY.read_text());fs=git('ls-files').splitlines();commit=git('rev-parse','HEAD');bs=Counter();bc=Counter();sc=defaultdict(Counter);stems=defaultdict(list);ss=[];rows=[]
 for p in fs:
  s=state(p,r);cs=[n for n,f in RULES if f(p)] or ['other'];bs[s]+=1
  for c in cs:bc[c]+=1;sc[c][s]+=1
  if s in ACTIVE and p.endswith(('.py','.ts','.js','.ps1','.sh')):stems[Path(p).stem.lower()].append(p)
  if 'ssot' in p.lower() and s in ACTIVE:ss.append(p)
  rows.append({'path':p,'state':s,'categories':cs})
 dup={k:v for k,v in stems.items() if len(v)>1};total=len(fs);awake=sum(bs[x] for x in ACTIVE);unk=bs['UNKNOWN'];dorm=sum(bs[x] for x in ('HISTORICAL','DORMANT','DOCUMENTATION_ONLY'));cp={}
 for c,t in sorted(bc.items()):
  a=sum(sc[c][x] for x in ACTIVE);cp[c]={'total':t,'awake':a,'awake_ratio':round(a/t,6) if t else 0,'unknown':sc[c]['UNKNOWN'],'historical_or_dormant':sc[c]['HISTORICAL']+sc[c]['DORMANT']+sc[c]['DOCUMENTATION_ONLY']}
 rec={'schema':'triage-repo-census/v1','repository':r['repository'],'role':r['role'],'commit':commit,'population':{'tracked_files':total},'lifecycle':{'counts':dict(sorted(bs.items())),'awake':awake,'awake_ratio':round(awake/total,6) if total else 0,'unknown':unk,'unknown_ratio':round(unk/total,6) if total else 0,'historical_dormant_docs':dorm},'category_penetration':cp,'ambiguity':{'active_ssot_candidates':sorted(ss),'active_ssot_candidate_count':len(ss),'duplicate_active_runtime_stems':dup,'duplicate_active_runtime_stem_count':len(dup)},'files':rows};rec['receipt_sha256']=hashlib.sha256(json.dumps(rec,sort_keys=True,separators=(',',':')).encode()).hexdigest();OUT.mkdir(parents=True,exist_ok=True);(OUT/'REPO_CENSUS_EXECUTED.json').write_text(json.dumps(rec,indent=2,sort_keys=True)+'\n');(OUT/'REPO_CENSUS_EXECUTED.md').write_text(f"# TRIAGE Repository Census — {r['repository']}\n\nTracked **{total}**; awake **{awake} ({rec['lifecycle']['awake_ratio']:.1%})**; unknown **{unk} ({rec['lifecycle']['unknown_ratio']:.1%})**; historical/dormant/docs **{dorm}**.\n\nActive SSOT candidates: **{len(ss)}**. Duplicate active runtime stems: **{len(dup)}**.\n")
 print(json.dumps({k:rec[k] for k in ('repository','commit','population','lifecycle','ambiguity')},indent=2))
if __name__=='__main__':main()
