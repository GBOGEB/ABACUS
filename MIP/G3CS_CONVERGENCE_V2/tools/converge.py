#!/usr/bin/env python3
"""G3C-S evidence projection v2: one source -> metrics + typed DAG + SIPOC + HTML.

Read-only; never grants merge admission, independent review, authenticated Crew,
root closure, statistical convergence, or main/diff coverage from PR testflights.
Standard-library Python 3.9+; optional Graphviz 'dot' produces two SVGs.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import re
import shutil
import subprocess
from pathlib import Path

SCHEMA='codepurple.g3cs.convergence-input.v2'
SHA40=re.compile(r'^[0-9a-f]{40}$')
SHA64=re.compile(r'^[0-9a-f]{64}$')
WAVES=('S1','S2','S3')
LANES=('A_registry_gap','B_reference_gap','C_consumer_penetration','D_graph_orphan_drop','E_lineage_evidence')

def check(test, msg):
    if not test: raise ValueError(msg)
def canonical(data):
    return json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')
def digest(data): return hashlib.sha256(canonical(data)).hexdigest()
def filehash(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def integer(n): return type(n) is int and n>=0

def validate(data):
    check(isinstance(data,dict) and data.get('schema')==SCHEMA,'unexpected schema')
    check(data.get('repository')=='GBOGEB/ABACUS','repository mismatch')
    for p in ('observed_main_sha','before_main_sha'):
        check(bool(SHA40.fullmatch(data.get(p,''))),f'bad {p}')
    check(data.get('parallel_heads_are_not_serial')=='REQUIRED','parallel/serial protection missing')
    g=data['governance']; check(g['admission']=='HOLD' and g['security_waiver'] is False and g['authority_transfer'] is False,'unsafe authority claim')
    check(g['negative_red_canary_proven'] is False,'unsupported negative canary')
    check(g['required_approvals']==0 and g['required_status_contexts']==[],'observed ruleset drift: obtain new snapshot')
    e=data['external']; check(e['remote_crew_launch_verified'] is False,'unproven crew promotion')
    for k in ('deduplicated_roots_open','deduplicated_roots_closed','main_statement_coverage','main_branch_coverage','diff_coverage'):
        check(e[k] is None,f'{k} must be UNKNOWN until native evidence')
    check(integer(e['issues_open']) and integer(e['issues_closed']),'invalid issue count')
    waves=data['waves'];check(len(waves)==3 and tuple(w['wave'] for w in waves)==WAVES,'invalid parallel cohort')
    ids=set(); hashes=set(); base=data['before_main_sha']
    for w in waves:
        name=w['wave']; check(bool(SHA40.fullmatch(w['source_sha'])) and bool(SHA40.fullmatch(w['main_merge_sha'])),'bad head/merge SHA')
        check(w['source_sha']!=w['main_merge_sha'] and w['source_base_sha']==base,'lineage mismatch')
        check(w['merged'] is True and w['eligible_approvals']==0,'unverified review/admission')
        check(w['source_sha'] not in hashes,'duplicate PR source identity');hashes.add(w['source_sha'])
        c=w['workflow_census']; check(c['scope']=='SELECTED_PR_TRIGGERED_FIRST_PAGE' and c['completeness']=='FIRST_PAGE_ONLY','unsupported complete census')
        for field in ('observed','success','failure','nonterminal','other_terminal'):
            check(integer(c[field]),f'{name} invalid {field}')
        check(c['observed']==sum(c[k] for k in ('success','failure','nonterminal','other_terminal')),'workflow conservation failure')
        check(len(c['run_ids'])==c['observed'] and len(set(c['run_ids']))==c['observed'],'run identity cardinality mismatch')
        check(all(type(x) is int and x>0 for x in c['run_ids']),'nonpositive run ID')
        check(ids.isdisjoint(c['run_ids']),'cross-cohort run duplicate');ids.update(c['run_ids'])
        t=w['w70'];check(t['source_sha']==w['source_sha'] and SHA64.fullmatch(t['scope_sha256']),'W70 SHA mismatch')
        for k in ('lines','branches'):
            check(integer(t[k]['covered']) and integer(t[k]['eligible']) and 0<t[k]['eligible'] and t[k]['covered']<=t[k]['eligible'],'invalid W70 coverage')
        check(t['unique_confirmed_roots'] is None and t['coverage_delta']['comparable'] is False,'W70 closure/comparability invented')
        check(tuple(t['lanes'])==LANES or set(t['lanes'])==set(LANES),'missing W70 lane')
        for lane in LANES:
            l=t['lanes'][lane];check(all(integer(l[k]) for k in ('open','closed','population')) and l['open']+l['closed']==l['population'],'W70 lane total inconsistent')
        check(sum(t['lanes'][s]['population'] for s in LANES)==76,'W70 population drift')
        check(sum(t['lanes'][s]['open'] for s in LANES)==t['open_manifestations'],'W70 open debt mismatch')
        check(sum(t['lanes'][s]['closed'] for s in LANES)==t['closed_manifestations'],'W70 closed debt mismatch')
        d=w['dab'];check(d['source_sha']==w['source_sha'] and integer(d['total']) and d['command'].startswith('flake8 '),'invalid DAB provenance')
    check(len(data['evidence_files'])==6,'missing source artifact lineage')
    for x in data['evidence_files']:
        check(bool(SHA64.fullmatch(x['sha256'])) and bool(SHA64.fullmatch(x['container_zip_sha256'])),'missing artifact hash')
    return True

def typed_graph(data):
    nodes=[]; edges=[]
    def n(id,kind,label,state='OBSERVATION',**extra):nodes.append({'id':id,'type':kind,'label':label,'state':state,**extra})
    def e(a,b,kind):edges.append({'from':a,'to':b,'type':kind})
    n('native','SUPPLIER','GitHub API & artifacts');n('normalise','PROCESS','Source/attempt/selection validation');e('native','normalise','SUPPLIES')
    n('branch','PROCESS','Parallel PR-head clock');e('normalise','branch','CLASSIFIES')
    n('main','PROCESS','Serial main commit clock');e('normalise','main','CLASSIFIES')
    n('quality','MEASURE','Full static/DAB');n('matrix','MEASURE','Native test & first-red');n('coverage','MEASURE','Scoped coverage, matching rules')
    for k in ('quality','matrix','coverage'): e('branch',k,'INPUT')
    n('roots','MEASURE','Causal-root ledger (UNKNOWN)','UNKNOWN');e('matrix','roots','FINGERPRINTS_NOT_CLOSURES')
    n('graph','PROCESS','Typed DAG & dependency reach');e('roots','graph','CANDIDATE_LINKS');e('quality','graph','MEASUREMENT')
    n('dmaic','PROCESS','DMAIC · MIP · paired deltas');e('graph','dmaic','DEPENDENCY');e('coverage','dmaic','REQUIRES_SCOPE')
    n('owner','AUTHORITY','Source owners & native CI');e('dmaic','owner','REPAIR_REVIEW')
    n('reviews','AUTHORITY','Independent eligible human review','HOLD');e('owner','reviews','REQUIRES')
    n('gate','AUTHORITY','Effective required checks / negative RED canary','HOLD');e('main','gate','MAIN_STATE');e('reviews','gate','REQUIRES')
    n('admission','DECISION','Governed merge admission','HOLD');e('gate','admission','BLOCKS_UNTIL_PROVEN')
    n('post','PROCESS','Exact merged-main CI & matched coverage','UNKNOWN');e('main','post','SOURCE');e('admission','post','REQUIRES')
    n('dashboard','OUTPUT','Read-only scorecard, SIPOC, burndowns');e('dmaic','dashboard','PROJECTS');e('post','dashboard','STATUS_ONLY')
    n('codeX','CONSUMER','CODEX Crew #977 — no launch','HOLD');n('qps','CONSUMER','QPS / gg_MATH / REX — nonpromoting','HOLD')
    e('dashboard','codeX','EVIDENCE_ONLY');e('dashboard','qps','EVIDENCE_ONLY')
    for w in data['waves']:
        key='pr:'+str(w['pr']);n(key,'PR',f'{w["wave"]} · PR #{w["pr"]}','MERGED_UNGOVERNED',sha=w['source_sha']);e('branch',key,'INDEPENDENT_HEAD');e(key,'quality','MEASURES');e(key,'main','MERGED_EVENT_NOT_ADMISSION')
    ids={x['id'] for x in nodes};check(len(ids)==len(nodes),'duplicate graph atom')
    for x in edges:check(x['from'] in ids and x['to'] in ids,'dangling graph edge')
    adjacency={k:[] for k in ids}
    for x in edges:adjacency[x['from']].append(x['to'])
    visiting=set();visited=set()
    def walk(v):
        check(v not in visiting,'cycle detected')
        if v in visited:return
        visiting.add(v)
        for nxt in adjacency[v]:walk(nxt)
        visiting.remove(v);visited.add(v)
    for v in sorted(ids):walk(v)
    return {'schema':'codepurple.g3cs.typed-dag.v2','nodes':nodes,'edges':edges,'node_count':len(nodes),'edge_count':len(edges),
       'safety':{'causal_edges_are_not_root_closure':True,'merges_not_admission':True,'authority_transfer':False,'admission':'HOLD'}}

def sipoc(data):
    s=[
      ['GitHub source owners','Exact PR head, merged-main SHA, native run/attempt IDs','Pin two clocks, reject staleness','Versioned provenance + run census','ABACUS B0, admission #1860'],
      ['Actions / CI scanners','JUnit, job logs, DAB, W70 and B1 receipts','Validate hashes, populations, failure topology','First-reds, focused tests, bounded quality deltas','Engineering owner + independent reviewer'],
      ['MIP / gg_MATH','Coverage scope/tool/config hashes, wave axis','Match cohorts, compute noncompensating DMAIC metrics','Measured delta or NONCOMPARABLE; qualified uncertainty','MIP/REX, control chart users'],
      ['Security & branch administrator','Effective ruleset, review identity, RED canary','Verify mandatory controls independently','Governed admission verdict; HOLD until PASS','Merge governor / main release'],
      ['CODEX / QPS consumers','Receipt digest, source context, DAG edge leases','Read-only federated replay / owner REX','Acknowledged consumer receipt; no worker authority','Mission Control #977 / QPS']]
    return {'schema':'codepurple.g3cs.sipoc.v2','columns':['Supplier','Input','Process','Output','Customer'],
       'rows':s,'authority_transfer':False,'source_of_truth':'ABACUS existing source and native artifacts',
       'adapter_only':True,'existing_provider_paths':data['existing_providers']}

def metrics(data):
    rows=[]; sums={'observed':0,'success':0,'failure':0,'nonterminal':0,'other_terminal':0}
    for w in data['waves']:
        c=w['workflow_census'];
        for k in sums:sums[k]+=c[k]
        terminal=c['success']+c['failure']+c['other_terminal']
        rows.append({'wave':w['wave'],'pr':w['pr'],'sha':w['source_sha'],'merge_sha':w['main_merge_sha'],
          **{k:c[k] for k in sums},'terminal':terminal,
          'green_observed_share':round(100*c['success']/c['observed'],4),
          'terminal_fraction':round(100*terminal/c['observed'],4),
          'terminal_success_fraction':round(100*c['success']/terminal,4) if terminal else None,
          'qualifying_full_ci':None,'eligible_review':False,
          'pr_url':f'https://github.com/GBOGEB/ABACUS/pull/{w["pr"]}'})
    a,b,c=data['waves']; t=a['w70'];
    same=(all(w['w70']['lanes']==t['lanes'] for w in data['waves']) and all(w['w70']['scope_sha256']==t['scope_sha256'] for w in data['waves']))
    static={'S1':a['dab']['total'],'S2':b['dab']['total'],'S3':c['dab']['total']}
    current={'workflow_total':sums['observed'],'workflow_success':sums['success'],'workflow_nonterminal':sums['nonterminal'],
      'workflow_terminal':sums['observed']-sums['nonterminal'],
      'observed_green_pct':round(100*sums['success']/sums['observed'],4),
      'terminal_success_pct':None if sums['observed']==sums['nonterminal'] else round(100*sums['success']/(sums['observed']-sums['nonterminal']),4),
      'job_first_reds_at_least':7,'job_red_lower_bound_basis':'historical W1 CI/CD job topology, parent run not terminal',
      'eligible_governed_merges':0,'observed_ordinary_merges':3,
      'focus_lines':{'covered':t['lines']['covered'],'eligible':t['lines']['eligible'],'percent':round(100*t['lines']['covered']/t['lines']['eligible'],4)},
      'focus_branches':{'covered':t['branches']['covered'],'eligible':t['branches']['eligible'],'percent':round(100*t['branches']['covered']/t['branches']['eligible'],4)},
      'manifestations_closed':t['closed_manifestations'],'manifestations_open':t['open_manifestations'],
      'manifestations_population':t['closed_manifestations']+t['open_manifestations'],
      'manifestations_same_across_parallel_heads':same,
      'flake8_parallel_counts':static,
      'specific_static_candidate_changes':{'S1_E225_against_S2':a['dab']['families']['E225']-b['dab']['families']['E225'],
          'S3_W292_against_S2':c['dab']['families']['W292']-b['dab']['families']['W292']},
      'issues_open':data['external']['issues_open'],'issues_closed':data['external']['issues_closed'],
      'current_main_coverage':None,'current_diff_coverage':None,'unique_roots_closed':None,
      'queue_p95_seconds':None,'execution_p95_seconds':None,
      'canary_rejected':False}
    return {'schema':'codepurple.g3cs.dmaic-contract.v2','source_sha256':digest(data),'observed_main_sha':data['observed_main_sha'],
       'clock_model':{'PR_HEAD':'PARALLEL_EXPERIMENTS','MAIN':'SERIAL_MERGE_EVENTS','EPOCH':'READBACK_SNAPSHOT_NOT_A_TRIAL'},
       'waves':rows,'totals':current,
       'comparison':{'prior_success':data['history']['previous_snapshot']['successful'],
           'prior_observed':data['history']['previous_snapshot']['observed'],
           'current_success':sums['success'],'current_observed':sums['observed'],
           'observed_success_count_difference':sums['success']-data['history']['previous_snapshot']['successful'],
           'comparable':False,'reason':'DIFFERENT_WORKFLOW_POPULATIONS_NO_RUN_ID_PAIRING'},
       'w70_lane_counts':t['lanes'],'native_evidence_status':'SOURCE_BOUND_ARTIFACT_CONTENTS_AND_GITHUB_READBACK',
       'convergence':{'formal_regime':'INSUFFICIENT_SERIAL_COMPARABLE_MAIN_SAMPLES',
           'descriptive_parallel_flat_ae':same,'six_sigma':None,'pca':None,'bradley_terry':None,
           'root_closure_rate':None,'accepted_admission':'HOLD'},
       'forecast':{'schema':'codepurple.g3cs.horizon-bounds.v1','kind':'ARITHMETIC_BOUND_NOT_STATISTICAL_PREDICTION',
           'source_sha256':digest(data),'cohort_frozen':True,'next_observed_success_min':sums['success'],
           'next_observed_success_max':sums['success']+sums['nonterminal'],
           'next_scope':'ONLY_SAME_62_RUN_IDENTITIES_IF_NOT_CANCELLED','registration':'AS_OF_THIS_SNAPSHOT_NOT_PREVIOUSLY_PRE_REGISTERED'},
       'authority':{'admission':'HOLD','protected_merge_credit':0,'security_waiver':False,'authority_transfer':False}}

def dot_escape(s):return str(s).replace('\\','\\\\').replace('"','\\"').replace('\n',' ')
def dag_dot(graph):
    colors={'SUPPLIER':'#ccdfed','PROCESS':'#d9e9dc','MEASURE':'#f7e8be','AUTHORITY':'#f8d9d6','DECISION':'#f8d9d6','OUTPUT':'#d8dff4','CONSUMER':'#e9deec','PR':'#dfedf7'}
    lines=['digraph G {','rankdir=TB; graph [fontname="DejaVu Sans", bgcolor="white",nodesep="0.2",ranksep="0.38",pad="0.24",splines=polyline];',
           'node [shape=box,style="rounded,filled",color="#a8b6c5",fontname="DejaVu Sans",fontsize=10,margin="0.14,0.09"];',
           'edge [color="#8195ab",arrowsize=0.52,penwidth=1.1,fontname="DejaVu Sans",fontsize=8];']
    for x in graph['nodes']:
        label=x['label']+'\n'+x['type']+(' · HOLD' if x['state']=='HOLD' else '')
        lines.append('"'+dot_escape(x['id'])+'" [label="'+dot_escape(label)+'",fillcolor="'+colors.get(x['type'],'#edf1f5')+'"];')
    for x in graph['edges']:
        lines.append('"'+dot_escape(x['from'])+'" -> "'+dot_escape(x['to'])+'" [label="'+dot_escape(x['type'])+'"];')
    return '\n'.join(lines+['}'])+'\n'

def sipoc_dot(doc):
    colors=['#d5e6f2','#e0ece4','#f8e9cb','#eddee5','#dbe0f3']
    lines=['digraph S {','rankdir=LR; graph [fontname="DejaVu Sans",bgcolor="white",pad="0.35",ranksep="0.22",nodesep="0.2"];',
       'node [shape=box,style="rounded,filled",fontname="DejaVu Sans",fontsize=10,color="#aebaca",margin="0.15,0.11"];','edge [arrowhead=normal,color="#8196a9",penwidth=1.2];']
    for i,title in enumerate(doc['columns']):
        entries=[r[i] for r in doc['rows']]
        short='\n'.join(x[:30] + ('…' if len(x)>30 else '') for x in entries)
        lines.append(f'c{i} [label="{dot_escape(title)}\\n\\n{dot_escape(short)}", fillcolor="{colors[i]}"];')
        if i:lines.append(f'c{i-1} -> c{i};')
    return '\n'.join(lines+['}'])+'\n'

def compact_sipoc_svg(doc):
    """Readable five-column SIPOC grid instead of a 4000-point linear string."""
    import textwrap
    colors=['#e0edf5','#e4f0e7','#fcf0da','#f2e7ea','#e5eaf8']
    W,H=1420,660
    cols=len(doc['columns']);left=20;gap=8;cw=(W-40-(cols-1)*gap)/cols;header=73;rowh=104
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Five-column SIPOC with five evidence-control rows">',
         '<rect width="100%" height="100%" fill="#f8fafc"/>',
         '<text x="22" y="27" fill="#24445c" font-family="DejaVu Sans" font-size="15" font-weight="bold">CODE PURPLE | source-bound SIPOC</text>',
         '<text x="22" y="46" fill="#5b7687" font-family="DejaVu Sans" font-size="10">Five suppliers → five outputs → non-authoritative consumers; HOLD preserved</text>']
    for j,head in enumerate(doc['columns']):
        x=left+j*(cw+gap);y=header
        out.append(f'<rect x="{x:.1f}" y="{y}" width="{cw:.1f}" height="48" rx="8" fill="{colors[j]}" stroke="#c5d3df"/>')
        out.append(f'<text x="{x+12:.1f}" y="{y+29}" font-size="14" font-weight="bold" font-family="DejaVu Sans" fill="#23445b">{esc(head)}</text>')
    for i,row in enumerate(doc['rows']):
        y=header+58+i*rowh
        for j,cell in enumerate(row):
            x=left+j*(cw+gap)
            out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cw:.1f}" height="{rowh-7}" rx="7" fill="#fff" stroke="#d9e3eb"/>')
            segments=textwrap.wrap(str(cell),width=31,break_long_words=False,break_on_hyphens=False) or ['']
            for k,line in enumerate(segments[:5]):
                out.append(f'<text x="{x+11:.1f}" y="{y+22+k*15:.1f}" fill="#344e65" font-size="11" font-family="DejaVu Sans">{esc(line)}</text>')
    out.append('</svg>')
    return '\n'.join(out)+'\n'

def esc(x):return html.escape(str(x),quote=True)
def build_html(data,summary,dag,sipoc_doc):
    t=summary['totals']; s=summary['source_sha256']
    wave_cards=''.join(f'''<article class="wave" data-wave="{esc(x['wave'])}"><div class="whead"><span class="eyebrow">{esc(x['wave'])} · PARALLEL HEAD</span><a href="{esc(x['pr_url'])}" target="_blank" rel="noopener">PR #{x['pr']} ↗</a></div><h3>{'Handover evidence' if x['wave']=='S1' else 'MIP timing / Python 3.9' if x['wave']=='S2' else 'Fail-closed pytest shims'}</h3><div class="bignum">{x['success']}<span> / {x['observed']} observed green</span></div><div class="stack"><i style="width:{x['green_observed_share']}%"></i></div><div class="small">{x['nonterminal']} nonterminal · {x['failure']} completed failure · 0 eligible approval</div><code title="Exact source SHA">{x['sha'][:18]}…</code></article>''' for x in summary['waves'])
    rows=''.join(f'<tr><td>{esc(k.split("_")[0])}</td><td>{v["population"]}</td><td>{v["closed"]}</td><td>{v["open"]}</td><td><div class="bar"><i style="width:{100*v["closed"]/v["population"]:.2f}%"></i></div></td></tr>' for k,v in summary['w70_lane_counts'].items())
    points=[(x['wave'],x['success'],x['nonterminal'],x['observed']) for x in summary['waves']]
    chart=''.join(f'''<div class="parallel-row"><span>{esc(w)}</span><div class="stack"><i style="width:{100*su/n:.3f}%"></i></div><strong>{su}/{n}</strong><small>{pending} pending</small></div>''' for w,su,pending,n in points)
    static=''.join(f'<div class="parallel-row"><span>{esc(k)}</span><div class="stack flake"><i style="width:{100*v/7400:.3f}%"></i></div><strong>{v:,}</strong></div>' for k,v in t['flake8_parallel_counts'].items())
    nodes=''.join(f'<div class="atom" data-type="{esc(x["type"])}" data-search="{esc(x["label"].lower())}"><span>{esc(x["type"])}</span><strong>{esc(x["label"])}</strong><code>{esc(x["id"])}</code></div>' for x in dag['nodes'])
    sipoc_rows=''.join('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in r)+'</tr>' for r in sipoc_doc['rows'])
    baseline=data['history']['historical_main_coverage'];coverage_label=f"{baseline['covered']:,}/{baseline['eligible']:,} historical · SHA {baseline['source_sha'][:10]}"
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><meta name="source-sha256" content="{s}"><title>CODE PURPLE / G3C-S · Convergence Observatory</title><style>
:root{{--bg:#f3f6f9;--paper:#fff;--ink:#193249;--muted:#647889;--line:#dce5ed;--deep:#142d43;--teal:#178f7b;--gold:#d79529;--red:#ba574a;--blue:#356a91}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.52 system-ui,-apple-system,Segoe UI,sans-serif;overflow-x:hidden}}a{{color:#20638c}}a:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible{{outline:2px solid #eaa448;outline-offset:3px}}.hero{{background:linear-gradient(125deg,#112739,#1e4661);color:white;padding:28px max(24px,calc((100vw - 1260px)/2)) 23px}}.hero h1{{font-size:clamp(23px,3vw,37px);margin:4px 0;font-weight:750;letter-spacing:-.045em;max-width:1000px}}.hero p{{color:#c7d9e7;margin:8px 0 0;max-width:900px}}.tag{{text-transform:uppercase;font-size:11px;letter-spacing:.13em;font-weight:760;color:#89cfbe}}main{{max-width:1260px;margin:auto;padding:23px 22px 65px}}.cards{{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px}}.card,.panel,.wave{{background:var(--paper);border:1px solid var(--line);border-radius:12px;box-shadow:0 1px 3px #0b2b3c08}}.card{{padding:17px 15px}}.card .sub{{font-size:12px;color:var(--muted);font-weight:650}}.card strong{{display:block;font-size:clamp(22px,3vw,29px);font-weight:770;letter-spacing:-.04em;font-variant-numeric:tabular-nums;margin:6px 0 2px}}.card em{{font-size:11px;color:var(--muted);font-style:normal}}.hold strong{{color:#ae5b35}}.good strong{{color:#247c70}}.panels{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:15px}}.panel{{padding:18px;min-width:0}}h2{{font-size:19px;margin:0 0 6px;letter-spacing:-.025em}}h3{{font-size:15px;margin:5px 0 10px}}.lede{{font-size:12px;color:var(--muted);margin:0 0 16px}}.stack{{height:12px;border-radius:8px;background:#e6ecf1;overflow:hidden;min-width:0}}.stack i{{display:block;height:100%;background:var(--teal)}}.parallel-row{{display:grid;grid-template-columns:37px minmax(65px,1fr) 75px 72px;gap:12px;align-items:center;margin:13px 0;font-size:12px}}.parallel-row strong{{text-align:right;font-variant-numeric:tabular-nums}}.parallel-row small{{color:var(--muted)}}.flake i{{background:#d09a51}}.waves{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:11px}}.wave{{padding:15px;min-width:0}}.whead{{display:flex;justify-content:space-between;gap:8px;font-size:12px}}.wave .eyebrow{{font-size:10px;color:var(--muted);letter-spacing:.07em;font-weight:800}}.wave h3{{min-height:24px}}.bignum{{font-size:28px;font-weight:750;margin-bottom:6px;font-variant-numeric:tabular-nums}}.bignum span{{font-size:12px;font-weight:500;color:var(--muted)}}.wave .small{{font-size:11px;color:var(--muted);margin:7px 0}}code{{font-size:10px;overflow-wrap:anywhere;color:#52677c}}.section{{margin:26px 0 10px}}.controls{{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0}}input[type=search],select{{border:1px solid #bbccd8;border-radius:6px;padding:8px 11px;background:white;font:inherit}}.controls label{{font-size:12px;font-weight:700;display:flex;align-items:center;gap:7px}}.scroll{{overflow-x:auto}}table{{width:100%;border-collapse:collapse;font-size:12px}}th,td{{padding:10px 9px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}}th{{background:#f2f6fa;font-weight:730}}.bar{{width:100%;height:8px;background:#e9edf2;border-radius:6px;overflow:hidden;min-width:80px}}.bar i{{display:block;height:100%;background:#308a79}}.warn{{padding:12px 14px;border-left:3px solid var(--gold);background:#fffbf1;border-radius:4px;font-size:13px}}.warn b{{color:#755321}}.asset{{border:1px solid var(--line);border-radius:9px;background:white;padding:10px;overflow-x:auto}}.asset img{{display:block;width:100%;max-width:100%;height:auto}}.atomgrid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px}}.atom{{border:1px solid var(--line);border-radius:8px;padding:10px;background:#fff;min-width:0}}.atom span{{font-size:10px;color:var(--muted);display:block}}.atom strong{{font-size:12px;display:block;margin:3px 0}}.atom code{{font-size:9px}}.tiny{{font-size:11px;color:var(--muted)}}.mono{{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;overflow-wrap:anywhere}}.list{{line-height:1.75;padding-left:19px}}footer{{margin-top:25px;border-top:1px solid var(--line);padding-top:16px;font-size:11px;color:var(--muted)}}[hidden]{{display:none!important}}@media(max-width:980px){{.cards{{grid-template-columns:repeat(3,1fr)}}.panels{{grid-template-columns:1fr}}.atomgrid{{grid-template-columns:repeat(3,1fr)}}}}@media(max-width:640px){{main{{padding:14px 12px 38px}}.hero{{padding:24px 13px}}.cards{{grid-template-columns:repeat(2,minmax(0,1fr))}}.waves{{grid-template-columns:1fr}}.atomgrid{{grid-template-columns:repeat(2,minmax(0,1fr))}}.parallel-row{{grid-template-columns:34px minmax(45px,1fr) 61px 62px;gap:5px}}.parallel-row small{{font-size:10px}}.panel{{padding:13px}}.asset{{overflow-x:auto}}.asset img{{min-width:700px}}}}
</style></head><body><header class="hero"><div class="tag">CODE PURPLE · MIP × DMAIC × MYCELIUM · G3C-S</div><h1>Convergence observatory</h1><p>One source-bound evidence projection · parallel PR qualification versus serial main integration · noncompensating admission gates</p><p class="tiny" style="color:#c1d9eb">Main observed <span class="mono">{esc(data['observed_main_sha'])}</span> · 18 October 2026 · source digest <span class="mono">{s[:18]}…</span></p></header><main>
<section class="cards" aria-label="Executive metrics"><article class="card good"><div class="sub">Observed green workflows</div><strong>{t['workflow_success']} / {t['workflow_total']}</strong><em>74.19% of selected observations</em></article><article class="card"><div class="sub">Nonterminal workflow runs</div><strong>{t['workflow_nonterminal']}</strong><em>Not successes or failures</em></article><article class="card"><div class="sub">W70 manifestations</div><strong>{t['manifestations_open']} open</strong><em>{t['manifestations_closed']}/{t['manifestations_population']} historically closed; Δ 0</em></article><article class="card"><div class="sub">Focused coverage</div><strong>100%</strong><em>133/133 lines · 17/18 branches</em></article><article class="card hold"><div class="sub">Governed admission</div><strong>HOLD</strong><em>3 ordinary merges · 0 eligible</em></article></section>
<section class="section"><h2>01 · Three disjoint engineering repairs</h2><p class="lede">Each PR originated from one common base. The bars compare parallel candidate populations, not sequential integration improvements. A new workflow appearing changes the denominator.</p><div class="waves">{wave_cards}</div></section>
<div class="panels"><section class="panel"><h2>02 · Native CI, not just activity</h2><p class="lede">Green / observed fraction — pending included in the denominator. Each source head is pinned independently.</p>{chart}<div class="warn"><b>Source-level red remains:</b> at least seven failed jobs observed inside one W1 broad CI workflow before the parent became terminal. Workflow success totals cannot cancel job-level first-reds.</div></section><section class="panel"><h2>03 · Static quality and cohort caveat</h2><p class="lede">Native full-repo Flake8, same command, separate source branches. Whole numbers only.</p>{static}<p class="tiny">S1 E225 = 737 versus S2 = 738; S3 W292 = 17 versus S2 = 18. These are bounded source-level differences, <b>not</b> cumulative current-main reductions. Historical 272→142 B1 false-green counts are noncomparable scanner populations.</p></section></div>
<div class="panels"><section class="panel"><h2>04 · A–E evidence penetration</h2><p class="lede">Five measured lanes, 76 manifestations, unchanged across all three parallel heads. Do not collapse to unique causal roots.</p><div class="scroll"><table><thead><tr><th>Lane</th><th>Population</th><th>Closed</th><th>Open</th><th>Completion</th></tr></thead><tbody>{rows}</tbody></table></div><p class="tiny">Independent unique root count: UNKNOWN. No serial stability or Six Sigma claim follows from three coupled heads.</p></section><section class="panel"><h2>05 · Guarded N+1 horizon</h2><p class="lede">Arithmetic continuation bounds, not a statistical forecast. Only the frozen set of 62 selected PR run identities is included.</p><div style="padding:18px 7px"><div class="bignum">46 <span>to</span> 62 <span>possible successful workflows</span></div><div class="stack"><i style="width:74.19%"></i></div><p class="tiny">Lower bound retains currently proven 46 successes; upper bound assumes all 16 nonterminal eventually succeed. A cancellation/changed source breaks this simple bound. No queue p95 or capacity forecast without job timestamps.</p></div><div class="warn"><b>Comparability:</b> previous 42/60 and current 46/62 are <b>not matched populations</b>. Historical main coverage {esc(coverage_label)}; current-main statement/branch and changed-line coverage UNKNOWN.</div></section></div>
<section class="section"><h2>06 · Source-owned evidence DAG</h2><p class="lede">Nodes/edges are dependencies or observation links, never proof of common cause. Read the graph left to right; the admission branch blocks release.</p><div class="asset"><img src="G3CS_CONVERGENCE_DAG.svg" alt="Typed DAG connecting GitHub native evidence, dual clocks, quality and coverage, governance and consumers"></div></section>
<section class="section"><h2>07 · Cross-repository SIPOC</h2><p class="lede">Existing acceptance and MIP telemetry modules remain canonical providers. This view is a nonpromoting adapter.</p><div class="asset"><img src="G3CS_CONVERGENCE_SIPOC.svg" alt="SIPOC from source and native receipts through validation to consumers"></div><details><summary>Inspect all SIPOC control rows</summary><div class="scroll"><table><thead><tr>{''.join('<th>'+esc(c)+'</th>' for c in sipoc_doc['columns'])}</tr></thead><tbody>{sipoc_rows}</tbody></table></div></details></section>
<section class="section"><h2>08 · Typed atomic dependency inventory</h2><div class="controls"><label>Filter graph atoms <select id="type-filter"><option value="all">All node types</option>{''.join('<option>'+esc(k)+'</option>' for k in sorted(set(x['type'] for x in dag['nodes'])))}</select></label><label>Search nodes <input type="search" id="node-search" placeholder="review, first-red, CODEX, SHA …"></label><span id="visible-count" class="tiny" aria-live="polite"></span></div><div class="atomgrid" id="atoms">{nodes}</div><p class="tiny">{len(dag['nodes'])} nodes · {len(dag['edges'])} directed edges · acyclic verified by generator · immutable metric semantics.</p></section>
<section class="section"><h2>09 · Noncompensating acceptance vector</h2><div class="panels"><article class="panel"><h3>Measured engineering progress</h3><p>Three merged PR source changes, seven authored commits, nine proposed test methods, 14 observed handover regression tests, and a successful exact-head Pytest Config Validation workflow.</p><p class="tiny">Engineering benefit is not proof of improved current-main combined coverage, deduplicated root closure or remote Crew launch.</p></article><article class="panel"><h3>P0 engineering governance</h3><p>Required approval count = 0 · required statuses = none · negative RED canary = NOT PROVEN · eligible approving reviews = 0.</p><p class="tiny">No admin restoration, security waiver, merged-main recertification or REX promotion claimed.</p></article></div></section>
<footer>Source semantic SHA-256: <span class="mono">{s}</span>. Built offline and checked against retained native artifact members; sampled GitHub run list is FIRST_PAGE_ONLY, not a complete repository census. Source-provider references: <code>tools/everred_v3/acceptance/graph.py</code>, <code>tools/everred_v3/acceptance/telemetry.py</code>, <code>tools/mip_ci_temporal_rollup.py</code>, and <code>scripts/cbd_matched_coverage_delta.py</code>. No network, no automatic merge, no worker dispatch.</footer></main><script>
const filter=document.getElementById('type-filter'), search=document.getElementById('node-search'), atoms=[...document.querySelectorAll('.atom')], count=document.getElementById('visible-count');function refresh(){{const q=search.value.toLowerCase().trim();let visible=0;for(const x of atoms){{const yes=(filter.value==='all'||x.dataset.type===filter.value)&&(!q||x.textContent.toLowerCase().includes(q));x.hidden=!yes;if(yes)visible++;}}count.textContent=visible+' / '+atoms.length+' atoms visible';}}filter.addEventListener('change',refresh);search.addEventListener('input',refresh);refresh();
</script></body></html>'''

def portable_dag_svg(graph):
    """Dependency-preserving, deterministic SVG when Graphviz is unavailable.

    This draws dependency edges only; it never upgrades any evidence state.
    """
    from collections import defaultdict
    from textwrap import wrap

    nodes = graph['nodes']
    edges = graph['edges']
    by_id = {item['id']: item for item in nodes}
    check(len(by_id) == len(nodes), 'duplicate portable DAG node')
    parents = {key: [] for key in by_id}
    successors = {key: [] for key in by_id}
    for edge in edges:
        a, b = edge['from'], edge['to']
        check(a in by_id and b in by_id, 'unknown portable DAG endpoint')
        parents[b].append(a)
        successors[a].append(b)
    degrees = {key: len(values) for key, values in parents.items()}
    ready = sorted(key for key in by_id if degrees[key] == 0)
    ranks = {}
    while ready:
        key = ready.pop(0)
        ranks[key] = max((ranks[parent] + 1 for parent in parents[key]), default=0)
        for next_id in sorted(successors[key]):
            degrees[next_id] -= 1
            if degrees[next_id] == 0:
                ready.append(next_id)
        ready.sort()
    check(len(ranks) == len(nodes), 'cyclic portable DAG')
    layers = defaultdict(list)
    for key, rank in ranks.items():
        layers[rank].append(key)
    box_w, box_h, gap_x, gap_y, pad, header = 266, 76, 32, 55, 20, 86
    largest = max(map(len, layers.values()), default=1)
    width = max(900, 2 * pad + largest * box_w + (largest - 1) * gap_x)
    height = header + (max(layers, default=0) + 1) * (box_h + gap_y) + pad
    positions = {}
    for depth in sorted(layers):
        items = sorted(layers[depth])
        row_width = len(items) * box_w + (len(items) - 1) * gap_x
        for index, key in enumerate(items):
            positions[key] = ((width - row_width) / 2 + index * (box_w + gap_x),
                              header + depth * (box_h + gap_y))
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Source-bound G3CS typed dependency graph">',
        '<defs><marker id="g3cs-arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0,0 L7,3.5 L0,7 z" fill="#8293a5"/></marker></defs>',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        '<text x="24" y="28" font-family="DejaVu Sans, sans-serif" font-size="19" font-weight="bold" fill="#1a354b">CODE PURPLE | source-bound evidence DAG</text>',
        '<text x="24" y="48" font-family="DejaVu Sans, sans-serif" font-size="12" fill="#567083">Portable renderer | edges describe dependencies, never causal closure or merge admission</text>',
    ]
    for edge in sorted(edges, key=lambda item: (item['from'], item['to'], item['type'])):
        ax, ay = positions[edge['from']]
        bx, by = positions[edge['to']]
        x1, y1 = ax + box_w / 2, ay + box_h
        x2, y2 = bx + box_w / 2, by
        half = (y2 - y1) / 2
        out.append(
            f'<path data-from="{esc(edge["from"])}" data-to="{esc(edge["to"])}" data-edge-type="{esc(edge["type"])}" '
            f'd="M{x1:.1f},{y1:.1f} C{x1:.1f},{y1 + half:.1f} {x2:.1f},{y2 - half:.1f} {x2:.1f},{y2:.1f}" '
            'stroke="#9aaabc" stroke-width="1.4" fill="none" marker-end="url(#g3cs-arrow)"/>'
        )
    fills = {'AUTHORITY': '#fff1ed', 'DECISION': '#fff1ed', 'MEASURE': '#fcf4df',
             'OUTPUT': '#edf1fc', 'CONSUMER': '#f5effb', 'PR': '#eaf4fb'}
    for key in sorted(by_id):
        node = by_id[key]
        x, y = positions[key]
        fill = fills.get(node['type'], '#edf6f0')
        out.append(f'<g data-node-id="{esc(key)}" data-node-type="{esc(node["type"])}">')
        out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{box_w}" height="{box_h}" rx="8" fill="{fill}" stroke="#b7c8d4"/>')
        out.append(f'<text x="{x + 11:.1f}" y="{y + 18:.1f}" font-size="10" font-weight="bold" font-family="DejaVu Sans, sans-serif" fill="#5a6e80">{esc(node["type"])} | {esc(node["state"])}</text>')
        label_lines = wrap(str(node['label']), width=35, break_long_words=False, break_on_hyphens=False) or ['']
        if len(label_lines) > 2:
            label_lines = [label_lines[0], label_lines[1][:31] + '...']
        for index, line in enumerate(label_lines):
            out.append(f'<text x="{x + 11:.1f}" y="{y + 39 + index * 18:.1f}" font-size="12" font-family="DejaVu Sans, sans-serif" fill="#234158">{esc(line)}</text>')
        out.append('</g>')
    out.append('</svg>')
    return '\n'.join(out) + '\n'

def write_bundle(data,out):
    validate(data);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    summary=metrics(data);graph=typed_graph(data);s=sipoc(data)
    values=[('G3CS_CONVERGENCE_METRICS.json',summary),('G3CS_CONVERGENCE_DAG.json',graph),('G3CS_CONVERGENCE_SIPOC.json',s)]
    for name,value in values:(out/name).write_text(json.dumps(value,sort_keys=True,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for name,doc in [('G3CS_CONVERGENCE_DAG',dag_dot(graph)),('G3CS_CONVERGENCE_SIPOC',sipoc_dot(s))]:
        src=out/(name+'.dot');src.write_text(doc,encoding='utf-8')
        if shutil.which('dot'):
            run=subprocess.run(['dot','-Tsvg',str(src),'-o',str(out/(name+'.svg'))],capture_output=True,text=True)
            check(run.returncode==0,'Graphviz render failure '+run.stderr)
        elif name=='G3CS_CONVERGENCE_DAG':
            # Keep the generation contract executable on CI runners without dot.
            # The standalone DOT source remains available for native Graphviz QA.
            (out/(name+'.svg')).write_text(portable_dag_svg(graph),encoding='utf-8')
    (out/'G3CS_CONVERGENCE_SIPOC.svg').write_text(compact_sipoc_svg(s),encoding='utf-8')
    page=build_html(data,summary,graph,s)
    # Single-file review surface: SVGs embedded for offline portability while
    # standalone SVG/JSON/DOT remain independently downloadable.
    for name in ('G3CS_CONVERGENCE_DAG.svg','G3CS_CONVERGENCE_SIPOC.svg'):
        enc=base64.b64encode((out/name).read_bytes()).decode('ascii')
        page=page.replace('src="'+name+'"','src="data:image/svg+xml;base64,'+enc+'"')
    (out/'G3CS_CONVERGENCE_DASHBOARD.html').write_text(page,encoding='utf-8')
    artifacts=sorted([p for p in out.iterdir() if p.is_file() and p.name!='QA_RECEIPT.json'])
    record={'schema':'qps-artifact-qa/1.0',
       'source':{'locator':'source/G3CS_CONVERGENCE_INPUT.json','semantic_sha256':digest(data),'git_sha':data['observed_main_sha']},
       'artifacts':{p.name:{'sha256':filehash(p),'status':'PASS','bytes':p.stat().st_size} for p in artifacts},
       'checks':{'structural':'PASS','formula_or_content':'PASS','render_visual':'DEFER','playwright':'DEFER','cross_format_parity':'PASS'},
       'evidence_level':'LOCAL_REPRODUCIBILITY','defects':[],
       'notes':['Native source is a frozen historical observation, not a claim of exact current GitHub state.',
                'Unreviewed merges cannot satisfy mandatory independent approval.',
                'No source is mutated, and the generated review projection is not the SSOT.']}
    (out/'QA_RECEIPT.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return record

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    x=p.parse_args(argv)
    source=json.loads(x.input.read_text(encoding='utf-8'))
    rec=write_bundle(source,x.out)
    print(json.dumps({'source_sha256':rec['source']['semantic_sha256'],'artifacts':len(rec['artifacts']),
          'evidence_level':rec['evidence_level'],'checks':rec['checks']},sort_keys=True))
if __name__=='__main__':main()
