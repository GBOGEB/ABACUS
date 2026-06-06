#!/usr/bin/env python3
"""
build_viewer.py  --  Wave W006 / Option B  *** SCAFFOLD / WIP ***
==================================================================

STATUS: This is an intentionally MINIMAL scaffold, not a finished deliverable.
        It establishes the skeleton for an interactive design<->as-drawn viewer
        so later waves (see docs/W006_INTERACTIVE_UI_PLAN.md) can flesh out the
        full feature set (deep SVG element linking, comparison overlays, export).

What the scaffold DOES today (working, end-to-end):
  * Reads the W006 cross-map (data/crossmap/design_to_asdrawn.json) and the
    as-drawn catalog (data/excel/catalog_register.json).
  * Emits publish/interactive_viewer.html -- a single self-contained file with:
      - layer toggle checkboxes (driven by the same lyr-NN class scheme as the
        v6 atlas, so the panel is wired and ready),
      - pan + zoom on the embedded QCELL SVG (wheel = zoom, drag = pan),
      - search-by-tag box (matches design OR as-drawn tag, jumps to the row),
      - a confidence-coloured cross-map table (HIGH/MEDIUM/LOW/unmapped),
      - a metadata popup placeholder that shows the selected pair's reasons.

What the scaffold deliberately does NOT do yet (tracked in the UI plan):
  * It does not yet hit-test/highlight the actual SVG element for a tag
    (needs per-element tag annotation -- a planned W006/W00x task).
  * No comparison side-by-side overlay, no PNG/PDF export, no URL state.
  * Layer toggles operate on the embedded atlas classes only.

Inputs : data/crossmap/design_to_asdrawn.json   (from build_w006_crossmap)
         data/excel/catalog_register.json        (from build_w005)
         output_v6/QCELL/*_13layers.svg           (from build_atlas_v6, optional)
Output : publish/interactive_viewer.html
"""
from __future__ import annotations

import glob
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CROSSMAP = os.path.join(ROOT, "data", "crossmap", "design_to_asdrawn.json")
CATALOG = os.path.join(ROOT, "data", "excel", "catalog_register.json")
ATLAS_DIR = os.path.join(ROOT, "output_v6", "QCELL")
PUBLISH = os.path.join(ROOT, "publish")

TIER_COLOUR = {
    "HIGH": "#1b9e77",
    "MEDIUM": "#d9a300",
    "LOW": "#d95f02",
    "UNMAPPED": "#888888",
}


def _load_json(path):
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        return json.load(fh)


def _embed_svg():
    """Inline the first annotated QCELL atlas SVG if available (optional)."""
    cands = sorted(glob.glob(os.path.join(ATLAS_DIR, "*_13layers.svg")))
    if not cands:
        return None
    with open(cands[0]) as fh:
        svg = fh.read()
    return re.sub(r"<\?xml[^>]*\?>", "", svg).strip()


def _rows(crossmap, catalog):
    """Build the unified row list: mapped pairs + unmapped design tags."""
    mapped = {m["design_tag"]: m for m in crossmap.get("mappings", [])}
    d2a = crossmap.get("design_to_asdrawn", {})
    universe = set(d2a) | set(mapped)
    rows = []
    for m in crossmap.get("mappings", []):
        rows.append({
            "design": m["design_tag"],
            "asdrawn": m["asdrawn_tag"],
            "type": m.get("type", ""),
            "confidence": m.get("confidence", 0.0),
            "tier": m.get("tier", "UNMAPPED"),
            "reasons": m.get("reasons", []),
            "sheet": m.get("asdrawn_sheet", ""),
        })
    conf = _load_json(os.path.join(os.path.dirname(CROSSMAP),
                                   "crossmap_confidence.json")) or {}
    for u in conf.get("unmapped_design", []):
        # entries are dicts: {design_tag, type, band, reason}
        dtag = u.get("design_tag") if isinstance(u, dict) else u
        if dtag and dtag not in universe:
            reason = u.get("reason", "NO_CONFIDENT_MATCH") if isinstance(u, dict) \
                else "NO_CONFIDENT_MATCH"
            rows.append({
                "design": dtag, "asdrawn": "",
                "type": (u.get("type") if isinstance(u, dict) else dtag[:2]) or dtag[:2],
                "confidence": 0.0, "tier": "UNMAPPED",
                "reasons": [reason], "sheet": "",
            })
    rows.sort(key=lambda r: (r["tier"] != "HIGH", r["tier"] != "MEDIUM",
                             r["tier"] != "LOW", r["design"]))
    return rows


def _table_html(rows):
    out = []
    for i, r in enumerate(rows):
        colour = TIER_COLOUR.get(r["tier"], "#888")
        reasons = html.escape("; ".join(r["reasons"]))
        out.append(
            f'<tr class="row" data-design="{r["design"]}" '
            f'data-asdrawn="{r["asdrawn"]}" data-i="{i}" '
            f'onclick="showMeta({i})">'
            f'<td>{html.escape(r["design"])}</td>'
            f'<td>{html.escape(r["asdrawn"]) or "&mdash;"}</td>'
            f'<td>{html.escape(r["type"])}</td>'
            f'<td><span class="pill" style="background:{colour}">'
            f'{r["tier"]}</span></td>'
            f'<td>{r["confidence"]:.2f}</td>'
            f'<td class="reasons">{reasons}</td></tr>')
    return "\n".join(out)


