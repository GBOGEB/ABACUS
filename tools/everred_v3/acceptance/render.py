"""Offline human + machine acceptance debt dashboards and immutable receipts."""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path

from .core import canonical, digest, require


def esc(value):
    return html.escape(str(value), quote=True)


def markdown_debt(projection):
    lines = [
        "# CODE PURPLE - acceptance debt (read-only projection)",
        "",
        "**Evidence checks are NOT admission approval.** A checked observation means",
        "a source-bound receipt was recorded under the frozen comparison context.",
        "The native runner, security owner and independent reviewer must still",
        "reconfirm current exact-head evidence; `main` admission remains **HOLD**.",
        "",
        "| ID | Evidence | Admission | Repository | Acceptance item | State |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in projection["obligations"]:
        ev = "[x]" if item["evidence_checked"] else "[ ]"
        adm = "[x]" if item["admission_checked"] else "[ ]"
        title = item["title"].replace("|", "\\|").replace("\n", " ")
        lines.append("| " + " | ".join((item["id"], ev, adm, item["repo"],
                                       title, item["evidence_state"])) + " |")
    lines.extend(["", "## Evidence links (source-bound observation only)", ""])
    for item in projection["obligations"]:
        if item["latest_evidence_url"]:
            lines.append("- " + item["id"] + ": [read native source](" +
                         item["latest_evidence_url"] + ") on head `" +
                         item["latest_subject_sha"] + "`; status `" +
                         item["evidence_state"] + "`.")
    lines.extend(["", "Unknown values are `null`, not zero. Root closure,",
                  "Crew dispatch, current-main and diff coverage are unverified.", ""])
    return "\n".join(lines)


def render_html(projection, graph, sipoc, temporal, local_testflight=None):
    metrics = projection["metrics"]
    require(projection["admission"] == "HOLD" and sipoc["admission"] == "HOLD",
            "dashboard cannot represent unadmitted source as accepted")
    cards = [
        ("Evidence observed", str(metrics["evidence_observed"]) + " / " + str(metrics["obligations"])),
        ("Current stale", metrics["evidence_stale"]),
        ("Blocked / dependencies", metrics["evidence_blocked"]),
        ("Admission", "HOLD"),
        ("Main coverage", "UNKNOWN"),
    ]
    kpis = "".join("<article class='kpi'><span>" + esc(name) + "</span>"
                   "<strong>" + esc(value) + "</strong></article>"
                   for name, value in cards)
    rows = []
    for item in projection["obligations"]:
        observed = " checked" if item["evidence_checked"] else ""
        admitted = " checked" if item["admission_checked"] else ""
        link = ("<a target='_blank' rel='noopener noreferrer' href='" +
                esc(item["latest_evidence_url"]) + "'>Evidence source</a>"
                if item["latest_evidence_url"] else "<span class='muted'>No receipt</span>")
        evidence = item["latest_evidence_url"] or ""
        rows.append(
            "<article class='debt' data-repo='" + esc(item["repo"]) +
            "' data-status='" + esc(item["evidence_state"]) + "' data-kind='" +
            esc(item["kind"]) + "'><div class='debt-head'><div>"
            "<span class='micro'>" + esc(item["id"]) + " &middot; " +
            esc(item["repo"]) + "</span><h3>" + esc(item["title"]) +
            "</h3></div><span class='pill state-" + esc(item["evidence_state"]) +
            "'>" + esc(item["evidence_state"]) + "</span></div>"
            "<div class='checks'><label title='Structural evidence captured, not authenticated approval'>"
            "<input type='checkbox' disabled" + observed +
            "> Evidence captured</label><label title='Never automatically marked by this projection'>"
            "<input type='checkbox' disabled" + admitted +
            "> Independently admitted</label></div>"
            "<details><summary>Provenance and dependency detail</summary><p>"
            "Scope: <code>" + esc(item["scope"]) + "</code> &middot; Kind: <code>" +
            esc(item["kind"]) + "</code></p><p>Requires: " +
            esc(", ".join(item["depends_on"]) or "none") + "</p>"
            "<p>Observed head: <code>" + esc(item["latest_subject_sha"] or "UNKNOWN") +
            "</code></p><p>Epoch: <code>" + esc(item["latest_epoch"] if item["latest_epoch"] is not None else "UNKNOWN") +
            "</code></p><p>" + link + "</p></details></article>"
        )
    frontier = "".join(
        "<tr><td>" + esc(x["id"]) + "</td><td>" +
        esc(x["observed_state"]) + "</td><td>" +
        esc(x["downstream_dependency_reach"]) + "</td></tr>"
        for x in graph["blocked_frontier"][:14]
    )
    pulse_rows = "".join(
        "<tr><td>" + esc(x["pulse"]) + "</td><td>" +
        esc(x["observed_evidence"]) + "/" + esc(x["obligations"]) +
        "</td><td>" + esc(x["state_changes_from_previous"] if x["state_changes_from_previous"] is not None else "UNKNOWN") +
        "</td><td>" + esc(round(x["descriptive_status_stability"] * 100, 1)
                              if x["descriptive_status_stability"] is not None else "UNKNOWN") +
        "</td></tr>" for x in temporal["pulses"]
    )
    sipoc_rows = "".join(
        "<tr><td>" + esc(repo) + "</td><td>" + esc(s["plane"]) +
        "</td><td>" + esc(s["consumer"]) + "</td></tr>"
        for repo, s in sipoc["sources"].items()
    )
    tests = "" if not local_testflight else (
        "<p class='muted'>Local standalone testflight: " +
        esc(local_testflight.get("tests_passed", "UNKNOWN")) + " cases, " +
        esc(local_testflight.get("coverage_percent", "UNKNOWN")) +
        "% module statement/branch coverage; not GitHub admission.</p>"
    )
    # All snapshot values are escaped server-side; no dynamic remote fetch is used.
    return """<!doctype html><html lang='en'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<meta name='referrer' content='no-referrer'>
<title>CODE PURPLE | Acceptance debt and federation DAG</title>
<style>
:root{color-scheme:light;--ink:#172a42;--muted:#52677f;--navy:#0c263e;--blue:#1663b5;--line:#dce4ed;--paper:#fff;--bg:#f4f7fb}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.55 system-ui,-apple-system,Segoe UI,sans-serif}
a{color:#075caa}a:focus-visible,select:focus-visible,input:focus-visible{outline:2px solid #f5aa2b;outline-offset:3px}
header{background:linear-gradient(120deg,#0b2238,#173e5e);padding:35px max(calc((100vw - 1220px)/2),24px);color:white}
header h1{font-size:32px;letter-spacing:-.7px;margin:7px 0 12px}header p{max-width:850px;color:#d8e9f7;font-size:15px}
.eyebrow{font-size:11px;letter-spacing:2px;text-transform:uppercase;font-weight:800;color:#9fc9ef}
main{max-width:1220px;margin:0 auto;padding:24px}h2{font-size:20px;letter-spacing:-.3px;margin:30px 0 12px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px}
.kpi{border:1px solid var(--line);background:var(--paper);padding:15px 17px;border-radius:10px;box-shadow:0 2px 8px #1935510a}
.kpi span{display:block;color:var(--muted);font-size:12px}.kpi strong{display:block;font-size:26px;font-variant-numeric:tabular-nums}
.warning{border-left:4px solid #a86c15;background:#fffaf0;padding:12px 15px;margin:18px 0;border-radius:0 8px 8px 0}
.filters{display:flex;flex-wrap:wrap;gap:12px;margin:18px 0}label.filter{display:flex;flex-direction:column;gap:5px;min-width:195px;font-weight:700}
select,input[type=search]{font:inherit;border:1px solid #bacbdc;background:#fff;border-radius:7px;padding:9px 10px}
.debts{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,480px),1fr));gap:12px}
.debt{background:#fff;border:1px solid var(--line);border-radius:10px;padding:15px}
.debt-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}.debt h3{font-size:15px;margin:3px 0 8px}
.micro{font-size:11px;color:var(--muted);font-weight:700}.pill{font-size:11px;font-weight:800;padding:4px 7px;background:#edf1f6;border-radius:15px;white-space:nowrap}
.state-OBSERVED{background:#e1f4e9;color:#13623f}.state-STALE{background:#fff1d9;color:#8e5a09}.state-BLOCKED{background:#fbe3e4;color:#94363b}
.checks{display:flex;gap:15px;flex-wrap:wrap;margin:7px 0 9px}.checks label{font-size:12px;color:#31475f}.checks input{accent-color:#18865a}
details{border-top:1px solid var(--line);padding-top:7px;color:var(--muted)}summary{cursor:pointer;font-weight:650;color:#145c9c}
code{overflow-wrap:anywhere;font-size:12px}table{width:100%;border-collapse:collapse;background:#fff}th,td{padding:10px 12px;border-bottom:1px solid var(--line);text-align:left}th{font-size:12px;background:#eaf0f7}
.columns{display:grid;grid-template-columns:1fr 1fr;gap:18px}.panel{border:1px solid var(--line);border-radius:10px;background:#fff;padding:14px;overflow:auto}
.muted{color:var(--muted)}footer{margin-top:36px;border-top:1px solid var(--line);padding:16px 0;color:var(--muted)}.empty{margin:10px 0;color:var(--muted)}
@media(max-width:760px){header{padding:25px 20px}header h1{font-size:25px}main{padding:16px}.columns{grid-template-columns:1fr}.debts{grid-template-columns:1fr}}
</style></head><body>
<header><div class='eyebrow'>ABACUS / CODEX / QPS  |  DMAIC + MIP</div><h1>Acceptance debt &amp; federation evidence</h1>
<p>Source-bound, human-readable and machine-readable obligations. Two separate controls: evidence captured and independently admitted. This is a frozen review snapshot, not live GitHub CI.</p></header><main>
<section class='cards'>""" + kpis + """</section>
<div class='warning'><strong>Admission HOLD.</strong> A recorded pass is not a certified pass. Previous-head receipts become stale when the source/base/policy/epoch changes; no reviewer or security approval is manufactured.</div>
<h2>Acceptance debt register</h2><div class='filters'>
<label class='filter' for='repoFilter'>Repository<select id='repoFilter'><option value='all'>All federation repos</option><option value='GBOGEB/ABACUS'>ABACUS</option><option value='GBOGEB/CODEX'>CODEX</option><option value='GBOGEB/cryoplant-project'>QPS</option></select></label>
<label class='filter' for='stateFilter'>Evidence state<select id='stateFilter'><option value='all'>All states</option><option>OBSERVED</option><option>MISSING</option><option>STALE</option><option>BLOCKED</option><option>WITHHELD</option><option>BLOCKED_DEPENDENCY</option></select></label>
<label class='filter' for='searchFilter'>Search title or ID<input type='search' id='searchFilter' placeholder='Filter debts'></label></div>
<p class='muted' id='shownCount' aria-live='polite'></p><div class='debts' id='debtItems'>""" + "".join(rows) + """</div>
<h2>DAG dependency frontier &amp; change waves</h2><div class='columns'><section class='panel'><h3>Unblocking reach (descriptive)</h3>
<p class='muted'>Downstream node count, not number of roots fixed or probability of success.</p>
<table><thead><tr><th>Debt</th><th>State</th><th>Reach</th></tr></thead><tbody>""" + frontier + """</tbody></table>
</section><section class='panel'><h3>Three local replay pulses</h3>
<p class='muted'>Frozen evidence revealed in stages. Not three independent Github experiments.</p>
<table><thead><tr><th>Pulse</th><th>Evidence</th><th>State changes</th><th>Stable %</th></tr></thead><tbody>""" + pulse_rows + """</tbody></table></section></div>
<h2>SIPOC and authority planes</h2><div class='panel'><table><thead><tr><th>Supplier</th><th>Plane</th><th>Consumer</th></tr></thead><tbody>""" + sipoc_rows + """</tbody></table>
<p class='muted'>All source-bound edges are observations, never automatic security approval or root closure.</p></div>
""" + tests + """
<footer>Data provenance: exact-source observation ledger; no network calls; SHA-256 receipts accompany the bundle. Independent trial count, current-main coverage, diff coverage, root closures and authenticated dispatch remain UNKNOWN.</footer>
</main><script>
(function(){'use strict';const repo=document.getElementById('repoFilter'),state=document.getElementById('stateFilter'),query=document.getElementById('searchFilter');
const cards=[...document.querySelectorAll('.debt')],counter=document.getElementById('shownCount');
function update(){let seen=0;const search=query.value.toLowerCase();for(const card of cards){
const ok=(repo.value==='all'||card.dataset.repo===repo.value)&&(state.value==='all'||card.dataset.status===state.value)&&card.textContent.toLowerCase().includes(search);
card.hidden=!ok;if(ok)seen++;}counter.textContent=seen+' of '+cards.length+' acceptance obligations shown';}
for(const el of [repo,state,query])el.addEventListener('input',update);update();})();
</script></body></html>\n"""


def write_bundle(output, projection, graph, sipoc, temporal, local_testflight=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    records = projection["ledger"]
    data = {
        "acceptance.json": canonical({k: v for k, v in projection.items() if k != "ledger"}) + "\n",
        "dag.json": canonical(graph) + "\n",
        "sipoc.json": canonical(sipoc) + "\n",
        "dmaic_mip_pulses.json": canonical(temporal) + "\n",
        "ledger_proposals.jsonl": "".join(canonical(e) + "\n" for e in records),
        "acceptance_debt.md": markdown_debt(projection),
        "index.html": render_html(projection, graph, sipoc, temporal, local_testflight),
    }
    for name, content in data.items():
        (output / name).write_text(content, encoding="utf-8")
    hashes = {k: hashlib.sha256(value.encode("utf-8")).hexdigest()
              for k, value in sorted(data.items())}
    (output / "sha256.json").write_text(canonical(hashes) + "\n", encoding="utf-8")
    return hashes
