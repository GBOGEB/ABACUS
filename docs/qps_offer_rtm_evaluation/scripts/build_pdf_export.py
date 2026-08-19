"""
build_pdf_export.py -- static, print-friendly PDF versions of the Taxonomy
and Domain Summary tabs (Task #47: "readable text also as PDF landscape or
portrait or mixed"). Two source HTML documents are built (one portrait, one
landscape), rendered to PDF with headless Chromium, then merged into a
single mixed-orientation PDF -- each section keeps the orientation that
actually suits its content (Taxonomy = prose/definition tables = portrait;
Domain Summary = wide table + Pareto bars = landscape) rather than forcing
one orientation on both.

All figures here are computed directly from nav_data_vN.json (same export
that feeds the HTML navigator) so the PDF can't drift from the navigator or
the workbook. Data source is now a CLI arg (was hardcoded to nav_data_v7.json
-- promoted to reusable this round, see merge_taxonomy_pdf.py for the
render+merge step this file's own docstring always described but never
saved as a script).

Usage: python3 build_pdf_export.py [/tmp/nav_data_vN.json]
"""
import json, re, sys, tempfile, warnings
from pathlib import Path
warnings.filterwarnings("ignore")

NAV_DATA_PATH = sys.argv[1] if len(sys.argv) > 1 else "/tmp/nav_data_v7.json"
DATA = json.load(open(NAV_DATA_PATH, encoding="utf-8"))
_m = re.search(r"v(\d+)", Path(NAV_DATA_PATH).name)
WB_VERSION = f"v{_m.group(1)}" if _m else "v7"

# Output dir for the two intermediate print-HTML files: was hardcoded to
# POSIX /tmp, which does not resolve to a real, writable location for
# Chromium's file:// URL loader on Windows (Python's own open("/tmp/...")
# silently drive-relatives it to <cwd drive>:\tmp, but a browser's file://
# resolver does not do the same remapping -- see merge_taxonomy_pdf.py,
# which failed on this exact mismatch). Use the OS temp dir via pathlib so
# both this script's writes and merge_taxonomy_pdf.py's reads agree on the
# same real path on any platform, not just the original Linux sandbox.
TMP_DIR = Path(tempfile.gettempdir())
TAXONOMY_HTML_PATH = TMP_DIR / "print_taxonomy.html"
DOMAIN_SUMMARY_HTML_PATH = TMP_DIR / "print_domain_summary.html"

CLUSTER_NAMES = {
    "C1": "Performance", "C2": "Process Design", "C3": "Mechanical & Equipment",
    "C4": "Software & Control", "C5": "Infrastructure & Integration",
    "C6": "Reliability & Maintenance", "C7": "Quality, Testing & Risk",
    "C8": "Commercial & Execution",
}

def cluster_key(c):
    if not c:
        return "Not linked"
    m = re.search(r"C[1-8]", c)
    return m.group(0) if m else "Not linked"

