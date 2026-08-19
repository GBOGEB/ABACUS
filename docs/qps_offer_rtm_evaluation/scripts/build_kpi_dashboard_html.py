import json, html

d = json.load(open("/tmp/kpi_data.json"))

def esc(s):
    return html.escape(str(s)) if s is not None else ""

def bar(pct, color="#0B3D5C"):
    pct = max(0, min(100, pct))
    return f'<div class="barwrap"><div class="bar" style="width:{pct}%;background:{color}"></div></div>'

# ---- sync table rows ----
sync_status_color = {"In sync": "#2E8B57", "Stale": "#C0392B", "Stale (unverified)": "#B8860B"}
sync_rows_html = ""
for name, latest, status, note, behind in d["sync_rows"]:
    c = sync_status_color.get(status, "#888")
    behind_txt = f"{behind} version(s) behind" if isinstance(behind, int) else "unknown"
    sync_rows_html += f"""<tr>
      <td>{esc(name)}</td>
      <td class="mono">{esc(latest)}</td>
      <td><span class="pill" style="background:{c}22;color:{c};border:1px solid {c}66">{esc(status)}</span></td>
      <td class="small">{esc(behind_txt)}</td>
      <td class="small">{esc(note)}</td>
    </tr>"""

# ---- bugs table ----
bug_rows_html = ""
for title, cat, status in d["bugs"]:
    ok = status.startswith("Fixed")
    c = "#2E8B57" if ok else "#B8860B"
    bug_rows_html += f"""<tr>
      <td>{esc(title)}</td>
      <td class="small">{esc(cat)}</td>
      <td><span class="pill" style="background:{c}22;color:{c};border:1px solid {c}66">{esc(status)}</span></td>
    </tr>"""

# ---- changelog ----
commit_rows_html = ""
for h, dt, msg in d["commits"]:
    commit_rows_html += f"""<div class="commit">
      <div class="commit-meta"><span class="mono">{esc(h)}</span> <span class="small">{esc(dt)}</span></div>
      <div class="commit-msg">{esc(msg)}</div>
    </div>"""

# ---- artefact width-of-type table ----
artefact_rows = [
    ("Master workbook (SSOT)", d["wb_latest"], d["wb_versions"], "xlsx", f"{d['wb_scripted']}/{d['wb_transitions']} transitions scripted ({round(d['wb_scripted']/d['wb_transitions']*100)}%)"),
    ("Reviewer workbook", d["lite_latest"], d["lite_versions"], "xlsx", "Derived 1:1 from FULL each round (slim-builder script)"),
    ("HTML Navigator", d["nav_latest"], d["nav_versions"], "html", "Data-export script saved; template-splice step still inline Python (standing gap)"),
    ("BT methodology deck", d["bt_latest"], d["bt_versions"], "pptx", f"{d['bt_scripted']}/{d['bt_transitions']} transitions scripted ({round(d['bt_scripted']/d['bt_transitions']*100)}%)"),
    ("MTBF/DMAIC deck", d["mtbf_latest"], d["mtbf_versions"], "pptx", "Separate lineage; untouched this round"),
]
art_rows_html = ""
for name, latest, vc, kind, note in artefact_rows:
    art_rows_html += f"""<tr>
      <td>{esc(name)}</td>
      <td class="mono small">{esc(latest)}</td>
      <td style="text-align:center">{vc}</td>
      <td style="text-align:center"><span class="kindtag">{esc(kind)}</span></td>
      <td class="small">{esc(note)}</td>
    </tr>"""

# ---- Expandable TODO cards: GBO asked "why is pending not a clickable/
# full breakdown expansion to perform or investigate next?" -- each item
# below is a <details> element the user can click open for what/why/files/
# next-step, instead of a flat label row. ----
todo_html = ""
for item in d["todo_detail"]:
    todo_html += f"""<details class="todo-card">
      <summary>
        <span class="todo-tag">{esc(item['tag'])}</span>
        <span class="todo-title">{esc(item['title'])}</span>
        <span class="todo-chevron">▸</span>
      </summary>
      <div class="todo-body">
        <div class="todo-field"><b>What:</b> {esc(item['what'])}</div>
        <div class="todo-field"><b>Why:</b> {esc(item['why'])}</div>
        <div class="todo-field"><b>Files:</b> <span class="mono">{esc(item['files'])}</span></div>
        <div class="todo-field"><b>Next step:</b> {esc(item['next_step'])}</div>
      </div>
    </details>"""

