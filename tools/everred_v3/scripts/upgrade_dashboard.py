"""Idempotent V3 telemetry/control panel upgrade of the HTML source template."""

import pathlib

P = pathlib.Path(__file__).resolve().parents[1]
p = P / "dashboard/template.html"
s = p.read_text()
if 'id="control"' not in s:
    s = s.replace(
        '<button data-scroll="data"><span>⤴</span> Data exchange</button>',
        '<button data-scroll="control"><span>⌁</span> Control history</button><button data-scroll="data"><span>⤴</span> Data exchange</button>',
    )
    control = """<section id="control" class="section"><div class="section-header"><h2>Control history · exact-source KPI pulses</h2><span class="hint">Immutable pulse lineage · null ≠ zero</span></div><div class="grid2"><div class="panel"><h3>Most recent source-bound pulses</h3><div class="table-wrap"><table class="tbl"><thead><tr><th>Pulse ID</th><th>Events</th><th>Root amplification</th><th>Consumer replay</th></tr></thead><tbody id="pulseRows"></tbody></table></div><p class="metricnote">Only numerators and denominators in comparable scopes can produce a valid trend. A historical pulse is not a live CI poll.</p></div><div class="panel"><h3>Recurrence sentinels</h3><div id="alertRows"></div><p class="metricnote">Alert generation and notification delivery are separate. No live notification is asserted without a delivery receipt.</p></div></div><div class="grid2" style="margin-top:14px"><div class="panel"><h3>Native ingestion</h3><p>API-authenticated Actions run/job metadata, artifact SHA-256 validation and read-only Bandit/coverage/JUnit/runtime parsers. Scanner output is observation, not independent security disposition.</p></div><div class="panel"><h3>Lease and replay status</h3><p>Dedicated Git-ref atomic lease registry; integration previews use immutable SHA triples. Actual remote worker launch and consumer native testflight remain UNKNOWN unless supported by run receipts.</p></div></div></section>"""
    s = s.replace(
        '<section id="data" class="section">',
        control + '\n<section id="data" class="section">',
    )
    s = s.replace(
        '<script id="svg-data" type="application/json">@@SVGJSON@@</script>',
        '<script id="svg-data" type="application/json">@@SVGJSON@@</script><script id="pulse-data" type="application/json">@@PULSES@@</script><script id="alerts-data" type="application/json">@@ALERTS@@</script>',
    )
    s = s.replace(
        "const visuals=JSON.parse(document.getElementById('svg-data').textContent);",
        "const visuals=JSON.parse(document.getElementById('svg-data').textContent);\nconst pulses=JSON.parse(document.getElementById('pulse-data').textContent);\nconst nativeAlerts=JSON.parse(document.getElementById('alerts-data').textContent);",
    )
    addition = """function renderControl(){
 $('pulseRows').innerHTML=pulses.length?pulses.slice(-6).reverse().map(p=>`<tr><td class="code">${esc(p.pulse_id)}</td><td>${fmt(p.source_event_count)}</td><td>${p.occurrence_amplification??'UNKNOWN'}</td><td>${p.consumer_replay_coverage_pct==null?'UNKNOWN':pct(p.consumer_replay_coverage_pct)}</td></tr>`).join(''):'<tr><td colspan="4">No validated historical pulses</td></tr>';
 $('alertRows').innerHTML=nativeAlerts.length?nativeAlerts.map(a=>`<div class="status-row"><span>${esc(a.root_id)} · ${esc(a.disposition)}</span>${badge('UNKNOWN')}</div>`).join(''):'<div class="status-row"><span>No recurrence receipt in this snapshot</span><strong>UNKNOWN</strong></div>';
}
"""
    s = s.replace("function renderRoots(){", addition + "function renderRoots(){")
    s = s.replace(" renderRoots();\n}", " renderRoots();renderControl();\n}")
p.write_text(s)