PAGE_CSS = """
<style>
  *{box-sizing:border-box;}
  body{font-family:"Aptos","Calibri","Segoe UI",Arial,sans-serif;margin:0;color:#222;font-size:12px;}
  h1{color:#17365D;font-size:22px;margin:0 0 4px;}
  h2{color:#17365D;font-size:16px;border-bottom:2px solid #C9D6E3;padding-bottom:5px;margin:26px 0 10px;}
  h3{color:#17365D;font-size:13px;margin:18px 0 6px;}
  .subtitle{color:#666;font-size:11px;margin:-4px 0 10px;}
  .coverpage{padding:60px 50px;}
  .coverpage .meta{margin-top:30px;font-size:12px;color:#444;line-height:1.8;}
  .coverpage .meta b{color:#17365D;}
  table{border-collapse:collapse;width:100%;font-size:10.5px;margin-bottom:6px;}
  th{background:#1F4E78;color:#fff;text-align:left;padding:5px 6px;}
  td{padding:5px 6px;border-bottom:1px solid #C9D6E3;vertical-align:top;}
  tr:nth-child(even) td{background:#F2F6FA;}
  .note{background:#FDF6E3;border-left:4px solid #B7950B;padding:8px 12px;border-radius:3px;font-size:10.5px;color:#5c4a00;margin:8px 0;}
  .callout{background:#EFE5F5;border-left:4px solid #441F63;padding:8px 12px;border-radius:3px;font-size:10.5px;margin:8px 0;}
  .callout b{color:#441F63;}
  .bar-row{display:flex;align-items:center;gap:6px;margin-bottom:2px;}
  .bar-label{width:150px;font-size:9px;text-align:right;flex-shrink:0;}
  .bar-outer{flex:1;background:#eef2f6;border-radius:2px;height:9.5px;position:relative;}
  .bar-inner{background:#0F6B78;height:100%;border-radius:2px;}
  .bar-cum-dot{position:absolute;top:-2px;width:6px;height:6px;border-radius:50%;background:#441F63;transform:translateX(-3px);}
  .bar-count{width:34px;font-size:9.5px;font-weight:700;text-align:right;flex-shrink:0;}
  .tile-row{display:flex;gap:10px;margin:10px 0 16px;}
  .tile{flex:1;background:#F2F6FA;border:1px solid #C9D6E3;border-radius:5px;padding:8px;text-align:center;}
  .tile .n{font-size:18px;font-weight:800;color:#17365D;}
  .tile .lbl{font-size:9px;color:#666;margin-top:2px;}
  .pie-wrap{display:flex;gap:16px;align-items:center;margin:10px 0;}
  .pie-donut{width:140px;height:140px;border-radius:50%;flex-shrink:0;}
  .pie-legend{font-size:10px;}
  .pie-legend .row{display:flex;align-items:center;gap:6px;padding:2px 0;}
  .pie-legend .sw{width:9px;height:9px;border-radius:2px;flex-shrink:0;}
  .footer-note{font-size:9px;color:#888;margin-top:16px;text-align:center;}
</style>
"""

def bar_rows(rows, use_log=False):
    """rows: list of (label, value). Returns HTML for Pareto rows with a
    cumulative-% dot, matching the navigator's hand-rolled chart style."""
    if not rows:
        return "<p>Nothing to show.</p>"
    import math
    total = sum(v for _, v in rows)
    max_val = max(v for _, v in rows)
    html = []
    cum = 0
    for label, val in rows:
        cum += val
        cum_pct = (cum / total * 100) if total else 0
        if use_log:
            bar_pct = (math.log10(val + 1) / math.log10(max_val + 1) * 100) if max_val else 0
        else:
            bar_pct = (val / max_val * 100) if max_val else 0
        html.append(f"""<div class="bar-row">
          <div class="bar-label">{label}</div>
          <div class="bar-outer"><div class="bar-inner" style="width:{bar_pct:.1f}%;"></div>
            <div class="bar-cum-dot" style="left:{cum_pct:.1f}%;" title="cum {cum_pct:.1f}%"></div></div>
          <div class="bar-count">{val}</div>
        </div>""")
    return "\n".join(html)

def donut(counts_dict, total):
    palette = ['#0F6B78','#17365D','#2874A6','#1E8449','#B7791F','#7F8C8D','#441F63','#C0392B','#9FC3D6']
    keys = sorted(counts_dict.keys(), key=lambda k: -counts_dict[k])
    acc = 0
    stops = []
    legend_rows = []
    for i, k in enumerate(keys):
        pct = counts_dict[k] / total * 100 if total else 0
        start, acc = acc, acc + pct
        color = palette[i % len(palette)]
        stops.append(f"{color} {start:.2f}% {acc:.2f}%")
        name = f"{k} — {CLUSTER_NAMES[k]}" if k in CLUSTER_NAMES else k
        legend_rows.append(f'<div class="row"><div class="sw" style="background:{color};"></div>'
                            f'<span>{name}: {counts_dict[k]} ({pct:.1f}%)</span></div>')
    gradient = ", ".join(stops)
    return f"""<div class="pie-wrap">
      <div class="pie-donut" style="background:conic-gradient({gradient});"></div>
      <div class="pie-legend">{''.join(legend_rows)}</div>
    </div>"""