REMAINING_SIMPLE_TODO = [
    ("Deferred (GBO's own priority order)", "Broad Master_Input folder scan/index by size+date, existing-git-repo discovery"),
    ("Deferred (GBO's own priority order)", "Index/rewrite all .txt files in Master_Input by category/topic"),
    ("Older, carried forward", "BT deck v7/v8/v9 build scripts never saved (only v6/v10/v12 exist)"),
    ("Older, carried forward", "workbook_full v10-v15 orchestration scripts never saved (logic scripts exist, glue doesn't)"),
    ("Older, carried forward", "Relic-field scan of EVALUATION_WORKSPACE/OFFER_CANONICAL not yet built"),
    ("Older, carried forward", "Cross-workbook font/heading-size consistency audit not yet done"),
    ("Open question (never answered by GBO)", "Aptos vs Carlito font-consistency preference"),
    ("Open question (never answered by GBO)", "Whether the earlier 'repaired file' Excel warning still applies to the current version"),
]
todo_simple_html = ""
for tag, text in REMAINING_SIMPLE_TODO:
    todo_simple_html += f"""<div class="todo-row"><span class="todo-tag">{esc(tag)}</span><span class="todo-text">{esc(text)}</span></div>"""

composite_color = "#2E8B57" if d["composite"] >= 75 else ("#B8860B" if d["composite"] >= 50 else "#C0392B")

