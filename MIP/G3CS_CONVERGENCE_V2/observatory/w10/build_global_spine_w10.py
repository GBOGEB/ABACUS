"""Rebuild standalone W10 Global SPINE HTML, Markdown and metrics from a frozen history.

Pure local renderer. Never fetches GitHub, merges PRs, grants admission or
converts missing native receipts to zero. W10 refresh is separate read-only I/O.
"""
from __future__ import annotations
import argparse, hashlib, html, json, math
from datetime import datetime, timezone
from pathlib import Path

BASE=Path(__file__).resolve().parent

def esc(s): return html.escape(str(s), quote=True)

def ensure_uint(n):
    if type(n) is not int or n<0: raise ValueError('nonnegative integer required')
    return n

def checked_history(d):
    if d.get('schema')!='codepurple.spine.w10.history.v1': raise ValueError('invalid history schema')
    r=d['clocks']['issues'][-1]
    for item in r['repos']:
        ensure_uint(item['issue_open']); ensure_uint(item['issue_closed'])
    if sum(x['issue_open'] for x in r['repos'])!=r['total_open'] or sum(x['issue_closed'] for x in r['repos'])!=r['total_closed']:
        raise ValueError('issue counts do not reconcile')
    if r['total_open']+r['total_closed']!=r['total_issues']: raise ValueError('issue total invalid')
    for key in ('main_ci','pr_ci'):
        for x in d['clocks'][key]:
            total=sum(ensure_uint(x.get(k,0)) for k in ('success','failure','cancelled','other'))
            if total!=x['total']: raise ValueError('workflow numerator/denominator mismatch')
    for x in d['clocks']['main_coverage']:
        if x.get('covered') is not None:
            if ensure_uint(x['eligible'])==0 or not (0<=ensure_uint(x['covered'])<=x['eligible']):
                raise ValueError('coverage count error')
            if ensure_uint(x['uncovered'])!=x['eligible']-x['covered']:raise ValueError('coverage uncovered mismatch')
    return d

def pct(num,den): return 100*num/den if den else None

def N(v): return f'{v:,}' if v is not None else 'UNKNOWN'

def pill(s,kind='neutral'):return f'<span class="pill {kind}">{esc(s)}</span>'

def badge_metric(num,den,unit='%'): return f'{pct(num,den):.2f}{unit}' if den else 'UNKNOWN'

def closed_open_rail(closed,open_,title=''):
    den=closed+open_
    if not den: return '<div class="rail muted"></div>'
    return f'<div class="rail" role="img" aria-label="{esc(title or f"{closed} closed and {open_} open")}"><span class="seg closed" style="width:{closed/den*100:.6f}%"></span><span class="seg open" style="width:{open_/den*100:.6f}%"></span></div>'

def chart_svg(values=(17036,17046)):
    # Compact fine-grained integer axis. First/last points inset >= 130 px to eliminate lower-left clashes.
    W,H=980,343; l,r,t,b=112,930,45,274
    lo=17025; hi=17055
    xs=[256,776]
    ty=lambda v:b-(v-lo)/(hi-lo)*(b-t)
    labels=['N−1 | earlier main','N | last green main']
    parts=[f'<svg id="debtChart" class="chart" viewBox="0 0 {W} {H}" aria-label="Historical whole-number uncovered obligations: 17036 then 17046; conditional N plus one separately" role="img">']
    parts.append(f'<rect x="{l}" y="{t}" width="{r-l}" height="{b-t}" rx="7" fill="#fafcff"/>')
    for k in range(17025,17056,5):
        y=ty(k)
        parts.append(f'<line x1="{l}" y1="{y:.1f}" x2="{r}" y2="{y:.1f}" stroke="#e4ebf1" stroke-width="1"/>')
        parts.append(f'<text x="{l-17}" y="{y+5:.1f}" text-anchor="end" class="charttick">{k:,}</text>')
    parts.append(f'<text x="{l}" y="24" class="chart-head">UNTESTED OPPORTUNITIES — INTEGER COUNTS, TIGHT RANGE</text>')
    parts.append(f'<path d="M {xs[0]} {ty(values[0]):.1f} L {xs[1]} {ty(values[1]):.1f}" fill="none" stroke="#db8c3c" stroke-width="4" stroke-linecap="round"/>')
    for i,v in enumerate(values):
        y=ty(v); x=xs[i]
        parts.append(f'<circle cx="{x}" cy="{y:.1f}" r="9" fill="#fff" stroke="#d78332" stroke-width="4"/>')
        # Both labels always visible inside canvas, no first-point/axis collision.
        txt_y=y-20 if i==0 else y-24
        parts.append(f'<text x="{x}" y="{txt_y:.1f}" text-anchor="middle" class="chartvalue">{v:,}</text>')
        parts.append(f'<text x="{x}" y="{b+28}" text-anchor="middle" class="charttick strong">{esc(labels[i])}</text>')
    parts.append(f'<text x="{W//2}" y="{H-16}" text-anchor="middle" class="chart-caption">Full integer Y labels · Tick step = 5 whole opportunities · Latest main = UNKNOWN</text>')
    parts.append('</svg>')
    return ''.join(parts)

