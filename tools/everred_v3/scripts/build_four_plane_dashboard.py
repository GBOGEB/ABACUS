#!/usr/bin/env python3
"""Deterministic, standalone four-plane evidence review dashboard."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]


def build(snapshot: Path, target: Path) -> dict:
    obj = json.loads(snapshot.read_text(encoding="utf-8"))
    if obj.get("schema") != "abacus.everred.four_plane.preflight.v1":
        raise ValueError("unknown preflight schema")
    base = obj["source_binding"]
    sha = base["source_sha"]
    if len(sha) != 40:
        raise ValueError("missing source pin")
    count = obj["joined_census"]["observation_count"]
    tasks = obj["dispatch_preview"]["tasks"]
    if count != len(obj["receipts"]) or len(tasks) != obj["plan"]["task_count"]:
        raise ValueError("dashboard source count mismatch")
    digest = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    svg = []
    for name in ("06_four_plane_execution.svg", "07_four_plane_sipoc.svg"):
        s = (BASE / "diagrams" / name).read_text(encoding="utf-8")
        svg.append(s[s.index("<svg") :])
    source_json = json.dumps(obj, sort_keys=True, ensure_ascii=True).replace(
        "<", "\\u003c"
    )
    source_json = source_json.replace("</", "<\\/")
    titles = ("Execution DAG", "SIPOC ownership and evidence flow")
    arts = "".join(
        '<article class="diagram"><h3>' + label + "</h3>" + s + "</article>"
        for label, s in zip(titles, svg)
    )
    page = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="EVERRED V3.1 four-plane dashboard"><meta name="source-digest" content="DIGEST">
<title>EVERRED V3.1 | Four-plane runtime evidence</title>
<style>
:root{font-family:Inter,system-ui,Segoe UI,Arial,sans-serif;color:#1d2b42;background:#f5f8fc;font-synthesis:none}
*{box-sizing:border-box}body{margin:0}header{background:#10223d;color:#fff;padding:34px max(25px,calc((100vw - 1350px)/2)) 44px}
.eyebrow{font-size:12px;letter-spacing:.17em;font-weight:750;text-transform:uppercase;color:#a7c6ed}
h1{font-size:clamp(27px,4vw,42px);font-weight:800;letter-spacing:-.035em;margin:8px 0}
.lead{color:#bed0e9;max-width:900px;line-height:1.6}.line{display:flex;flex-wrap:wrap;gap:9px;margin-top:20px}
.pill{border:1px solid #5c7999;border-radius:30px;padding:6px 12px;font-size:12px;color:#f2f7ff}
.pill.hold{background:#553b25;color:#ffdda5;border-color:#b78142}
main{max-width:1415px;margin:auto;padding:24px}section{margin-bottom:25px}
.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:13px;margin-top:-47px;position:relative}
.metric,.panel,.diagram{background:white;border:1px solid #dbe4f2;border-radius:14px;box-shadow:0 8px 24px #17294208}
.metric{padding:20px;min-width:0}.metric strong{display:block;font-size:29px;letter-spacing:-.03em;color:#174b89;margin:5px 0}
.label{font-size:12px;color:#5b6a7a;font-weight:700;letter-spacing:.05em;text-transform:uppercase}
.metric small{color:#67778c}.panel{padding:21px;overflow:hidden}h2{font-size:20px;letter-spacing:-.02em;margin:1px 0 15px}h3{font-size:15px;color:#344860;margin:0 0 12px}
.controls{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:15px}
button,label.upload{font:inherit;border-radius:8px;border:1px solid #bfd1ea;padding:9px 13px;background:#f3f8ff;color:#174b89;cursor:pointer;font-size:13px;font-weight:650}
button[aria-pressed=true]{background:#174b89;color:white;border-color:#174b89}button:focus-visible,label.upload:focus-within{outline:3px solid #77a5ff}
input[type=file]{position:absolute;left:-99999px}.diagram-grid{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(0,1fr);gap:16px}
.diagram{padding:18px;min-width:0;overflow:hidden}.diagram svg{width:100%;height:auto;max-height:720px;display:block}
.table-scroll{width:100%;overflow-x:auto}table{width:100%;border-collapse:collapse;text-align:left;min-width:650px}th,td{border-bottom:1px solid #e7eef6;padding:10px 12px;font-size:13px}th{font-size:11px;color:#627387;text-transform:uppercase;letter-spacing:.05em}tbody tr:hover{background:#f4f8ff}
.status{font-size:11px;font-weight:750;border-radius:20px;padding:4px 10px;white-space:nowrap}
.status.READY_TO_REQUEST{background:#e7f6ec;color:#1e7747}.status.WAITING_FOR_EVIDENCE{background:#fff5df;color:#8e5e09}
.status.HOLD_REVIEW,.status.BLOCKED_UPSTREAM_RED{background:#ffe8e8;color:#963b3b}
.note{font-size:13px;color:#5c6b7d;line-height:1.65}.provenance{font-size:12px;color:#54637b;overflow-wrap:anywhere}
footer{max-width:1415px;margin:auto;padding:5px 24px 35px;color:#627387;font-size:12px}
@media(max-width:950px){.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.diagram-grid{grid-template-columns:1fr}}
@media(max-width:500px){header{padding:26px 19px 52px}main{padding:17px}.metrics{gap:8px;margin-top:-42px}.metric{padding:13px}.metric strong{font-size:24px}.panel{padding:15px}}
</style></head><body>
<header><div class="eyebrow">ABACUS / Governed recovery / V3.1 Alpha</div><h1>Four-plane operational evidence</h1>
<p class="lead">Native diagnostic and runtime observations, YAML execution topology, LDAB correlation and independent admission. No historical, imported or local result is an automatic merge approval.</p>
<div class="line"><span class="pill hold">Admission: HOLD</span><span class="pill">Local reproducibility only</span><span class="pill">GitHub exact-run corroboration pending</span></div></header>
<main><section class="metrics" aria-label="Current counters">
<article class="metric"><span class="label">Joined observations</span><strong id="metricObservations">COUNT</strong><small>Local source-bound declarations</small></article>
<article class="metric"><span class="label">DAG tasks</span><strong id="metricTasks">TASKS</strong><small>Dependency validated</small></article>
<article class="metric"><span class="label">Confirmed LDAB causes</span><strong id="metricRoots">UNKNOWN</strong><small>No causal acceptance implied</small></article>
<article class="metric"><span class="label">RHEL / Docker proof</span><strong id="metricRuntime">UNKNOWN</strong><small>Native remote proof required</small></article>
</section><section class="panel"><h2>Source provenance and interactive execution plan</h2>
<p class="provenance">Snapshot digest: <code id="digest">DIGEST</code> · Declared source SHA: <code id="sha">HEAD_PLACEHOLDER</code></p>
<div class="controls" role="group" aria-label="Filter execution tasks"><button data-plane="all" aria-pressed="true">All planes</button>
<button data-plane="diagnostic" aria-pressed="false">Diagnostic</button><button data-plane="runtime" aria-pressed="false">Runtime</button>
<button data-plane="orchestration" aria-pressed="false">Orchestration</button><button data-plane="evidence" aria-pressed="false">Evidence</button>
<label class="upload">Import JSON snapshot (unverified)<input type="file" id="importJson" accept=".json,application/json"></label></div>
<div class="table-scroll"><table><thead><tr><th>Task / work package</th><th>Plane</th><th>Owner</th><th>Dependencies</th><th>Readiness</th></tr></thead><tbody id="taskRows"></tbody></table></div>
<p class="note" id="importStatus">Snapshots are operator review aids. Imports never change trust, governance, branch protection or admission state.</p></section>
<section><h2>Architecture and SIPOC</h2><div class="diagram-grid">ARTS</div></section>
<section class="panel"><h2>Acceptance boundaries</h2><p class="note">Source and executed SHA are independent fields. A CLI installation is not an executing debug session; a Docker file is not a running container; a port observed during a temporary probe is not a persistent listener. RHEL is UNKNOWN unless an authenticated RHEL runner receipt arrives. The existing ABACUS policy JSON and mesh YAML remain their respective authorities.</p>
<p class="note">Only an external eligible reviewer plus protected-branch security and CI controls may authorize merge. <strong>This dashboard cannot.</strong></p></section></main>
<footer>EVERRED V3.1 · Review-only visualization · Generated from one four-plane preflight JSON · No live polling or credentials.</footer>
<script type="application/json" id="embeddedSnapshot">DATA</script>
<script>
"use strict";
let current=JSON.parse(document.getElementById('embeddedSnapshot').textContent);
let filter='all';const rows=document.getElementById('taskRows');
function node(tag, text){let el=document.createElement(tag);el.textContent=String(text??'UNKNOWN');return el;}
function render(){
 const tasks=current.dispatch_preview.tasks;
 document.getElementById('metricObservations').textContent=current.joined_census.observation_count;
 document.getElementById('metricTasks').textContent=tasks.length;
 document.getElementById('metricRoots').textContent='UNKNOWN';
 document.getElementById('metricRuntime').textContent='UNKNOWN';
 document.getElementById('sha').textContent=current.source_binding.source_sha;
 rows.replaceChildren();
 for(const row of tasks){if(filter!=='all'&&row.plane!==filter)continue;
   const tr=document.createElement('tr');
   for(const v of [row.id,row.plane,row.actor,row.needs.join(' · ')||'None'])tr.appendChild(node('td',v));
   const cell=node('td','');let badge=node('span',row.state);badge.className='status '+row.state;cell.appendChild(badge);tr.appendChild(cell);rows.appendChild(tr);
 }
}
for(const btn of document.querySelectorAll('button[data-plane]')){
 btn.addEventListener('click',()=>{filter=btn.dataset.plane;for(const b of document.querySelectorAll('button[data-plane]'))b.setAttribute('aria-pressed',String(b===btn));render();});
}
document.getElementById('importJson').addEventListener('change',async e=>{
 const file=e.target.files[0];if(!file)return;
 try {if(file.size>2e6)throw Error('Snapshot too large');let d=JSON.parse(await file.text());
  if(d.schema!=='abacus.everred.four_plane.preflight.v1'||!Array.isArray(d.dispatch_preview?.tasks)||
     !Array.isArray(d.receipts)||!d.source_binding?.source_sha||d.claims?.admission!=='HOLD'||
     d.joined_census?.observation_count!==d.receipts.length)throw Error('Invalid/untrusted snapshot contract');
  current=d;filter='all';for(const b of document.querySelectorAll('button[data-plane]'))b.setAttribute('aria-pressed',String(b.dataset.plane==='all'));
  document.getElementById('importStatus').textContent='Imported locally for review — MANUAL_UNVERIFIED. No admission credit.';render();
 }catch(err){document.getElementById('importStatus').textContent='Import rejected: '+err.message;}
 e.target.value='';
});
render();
</script></body></html>"""
    page = (
        page.replace("DIGEST", digest)
        .replace("COUNT", str(count))
        .replace("TASKS", str(len(tasks)))
    )
    page = (
        page.replace("DIGEST", digest)
        .replace("HEAD_PLACEHOLDER", html.escape(sha))
        .replace("ARTS", arts)
        .replace("DATA", source_json)
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")
    return {
        "html": target.as_posix(),
        "html_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "snapshot_sha256": digest,
        "observations": count,
        "tasks": len(tasks),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--snapshot", type=Path, default=BASE / "data/four_plane_preflight.json"
    )
    p.add_argument(
        "--output", type=Path, default=BASE / "dashboard/four_plane_status.html"
    )
    x = p.parse_args()
    print(json.dumps(build(x.snapshot, x.output), sort_keys=True))


if __name__ == "__main__":
    main()