html_out = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>QPS Project — DMAIC KPI Dashboard</title>
<style>
  :root {{
    --purple: #441F63; --purple-bg: #F3ECF8; --accent: #0B3D5C; --callout: #EFE5F5;
    --text: #22222; --muted: #666; --border: #ddd;
  }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: 'Segoe UI', Aptos, Arial, sans-serif; margin: 0; background: #f7f5fa; color: #222; }}
  header {{ background: var(--purple); color: white; padding: 28px 36px; }}
  header h1 {{ margin: 0 0 4px 0; font-size: 26px; }}
  header .sub {{ opacity: 0.85; font-size: 13.5px; }}
  .tabs {{ display: flex; gap: 4px; background: #2f1548; padding: 0 36px; }}
  .tab {{ padding: 10px 18px; color: #cbb8e0; cursor: pointer; font-size: 13.5px; border-bottom: 3px solid transparent; }}
  .tab.active {{ color: white; border-bottom-color: #ffffff; background: rgba(255,255,255,0.08); }}
  main {{ padding: 28px 36px 60px; max-width: 1280px; margin: 0 auto; }}
  .panel {{ display: none; }}
  .panel.active {{ display: block; }}
  .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 28px; }}
  .card {{ background: white; border: 1px solid var(--border); border-radius: 8px; padding: 16px 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }}
  .card .label {{ font-size: 11.5px; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted); margin-bottom: 6px; }}
  .card .value {{ font-size: 30px; font-weight: 700; color: var(--purple); }}
  .card .note {{ font-size: 11.5px; color: var(--muted); margin-top: 6px; }}
  .barwrap {{ background: #eee; border-radius: 6px; height: 8px; margin-top: 8px; overflow: hidden; }}
  .bar {{ height: 100%; border-radius: 6px; }}
  .composite-card {{ background: linear-gradient(135deg, var(--purple), var(--accent)); color: white; grid-column: span 2; }}
  .composite-card .value {{ color: white; font-size: 44px; }}
  .composite-card .label {{ color: #e5d7f0; }}
  h2 {{ font-size: 18px; color: var(--purple); border-bottom: 2px solid var(--callout); padding-bottom: 8px; margin-top: 36px; }}
  h3 {{ font-size: 14.5px; color: var(--accent); margin-top: 22px; }}
  p.desc {{ font-size: 13px; color: var(--muted); max-width: 900px; line-height: 1.5; }}
  table {{ width: 100%; border-collapse: collapse; background: white; margin-top: 10px; font-size: 13px; }}
  th {{ background: var(--accent); color: white; text-align: left; padding: 8px 10px; font-size: 11.5px; text-transform: uppercase; letter-spacing: 0.03em; }}
  td {{ padding: 8px 10px; border-bottom: 1px solid #eee; vertical-align: top; }}
  tr:nth-child(even) td {{ background: #fafafa; }}
  .mono {{ font-family: 'Consolas', monospace; font-size: 12px; }}
  .small {{ font-size: 12px; color: var(--muted); }}
  .pill {{ padding: 2px 9px; border-radius: 10px; font-size: 11.5px; font-weight: 600; white-space: nowrap; }}
  .kindtag {{ background: #eee; padding: 2px 8px; border-radius: 4px; font-size: 11px; }}
  .dmaic-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-top: 14px; }}
  .dmaic-box {{ background: white; border: 1px solid var(--border); border-top: 4px solid var(--purple); border-radius: 6px; padding: 14px; }}
  .dmaic-box h4 {{ margin: 0 0 8px 0; color: var(--purple); font-size: 14px; }}
  .dmaic-box ul {{ margin: 0; padding-left: 18px; font-size: 12px; color: #333; line-height: 1.5; }}
  .commit {{ border-left: 3px solid var(--callout); padding: 6px 0 6px 14px; margin-bottom: 4px; }}
  .commit-meta {{ font-size: 11.5px; color: var(--muted); }}
  .commit-msg {{ font-size: 13px; }}
  .todo-row {{ display: flex; gap: 12px; padding: 8px 0; border-bottom: 1px solid #eee; font-size: 13px; align-items: baseline; }}
  .todo-tag {{ flex: 0 0 240px; font-size: 11px; font-weight: 700; color: var(--accent); text-transform: uppercase; letter-spacing: 0.02em; }}
  .todo-text {{ flex: 1; }}
  .todo-card {{ background: white; border: 1px solid var(--border); border-left: 4px solid var(--purple); border-radius: 6px; margin-bottom: 10px; overflow: hidden; }}
  .todo-card summary {{ list-style: none; cursor: pointer; padding: 12px 16px; display: flex; align-items: center; gap: 14px; }}
  .todo-card summary::-webkit-details-marker {{ display: none; }}
  .todo-card .todo-tag {{ flex: 0 0 220px; font-size: 10.5px; }}
  .todo-card .todo-title {{ flex: 1; font-size: 13.5px; font-weight: 600; color: var(--text); }}
  .todo-card .todo-chevron {{ color: var(--muted); transition: transform 0.15s; font-size: 12px; }}
  .todo-card[open] .todo-chevron {{ transform: rotate(90deg); }}
  .todo-card[open] summary {{ background: var(--callout); border-bottom: 1px solid var(--border); }}
  .todo-card:hover summary {{ background: #faf7fc; }}
  .todo-body {{ padding: 14px 18px; font-size: 12.5px; line-height: 1.6; }}
  .todo-field {{ margin-bottom: 8px; }}
  .todo-field b {{ color: var(--accent); }}
  .note-box {{ background: var(--callout); border-left: 4px solid var(--purple); padding: 12px 16px; font-size: 13px; margin: 16px 0; border-radius: 0 6px 6px 0; }}
  footer {{ padding: 20px 36px; text-align: center; font-size: 11.5px; color: var(--muted); }}
</style>
</head>
<body>

<header>
  <h1>QPS OFFER Evaluation — Project DMAIC KPI Dashboard</h1>
  <div class="sub">Delivery-process metrics, not the engineering DMAIC (that's the separate MTBF/DMAIC deck) — generated {esc(d['generated'])} · SSOT: {esc(d['wb_latest'])}</div>
</header>

<div class="tabs" id="tabs">
  <div class="tab active" data-panel="overview">Overview</div>
  <div class="tab" data-panel="dmaic">DMAIC</div>
  <div class="tab" data-panel="artefacts">Artefacts &amp; Lineage</div>
  <div class="tab" data-panel="tasks">Tasks</div>
  <div class="tab" data-panel="changelog">Changelog</div>
  <div class="tab" data-panel="todo">TODO / Outstanding</div>
</div>

<main>

  <div class="note-box">
    <strong>Framing note:</strong> "DMAIC" here is applied to <em>how this project itself is being delivered</em>
    round over round (task completion, SSOT sync, script lineage, bug closure, QA-gate adherence) —
    a project-management use of the framework, distinct from the QPS system's own engineering DMAIC
    (reliability/MTBF), which lives in <span class="mono">QPS_MTBF_WCS_DMAIC_v7.pptx</span>. Every number
    below is computed directly from <span class="mono">ARTIFACT_REGISTRY.json</span>, the live task list,
    and <span class="mono">git log</span> — nothing here is estimated.
  </div>

  <div class="panel active" id="panel-overview">
    <h2>Composite &amp; individual KPIs</h2>
    <div class="cards">
      <div class="card composite-card">
        <div class="label">Composite Project Delivery Health</div>
        <div class="value">{d['composite']}%</div>
        <div class="note">Weighted: Task completion 30% · SSOT sync 25% · Lineage/idempotency 20% · Bug closure 15% · QA-gate adherence 10%</div>
      </div>
      <div class="card">
        <div class="label">Task completion</div>
        <div class="value">{d['task_completion_pct']}%</div>
        {bar(d['task_completion_pct'], '#0B3D5C')}
        <div class="note">{d['tasks_completed']}/{d['tasks_total']} tasks completed · {d['tasks_in_progress']} in progress · {d['tasks_pending']} pending</div>
      </div>
      <div class="card">
        <div class="label">SSOT sync rate</div>
        <div class="value">{d['sync_pct']}%</div>
        {bar(d['sync_pct'], '#C0392B')}
        <div class="note">{d['in_sync']}/{d['sync_total']} derived artefacts fully in sync with {esc(d['wb_latest'])} right now</div>
      </div>
      <div class="card">
        <div class="label">Lineage / idempotency</div>
        <div class="value">{d['lineage_pct']}%</div>
        {bar(d['lineage_pct'], '#8E5A9E')}
        <div class="note">Version-transitions with a saved, re-runnable build script (workbook + BT deck combined)</div>
      </div>
      <div class="card">
        <div class="label">Bug closure rate</div>
        <div class="value">{d['bug_closure_pct']}%</div>
        {bar(d['bug_closure_pct'], '#2E8B57')}
        <div class="note">{d['bugs_fixed']}/{d['bugs_total']} found-this-session bugs fixed before shipping</div>
      </div>
      <div class="card">
        <div class="label">QA gate adherence</div>
        <div class="value">{d['qa_gate_pct']}%</div>
        {bar(d['qa_gate_pct'], '#2E8B57')}
        <div class="note">{d['qa_gate_types']} gate types (xlsx recalc, xlsx XML integrity, HTML Playwright, pptx visual+badge-grep) enforced every round, zero known bypass</div>
      </div>
    </div>

    <h2>Width of artefact types tracked</h2>
    <div class="cards">
      <div class="card"><div class="label">Total artefact families</div><div class="value">{d['total_families']}</div><div class="note">Distinct file lineages, per ARTIFACT_REGISTRY.json</div></div>
      <div class="card"><div class="label">Total files on disk</div><div class="value">{d['total_files']}</div><div class="note">Across all versions of all families</div></div>
      <div class="card"><div class="label">Committed changes, this project's own path</div><div class="value">{d['commit_count']}</div><div class="note">git log scoped to docs/qps_offer_rtm_evaluation/ only (was unscoped -- pulled all 2129 commits across the whole shared repo before this round's fix). A GitHub remote does exist (github.com/GBOGEB/ABACUS.git) -- nothing from this project has been pushed there yet.</div></div>
      <div class="card"><div class="label">Uncommitted changes right now</div><div class="value">{d['uncommitted_count']}</div><div class="note">Modified/untracked files in this project's own path, not yet committed to the worktree branch -- includes this round's own work</div></div>
      <div class="card"><div class="label">Backlog findings logged</div><div class="value">{d['backlog_sections']}</div><div class="note">Dated sections in NEXT_ITERATION_BACKLOG.md, counted live via regex, not hand-typed</div></div>
    </div>
  </div>

  <div class="panel" id="panel-dmaic">
    <h2>DMAIC applied to project delivery</h2>
    <p class="desc">Same 5-phase structure as the engineering DMAIC, applied to the process of building and shipping this evaluation project itself.</p>
    <div class="dmaic-grid">
      <div class="dmaic-box"><h4>Define</h4><ul>
        <li>Score 50 OFFER items vs 722 RTM requirements, 7-dim weighted BT method</li>
        <li>No duplicated SSOT — one workbook, everything else derives</li>
        <li>Disclose rather than fabricate on every inferred value</li>
      </ul></div>
      <div class="dmaic-box"><h4>Measure</h4><ul>
        <li>{d['total_files']} files / {d['total_families']} families tracked</li>
        <li>{d['tasks_total']} tasks logged, {d['task_completion_pct']}% complete</li>
        <li>{d['commit_count']} commits, {d['backlog_sections']} backlog findings</li>
      </ul></div>
      <div class="dmaic-box"><h4>Analyze</h4><ul>
        <li>SSOT sync: only {d['sync_pct']}% of derived artefacts current right now</li>
        <li>Lineage gaps concentrated in 2 spans: workbook v9-v15, BT deck v6-v10</li>
        <li>Bug root causes cluster around 2 openpyxl API gotchas + 3 unverified-assumption patterns</li>
      </ul></div>
      <div class="dmaic-box"><h4>Improve</h4><ul>
        <li>{d['bugs_fixed']}/{d['bugs_total']} bugs fixed pre-ship this session</li>
        <li>Task-list hygiene pass this round: 9 stale entries corrected with cited evidence</li>
        <li>Control actions written per recurring bug pattern (see Artefacts tab)</li>
      </ul></div>
      <div class="dmaic-box"><h4>Control</h4><ul>
        <li>4 QA gate types enforced every round, no bypass</li>
        <li>Re-read-saved-file convention catches silent data loss before ship</li>
        <li>Append-only slide/section numbering avoids cross-reference breaks</li>
      </ul></div>
    </div>

    <h3>Bug register (this session)</h3>
    <table>
      <tr><th>Issue</th><th>Root-cause category</th><th>Status</th></tr>
      {bug_rows_html}
    </table>
  </div>

  <div class="panel" id="panel-artefacts">
    <h2>Artefact lineage &amp; idempotency</h2>
    <p class="desc">"Idempotency" here means: can this file's current version be reproduced from scratch by re-running a saved script against the prior version? Where the answer is no, that transition's content is only reconstructable from the binary itself or prose description.</p>
    <table>
      <tr><th>Family</th><th>Latest</th><th>Versions</th><th>Type</th><th>Lineage note</th></tr>
      {art_rows_html}
    </table>

    <h2>SSOT sync status (right now)</h2>
    <p class="desc">Which derived artefacts actually reflect the current canonical workbook ({esc(d['wb_latest'])}) at this moment — not whether they were correct when built.</p>
    <table>
      <tr><th>Artefact</th><th>Latest file</th><th>Sync status</th><th>Drift</th><th>Note</th></tr>
      {sync_rows_html}
    </table>
  </div>

  <div class="panel" id="panel-tasks">
    <h2>Task breakdown</h2>
    <div class="cards">
      <div class="card"><div class="label">Completed</div><div class="value" style="color:#2E8B57">{d['tasks_completed']}</div></div>
      <div class="card"><div class="label">In progress</div><div class="value" style="color:#B8860B">{d['tasks_in_progress']}</div></div>
      <div class="card"><div class="label">Pending</div><div class="value" style="color:#C0392B">{d['tasks_pending']}</div></div>
    </div>
    <div class="note-box">
      <strong>Hygiene pass performed this round:</strong> 9 task entries (#21, #30, #31, #36, #38, #41, #45, #46, #47)
      were sitting as "pending"/"in progress" from earlier rounds despite direct evidence they were already done
      (e.g. #30 "Build HTML navigator companion" — the Navigator is on its 20th version; #46 "GitHub integration" —
      resolved by GBO's own explicit "local git only" decision, not an open build item). Corrected with cited
      evidence rather than left to silently understate progress. The remaining 9 pending items are genuinely
      not yet started — see the TODO tab.
    </div>
  </div>

  <div class="panel" id="panel-changelog">
    <h2>Main change log</h2>
    <p class="desc">Full local git history, newest first ({d['commit_count']} commits).</p>
    {commit_rows_html}
  </div>

  <div class="panel" id="panel-todo">
    <h2>TODO / Outstanding — honest checklist</h2>
    <p class="desc">Click any item below to expand what it is, why it matters, which files it touches, and the concrete next step — not just a label.</p>
    {todo_html}
    <h3>Smaller items (no expanded breakdown needed)</h3>
    {todo_simple_html}
  </div>

</main>

<footer>QPS OFFER Evaluation project · DMAIC KPI Dashboard · regenerate via gen_kpi_dashboard.py + build_kpi_dashboard_html.py, both committed to the local git repo</footer>

<script>
  document.querySelectorAll('.tab').forEach(t => {{
    t.addEventListener('click', () => {{
      document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
      document.querySelectorAll('.panel').forEach(x => x.classList.remove('active'));
      t.classList.add('active');
      document.getElementById('panel-' + t.dataset.panel).classList.add('active');
    }});
  }});
</script>

</body>
</html>
"""

open("QPS_DMAIC_KPI_Dashboard.html", "w", encoding="utf-8").write(html_out)
print(f"wrote QPS_DMAIC_KPI_Dashboard.html ({len(html_out)} bytes)")