# =========================================================== PORTRAIT: TAXONOMY
def build_taxonomy_html():
    tax = DATA["taxonomy"]
    rt_rows = "".join(
        f"<tr><td><b>{r['type']}</b></td><td>{r['definition']}</td><td>{r['subcategories']}</td><td>{r['example']}</td></tr>"
        for r in tax["requirementTypes"]
    )
    sg_rows = "".join(
        f"<tr><td><b>{r['name']}</b></td><td>{r['phases']}</td><td>{r['evidence']}</td></tr>"
        for r in tax["supergroups"]
    )
    disp_rows = "".join(
        f"<tr><td><b>{r['disposition']}</b></td><td>{r['definition']}</td></tr>"
        for r in tax["disposition"]
    )
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">{PAGE_CSS}
    <style>@page {{ size: A4 portrait; margin: 16mm 14mm; }}</style></head><body>
    <div class="coverpage">
      <h1>QPS OFFER Evaluation — Requirement Taxonomy & Domain Summary</h1>
      <p class="subtitle">Static PDF export, generated from QPS_OFFER_Evaluation_FULL_{WB_VERSION}.xlsx (same SSOT data as the HTML navigator). Read-only reference — edits happen in the workbook.</p>
      <div class="meta">
        <div><b>Section 1 (this page, portrait):</b> Requirement taxonomy &amp; definitions</div>
        <div><b>Section 2 (following pages, landscape):</b> RTM domain summary, Pareto volume charts, Domain × Cluster breakdown</div>
        <div style="margin-top:14px;"><b>722</b> RTM requirements &nbsp;·&nbsp; <b>50</b> OFFER items &nbsp;·&nbsp; <b>43</b> T0 Gate (hand-reviewed) &nbsp;·&nbsp; <b>679</b> rule-classified &nbsp;·&nbsp; <b>8</b> OFFER clusters (C1–C8)</div>
      </div>
    </div>
    <div style="page-break-before:always;"></div>

    <h2>Requirement Type</h2>
    <table><thead><tr><th>Type</th><th>Definition</th><th>Subcategories</th><th>Example (T0 Gate)</th></tr></thead>
    <tbody>{rt_rows}</tbody></table>
    <div class="note">{tax['requirementTypeNote']}</div>

    <h2>Lifecycle supergroups</h2>
    <table><thead><tr><th>Supergroup</th><th>Applicable phase(s)</th><th>Evidence at this stage</th></tr></thead>
    <tbody>{sg_rows}</tbody></table>
    <div class="note">{tax['supergroupNote']}</div>

    <h2>OFFER disposition vocabulary</h2>
    <table><thead><tr><th>Disposition</th><th>Definition</th></tr></thead>
    <tbody>{disp_rows}</tbody></table>
    <div class="callout">{tax['dispositionNote']}</div>

    <div class="footer-note">QPS OFFER Evaluation Workbook — {WB_VERSION} · Taxonomy (portrait section) · page 1 of the combined PDF continues in landscape below</div>
    </body></html>"""

# =========================================================== LANDSCAPE: DOMAIN SUMMARY
def build_domain_summary_html():
    ds = DATA["domainSummary"]
    cols = [
        ("domain","Domain"),("rtmCount","RTM count"),("gateCount","Gate count"),
        ("t1","T1"),("t2","T2"),("t3","T3"),("avgS","Avg Weighted S"),("maxS","Max Weighted S"),
        ("topRtm","Top RTM"),("stds","Explicit standards"),("delivs","Explicit deliverables"),
    ]
    head = "".join(f"<th>{lbl}</th>" for _, lbl in cols)
    body_rows = []
    for d in ds:
        cells = []
        for k, _ in cols:
            v = d.get(k, "")
            if isinstance(v, float):
                v = round(v, 2)
            cells.append(f"<td>{v}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    table_html = f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"

    # Domain volume Pareto (linear)
    dom_rows = sorted([(d["domain"], d["rtmCount"]) for d in ds], key=lambda x: -x[1])
    dom_rows_excl = [r for r in dom_rows if r[0] != "Subsystems"]

    # Cluster breakdown (direct + inferred, keyed) across all 722 RTMs
    cluster_counts = {}
    for r in DATA["rtmRanking"]:
        k = cluster_key(r.get("cluster"))
        cluster_counts[k] = cluster_counts.get(k, 0) + 1
    cluster_rows = sorted(
        [((k if k == "Not linked" else f"{k} — {CLUSTER_NAMES.get(k,'')}"), v) for k, v in cluster_counts.items()],
        key=lambda x: -x[1]
    )

    # Subsystems-only cluster pie
    sub_rows = [r for r in DATA["rtmRanking"] if r.get("domain") == "Subsystems"]
    sub_counts = {}
    for r in sub_rows:
        k = cluster_key(r.get("cluster"))
        sub_counts[k] = sub_counts.get(k, 0) + 1

    # 80:20 zoom (Subsystems excluded, matching the navigator's default framing)
    total_excl = sum(v for _, v in dom_rows_excl)
    cum = 0
    vital = []
    for label, val in dom_rows_excl:
        cum += val
        vital.append((label, val))
        if total_excl and cum / total_excl >= 0.8:
            break

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">{PAGE_CSS}
    <style>@page {{ size: A4 landscape; margin: 12mm 14mm; }}</style></head><body>
    <h1 style="font-size:18px;">RTM domain summary</h1>
    <p class="subtitle">Counts and average importance by contract domain, for review allocation. Static snapshot from QPS_OFFER_Evaluation_FULL_{WB_VERSION}.xlsx.</p>
    {table_html}

    <div style="page-break-before:always;"></div>
    <h2>Domain volume — Pareto (linear scale)</h2>
    <p class="subtitle">RTM count per domain, largest to smallest, with a running cumulative-% marker (purple dot). Subsystems (202 RTMs, ~28% of the register on its own) dominates the linear scale.</p>
    {bar_rows(dom_rows, use_log=False)}

    <h2 style="margin-top:20px;">Domain volume — with Subsystems excluded, plus its own breakdown</h2>
    <div style="display:flex;gap:24px;">
      <div style="flex:1;">{bar_rows(dom_rows_excl, use_log=False)}</div>
      <div style="flex:1;">
        <h3 style="margin-top:0;">Subsystems domain ({len(sub_rows)} RTMs) — its own Cluster breakdown</h3>
        {donut(sub_counts, len(sub_rows) or 1)}
      </div>
    </div>

    <h2 style="margin-top:26px;">80:20 zoom — domains that alone drive 80% of the register (Subsystems excluded)</h2>
    <p class="subtitle">{len(vital)} of {len(dom_rows_excl)} domains already account for ≥80% of their {total_excl}-RTM total:</p>
    {bar_rows(vital, use_log=False)}

    <h2 style="margin-top:20px;">Cluster breakdown (C1–C8) — thematic, not ranking</h2>
    <p class="subtitle">All 722 RTMs, regrouped by Cluster (direct crosswalk + inferred, combined — see the Taxonomy section for the inference methodology). "Not linked" is the honestly-unclassified remainder.</p>
    {bar_rows(cluster_rows, use_log=False)}

    <div class="footer-note">QPS OFFER Evaluation Workbook — {WB_VERSION} · Domain Summary (landscape section) · read-only — edit the workbook itself, not this page</div>
    </body></html>"""

TAXONOMY_HTML_PATH.write_text(build_taxonomy_html(), encoding="utf-8")
DOMAIN_SUMMARY_HTML_PATH.write_text(build_domain_summary_html(), encoding="utf-8")
print(f"wrote {TAXONOMY_HTML_PATH} and {DOMAIN_SUMMARY_HTML_PATH}")