def build_html():
    crossmap = _load_json(CROSSMAP)
    if not crossmap:
        raise SystemExit("W006 crossmap not found -- run build_w006_crossmap first.")
    catalog = _load_json(CATALOG) or {}
    rows = _rows(crossmap, catalog)
    svg_inline = _embed_svg()
    has_svg = svg_inline is not None
    rows_json = json.dumps(rows)

    stats = {
        "total": len(rows),
        "mapped": sum(1 for r in rows if r["asdrawn"]),
        "high": sum(1 for r in rows if r["tier"] == "HIGH"),
        "medium": sum(1 for r in rows if r["tier"] == "MEDIUM"),
        "low": sum(1 for r in rows if r["tier"] == "LOW"),
        "unmapped": sum(1 for r in rows if not r["asdrawn"]),
    }

    svg_block = (f'<div id="svgwrap"><div id="svgpan">{svg_inline}</div></div>'
                 if has_svg else
                 '<div id="svgwrap" class="empty">Annotated atlas SVG not found.'
                 '<br/>Run <code>./make.sh</code> (build_atlas_v6) to embed it.</div>')

    html_doc = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>
<title>MINERVA W006 - Interactive Cross-Map Viewer (SCAFFOLD)</title>
<style>
 *{{box-sizing:border-box;}}
 body{{font-family:Consolas,'DejaVu Sans Mono',monospace;margin:0;
   display:flex;height:100vh;color:#1b2733;}}
 #side{{width:340px;background:#1e2430;color:#e8edf4;padding:14px;
   overflow:auto;flex:none;}}
 #side h1{{font-size:14px;margin:0 0 4px;}}
 .wip{{background:#d9a300;color:#1e2430;font-size:10px;font-weight:bold;
   padding:2px 6px;border-radius:3px;display:inline-block;margin-bottom:8px;}}
 #side p{{font-size:11px;color:#9fb0c4;line-height:1.4;}}
 #side label{{display:block;font-size:11px;margin:2px 0;cursor:pointer;}}
 #search{{width:100%;padding:6px;margin:8px 0;border:0;border-radius:4px;
   font-family:inherit;}}
 .stat{{font-size:11px;color:#cfe;margin:1px 0;}}
 .pill{{color:#fff;padding:1px 6px;border-radius:8px;font-size:10px;}}
 #main{{flex:1;display:flex;flex-direction:column;overflow:hidden;}}
 #svgwrap{{flex:1;overflow:hidden;background:#fff;position:relative;
   border-bottom:2px solid #1e2430;}}
 #svgwrap.empty{{display:flex;align-items:center;justify-content:center;
   color:#888;font-size:13px;text-align:center;}}
 #svgpan{{transform-origin:0 0;cursor:grab;}}
 #svgpan svg{{width:100%;height:auto;display:block;}}
 #tablewrap{{height:46%;overflow:auto;background:#f6f8fa;}}
 table{{border-collapse:collapse;width:100%;font-size:11px;}}
 th,td{{text-align:left;padding:4px 8px;border-bottom:1px solid #e1e6eb;}}
 th{{position:sticky;top:0;background:#1e2430;color:#e8edf4;z-index:2;}}
 tr.row:hover{{background:#eef3f8;cursor:pointer;}}
 tr.hit{{background:#fff3cd!important;}}
 td.reasons{{color:#5a6b7b;}}
 #meta{{position:fixed;right:14px;bottom:14px;width:300px;background:#1e2430;
   color:#e8edf4;padding:12px;border-radius:6px;font-size:11px;display:none;
   box-shadow:0 4px 18px rgba(0,0,0,.4);z-index:5;}}
 #meta h3{{margin:0 0 6px;font-size:12px;}}
 #meta .close{{float:right;cursor:pointer;color:#9fb0c4;}}
</style></head>
<body>
<div id="side">
 <h1>W006 Cross-Map Viewer</h1>
 <span class="wip">SCAFFOLD / WIP</span>
 <p>Bidirectional design&harr;as-drawn tag map. Heuristic, confidence-scored.
    See <code>W006_CROSSMAP_REPORT.md</code> for method &amp; honesty notes.</p>
 <input id="search" placeholder="search tag (e.g. CV001 or TT509)"
   oninput="doSearch(this.value)"/>
 <div class="stat">rows: {stats['total']} &middot; mapped: {stats['mapped']}</div>
 <div class="stat">HIGH {stats['high']} &middot; MEDIUM {stats['medium']}
   &middot; LOW {stats['low']} &middot; unmapped {stats['unmapped']}</div>
 <hr style="border-color:#33404f;margin:10px 0;"/>
 <strong style="font-size:11px;">Layers (atlas v6 classes)</strong>
 <div id="layers"></div>
 <p style="margin-top:10px;color:#7d8ea3;">Scaffold limits: SVG element
   highlight, comparison overlay &amp; export are planned, not built.
   Wheel=zoom, drag=pan.</p>
</div>
<div id="main">
 {svg_block}
 <div id="tablewrap">
  <table>
   <thead><tr><th>design</th><th>as-drawn</th><th>type</th>
     <th>tier</th><th>conf</th><th>reasons</th></tr></thead>
   <tbody id="rows">{_table_html(rows)}</tbody>
  </table>
 </div>
</div>
<div id="meta"><span class="close" onclick="hideMeta()">&times;</span>
  <h3 id="meta-title"></h3><div id="meta-body"></div></div>
<script>
 var ROWS = {rows_json};
 // ---- layer toggles (wired to lyr-NN classes on the embedded SVG) ----
 var pan = document.getElementById('svgpan');
 var LAYERS = 21;
 var lc = document.getElementById('layers');
 for (var i=0;i<LAYERS;i++) {{
   (function(idx){{
     var lab=document.createElement('label');
     var cb=document.createElement('input');
     cb.type='checkbox'; cb.checked=true;
     cb.onchange=function(){{ if(pan) pan.classList.toggle('hide-'+idx, !cb.checked); }};
     lab.appendChild(cb);
     lab.appendChild(document.createTextNode(' lyr-'+String(idx).padStart(2,'0')));
     lc.appendChild(lab);
   }})(i);
 }}
 var st=document.createElement('style');
 var rules=''; for(var i=0;i<LAYERS;i++){{rules+='#svgpan.hide-'+i+' .lyr-'+String(i).padStart(2,'0')+'{{display:none!important}}';}}
 st.textContent=rules; document.head.appendChild(st);

 // ---- pan + zoom (scaffold; transform on #svgpan) ----
 var scale=1, tx=0, ty=0, dragging=false, sx=0, sy=0;
 function apply(){{ if(pan) pan.style.transform='translate('+tx+'px,'+ty+'px) scale('+scale+')'; }}
 var wrap=document.getElementById('svgwrap');
 if (pan) {{
   wrap.addEventListener('wheel', function(e){{
     e.preventDefault();
     var f=e.deltaY<0?1.1:0.9; scale=Math.min(8,Math.max(0.2,scale*f)); apply();
   }}, {{passive:false}});
   pan.addEventListener('mousedown', function(e){{dragging=true;sx=e.clientX-tx;sy=e.clientY-ty;pan.style.cursor='grabbing';}});
   window.addEventListener('mouseup', function(){{dragging=false;if(pan)pan.style.cursor='grab';}});
   window.addEventListener('mousemove', function(e){{if(dragging){{tx=e.clientX-sx;ty=e.clientY-sy;apply();}}}});
 }}

 // ---- search ----
 function doSearch(q){{
   q=(q||'').trim().toUpperCase();
   var trs=document.querySelectorAll('#rows tr.row'); var first=null;
   trs.forEach(function(tr){{
     var d=(tr.getAttribute('data-design')||'').toUpperCase();
     var a=(tr.getAttribute('data-asdrawn')||'').toUpperCase();
     var hit=q && (d.indexOf(q)>=0 || a.indexOf(q)>=0);
     tr.classList.toggle('hit', !!hit);
     if(hit && !first) first=tr;
   }});
   if(first) first.scrollIntoView({{block:'center'}});
 }}

 // ---- metadata popup placeholder ----
 function showMeta(i){{
   var r=ROWS[i]; if(!r) return;
   document.getElementById('meta-title').textContent =
     r.design + (r.asdrawn ? '  \u2194  '+r.asdrawn : '  (unmapped)');
   document.getElementById('meta-body').innerHTML =
     '<div>type: '+r.type+'</div>'+
     '<div>tier: '+r.tier+' &middot; confidence: '+r.confidence.toFixed(2)+'</div>'+
     '<div>sheet: '+(r.sheet||'&mdash;')+'</div>'+
     '<div style="margin-top:6px;color:#9fb0c4;">'+r.reasons.join('<br/>')+'</div>'+
     '<div style="margin-top:8px;color:#7d8ea3;font-size:10px;">'+
     '[scaffold] SVG element highlight is a planned feature.</div>';
   document.getElementById('meta').style.display='block';
 }}
 function hideMeta(){{ document.getElementById('meta').style.display='none'; }}
</script>
</body></html>"""

    os.makedirs(PUBLISH, exist_ok=True)
    out = os.path.join(PUBLISH, "interactive_viewer.html")
    with open(out, "w") as fh:
        fh.write(html_doc)
    return out, stats


def main():
    out, stats = build_html()
    print(">>> W006 interactive viewer (SCAFFOLD) written")
    print(f"    {out}")
    print(f"    rows={stats['total']} mapped={stats['mapped']} "
          f"HIGH={stats['high']} MEDIUM={stats['medium']} "
          f"LOW={stats['low']} unmapped={stats['unmapped']}")
    return out


if __name__ == "__main__":
    main()