def coverage_svg(d):
    observations=d['clocks']['main_coverage'];old=observations[0];green=observations[1]
    W,H=980,300;l,r,t,b=106,940,45,222
    lo,hi=66.5,68.6
    xs=[200,426,653,863]
    yy=lambda v:b-(v-lo)/(hi-lo)*(b-t)
    vals=[pct(old['covered'],old['eligible']),pct(green['covered'],green['eligible'])]
    target=pct(green['covered']+d['next_scenario']['net_unique_existing_coverage_opportunities'],green['eligible'])
    parts=[f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="Historical main combined coverage with unmeasured current main and conditional next target">',f'<rect x="{l}" y="{t}" width="{r-l}" height="{b-t}" rx="7" fill="#fafcff"/>']
    for v in [66.5,67.,67.5,68.,68.5]:
        y=yy(v);parts.append(f'<line x1="{l}" x2="{r}" y1="{y:.1f}" y2="{y:.1f}" stroke="#e4ebf1"/><text x="{l-12}" y="{y+4:.1f}" text-anchor="end" class="charttick">{v:.1f}%</text>')
    parts.append(f'<path d="M {xs[0]} {yy(vals[0]):.1f} L {xs[1]} {yy(vals[1]):.1f}" stroke="#158e8a" fill="none" stroke-width="4"/>')
    for i,v in enumerate(vals):
        parts.append(f'<circle cx="{xs[i]}" cy="{yy(v):.1f}" r="8" fill="#fff" stroke="#158e8a" stroke-width="3"/><text x="{xs[i]}" y="{yy(v)-17:.1f}" class="chartvalue" text-anchor="middle">{v:.3f}%</text>')
    parts.append(f'<text x="{xs[2]}" y="{b-48}" text-anchor="middle" class="chartvalue" fill="#ba534b">UNKNOWN</text><text x="{xs[2]}" y="{b-24}" text-anchor="middle" class="chart-caption">Native B0 red</text>')
    parts.append(f'<circle cx="{xs[3]}" cy="{yy(target):.1f}" r="8" fill="#fff" stroke="#b88735" stroke-width="3" stroke-dasharray="3,3"/><text x="{xs[3]}" y="{yy(target)-19:.1f}" class="chartvalue" text-anchor="middle">{target:.3f}%*</text>')
    for i,label in enumerate(['E1 main','E2 main','N main','N+1 scenario']):parts.append(f'<text x="{xs[i]}" y="{b+24}" text-anchor="middle" class="charttick strong">{label}</text>')
    parts.append(f'<text x="{W//2}" y="{H-12}" text-anchor="middle" class="chart-caption">* Scenario reuses the E2 denominator of {green["eligible"]:,} — not a measured prediction from the latest main SHA</text></svg>')
    return ''.join(parts)

def repo_table(registry):
    cells=[]
    for row in registry:
        org=row['repo'].split('/')[-1]
        role=esc(row['layer'])
        cells.append(f'<tr><td><b>{esc(org)}</b><small class="minor">{role}</small></td><td><a href="{esc(row["url"])}" target="_blank" rel="noopener">{esc(row["path"])}</a><small class="minor">{esc(row["purpose"])}</small></td><td><code>{esc(row["sha"][:12])}…</code></td></tr>')
    return '\n'.join(cells)

def make_html(d,svg):
    issues=d['clocks']['issues'][-1];ci_prev,ci_now=d['clocks']['main_ci'][-2:];prprev,prnow=d['clocks']['pr_ci'][-2:]
    eg=d['clocks']['main_coverage'][0];lg=d['clocks']['main_coverage'][1]
    scenario=d['next_scenario'];issue_next_open=issues['total_open']-scenario['issues_closed_count'];issue_next_closed=issues['total_closed']+scenario['issues_closed_count']
    rows=[]
    for repo in issues['repos']:
        o,c=repo['issue_open'],repo['issue_closed'];t=o+c
        rows.append(f'<tr><td><a href="https://github.com/{esc(repo["repo"])}" target="_blank" rel="noopener">{esc(repo["repo"].split("/")[-1])}</a></td><td class="num">{o}</td><td class="num">{c}</td><td class="num"><b>{t}</b></td><td class="num">{pct(c,t):.2f}%</td><td class="railcell">{closed_open_rail(c,o)}</td></tr>')
    rows=''.join(rows)
    ld=[]
    for x in d['local_dod']:
        name=x['state'].lower().replace('_','-');ld.append(f'<tr><td><code>{x["id"]}</code></td><td><b>{esc(x["predicate"])}</b><small class="minor">{esc(x["evidence"])}</small></td><td><span class="pill {name}">{esc(x["state"])}</span></td></tr>')
    md=[]
    for x in d['mission_goals']:
        name=x['state'].lower().replace('_','-');md.append(f'<tr><td><code>{x["id"]}</code></td><td><b>{esc(x["goal"])}</b><small class="minor">{esc(x["evidence"])}</small></td><td><span class="pill {name}">{esc(x["state"])}</span></td></tr>')
    names={'ABACUS':'ABACUS runtime','CODEX':'CODEX governance','cryoplant-project':'QPS engineering'}
    mirror=json.dumps(d,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    # Mermaid source stays available offline to copy; Graphviz-linked SVG is static and accessible.
    mermaid=esc((BASE/'CODE_PURPLE_W10_REPO_SPINE.mmd').read_text(encoding='utf-8'))
    style='''
    :root{--bg:#f2f6fa;--white:#fff;--ink:#17364a;--muted:#627a8b;--line:#dbe6ec;--teal:#0e9388;--red:#d45c4d;--orange:#be8639;--navy:#163748;--blue:#3281a8}
    *{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;color:var(--ink);background:var(--bg);font:14px/1.52 system-ui,-apple-system,Segoe UI,Arial,sans-serif}a{color:#056786;text-decoration:none}a:hover{text-decoration:underline}button,input{font:inherit}
    .shell{max-width:1340px;margin:auto;padding:0 22px 48px}.hero{background:linear-gradient(117deg,#123246 0%,#174d57 75%,#1e6470);color:#fff;padding:32px max(22px,calc((100vw - 1300px)/2)) 80px}.hero .eyebrow{color:#9df2d1;font-size:11px;font-weight:850;letter-spacing:.14em}.hero h1{font-size:clamp(30px,3.6vw,49px);letter-spacing:-.045em;line-height:1.08;margin:12px 0}.hero p{max-width:1000px;color:#cee1e7}.tiny{font-size:11px}.hero .tiny{color:#cfe5e8}.anchor{display:flex;flex-wrap:wrap;gap:8px;margin-top:17px}.anchor a{font-size:12px;color:#e9f8f8;padding:5px 9px;border:1px solid #6c9da588;border-radius:8px}.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin-top:-47px;position:relative}.card{min-width:0;padding:16px 17px 15px;background:white;border:1px solid var(--line);border-radius:13px;box-shadow:0 4px 18px #092a3710}.card .label{font-size:10px;font-weight:850;letter-spacing:.07em;color:var(--muted);text-transform:uppercase}.big{font-size:29px;font-weight:800;line-height:1.1;margin:10px 0 2px;letter-spacing:-.04em;font-variant-numeric:tabular-nums}.sub{font-size:11px;color:var(--muted)}.mono{font:11px/1.5 ui-monospace,Consolas,monospace;overflow-wrap:anywhere}.card .sub{min-height:37px}.micro{font-size:11px;margin-top:7px;display:grid;gap:4px;color:#527181}.micro b{font-variant-numeric:tabular-nums;color:#243e4d}.teal{color:var(--teal)}.red{color:var(--red)}.orange{color:var(--orange)}.panel{background:white;border:1px solid var(--line);border-radius:13px;box-shadow:0 2px 13px #15435c08;padding:20px;min-width:0}.section{margin-top:17px}.panel h2{font-size:19px;margin:0 0 7px;letter-spacing:-.023em}.panel h3{font-size:15px;margin:12px 0 7px}.muted{color:var(--muted)}.kicker{font-size:10px;text-transform:uppercase;font-weight:800;letter-spacing:.09em;color:var(--muted)}.cols{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:17px}.cols>*{min-width:0}.rail{width:100%;height:18px;border-radius:5px;display:flex;overflow:hidden;background:#e8edf1;margin-top:12px;position:relative}.rail.muted{background:#ecf1f5}.seg{height:100%;display:block;transition:width .25s ease}.seg.closed{background:var(--teal)}.seg.open{background:var(--red)}.totalbar{height:28px}.issuefigure{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin:9px 0}.issuefigure b{font-size:24px;font-variant-numeric:tabular-nums;letter-spacing:-.02em}.issuefigure .small{font-size:11px;color:var(--muted)}.tablewrap{overflow-x:auto;max-width:100%}table{border-collapse:collapse;width:100%;font-size:12px;min-width:530px}td,th{padding:10px 9px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}th{background:#f3f7fa;font-weight:800}.num{text-align:right;font-variant-numeric:tabular-nums}.railcell{min-width:160px}.railcell .rail{height:10px;margin:4px 0}.minor{display:block;font-size:11px;color:var(--muted);margin-top:4px}.triple{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.epoch{border:1px solid #d9e5eb;border-radius:10px;padding:12px;background:#fbfdff}.epoch.next{border-style:dashed;background:#fffaf2}.epoch small{display:block;color:var(--muted);font-size:10px;text-transform:uppercase;font-weight:780}.epoch b{display:block;font-size:20px;font-variant-numeric:tabular-nums;letter-spacing:-.02em}.epoch p{font-size:11px;color:var(--muted);margin:6px 0 0}.chart{max-width:100%;height:auto;display:block;margin:7px auto}.chart-scroll{overflow-x:auto;max-width:100%;scrollbar-width:thin}.charttick{font-family:system-ui,sans-serif;font-size:15px;fill:#526d7c}.charttick.strong{font-weight:700}.chartvalue{font-family:system-ui,sans-serif;font-size:18px;font-weight:760;fill:#1f485b}.chart-head{font-family:system-ui,sans-serif;font-size:12px;font-weight:850;letter-spacing:.05em;fill:#426577}.chart-caption{font-family:system-ui,sans-serif;font-size:12px;fill:#657b86}.pill{display:inline-block;padding:3px 8px;border-radius:30px;font-size:10px;font-weight:800;background:#edf2f5;color:#586b75;white-space:nowrap}.pill.pass{background:#e0f2e9;color:#0c7962}.pill.fail,.pill.blocked{background:#ffeae5;color:#a83d32}.pill.staged,.pill.partial,.pill.not-yet{background:#fff1db;color:#996221}.alert{padding:11px 14px;border:1px solid #e8c7a9;background:#fff9f1;border-radius:9px;font-size:12px}.alert.danger{background:#fff5f4;border-color:#f0d0cb}.scenario{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:13px}.scenario label{font-size:11px;font-weight:700;color:#587082}.scenario input{width:100%;accent-color:#177d84}.scenario strong{display:block;font-size:21px;font-variant-numeric:tabular-nums}.split{display:flex;flex-wrap:wrap;gap:12px;justify-content:space-between;align-items:center}.button{border:1px solid #c5d7e1;border-radius:9px;padding:9px 13px;background:#eff7fa;color:#215a71;font-weight:720;cursor:pointer}.button:hover{background:#ddeefa}.button.danger{background:#fff2ef;color:#ae443d}.network{border:1px solid var(--line);border-radius:10px;overflow-x:auto;background:#fff;max-width:100%}.network svg{display:block;width:100%;height:auto;max-height:700px}.assetnote{background:#f6fbfc;padding:11px;border-left:3px solid #52a0a6;font-size:12px;overflow-wrap:anywhere}.controls{display:flex;gap:9px;align-items:center;flex-wrap:wrap}.controls input[type=file]{max-width:290px;font-size:12px}.controls span{font-size:12px}.badge-row{display:flex;gap:7px;flex-wrap:wrap;margin:9px 0}.divider{height:1px;background:var(--line);margin:17px 0}code,pre{font-family:ui-monospace,Consolas,monospace}pre{font-size:11px;overflow:auto;padding:13px;border-radius:9px;background:#f1f5f8;color:#254454;max-height:320px}details summary{cursor:pointer;font-weight:800;color:#1a637b;padding:6px 0}footer{font-size:11px;color:var(--muted);padding:25px 5px}#refreshStatus{font-size:12px;color:#986323}.provenance{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}.provenance a{font-size:11px;border:1px solid #d7e5ec;padding:4px 8px;border-radius:8px}.mathline{font:12px/1.6 ui-monospace,Consolas,monospace;overflow-wrap:anywhere;background:#f7f9fc;padding:8px 12px;border-radius:7px}.t-all{font-variant-numeric:tabular-nums}
    @media(max-width:1000px){.cards{grid-template-columns:repeat(2,minmax(0,1fr))}.cols{grid-template-columns:minmax(0,1fr)}.scenario{grid-template-columns:1fr 1fr 1fr}}
    @media(max-width:600px){.chart-scroll .chart{min-width:680px;max-width:none}.network svg{min-width:850px;max-height:none}.hero{padding:26px 14px 73px}.shell{padding:0 10px 38px}.panel{padding:14px}.card{padding:13px}.big{font-size:25px}.triple{grid-template-columns:1fr}.issuefigure{grid-template-columns:1fr 1fr}.scenario{grid-template-columns:1fr}.charttick{font-size:15px}.chartvalue{font-size:17px}.hero .anchor{display:none}}
    '''
    css=style
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><title>CODE PURPLE · W10 recursive Global SPINE</title><style>{css}</style></head><body>
<header class="hero"><div class="eyebrow">CODE PURPLE · MIP / DMAIC / MYCELIUM · RECURSIVE N-WAVE</div><h1>Global SPINE &amp; coverage convergence</h1><p>Measured totals with meaningful populations, earlier/current/conditional-next wave snapshots, native-proof boundaries and actual GitHub repository asset locations. The offline view can import a newer source-reported snapshot; only GitHub-native readback can authenticate it.</p><div class="tiny">Source epochs pinned to exact repo SHAs. Latest observed ABACUS main: <code>{esc(d['clocks']['main_ci'][-1]['sha'])}</code></div><nav class="anchor"><a href="#population">Issue population</a><a href="#progression">Wave comparison</a><a href="#uncovered">Coverage &amp; debt</a><a href="#topology">Repo SPINE</a><a href="#reload">Refresh / handover</a> <a href="../../../EVIDENCE_TO_ADMISSION_OBSERVATORY/global/index.html" title="W38 global DOV source-bound review">W38 global DOV</a></nav></header>
<main class="shell"><section class="cards" aria-label="Four programme KPI tiles">
 <div class="card"><div class="label">3-repo ordinary issues · open / total</div><div class="big red"><span id="tileIssueOpen">{issues['total_open']}</span> <span class="sub">/ <span id="tileIssueTotal">{issues['total_issues']}</span></span></div><div class="sub"><span id="tileIssuePct">{pct(issues['total_open'],issues['total_issues']):.2f}%</span> open · <span id="tileIssueClosed">{issues['total_closed']}</span> closed</div>{closed_open_rail(issues['total_closed'],issues['total_open'])}<div class="micro"><span>N−1: <b>UNKNOWN</b> (no matched 3-repo observation)</span><span>N+1 scenario: <b id="issueTargetMicro">{issue_next_open}/{issues['total_issues']}</b> if 4 close</span></div></div>
 <div class="card"><div class="label">Latest main CI · success / observed</div><div class="big red"><span id="tileCiSuccess">{ci_now['success']}</span> <span class="sub">/ <span id="tileCiTotal">{ci_now['total']}</span></span></div><div class="sub"><span id="tileCiPct">{pct(ci_now['success'],ci_now['total']):.2f}%</span> success · <span id="tileCiFailed">{ci_now['failure']}</span> FAIL (push cohort)</div><div class="rail"><span class="seg closed" style="width:{pct(ci_now['success'],ci_now['total']):.3f}%"></span><span class="seg open" style="width:{pct(ci_now['failure'],ci_now['total']):.3f}%"></span></div><div class="micro"><span>N−1: <b>{ci_prev['success']}/{ci_prev['total']} ({pct(ci_prev['success'],ci_prev['total']):.2f}%)</b> different workflow cohort</span><span>N+1 scenario: <b id="ciTargetMicro">{ci_now['success']+2}/{ci_now['total']}</b> if two reds clear</span></div></div>
 <div class="card"><div class="label">Last green main · covered / eligible</div><div class="big teal">{pct(lg['covered'],lg['eligible']):.3f}%</div><div class="sub">{lg['covered']:,}/{lg['eligible']:,} opportunities · latest main UNKNOWN</div><div class="rail"><span class="seg closed" style="width:{pct(lg['covered'],lg['eligible']):.3f}%"></span><span class="seg open" style="width:{100-pct(lg['covered'],lg['eligible']):.3f}%"></span></div><div class="micro"><span>Earlier main: <b>{pct(eg['covered'],eg['eligible']):.3f}%</b> · +{pct(lg['covered'],lg['eligible'])-pct(eg['covered'],eg['eligible']):.3f} pp</span><span>N+1 from last-green fixed scope: <b id="covTargetMicro">{pct(lg['covered']+scenario['net_unique_existing_coverage_opportunities'],lg['eligible']):.3f}%*</b></span></div></div>
 <div class="card"><div class="label">Local PR #2239 · passed / observed workflows</div><div class="big" style="color:#b8802a">{prnow['success']} <span class="sub">/ {prnow['total']}</span></div><div class="sub">{pct(prnow['success'],prnow['total']):.2f}% · Safety RED · zero reviews</div><div class="rail"><span class="seg closed" style="width:{pct(prnow['success'],prnow['total']):.3f}%"></span><span class="seg open" style="width:{pct(prnow['failure'],prnow['total']):.3f}%"></span></div><div class="micro"><span>N−1: <b>{prprev['success']}/{prprev['total']}</b> PR #{prprev['pr']} (different cohort)</span><span>N+1 scenario: <b id="prTargetMicro">20/20</b> if Safety resolves</span></div></div>
 </section>
 <section class="panel section" id="population"><div class="split"><h2>01 · Three-repository issue population</h2>{pill('Only 3 repos sampled; not federation total','partial')}</div>
  <div class="issuefigure"><div><div class="kicker">Closed</div><b class="teal" id="closedBig">{issues['total_closed']:,}</b><div class="small" id="closedFrac">{pct(issues['total_closed'],issues['total_issues']):.2f}% of {issues['total_issues']:,}</div></div><div><div class="kicker">Open</div><b class="red" id="openBig">{issues['total_open']:,}</b><div class="small" id="openFrac">{pct(issues['total_open'],issues['total_issues']):.2f}% of {issues['total_issues']:,}</div></div><div><div class="kicker">Total ordinary issues</div><b id="totalBig">{issues['total_issues']:,}</b><div class="small">Open + closed only; PRs separate</div></div></div>
  <div class="rail totalbar" role="img" aria-label="373 closed of 478 total, 105 open"><span id="issueBarClosed" class="seg closed" style="width:{pct(issues['total_closed'],issues['total_issues']):.4f}%"></span><span id="issueBarOpen" class="seg open" style="width:{pct(issues['total_open'],issues['total_issues']):.4f}%"></span></div>
  <div class="badge-row">{pill('Closed 373 / 478 = 78.03%','pass')}{pill('Open 105 / 478 = 21.97%','fail')}{pill('Deduplicated BD/root rates = UNKNOWN')}</div>
  <div class="tablewrap"><table aria-label="Three repository issue shares"><thead><tr><th>Repository</th><th class="num">Open</th><th class="num">Closed</th><th class="num">Total</th><th class="num">Closure %</th><th>Closed / open composition</th></tr></thead><tbody id="repoRows">{rows}<tr style="background:#eff7f8"><th>Verified subset</th><th class="num" id="rowOpen">{issues['total_open']}</th><th class="num" id="rowClosed">{issues['total_closed']}</th><th class="num" id="rowTotal">{issues['total_issues']}</th><th class="num" id="rowClosedPct">{pct(issues['total_closed'],issues['total_issues']):.2f}%</th><th>Three repositories only</th></tr></tbody></table></div>
 </section>
 <div class="cols section" id="progression"><section class="panel"><h2>02 · N−1 / N / N+1 — governance-aware CI</h2><div class="triple"><div class="epoch"><small>N−1 · prior green main</small><b>{ci_prev['success']} / {ci_prev['total']}</b><span class="sub">{pct(ci_prev['success'],ci_prev['total']):.2f}% success · 2 fail / 1 cancelled</span></div><div class="epoch"><small>N · latest main</small><b class="red" id="ciEpochN">{ci_now['success']} / {ci_now['total']}</b><span class="sub">{pct(ci_now['success'],ci_now['total']):.2f}% · 7 fail</span></div><div class="epoch next"><small>N+1 · target only</small><b id="ciEpochTarget">{ci_now['success']+2} / {ci_now['total']}</b><span class="sub">Assumes two failures turn success</span></div></div><p class="muted tiny">N−1 includes 23 push-run observations; N contains 26. Different workflow population and repeat canonicalizations preclude causal % change credit.</p><div class="alert danger">Latest main still has B0, matrix and other CI REDs. PR #2239 has B0, matrix and A10 success, but independent Safety remains RED. P0 admission stays HOLD.</div></section>
 <section class="panel"><h2>03 · Covered main percentages (PR separate)</h2><div class="chart-scroll">{coverage_svg(d)}</div><div class="split"><span class="muted tiny">Statement + branch covered / eligible; no source baseline swaps.</span>{pill('Current-main broad = UNKNOWN')}</div><p class="muted tiny">Last green main: {lg['covered']:,}/{lg['eligible']:,}. PR #2239: {d['coverage']['pr2239']['num']:,}/{d['coverage']['pr2239']['den']:,} = {d['coverage']['pr2239']['percent']:.3f}% <b>(PR-only, different source)</b>.</p></section></div>
 <section class="panel section" id="uncovered"><h2>04 · Uncovered-code obligations — visually corrected, integer-scale</h2><div class="cols"><div><div class="chart-scroll">{chart_svg()}</div><div class="alert">Measured absolute uncovered debt increased <b>17,036 → 17,046 (+10)</b> even while coverage rose from 66.955% to 67.345%. Percent rise and debt decrease are different performance objectives.</div></div><div><div class="kicker">Conservation of coverage opportunities</div><div class="mathline">Earlier green: 34,518 covered + 17,036 uncovered = <b>51,554</b><br>Later green: 35,154 covered + 17,046 uncovered = <b>52,200</b><br>Δ covered <b>+636</b> · Δ eligible <b>+646</b> · Δ uncovered <b>+10</b></div><h3>Conditional N+1 planning target</h3><p class="muted">From the <b>last green</b> denominator, closing <b id="covScenarioNum">522</b> unique existing uncovered opportunities gives <b id="covScenarioPct">68.345%</b> and <b id="debtScenarioCount">16,524</b> remaining. This is a planning scenario, not measured current-main coverage.</p><div class="alert danger">Latest main 1122dca… is <b>unmeasured</b> because canonical B0 failed during collection. Do not join the PR-head percentage to this graph as an accepted new main datapoint.</div></div></div></section>
 <section class="panel section" id="scenario"><div class="split"><h2>05 · N+1 planning scenario — adjustable, never claimed observed</h2>{pill('NOT a statistical forecast','partial')}</div><p class="muted">Change explicit assumptions below; counts recalculate but never change recorded N−1/N facts. A real future N+1 requires an exact-SHA native run and an accepted source-bound observation.</p><div class="scenario"><div><label for="closeSlider">Ordinary issue closures (no new issues)</label><input id="closeSlider" type="range" min="0" max="20" value="{scenario['issues_closed_count']}"><strong id="closeSliderVal">{scenario['issues_closed_count']} issues</strong></div><div><label for="ciSlider">Main workflow failures recovered</label><input id="ciSlider" type="range" min="0" max="7" value="{scenario['ci_failures_recovered']}"><strong id="ciSliderVal">{scenario['ci_failures_recovered']} transitions</strong></div><div><label for="covSlider">Unique existing coverage opportunities gained</label><input id="covSlider" type="range" min="0" max="903" step="1" value="{scenario['net_unique_existing_coverage_opportunities']}"><strong id="covSliderVal">{scenario['net_unique_existing_coverage_opportunities']} opportunities</strong></div></div><div class="triple" style="margin-top:15px"><div class="epoch next"><small>Issues after scenario</small><b id="outIssues">101 open / 478</b><p>377 closed / 478 total</p></div><div class="epoch next"><small>Main CI after scenario</small><b id="outCI">21/26</b><p>80.77% success if denominators unchanged</p></div><div class="epoch next"><small>Coverage from last green</small><b id="outCoverage">68.345%</b><p>Hypothetical fixed 52,200 denominator</p></div></div></section>
 <section class="panel section" id="topology"><div class="split"><h2>06 · Actual GitHub asset SPINE — repo, folder, source, bridge</h2>{pill('Pinned exact-head path audit','pass')}</div><p class="muted">The three repository boundaries are independent GitHub repositories, not three subfolders in a common super-repo. Their <code>federation/</code>, <code>mission_control/</code>, <code>MIP/</code> and <code>.mesh/</code> directories are nested tracked folders; whether an unrelated local nested folder is a genuine gitlink requires a local <code>git ls-files --stage</code> check.</p><div class="network">{svg}</div><p class="tiny muted">This embedded SVG has live GitHub deep links. Solid arrows denote local data generation/contract sequences, dashed cross-repo arrows denote typed references or future conditional returns, <b>not</b> unverified dispatch or approval.</p><details><summary>View exact 24 asset locations and their GitHub paths</summary><div class="tablewrap"><table><thead><tr><th>Authority</th><th>Actual main-tree path / purpose</th><th>Observed SHA</th></tr></thead><tbody>{repo_table(d['source_registry'])}</tbody></table></div></details><details><summary>Copy Mermaid wireframe for repo/subfolder SPINE</summary><pre id="mermaidSource">{mermaid}</pre><button class="button" type="button" id="copyMermaid">Copy Mermaid source</button></details><div class="assetnote">The previous W9 dashboard was a generated local HTML/ZIP with issue-comment evidence, **not a committed ABACUS dashboard file**. The existing GitHub <code>MIP/G3CS_CONVERGENCE_V2/output/G3CS_CONVERGENCE_DASHBOARD.html</code> is a different committed asset. W10 publishing is proposed on a separate source-owned draft branch only; no mutation/remote authority implied.</div></section>
 <div class="cols section"><section class="panel"><h2>07 · Mission goals vs W9 local DoD</h2><details open><summary>Show global noncompensating mission gates</summary><div class="tablewrap"><table><thead><tr><th>ID</th><th>Goal / evidence</th><th>State</th></tr></thead><tbody>{''.join(md)}</tbody></table></div></details></section><section class="panel"><h2>08 · Full local DoD checklist</h2><details><summary>Expand all 15 local completion predicates</summary><div class="tablewrap"><table><thead><tr><th>ID</th><th>Predicate / evidence</th><th>State</th></tr></thead><tbody>{''.join(ld)}</tbody></table></div></details><div class="badge-row">{pill('5 PASS','pass')}{pill('6 FAIL','fail')}{pill('3 UNKNOWN')}{pill('1 NOT ASSESSABLE')}</div><p class="muted tiny">DoD is not passed because 5/15 is green; a single hard P0 failure retains the global hold.</p></section></div>
 <section class="panel section" id="reload"><div class="split"><h2>09 · Reload / refresh / lossless handover</h2>{pill('Read-only recursive observer','pass')}</div><p class="muted">This HTML is complete offline. <b>Import newer snapshot JSON</b> to compare the next wave without rebuilding. Browser imports are still <b>source-reported/unverified</b> until the separate refresh producer cross-checks actual GitHub run and artifact receipts. No GitHub token is entered in the browser.</p><div class="controls"><label class="button" for="snapshotFile">Choose snapshot JSON</label><input id="snapshotFile" type="file" accept="application/json,.json"><button class="button" id="exportSession" type="button">Export handover state</button><button class="button" id="resetSession" type="button">Reset to pinned epoch</button><span id="refreshStatus" aria-live="polite">Pinned W10 snapshot loaded; no network calls</span></div><div id="importEpochs" class="subtle" style="margin:11px 0">No imported epochs yet.</div><div class="divider"></div><div class="triple"><div class="epoch"><small>N−1 · immutable</small><b>Previous receipts</b><p>Native earlier main / previous PR and separate issue clock</p></div><div class="epoch"><small>N · independently observed</small><b>Current source tuple</b><p>SHA, run/attempt, coverage tool/scope, official issue census</p></div><div class="epoch next"><small>N+1 · not auto-admitted</small><b>Import + verify</b><p>Readback new native receipts, review hard gates, publish a new handover</p></div></div><h3>Restart command (read-only Python collector → deterministic HTML)</h3><pre>python refresh_w10_spine.py --out CODE_PURPLE_W10_NEXT_SNAPSHOT.json
python build_global_spine_w10.py --history CODE_PURPLE_W10_SPINE_HISTORY.json
# Import newly emitted observation into the offline HTML, or append it to
# a source-controlled history only after owner-reviewed proof reconciliation.</pre><div class="provenance"><a href="{esc(d['provenance_urls']['issues_abacus'])}" target="_blank">ABACUS #1860</a><a href="{esc(d['provenance_urls']['issues_codex'])}" target="_blank">CODEX #977</a><a href="{esc(d['provenance_urls']['root_census'])}" target="_blank">Root census #1929</a><a href="{esc(d['provenance_urls']['last_green_main'])}" target="_blank">Last-green B0 artifact</a><a href="{esc(d['provenance_urls']['pr2239'])}" target="_blank">PR #2239</a></div></section>
 <footer>LOCAL_REPRODUCIBILITY · W10 visualization does not confer merge admission, safety clearance, independent approval, Crew launch, accepted REX, causal-root closure or process stability. <b>MERGE_ADMISSION=HOLD</b>. Data stamped {esc(d['created_utc'])}.</footer></main>
 <script id="w10data" type="application/json">{mirror}</script>
 <script>
 (()=>{{'use strict';
 const d=JSON.parse(document.getElementById('w10data').textContent); const $=id=>document.getElementById(id);
 const pct=(a,b)=> b>0?(a/b*100):null; const fmt=n=>Number(n).toLocaleString('en-US');
 const sa=(id,value)=>{{if($(id))$(id).textContent=value;}};
 function scenario(){{
   const issues=d.clocks.issues.at(-1), ci=d.clocks.main_ci.at(-1), co=d.clocks.main_coverage.find(x=>x.status==='NATIVE_PASS' && x.epoch==='N-1');
   const closed=Math.min(Number($('closeSlider').value),issues.total_open);const rec=ci.failure===null?null:Math.min(Number($('ciSlider').value),ci.failure);const gained=Math.min(Number($('covSlider').value),co.uncovered);
   sa('closeSliderVal',closed+' issues');sa('ciSliderVal',rec===null?'UNKNOWN':rec+' transitions');sa('covSliderVal',fmt(gained)+' opportunities');
   sa('issueTargetMicro',(issues.total_open-closed)+'/'+issues.total_issues);sa('ciTargetMicro',rec===null?'UNKNOWN':(ci.success+rec)+'/'+ci.total);sa('covTargetMicro',(pct(co.covered+gained,co.eligible)).toFixed(3)+'%*');
   sa('outIssues',(issues.total_open-closed)+' open / '+issues.total_issues);sa('outCI',rec===null?'UNKNOWN':(ci.success+rec)+'/'+ci.total);sa('outCoverage',pct(co.covered+gained,co.eligible).toFixed(3)+'%');
   sa('covScenarioNum',fmt(gained));sa('covScenarioPct',pct(co.covered+gained,co.eligible).toFixed(3)+'%');sa('debtScenarioCount',fmt(co.uncovered-gained));
 }}
 ['closeSlider','ciSlider','covSlider'].forEach(x=>$(x).addEventListener('input',scenario));scenario();
 $('copyMermaid').addEventListener('click',()=>{{navigator.clipboard?.writeText($('mermaidSource').textContent).then(()=>sa('refreshStatus','Mermaid copied')).catch(()=>sa('refreshStatus','Clipboard blocked; manually select source'));}});
 let imported=[];
 function nonnegative(x){{return Number.isSafeInteger(x)&&x>=0;}}
 function validSnap(s){{
   if(!s||s.schema!=='codepurple.spine.w10.snapshot.v1') throw Error('Unrecognized W10 observed snapshot schema');
   if(!/^([a-f0-9]{{40}})$/.test(s.abacus_main_sha))throw Error('Missing exact source SHA');
   if(!s.as_of_utc||!/^\\d{{4}}-\\d{{2}}-\\d{{2}}T/.test(s.as_of_utc))throw Error('Missing UTC observation timestamp');
   if(!Array.isArray(s.repos)||s.repos.length!==3)throw Error('Exactly three scoped repositories required');
   const expected=['GBOGEB/ABACUS','GBOGEB/CODEX','GBOGEB/cryoplant-project'];
   if(new Set(s.repos.map(x=>x.repo)).size!==3||s.repos.some(x=>!expected.includes(x.repo)))throw Error('Wrong federation cohort');
   for(const r of s.repos)if(!nonnegative(r.issue_open)||!nonnegative(r.issue_closed))throw Error('Invalid issue counts');
   if(!s.main_ci||s.main_ci.sha!==s.abacus_main_sha)throw Error('CI head source mismatch');
   const ciKeys=['success','failure','cancelled','other','total']; const allNull=ciKeys.every(k=>s.main_ci[k]===null);
   if(!allNull && ciKeys.some(k=>!nonnegative(s.main_ci[k])))throw Error('CI counters must all be integer or all UNKNOWN');
   if(!allNull && s.main_ci.success+s.main_ci.failure+s.main_ci.cancelled+s.main_ci.other!==s.main_ci.total)throw Error('CI counts do not conserve');
   if(s.coverage!==null&&s.coverage!==undefined){{
     const c=s.coverage;
     if(c.source_sha!==s.abacus_main_sha||!nonnegative(c.covered)||!nonnegative(c.eligible)||c.eligible===0||c.covered>c.eligible)throw Error('Invalid source-bound coverage');
     if(!(Number.isSafeInteger(c.native_run_id)&&c.native_run_id>0&&Number.isSafeInteger(c.artifact_id)&&c.artifact_id>0&&/^[a-f0-9]{{64}}$/.test(c.archive_sha256))) throw Error('Coverage is not pinned to native run, artifact and digest');
   }}
   return s;
 }}
 function setSourceReported(s){{
   const op=s.repos.reduce((v,r)=>v+r.issue_open,0),cl=s.repos.reduce((v,r)=>v+r.issue_closed,0),tot=op+cl;
   sa('tileIssueOpen',op);sa('tileIssueTotal',tot);sa('tileIssuePct',pct(op,tot).toFixed(2)+'%');sa('tileIssueClosed',cl);
   sa('openBig',fmt(op));sa('closedBig',fmt(cl));sa('totalBig',fmt(tot));sa('openFrac',pct(op,tot).toFixed(2)+'% of '+tot);sa('closedFrac',pct(cl,tot).toFixed(2)+'% of '+tot);
   sa('rowOpen',op);sa('rowClosed',cl);sa('rowTotal',tot);sa('rowClosedPct',pct(cl,tot).toFixed(2)+'%');
   $('issueBarClosed').style.width=pct(cl,tot).toFixed(4)+'%';$('issueBarOpen').style.width=pct(op,tot).toFixed(4)+'%';
   const known=s.main_ci.total!==null;sa('tileCiSuccess',known?s.main_ci.success:'UNKNOWN');sa('tileCiFailed',known?s.main_ci.failure:'UNKNOWN');sa('tileCiTotal',known?s.main_ci.total:'UNKNOWN');sa('tileCiPct',known?pct(s.main_ci.success,s.main_ci.total).toFixed(2)+'%':'UNKNOWN');sa('ciEpochN',known?s.main_ci.success+' / '+s.main_ci.total:'UNKNOWN (nonterminal)');
   const bar=$('tileCiSuccess').closest('.card').querySelectorAll('.rail .seg');if(bar.length===2){{bar[0].style.width=known?pct(s.main_ci.success,s.main_ci.total).toFixed(4)+'%':'0%';bar[1].style.width=known?pct(s.main_ci.failure,s.main_ci.total).toFixed(4)+'%':'0%';}}
   const rmap=new Map(s.repos.map(r=>[r.repo,r]));
   const tbody=$('repoRows');tbody.querySelectorAll('tr').forEach(row=>{{const anchor=row.querySelector('td a');if(!anchor)return;const key=['GBOGEB/ABACUS','GBOGEB/CODEX','GBOGEB/cryoplant-project'].find(x=>x.endsWith('/'+anchor.textContent));if(!key)return;const rec=rmap.get(key);const c=rec.issue_closed,o=rec.issue_open,t=c+o;const tds=row.querySelectorAll('td');tds[1].textContent=o;tds[2].textContent=c;tds[3].textContent=t;tds[4].textContent=pct(c,t).toFixed(2)+'%';const bars=row.querySelectorAll('.rail .seg');if(bars.length===2){{bars[0].style.width=pct(c,t).toFixed(4)+'%';bars[1].style.width=pct(o,t).toFixed(4)+'%';}}}});
   $('population').querySelectorAll('.badge-row .pill').forEach((el,i)=>{{if(i===0)el.textContent='Closed '+cl+' / '+tot+' = '+pct(cl,tot).toFixed(2)+'%';if(i===1)el.textContent='Open '+op+' / '+tot+' = '+pct(op,tot).toFixed(2)+'%';}});
   const note=s.coverage===null||s.coverage===undefined?'coverage UNKNOWN (no canonical B0)':'source-reported '+pct(s.coverage.covered,s.coverage.eligible).toFixed(3)+'% (NOT independently verified)';
   sa('refreshStatus','Imported '+s.as_of_utc+'; provisional — '+note);
   sa('importEpochs',imported.length+' imported source-reported epoch(s). Latest '+s.abacus_main_sha.slice(0,12)+'…; do not use as approved native evidence without receipt checks.');
   // Rebind scenario to imported counters, preserving frozen native last-green coverage.
   d.clocks.issues.push({{total_open:op,total_closed:cl,total_issues:tot,repos:s.repos}});
   d.clocks.main_ci.push(s.main_ci);
   $('closeSlider').max=op;$('ciSlider').max=s.main_ci.failure??0;$('ciSlider').disabled=s.main_ci.failure===null;
   scenario();
 }}
 $('snapshotFile').addEventListener('change',async event=>{{
   const file=event.target.files?.[0];if(!file)return;
   try{{const s=validSnap(JSON.parse(await file.text()));if(imported.some(x=>x.abacus_main_sha===s.abacus_main_sha&&x.as_of_utc===s.as_of_utc))throw Error('Duplicate source SHA/timestamp');imported.push(s);setSourceReported(s);}}
   catch(e){{sa('refreshStatus','IMPORT REJECTED: '+e.message);}}
   event.target.value='';
 }});
 $('exportSession').addEventListener('click',()=>{{
   const payload={{schema:'codepurple.spine.w10.handover.v1',base_source_sha:d.clocks.main_ci[1].sha,observations_imported:imported,scenario:{{issues_closed_count:+$('closeSlider').value,ci_failures_recovered:+$('ciSlider').value,net_unique_existing_coverage_opportunities:+$('covSlider').value}},governed_admission:'HOLD',verified_browser_imports:false}};
   const blob=new Blob([JSON.stringify(payload,null,2)+'\\n'],{{type:'application/json'}});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='CODE_PURPLE_W10_HANDOVER_STATE.json';a.click();URL.revokeObjectURL(url);
 }});
 $('resetSession').addEventListener('click',()=>location.reload());
 }})();
 </script></body></html>'''

def w11_native_main_panel(history):
    """Post-freeze native B0 epoch is additive, never rewrites W10 SSOT."""
    source=BASE/'W11_OBSERVED_MAIN_EPOCH.json'
    if not source.is_file():
        raise ValueError('W11 independently observed main epoch is missing')
    epoch=json.loads(source.read_text(encoding='utf-8'))
    if epoch.get('schema')!='codepurple.spine.w11.observed-main.v1':
        raise ValueError('W11 main epoch schema invalid')
    old, new = epoch['measurements']
    prior=history['clocks']['main_coverage'][1]
    if old.get('source_sha')!=prior['sha'] or old['combined']['covered']!=prior['covered'] or old['combined']['eligible']!=prior['eligible']:
        raise ValueError('W11 post-freeze before-main does not join frozen W10 baseline')
    if epoch.get('governance')!={'merge_admission':'HOLD','security_waiver':False,'authority_transfer':False,'accepted_rex':None,'authorized_crew_launch':None,'causal_root_closure':None}:
        raise ValueError('W11 post-freeze epoch cannot override authoritative governance')
    for item in (old,new):
        for key in ('statements','branches'):
            measure=item[key]
            if type(measure['covered']) is not int or type(measure['eligible']) is not int or not(0<=measure['covered']<=measure['eligible']):
                raise ValueError('Invalid W11 native coverage numerator/denominator')
        covered=sum(item[k]['covered'] for k in ('statements','branches'))
        eligible=sum(item[k]['eligible'] for k in ('statements','branches'))
        if covered!=item['combined']['covered'] or eligible!=item['combined']['eligible'] or item['combined']['uncovered']!=eligible-covered or item['native_b0_terminal']!='success':
            raise ValueError('W11 source coverage receipt inconsistent with B0 terminal')
        if len(item['source_sha'])!=40 or len(item['archive_sha256'])!=64:
            raise ValueError('Native main source/artifact digest invalid')
    diff=epoch['comparison'];b=old['combined'];a=new['combined']
    if (diff['covered_delta'],diff['eligible_delta'],diff['uncovered_delta']) != (a['covered']-b['covered'],a['eligible']-b['eligible'],a['uncovered']-b['uncovered']):
        raise ValueError('W11 native before/after conservation failed')
    if diff['new_test_ids']<0 or diff['removed_test_ids']<0:
        raise ValueError('Invalid W11 added/removed test identity counts')
    target=epoch['next_conditional']
    if target.get('classification')!='FIXED_DENOMINATOR_SENSITIVITY_NOT_STATISTICAL_PREDICTION' or target.get('assumed_eligible')!=a['eligible']:
        raise ValueError('W11 N+1 target must remain conditional')
    nb=100*b['covered']/b['eligible'];na=100*a['covered']/a['eligible'];nf=100*(a['covered']+target['net_new_covered'])/a['eligible']
    if target['net_new_covered']>a['uncovered']:
        raise ValueError('N+1 scenario exceeds uncovered main opportunities')
    if abs(na-epoch['measurements'][1]['combined']['percent'])>1e-5:
        raise ValueError('W11 source-reported coverage percentage invalid')
    return f'''<section class="panel section" id="w11-main-epoch">
    <h2>11 · N−1 → N observed main coverage · N+1 conditional</h2>
    <p class="muted">Append-only <b>post-W10</b> native main verification. The frozen W10 cards above retain their original time stamp; this newer epoch does not rewrite them.</p>
    <div class="triple">
    <div class="epoch"><small>N−1 native main · earlier green</small><b>{nb:.3f}%</b><p>{N(b['covered'])} / {N(b['eligible'])} covered; {N(b['uncovered'])} uncovered</p></div>
    <div class="epoch"><small>N native main · terminal B0 success</small><b>{na:.3f}%</b><p>{N(a['covered'])} / {N(a['eligible'])} covered; {N(a['uncovered'])} uncovered</p></div>
    <div class="epoch next"><small>N+1 conditional, not forecast</small><b>{nf:.3f}%*</b><p>+{N(target['net_new_covered'])} unique covered opportunities if denominator remains {N(a['eligible'])}</p></div></div>
    <div class="badge-row">{pill('Covered +'+N(diff['covered_delta']),'pass')}{pill('Eligible +'+N(diff['eligible_delta']))}
      {pill('Uncovered '+N(diff['uncovered_delta']),'pass')}{pill('New IDs '+N(diff['new_test_ids'])+' / removed '+N(diff['removed_test_ids']),'pass')}
      {pill('Governed admission HOLD','blocked')}</div>
    <p class="muted">Main SHA: <code>{esc(new['source_sha'])}</code>. This is a changing-population portfolio improvement, not a fixed-code causal delta.</p>
    <div class="provenance"><a href="W11_OBSERVED_MAIN_EPOCH.json">Native source and family census</a>
    <a href="https://github.com/GBOGEB/ABACUS/actions/runs/{new['native_b0_run_id']}/artifacts/{new['native_b0_artifact_id']}" target="_blank" rel="noopener">Canonical B0 ZIP receipt</a></div>
    </section>'''

def w11_contract_panel(history):
    """Load executable contract by file path; verify published JSON parity."""
    import importlib.util
    spec=importlib.util.spec_from_file_location('g3cs_w11_contract',BASE/'spine_contract.py')
    if spec is None or spec.loader is None:
        raise ValueError('Missing pinned W11 typed graph validator')
    validator=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    outcome=validator.build(history)
    sources={
        'SPINE_DAG_W11.json':outcome['dag'],
        'SPINE_SIPOC_W11.json':outcome['sipoc'],
        'SPINE_CONTRACT_W11.json':{k:v for k,v in outcome.items() if k not in ('dag','sipoc')},
    }
    for filename, expected in sources.items():
        path=BASE/filename
        if not path.is_file() or json.loads(path.read_text(encoding='utf-8'))!=expected:
            raise ValueError('W11 published evidence contract drift: '+filename)
    return f'''<section class="panel section" id="w11-contract">
     <div class="split"><div><h2>10 · Tested SPINE → DAG → SIPOC convergence</h2>
       <p class="muted">W11 typed evidence overlay derived from the same <b>frozen W10 source</b>; source ownership and admission remain independent.</p></div>
       {pill('LOCAL CONTRACT · NATIVE QUALIFICATION SEPARATE','partial')}</div>
     <div class="issuefigure"><div><b>{outcome['nodes']}</b><small class="minor">Typed nodes · stage, repo and file assets</small></div>
       <div><b>{outcome['edges']}</b><small class="minor">Directed, non-mutating proof/reference edges</small></div>
       <div><b>{outcome['sipoc_rows']}</b><small class="minor">Source-bound SIPOC rows</small></div></div>
     <div class="badge-row">{pill('24 frozen assets','pass')}{pill('3 independent repo owners','pass')}
       {pill('0 accepted root closures claimed')}{pill('Admission HOLD','blocked')}</div>
     <p class="muted">Evidence path: repository owner → source/run/attempt → normalized CI and coverage
     → typed dependency graph → SIPOC → read-only projection → candidate CODEX/QPS REX return.
     A reference edge is never an authenticated worker launch or authorization.</p>
     <div class="provenance"><a href="SPINE_DAG_W11.json">Typed DAG JSON</a>
     <a href="SPINE_SIPOC_W11.json">SIPOC JSON</a><a href="SPINE_CONTRACT_W11.json">Source contract receipt</a>
     <a href="W10_FROZEN_HISTORY.json">Pinned W10 historical source</a></div>
     <div class="alert" style="margin-top:10px">The W10 source still has latest-main coverage UNKNOWN at its frozen epoch.
     The W11 local regression expansion requires an <b>exact-PR-head native B0 test-ID and coverage receipt</b>
     before any uplift or closure is credited. Safety and effective ruleset protections are noncompensating gates.</div>
     </section>'''


def w12_dependency_statistics_panel(history):
    # Source-reported structural statistics; no inferential approval.
    import importlib.util
    module_path=BASE/'dependency_metrics.py'
    spec=importlib.util.spec_from_file_location('g3cs_w12_dependency_metrics',module_path)
    if spec is None or spec.loader is None:
        raise ValueError('Missing W12 source-controlled statistics provider')
    provider=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(provider)
    epoch=json.loads((BASE/'W11_OBSERVED_MAIN_EPOCH.json').read_text(encoding='utf-8'))
    calculated=provider.build(history,epoch)
    pinned=BASE/'SPINE_STATS_W12.json'
    if not pinned.exists() or json.loads(pinned.read_text(encoding='utf-8'))!=calculated:
        raise ValueError('W12 typed statistics drift from pinned source inputs')
    graph=calculated['graph']
    times=calculated['temporal']
    inference=calculated['inference']
    if inference['inference_ready'] or inference['p_values'] is not None:
        raise ValueError('Unqualified inferential statistic promoted')
    top=graph['top_structural_betweenness'][:5]
    rank_rows=''.join(f'<tr><td><code>{esc(x["id"])}</code></td><td>{x["in_degree"]} / {x["out_degree"]}</td><td>{x["structural_betweenness"]:.5f}</td></tr>' for x in top)
    model_rows=''.join('<tr><td><b>'+esc(name)+'</b></td><td>NOT QUALIFIED</td><td>'+esc(inference[name]['why'])+'</td></tr>' for name in ('PCA','ANOVA','MANOVA','Bradley_Terry_BT','bootstrap_temporal','DNN_temporal'))
    deltas=times['deltas']
    changes=', '.join(f'{x["portfolio_coverage_pp_delta"]:+.3f} pp / {x["uncovered_delta"]:+d} debt' for x in deltas)
    return f'''<section class="panel section" id="w12-stats">
      <div class="split"><div><h2>12 · N+i statistical observatory · typed DAG + SIPOC + SPINE</h2>
      <p class="muted">Actual **descriptive** structural metrics and serial native-main epochs. Graph structure is not a set of independent experimental observations.</p></div>
      {pill('DESCRIPTIVE ONLY · NO INFERENCE','partial')}</div>
      <div class="issuefigure">
        <div><b>{graph['nodes']} / {graph['edges']}</b><small class="minor">Validated nodes / typed edges</small></div>
        <div><b>{graph['directed_density']*100:.2f}%</b><small class="minor">Directed density (46 / 1,332 possible pairs)</small></div>
        <div><b>{graph['distinct_source_to_customer_paths']}</b><small class="minor">Structural ingest → consumer routes</small></div>
        <div><b>{graph['longest_dependency_path_hops']}</b><small class="minor">Longest dependency path, hops — NOT runtime</small></div>
      </div>
      <p class="muted"><b>All-path structural bottlenecks:</b> {esc(', '.join(graph['all_path_mandatory_nodes']))}.</p>
      <div class="badge-row">{pill('3 green-main coverage epochs')}{pill('2 descriptive transitions')}
       {pill('5 mandatory routing nodes')}{pill('Inferential methods NOT QUALIFIED','blocked')}</div>
      <div class="cols2" style="margin-top:12px">
       <div><h3>Structural betweenness & fan-in / fan-out</h3><div class="tablewrap"><table><thead><tr><th>Node</th><th>In / Out</th><th>Normalized betweenness</th></tr></thead><tbody>{rank_rows}</tbody></table></div></div>
       <div><h3>Temporal trend, descriptive only</h3>
        <p class="muted">N−2 → N−1 → N coverage: <b>{times['observed_main_percentages'][0]:.3f}% → {times['observed_main_percentages'][1]:.3f}% → {times['observed_main_percentages'][2]:.3f}%</b>.</p>
        <p class="muted">Absolute uncovered: <b>{times['observed_uncovered_counts'][0]:,} → {times['observed_uncovered_counts'][1]:,} → {times['observed_uncovered_counts'][2]:,}</b>.</p>
        <p class="muted">Sequential portfolio change: {changes}. These observations have <b>different source/coverage denominators</b>; they are not matched causal estimates.</p>
       </div></div>
      <h3>Statistical readiness — independent wave blocks required</h3><div class="tablewrap"><table><thead><tr><th>Method</th><th>DoV</th><th>Why not yet valid</th></tr></thead><tbody>{model_rows}</tbody></table></div>
      <p class="muted">BT is provisionally interpreted as <b>Bradley–Terry paired-strategy ranking</b>. Bayesian tracking and cluster/block bootstrap are separately gated. The next event collector must measure actual source-run-attempt-job-trigger latencies and disjoint wave IDs before temporal inference.</p>
      <div class="provenance"><a href="SPINE_STATS_W12.json">Full computed graph statistics JSON</a>
       <a href="SPINE_DAG_W11.json">Pinned DAG</a><a href="SPINE_SIPOC_W11.json">Process SIPOC</a><a href="W11_OBSERVED_MAIN_EPOCH.json">Exact-main temporal receipts</a></div>
      <div class="alert">N+i is append-only. No speculative p-values, PCA attribution, control limits, posterior probability, authenticated Crew launch, REX acceptance, or governed merge credit is generated by this view.</div>
      </section>'''



def main():
    p=argparse.ArgumentParser();p.add_argument('--history',type=Path,default=BASE/'W10_FROZEN_HISTORY.json');p.add_argument('--outdir',type=Path,default=BASE)
    args=p.parse_args();d=checked_history(json.loads(args.history.read_text(encoding='utf-8')))
    out=args.outdir;out.mkdir(parents=True,exist_ok=True)
    svg=(BASE/'CODE_PURPLE_W10_REPO_SPINE.svg').read_text(encoding='utf-8')
    # Strip XML declaration and DOCTYPE; inline SVG keeps linked nodes, no external assets.
    svg=svg[svg.find('<svg'):]
    body=make_html(d,svg)
    if body.count('<footer>')!=1:
        raise ValueError('W10 HTML footer anchor missing or ambiguous')
    body=body.replace('<footer>',w11_contract_panel(d)+w11_native_main_panel(d)+w12_dependency_statistics_panel(d)+'<footer>',1)
    html_file=out/'CODE_PURPLE_GLOBAL_SPINE_W10.html';html_file.write_text(body,encoding='utf-8')
    (out/'index.html').write_bytes(html_file.read_bytes())  # exact byte-identical HTML review surface
    issue=d['clocks']['issues'][-1];ci0,ci1=d['clocks']['main_ci'][-2:];pr0,pr1=d['clocks']['pr_ci'][-2:];a,b=d['clocks']['main_coverage'][:2]
    report=f'''# CODE PURPLE · W10 recursive Global SPINE handover

Observation source: three-repo **subset**, not complete federation. Full exact ABACUS main: `{ci1['sha']}`.

## N−1 / N / N+1

| KPI (explicit unit/denominator) | N−1 measured | N measured | N+1 conditional scenario, NOT predicted/verified |
|---|---|---|---|
| Ordinary issues, 3 repos | UNKNOWN (prior matched scope absent) | **{issue['total_open']} OPEN + {issue['total_closed']} CLOSED = {issue['total_issues']}**, {pct(issue['total_open'],issue['total_issues']):.2f}% open | **{issue['total_open']-4} / {issue['total_issues']} open** if 4 close and zero open |
| Main push CI success | **{ci0['success']}/{ci0['total']} = {pct(ci0['success'],ci0['total']):.2f}%** (different runs) | **{ci1['success']}/{ci1['total']} = {pct(ci1['success'],ci1['total']):.2f}%** | **{ci1['success']+2}/{ci1['total']}** if 2 failures recover and no new runs |
| Combined main coverage | **{pct(a['covered'],a['eligible']):.3f}%**, earlier green | **{pct(b['covered'],b['eligible']):.3f}%**, last green; latest main UNKNOWN | **{pct(b['covered']+522,b['eligible']):.3f}%** from last green if +522 covered and unchanged denominator |
| PR success | **{pr0['success']}/{pr0['total']}** #2237 | **{pr1['success']}/{pr1['total']}** #2239, Safety RED | **20/20** if Safety root solved and no other failures |

The issue denominator is **478 ordinary issues**: closed **373 = 78.03%**, open **105 = 21.97%**. No matched N−1 three-repo issue snapshot exists. PR totals are not added to ordinary issues. The issue percent is a workflow backlog descriptor, not deduplicated defect/root closure.

## Repo/subfolder/bridge wireframe

```text
GBOGEB/CODEX  [GOVERNANCE: own main]
  mission_control/mycelium/{{control_manifest.yaml, execution_gateway_contract.yaml}}
  scripts/missioncontrol_authenticated_transport.py  (stage only, mutation disabled)
  federation/rex/REPO_REX_RETURN_TEMPLATE_v1.yaml
           ^ typed observational references/returns (NO authority transfer)
GBOGEB/ABACUS [RUNTIME: own main]
  federation/manifest.yaml
  .github/workflows/mip-coverage-evidence.yml  --> native run/artifacts
  MIP/G3CS_CONVERGENCE_V2/
    source/G3CS_CONVERGENCE_INPUT.json
    tools/{{converge.py,serial_main_pair.py,postmerge_gate_receipt.py}}
    output/{{G3CS_CONVERGENCE_DASHBOARD.html,DAG.json,SIPOC.svg,...}}
    tests/test_postmerge_gate_receipt.py  <-- current canonical B0 discovery GAP
  scripts/cbd_matched_coverage_delta.py
  tests/test_g3cs_source_mutations.py
           ^ registered auxiliary QPS / no engineering-truth mutation
GBOGEB/cryoplant-project [ENGINEERING TRUTH: own main]
  federation/manifest.yaml
  federation/golden_thread/CONTRACT_v1.yaml
  federation/acceptance_dashboard/index.html

New W10 local/PR-candidate projection:
  CODE_PURPLE_GLOBAL_SPINE_W10.html  <-- generates from immutable W10_HISTORY.json
  refresh_w10_spine.py             <-- GitHub API GET + native B0 artifact proof
  CODE_PURPLE_W10_REPO_SPINE.mmd and .svg  <-- governed path/link visualization
```

Three independent repositories are **not** subfolders of ABACUS. Repo-local folders do not automatically represent git submodules. CODEX's `EMBEDDED_REPOS.md` explicitly warns that a definitive local gitlink audit was not performed; a `git ls-files --stage` local check is required for legacy nested dirs. GitHub reference paths above were inspected on exact head commits.

## Tight uncovered-count chart calibration

Historical N−1 **{a['uncovered']:,}** → N **{b['uncovered']:,}**. Integer axis 17,025–17,055 (tick step 5), widened 112px left margin and inset first data point. The hypothetical **16,524** is deliberately NOT drawn on this zoomed observed chart; it is shown separately, because doing so would erase useful 17k granularity. Never shorten values to `17k` at this scale.

## Static + recursive refresh semantics

1. Frozen JSON is the source for a reproducible offline HTML. All GitHub links use the independently read exact SHA for their owning repository.
2. Browser file-import accepts `codepurple.spine.w10.snapshot.v1` and recomputes scenario tiles in memory, but an imported file remains **source-reported/unverified** until pinned native proof is independently checked.
3. `refresh_w10_spine.py` uses read-only GitHub REST calls (authenticated through `GITHUB_TOKEN` in the environment when needed), checks three ordinary-issue denominators, exact-source push-run totals, and only issues coverage numbers if it validates a successful same-SHA canonical B0 artifact with SHA256 digest.
4. New observations must be appended, never silently overwrite historical snapshots. Repeatable renderer: `python build_global_spine_w10.py --history CODE_PURPLE_W10_SPINE_HISTORY.json`.
5. Each refresh emits an exact current main SHA and P0 status. No merge/launch/REX/review credit from this HTML; governance remains `HOLD`.

## Next admissible edges

Finish native collection of the 14 nested W7 tests, retain independent Safety RED, and require authorized restoration of effective required checks/independent approval/RED canary. Test four disjoint coverage fronts only with owner ownership and native receipts. Accept root/BD closures separately from ordinary issue count. Re-measure latest merged-main statements, branches and uncovered debt after *correctly* governed serial admission. The N+1 numerical scenarios are **hypothetical** and not machine forecasts.

`MERGE_ADMISSION=HOLD` / `SECURITY_WAIVER=false` / `AUTHORITY_TRANSFER=false`.
'''
    md=out/'CODE_PURPLE_GLOBAL_SPINE_W10_HANDOVER.md';md.write_text(report,encoding='utf-8')
    metrics={'schema':'codepurple.spine.w10.metrics.v1','source_history_sha256':hashlib.sha256(args.history.read_bytes()).hexdigest(),'html_sha256':hashlib.sha256(html_file.read_bytes()).hexdigest(),'history_source':args.history.name,'issue_closed_share':pct(issue['total_closed'],issue['total_issues']),'issue_open_share':pct(issue['total_open'],issue['total_issues']),'prior_ci_share':pct(ci0['success'],ci0['total']),'current_ci_share':pct(ci1['success'],ci1['total']),'future_ci_conditional_share':pct(ci1['success']+2,ci1['total']),'current_main_coverage':None,'last_green_main_coverage':pct(b['covered'],b['eligible']),'future_green_fixed_denominator_scenario':pct(b['covered']+522,b['eligible']),'native_main_admission':'HOLD'}
    js=out/'CODE_PURPLE_GLOBAL_SPINE_W10_METRICS.json';js.write_text(json.dumps(metrics,indent=2)+'\n',encoding='utf-8')
    for path in [html_file,md,js,out/'index.html']:print(path, path.stat().st_size)

if __name__=='__main__':main()