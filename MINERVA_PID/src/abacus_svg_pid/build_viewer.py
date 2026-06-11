#!/usr/bin/env python3
"""
build_viewer.py  --  Wave W008  *** PRODUCTION INTERACTIVE VIEWER ***
=====================================================================

STATUS: Full interactive design<->as-drawn cross-map review surface.
        Supersedes the W006 scaffold. Implements every feature in the
        Definition of Done from docs/W006_INTERACTIVE_UI_PLAN.md.

Delivered features (all client-side, single self-contained HTML file):
  1. Tag <-> SVG element highlighting (bidirectional click linking).
     - Each real as-drawn instrument is overlaid with a hit-testable marker
       (positioned from its catalog x/y in the shared 1527x1080 viewBox).
     - Click a table row / search hit -> marker outlines, flashes and the
       drawing pans to centre it. Click a marker -> selects the row + popup.
  2. Confidence-based triage workflow.
     - Filter chips (tier / type / circuit band / sheet), live search,
       column sorting, "unmapped/unclaimed only" quick view.
     - Per-row Confirm / Reject / Defer controls persisted in localStorage
       (never mutates the heuristic crossmap) and exportable as
       triage_decisions.json (the KNOWN_SEEDS feedback file).
  3. Per-layer export controls.
     - 21-layer tree (grouped, collapsible) with show/hide toggles.
     - Export the current composited view as SVG, export any single layer
       as a standalone SVG, and export the filtered table as CSV.
  4. Side-by-side QCELL vs RFCELL comparison view with synchronised
     highlight (a tag lights up on whichever sheet(s) it appears).
  5. Design <-> As-drawn toggle mode -- the table + highlight pivot between
     the design register (97 circuit-sequential tags) and the as-drawn
     catalog (141 SVG-instance tags), synchronised to the drawing.

UI/UX: tag search, colour-coded confidence pills + score bars, collapsible
       responsive sidebar, per-panel zoom & pan, deep-link URL hash state.

Honesty mandate: provenance (reasons[]) and confidence are always visible;
the heuristic crossmap is read-only -- human decisions live in a separate
triage file consumed by KNOWN_SEEDS on the next build_w006_crossmap run.

Inputs : data/crossmap/design_to_asdrawn.json    (build_w006_crossmap)
         data/crossmap/crossmap_confidence.json   (build_w006_crossmap)
         data/excel/catalog_register.json         (build_w005 / build_catalog)
         data/excel/canonical_register_v2.yaml     (build_w006_crossmap)
         configs/layers.yaml                        (layer contract)
         output_v6/{QCELL,RFCELL}/*_13layers.svg    (build_atlas_v6)
Output : publish/interactive_viewer.html
"""
from __future__ import annotations

import glob
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CROSSMAP = os.path.join(ROOT, "data", "crossmap", "design_to_asdrawn.json")
CONFIDENCE = os.path.join(ROOT, "data", "crossmap", "crossmap_confidence.json")
CATALOG = os.path.join(ROOT, "data", "excel", "catalog_register.json")
REGISTER_YAML = os.path.join(ROOT, "data", "excel", "canonical_register_v2.yaml")
LAYERS_YAML = os.path.join(ROOT, "configs", "layers.yaml")
OUT_V6 = os.path.join(ROOT, "output_v6")
PUBLISH = os.path.join(ROOT, "publish")

SHEETS = ["QCELL", "RFCELL"]

TIER_COLOUR = {
    "HIGH": "#1b9e77",
    "MEDIUM": "#d9a300",
    "LOW": "#d95f02",
    "UNMAPPED": "#8a97a8",
    "UNCLAIMED": "#6b5b95",
}


# --------------------------------------------------------------------------- #
#  Loading helpers
# --------------------------------------------------------------------------- #
def _load_json(path):
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        return json.load(fh)


def _load_register_yaml(path):
    """Parse canonical_register_v2.yaml without a hard PyYAML dependency."""
    if not os.path.exists(path):
        return []
    try:
        import yaml  # type: ignore
        doc = yaml.safe_load(open(path))
        return doc.get("instruments", []) if isinstance(doc, dict) else []
    except Exception:
        pass
    # Minimal fallback parser for the known flat list-of-dicts structure.
    instruments, cur, in_list = [], None, False
    for raw in open(path):
        line = raw.rstrip("\n")
        if line.strip() == "instruments:":
            in_list = True
            continue
        if not in_list:
            continue
        if re.match(r"^\s*-\s", line):
            if cur:
                instruments.append(cur)
            cur = {}
            line = re.sub(r"^\s*-\s", "  ", line)
        m = re.match(r"^\s+([A-Za-z_]+):\s*\"?([^\"]*)\"?\s*$", line)
        if m and cur is not None:
            k, v = m.group(1), m.group(2).strip()
            if v == "":
                continue
            try:
                v = float(v) if re.match(r"^-?\d+\.\d+$", v) else int(v) \
                    if re.match(r"^-?\d+$", v) else v
            except ValueError:
                pass
            cur[k] = v
        elif re.match(r"^\S", line) and line.strip() and not line.startswith(" "):
            break
    if cur:
        instruments.append(cur)
    return instruments


def _load_layers(path):
    """Return the ordered 21-layer list; index == lyr-NN class number."""
    fallback = [
        "00_Background_Grid", "01_TitleBlock", "02_ScopeBoundaries_Main",
        "03A_Manifold_COLD_Header", "03B_Manifold_WARM_Header",
        "04A_Lines_A_BLUE", "04B_Lines_B_CYAN", "04C_Lines_W_GREEN",
        "04D_Lines_S_OLIVE", "04E_Lines_V_GREY", "04F_Lines_D_ORANGE",
        "04G_Lines_E_RED", "05_HeatLoads_ALL", "06_SegmentNames_Vertical_Black",
        "07_Equipment_Major", "08_Instruments_Bubbles", "09_Control_Elements",
        "10_Signals_Dashed", "11_Text_ColorCoded", "12_Dots_SpecChanges_ALL",
        "13_Legend_Toggleable",
    ]
    layers = None
    if os.path.exists(path):
        try:
            import yaml  # type: ignore
            doc = yaml.safe_load(open(path))
            layers = [l["id"] for l in doc.get("layers", [])]
        except Exception:
            ids = re.findall(r'id:\s*"([^"]+)"', open(path).read())
            # keep only layer ids (NN_ / NNA_ prefix), preserve order, dedupe
            seen, out = set(), []
            for i in ids:
                if re.match(r"^\d", i) and i not in seen:
                    seen.add(i)
                    out.append(i)
            layers = out or None
    if not layers or len(layers) < 21:
        layers = fallback
    out = []
    for idx, lid in enumerate(layers):
        grp = lid.split("_")[0]
        out.append({"idx": idx, "id": lid, "group": grp})
    return out


# --------------------------------------------------------------------------- #
#  Data-model construction
# --------------------------------------------------------------------------- #
def _design_rows(register, mappings_by_design):
    """Design register (97 tags) joined with crossmap result."""
    rows = []
    for inst in register:
        dtag = inst.get("design_tag")
        if not dtag:
            continue
        m = mappings_by_design.get(dtag)
        if m:
            rows.append({
                "design": dtag,
                "type": inst.get("type", m.get("type", "")),
                "band": inst.get("circuit_band", m.get("design_band", "")),
                "location": inst.get("location", ""),
                "asdrawn": m.get("asdrawn_tag", ""),
                "confidence": float(m.get("confidence", 0.0)),
                "tier": m.get("tier", "UNMAPPED"),
                "reasons": m.get("reasons", []),
                "sheet": m.get("asdrawn_sheet", ""),
                "x": (m.get("asdrawn_xy") or [None, None])[0],
                "y": (m.get("asdrawn_xy") or [None, None])[1],
                "validation": m.get("validation_status", "auto_matched"),
            })
        else:
            rows.append({
                "design": dtag,
                "type": inst.get("type", dtag[:2]),
                "band": inst.get("circuit_band", ""),
                "location": inst.get("location", ""),
                "asdrawn": "",
                "confidence": 0.0,
                "tier": "UNMAPPED",
                "reasons": ["NO_CONFIDENT_MATCH"],
                "sheet": "",
                "x": None, "y": None,
                "validation": "unmapped",
            })
    tier_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "UNMAPPED": 3}
    rows.sort(key=lambda r: (tier_rank.get(r["tier"], 9), r["design"]))
    return rows


def _asdrawn_rows(catalog, asdrawn_to_design, mappings_by_asdrawn):
    """As-drawn catalog (real instances) joined with crossmap result."""
    rows = []
    for inst in catalog.get("instruments", []):
        if inst.get("template"):
            continue
        atag = inst.get("tag") or inst.get("norm")
        if not atag:
            continue
        dtag = asdrawn_to_design.get(atag, "")
        m = mappings_by_asdrawn.get(atag)
        if m:
            tier = m.get("tier", "MEDIUM")
            conf = float(m.get("confidence", 0.0))
            reasons = m.get("reasons", [])
        else:
            tier = "UNCLAIMED"
            conf = 0.0
            reasons = ["NO_DESIGN_CLAIM"]
        rows.append({
            "asdrawn": atag,
            "type": inst.get("prefix", atag[:2]),
            "design": dtag,
            "confidence": conf,
            "tier": tier,
            "reasons": reasons,
            "sheet": inst.get("sheet", ""),
            "x": inst.get("x"),
            "y": inst.get("y"),
            "layer": inst.get("layer", ""),
            "role": inst.get("role", ""),
            "colour": inst.get("colour", ""),
            "isa": inst.get("isa_canonical", ""),
        })
    tier_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "UNCLAIMED": 4}
    rows.sort(key=lambda r: (tier_rank.get(r["tier"], 9), r["asdrawn"]))
    return rows


def _markers(catalog):
    """Per-sheet overlay marker geometry, keyed by as-drawn tag."""
    out = {s: [] for s in SHEETS}
    for inst in catalog.get("instruments", []):
        if inst.get("template") or inst.get("x") is None:
            continue
        sheet = inst.get("sheet", "")
        if sheet not in out:
            continue
        out[sheet].append({
            "tag": inst.get("tag") or inst.get("norm"),
            "x": round(float(inst["x"]), 2),
            "y": round(float(inst["y"]), 2),
            "type": inst.get("prefix", ""),
        })
    return out


def _embed_svg(sheet):
    """Inline the annotated atlas SVG for a sheet (xml decl stripped)."""
    cands = sorted(glob.glob(os.path.join(OUT_V6, sheet, "*_13layers.svg")))
    if not cands:
        cands = sorted(glob.glob(os.path.join(OUT_V6, sheet, "*.svg")))
    if not cands:
        return None
    with open(cands[0]) as fh:
        svg = fh.read()
    svg = re.sub(r"<\?xml[^>]*\?>", "", svg).strip()
    return svg


def _inject_overlay(svg, markers):
    """Insert a hit-testable marker overlay group before the final </svg>."""
    if not svg:
        return svg
    parts = []
    for m in markers:
        tag = m["tag"]
        parts.append(
            f'<g class="tag-mk" data-tag="{tag}" data-type="{m["type"]}">'
            f'<circle cx="{m["x"]}" cy="{m["y"]}" r="13" class="tag-ring"/>'
            f'<circle cx="{m["x"]}" cy="{m["y"]}" r="16" class="tag-hit"/>'
            f'</g>')
    overlay = ('<g id="tag-overlay" '
               'style="pointer-events:visiblePainted">' + "".join(parts) + "</g>")
    idx = svg.rfind("</svg>")
    if idx == -1:
        return svg + overlay
    return svg[:idx] + overlay + svg[idx:]


# --------------------------------------------------------------------------- #
#  HTML / CSS / JS template  (placeholders filled by build_html)
# --------------------------------------------------------------------------- #
_CSS = r"""
*{box-sizing:border-box}
html,body{margin:0;height:100%}
body{font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
  color:#1b2733;background:#0f141b;display:flex;flex-direction:column;height:100vh;
  overflow:hidden}
button{font-family:inherit;cursor:pointer}
code{font-family:Consolas,'DejaVu Sans Mono',monospace}

/* ---- top bar ---- */
#topbar{flex:none;display:flex;align-items:center;gap:14px;flex-wrap:wrap;
  background:#11161f;color:#e8edf4;padding:8px 14px;border-bottom:1px solid #283446}
#topbar h1{font-size:15px;margin:0;font-weight:600;letter-spacing:.3px;white-space:nowrap}
#topbar .badge{background:#1b9e77;color:#fff;font-size:10px;font-weight:700;
  padding:2px 7px;border-radius:4px}
.seg{display:inline-flex;border:1px solid #34465c;border-radius:6px;overflow:hidden}
.seg button{background:#1a2230;color:#aebacb;border:0;padding:6px 12px;font-size:12px}
.seg button.on{background:#2d7ff9;color:#fff}
.seg button:not(:last-child){border-right:1px solid #34465c}
#topbar .grow{flex:1}
#search{padding:7px 10px;border:1px solid #34465c;border-radius:6px;background:#0c1219;
  color:#e8edf4;font-size:13px;min-width:200px}
#search::placeholder{color:#5f7186}
.tbtn{background:#1a2230;color:#cdd8e6;border:1px solid #34465c;border-radius:6px;
  padding:6px 11px;font-size:12px}
.tbtn:hover{background:#243047}
#men-toggle{display:none}

/* ---- body split ---- */
#body{flex:1;display:flex;min-height:0}
#side{width:300px;flex:none;background:#161c26;color:#dbe3ee;overflow:auto;
  padding:12px;border-right:1px solid #283446}
#side h2{font-size:11px;text-transform:uppercase;letter-spacing:.6px;color:#7e8ea3;
  margin:16px 0 6px}
#side h2:first-child{margin-top:0}
.stat-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.stat{background:#1d2532;border-radius:6px;padding:6px 8px}
.stat .n{font-size:18px;font-weight:700}
.stat .l{font-size:10px;color:#8b9bb0;text-transform:uppercase;letter-spacing:.4px}
.chips{display:flex;flex-wrap:wrap;gap:5px}
.chip{font-size:11px;padding:3px 9px;border-radius:12px;border:1px solid #34465c;
  background:#1a2230;color:#aebacb;cursor:pointer;user-select:none}
.chip.on{background:#2d7ff9;border-color:#2d7ff9;color:#fff}
.chip.tier-HIGH.on{background:#1b9e77;border-color:#1b9e77}
.chip.tier-MEDIUM.on{background:#d9a300;border-color:#d9a300;color:#1e2430}
.chip.tier-LOW.on{background:#d95f02;border-color:#d95f02}
.chip.tier-UNMAPPED.on,.chip.tier-UNCLAIMED.on{background:#6b5b95;border-color:#6b5b95}
.qv{display:flex;flex-direction:column;gap:5px}
.qv label{font-size:12px;display:flex;align-items:center;gap:7px;cursor:pointer}

/* ---- layer tree ---- */
#ltree .lgrp{margin-bottom:2px}
#ltree .ghead{display:flex;align-items:center;gap:6px;font-size:12px;font-weight:600;
  color:#cdd8e6;padding:3px 4px;border-radius:4px;cursor:pointer}
#ltree .ghead:hover{background:#1d2532}
#ltree .ghead .caret{font-size:9px;color:#7e8ea3;width:10px}
#ltree .litems{margin:0 0 4px 18px}
#ltree label{display:flex;align-items:center;gap:7px;font-size:11px;color:#a9b7c9;
  padding:2px 0;cursor:pointer}
.ltools{display:flex;gap:6px;margin-top:6px}
.ltools button{flex:1;font-size:10px;padding:4px;background:#1a2230;color:#aebacb;
  border:1px solid #34465c;border-radius:5px}

/* ---- main / svg panels ---- */
#main{flex:1;display:flex;flex-direction:column;min-width:0;background:#0f141b}
#panels{flex:1;display:flex;min-height:0;gap:2px;background:#283446}
.panel{flex:1;display:flex;flex-direction:column;background:#fff;min-width:0}
.panel-head{flex:none;display:flex;align-items:center;gap:8px;background:#1d2532;
  color:#dbe3ee;padding:5px 9px;font-size:12px}
.panel-head .ptitle{font-weight:600}
.panel-head .sp{flex:1}
.panel-head button{background:#283447;color:#cdd8e6;border:0;border-radius:4px;
  width:26px;height:24px;font-size:13px}
.panel-head button:hover{background:#34465c}
.panel-head select{background:#283447;color:#cdd8e6;border:0;border-radius:4px;
  font-size:11px;padding:3px}
.svgwrap{flex:1;overflow:hidden;position:relative;background:#fff;cursor:grab}
.svgwrap.empty{display:flex;align-items:center;justify-content:center;color:#888;
  font-size:13px;text-align:center;padding:20px}
.svgpan{transform-origin:0 0;will-change:transform}
.svgpan svg{width:100%;height:auto;display:block}

/* marker overlay */
.tag-ring{fill:rgba(45,127,249,.0);stroke:rgba(45,127,249,.0);stroke-width:2}
#tag-overlay.show .tag-ring{fill:rgba(45,127,249,.10);stroke:rgba(45,127,249,.55)}
.tag-hit{fill:transparent;stroke:none;cursor:pointer}
.tag-mk.hl .tag-ring{fill:rgba(255,193,7,.28)!important;stroke:#ff5722!important;
  stroke-width:3!important}
@keyframes flashring{0%{stroke-width:3}50%{stroke-width:7}100%{stroke-width:3}}
.tag-mk.flash .tag-ring{animation:flashring .55s ease-in-out 2}

/* layer hide rules injected at runtime */

/* ---- table ---- */
#tablewrap{height:40%;min-height:120px;overflow:auto;background:#f6f8fa;
  border-top:2px solid #283446;resize:vertical}
table{border-collapse:collapse;width:100%;font-size:12px}
th,td{text-align:left;padding:5px 9px;border-bottom:1px solid #e4e9ee;white-space:nowrap}
th{position:sticky;top:0;background:#1d2532;color:#dbe3ee;z-index:3;cursor:pointer;
  user-select:none;font-weight:600}
th .ar{font-size:9px;color:#7e8ea3;margin-left:3px}
td.reasons,td.loc{white-space:normal;color:#5a6b7b;font-size:11px;max-width:280px}
tr.row:hover{background:#eaf1fb;cursor:pointer}
tr.row.sel{background:#d6e6ff!important}
tr.row.hit{outline:2px solid #ffb300;outline-offset:-2px}
.pill{color:#fff;padding:1px 8px;border-radius:9px;font-size:10px;font-weight:600}
.bar{height:5px;border-radius:3px;background:#dde3ea;width:54px;display:inline-block;
  vertical-align:middle;overflow:hidden}
.bar>i{display:block;height:100%}
.tg{display:inline-flex;gap:3px}
.tg button{border:1px solid #cbd3dc;background:#fff;border-radius:4px;font-size:10px;
  padding:2px 6px;color:#56616e}
.tg button.confirm.on{background:#1b9e77;border-color:#1b9e77;color:#fff}
.tg button.reject.on{background:#d64545;border-color:#d64545;color:#fff}
.tg button.defer.on{background:#d9a300;border-color:#d9a300;color:#1e2430}

/* ---- meta popup ---- */
#meta{position:fixed;right:16px;bottom:16px;width:330px;max-width:90vw;background:#1d2532;
  color:#e8edf4;padding:14px;border-radius:8px;font-size:12px;display:none;
  box-shadow:0 8px 30px rgba(0,0,0,.5);z-index:50}
#meta h3{margin:0 0 8px;font-size:13px;display:flex;align-items:center;gap:8px}
#meta .close{margin-left:auto;cursor:pointer;color:#9fb0c4;font-size:16px}
#meta .kv{display:flex;justify-content:space-between;margin:3px 0;gap:10px}
#meta .kv span:first-child{color:#8b9bb0}
#meta .reasons{margin-top:8px;padding-top:8px;border-top:1px solid #33404f;color:#aebacb}
#meta .mtri{margin-top:10px;display:flex;gap:6px}
#meta .mtri button{flex:1;padding:6px;border:0;border-radius:5px;font-size:11px;
  font-weight:600;color:#fff}
#meta .mtri .confirm{background:#1b9e77}#meta .mtri .reject{background:#d64545}
#meta .mtri .defer{background:#d9a300;color:#1e2430}

/* ---- responsive ---- */
@media(max-width:860px){
  #menen-toggle{}
  #menen{}
  #side{position:absolute;z-index:40;height:calc(100% - 49px);transform:translateX(-100%);
    transition:transform .2s}
  #side.open{transform:translateX(0)}
  #menen-toggle,#menu-toggle{display:inline-block}
  #topbar h1 .sub{display:none}
}
.muted{color:#7e8ea3;font-size:11px;line-height:1.5}
"""


_JS = r"""
/* ====================================================================== */
/*  MINERVA W008 Interactive Cross-Map Viewer  --  client logic           */
/* ====================================================================== */
var VBW = 1527.2727, VBH = 1080;
var NLAYERS = DATA.layers.length;

var S = {
  mode: 'design',          // 'design' | 'asdrawn'
  sheet: 'QCELL',          // 'QCELL' | 'RFCELL'
  compare: false,
  filters: { tiers:{}, types:{}, bands:{}, search:'', flag:'all' },
  sort: { col:'tier', dir:1 },
  selected: null,          // primary key of selected row
  showMarkers: false
};
var TRIAGE = {};
try { TRIAGE = JSON.parse(localStorage.getItem('minerva_triage') || '{}'); } catch(e){ TRIAGE = {}; }

var TIER_COLOUR = {HIGH:'#1b9e77', MEDIUM:'#d9a300', LOW:'#d95f02',
                   UNMAPPED:'#8a97a8', UNCLAIMED:'#6b5b95'};

/* ---------- helpers ---------- */
function rowsForMode(){ return S.mode === 'design' ? DATA.designRows : DATA.asdrawnRows; }
function pk(r){ return S.mode === 'design' ? r.design : r.asdrawn; }
/* the as-drawn tag a row points to (for SVG highlight) */
function asdrawnOf(r){ return S.mode === 'design' ? r.asdrawn : r.asdrawn; }
function el(id){ return document.getElementById(id); }
function esc(s){ return (s==null?'':String(s)).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

/* ---------- filtering + sorting ---------- */
function uniq(arr){ var s={}; arr.forEach(function(v){ if(v) s[v]=1; }); return Object.keys(s).sort(); }

function passFilters(r){
  var f = S.filters;
  if(Object.keys(f.tiers).length && !f.tiers[r.tier]) return false;
  if(Object.keys(f.types).length && !f.types[r.type]) return false;
  if(Object.keys(f.bands).length){
    var b = r.band || ''; if(!f.bands[b]) return false;
  }
  if(f.flag === 'unmapped'){
    if(S.mode==='design' && r.asdrawn) return false;
    if(S.mode==='asdrawn' && r.design) return false;
  }
  if(f.flag === 'review' && !(r.tier==='MEDIUM'||r.tier==='LOW')) return false;
  if(f.flag === 'confirmed'){ var t=TRIAGE[pk(r)]; if(!t||t.decision!=='confirm') return false; }
  if(f.search){
    var q = f.search.toUpperCase();
    var hay = ((r.design||'')+' '+(r.asdrawn||'')+' '+(r.type||'')+' '+(r.band||'')+' '+(r.location||'')).toUpperCase();
    if(hay.indexOf(q) < 0) return false;
  }
  return true;
}

function sortRows(rows){
  var c = S.sort.col, d = S.sort.dir;
  var tierRank = {HIGH:0, MEDIUM:1, LOW:2, UNMAPPED:3, UNCLAIMED:4};
  return rows.slice().sort(function(a,b){
    var va, vb;
    if(c==='tier'){ va=tierRank[a.tier]; vb=tierRank[b.tier]; }
    else if(c==='confidence'){ va=a.confidence; vb=b.confidence; }
    else { va=(a[c]||'').toString().toUpperCase(); vb=(b[c]||'').toString().toUpperCase(); }
    if(va<vb) return -1*d; if(va>vb) return 1*d; return 0;
  });
}

/* ---------- render: stats ---------- */
function renderStats(){
  var rows = rowsForMode();
  var vis = rows.filter(passFilters);
  function cnt(t){ return rows.filter(function(r){return r.tier===t;}).length; }
  var mapped = rows.filter(function(r){ return S.mode==='design'? r.asdrawn : r.design; }).length;
  var g = el('stats');
  var unlabel = S.mode==='design' ? 'unmapped' : 'unclaimed';
  var untier  = S.mode==='design' ? 'UNMAPPED' : 'UNCLAIMED';
  g.innerHTML =
    statBox(rows.length, S.mode==='design'?'design tags':'as-drawn tags') +
    statBox(mapped, 'mapped') +
    statBox(cnt('HIGH'),'HIGH','#1b9e77') +
    statBox(cnt('MEDIUM'),'MEDIUM','#d9a300') +
    statBox(cnt('LOW'),'LOW','#d95f02') +
    statBox(cnt(untier), unlabel, '#6b5b95');
  el('viscount').textContent = vis.length + ' / ' + rows.length + ' shown';
}
function statBox(n,l,c){
  return '<div class="stat"><div class="n"'+(c?' style="color:'+c+'"':'')+'>'+n+
    '</div><div class="l">'+l+'</div></div>';
}

/* ---------- render: filter chips ---------- */
function buildFilterChips(){
  var rows = rowsForMode();
  var tiers = S.mode==='design' ? ['HIGH','MEDIUM','LOW','UNMAPPED']
                                : ['HIGH','MEDIUM','LOW','UNCLAIMED'];
  el('f-tiers').innerHTML = tiers.map(function(t){
    return '<span class="chip tier-'+t+'" data-k="tiers" data-v="'+t+'">'+t+'</span>';
  }).join('');
  el('f-types').innerHTML = uniq(rows.map(function(r){return r.type;})).map(function(t){
    return '<span class="chip" data-k="types" data-v="'+t+'">'+t+'</span>';
  }).join('');
  var bands = uniq(rows.map(function(r){return r.band;}));
  el('f-bands-wrap').style.display = bands.length ? '' : 'none';
  el('f-bands').innerHTML = bands.map(function(b){
    return '<span class="chip" data-k="bands" data-v="'+b+'">'+b+'</span>';
  }).join('');
  document.querySelectorAll('#side .chip').forEach(function(ch){
    ch.onclick = function(){
      var k=ch.getAttribute('data-k'), v=ch.getAttribute('data-v');
      if(S.filters[k][v]) delete S.filters[k][v]; else S.filters[k][v]=1;
      ch.classList.toggle('on');
      renderTable(); renderStats();
    };
  });
}

/* ---------- render: table ---------- */
function renderTable(){
  var rows = sortRows(rowsForMode().filter(passFilters));
  var thead, body=[];
  if(S.mode==='design'){
    thead = th('design','tag')+th('asdrawn','as-drawn')+th('type','type')+
      th('band','band')+th('tier','tier')+th('confidence','conf')+
      '<th>triage</th><th>reasons</th>';
    rows.forEach(function(r){ body.push(designRowHtml(r)); });
  } else {
    thead = th('asdrawn','as-drawn')+th('design','design')+th('type','type')+
      th('sheet','sheet')+th('tier','tier')+th('confidence','conf')+
      th('layer','layer')+'<th>reasons</th>';
    rows.forEach(function(r){ body.push(asdrawnRowHtml(r)); });
  }
  el('thead').innerHTML = '<tr>'+thead+'</tr>';
  el('rows').innerHTML = body.join('');
  bindRowEvents();
  if(S.selected) markSelected(S.selected);
}
function th(col,label){
  var ar = S.sort.col===col ? (S.sort.dir>0?'▲':'▼') : '';
  return '<th data-col="'+col+'">'+label+'<span class="ar">'+ar+'</span></th>';
}
function tierPill(t){ return '<span class="pill" style="background:'+(TIER_COLOUR[t]||'#888')+'">'+t+'</span>'; }
function confBar(v){
  var c = v>=0.75?'#1b9e77':v>=0.6?'#d9a300':v>0?'#d95f02':'#c2cad4';
  return v.toFixed(2)+' <span class="bar"><i style="width:'+Math.round(v*100)+'%;background:'+c+'"></i></span>';
}
function triageCell(key){
  var t = TRIAGE[key]||{}; var d=t.decision;
  return '<span class="tg" data-key="'+key+'">'+
    '<button class="confirm'+(d==='confirm'?' on':'')+'" data-d="confirm" title="confirm">✓</button>'+
    '<button class="defer'+(d==='defer'?' on':'')+'" data-d="defer" title="defer">~</button>'+
    '<button class="reject'+(d==='reject'?' on':'')+'" data-d="reject" title="reject">✗</button></span>';
}
function designRowHtml(r){
  return '<tr class="row" data-key="'+r.design+'">'+
    '<td><b>'+esc(r.design)+'</b></td>'+
    '<td>'+(r.asdrawn?esc(r.asdrawn):'<span class="muted">—</span>')+'</td>'+
    '<td>'+esc(r.type)+'</td><td>'+esc(r.band)+'</td>'+
    '<td>'+tierPill(r.tier)+'</td><td>'+confBar(r.confidence)+'</td>'+
    '<td>'+triageCell(r.design)+'</td>'+
    '<td class="reasons">'+esc((r.reasons||[]).join('; '))+
      (r.location?'<br><i class="muted">'+esc(r.location)+'</i>':'')+'</td></tr>';
}
function asdrawnRowHtml(r){
  return '<tr class="row" data-key="'+r.asdrawn+'">'+
    '<td><b>'+esc(r.asdrawn)+'</b></td>'+
    '<td>'+(r.design?esc(r.design):'<span class="muted">unclaimed</span>')+'</td>'+
    '<td>'+esc(r.type)+'</td><td>'+esc(r.sheet)+'</td>'+
    '<td>'+tierPill(r.tier)+'</td><td>'+confBar(r.confidence)+'</td>'+
    '<td class="loc">'+esc(r.layer||'')+'</td>'+
    '<td class="reasons">'+esc((r.reasons||[]).join('; '))+'</td></tr>';
}
function bindRowEvents(){
  document.querySelectorAll('#thead th[data-col]').forEach(function(h){
    h.onclick = function(){
      var c=h.getAttribute('data-col');
      if(S.sort.col===c) S.sort.dir*=-1; else { S.sort.col=c; S.sort.dir=1; }
      renderTable();
    };
  });
  document.querySelectorAll('#rows tr.row').forEach(function(tr){
    tr.onclick = function(e){
      if(e.target.closest('.tg')) return;
      selectKey(tr.getAttribute('data-key'), true);
    };
  });
  document.querySelectorAll('#rows .tg button').forEach(function(b){
    b.onclick = function(e){
      e.stopPropagation();
      var key=b.parentNode.getAttribute('data-key'), d=b.getAttribute('data-d');
      setTriage(key, d);
    };
  });
}

/* ---------- selection + highlight ---------- */
function rowByKey(key){
  return rowsForMode().filter(function(r){ return pk(r)===key; })[0];
}
function selectKey(key, fromTable){
  S.selected = key;
  markSelected(key);
  var r = rowByKey(key);
  if(r){ highlightTag(asdrawnOf(r), r.sheet); showMeta(r); setHash(); }
}
function markSelected(key){
  document.querySelectorAll('#rows tr.row').forEach(function(tr){
    tr.classList.toggle('sel', tr.getAttribute('data-key')===key);
    if(tr.getAttribute('data-key')===key) tr.scrollIntoView({block:'nearest'});
  });
}
function clearHl(){
  document.querySelectorAll('.tag-mk.hl').forEach(function(g){ g.classList.remove('hl','flash'); });
}
function highlightTag(tag, preferSheet){
  clearHl();
  if(!tag) return;
  var found=false;
  PANELS.forEach(function(p){
    var g = p.pan.querySelector('.tag-mk[data-tag="'+cssesc(tag)+'"]');
    if(g){
      g.classList.add('hl','flash');
      centerMarker(p, g);
      found=true;
      setTimeout(function(){ g.classList.remove('flash'); }, 1300);
    }
  });
  return found;
}
function cssesc(s){ return (s||'').replace(/"/g,'\\"'); }
function centerMarker(p, g){
  var ring = g.querySelector('.tag-ring');
  var mx = parseFloat(ring.getAttribute('cx')), my = parseFloat(ring.getAttribute('cy'));
  var wrapW = p.wrap.clientWidth, wrapH = p.wrap.clientHeight;
  var k0 = wrapW / VBW;
  if(p.scale < 2) p.scale = 2.4;
  p.tx = wrapW/2 - mx*k0*p.scale;
  p.ty = wrapH/2 - my*k0*p.scale;
  applyPan(p);
}

/* ---------- meta popup ---------- */
function showMeta(r){
  var m = el('meta');
  el('meta-title').innerHTML = (S.mode==='design'
      ? esc(r.design)+(r.asdrawn?' <span class="muted">↔</span> '+esc(r.asdrawn):' <span class="muted">(unmapped)</span>')
      : esc(r.asdrawn)+(r.design?' <span class="muted">↔</span> '+esc(r.design):' <span class="muted">(unclaimed)</span>'));
  var kv='';
  function row(k,v){ kv += '<div class="kv"><span>'+k+'</span><span>'+esc(v)+'</span></div>'; }
  row('type', r.type);
  if(r.band) row('circuit band', r.band);
  row('tier', r.tier);
  row('confidence', r.confidence.toFixed(2));
  if(r.sheet) row('sheet', r.sheet);
  if(r.location) row('location', r.location);
  if(r.layer) row('layer', r.layer);
  if(r.isa) row('ISA', r.isa);
  if(r.x!=null) row('xy', r.x+', '+r.y);
  el('meta-kv').innerHTML = kv;
  el('meta-reasons').innerHTML = '<b>provenance</b><br>'+esc((r.reasons||[]).join('  •  '));
  var key = pk(r);
  el('meta-tri').setAttribute('data-key', key);
  var d = (TRIAGE[key]||{}).decision;
  el('meta-tri').querySelectorAll('button').forEach(function(b){
    b.style.opacity = (!d || b.getAttribute('data-d')===d) ? 1 : .45;
  });
  m.style.display='block';
}
function hideMeta(){ el('meta').style.display='none'; }

/* ---------- triage ---------- */
function setTriage(key, decision){
  var cur = TRIAGE[key];
  if(cur && cur.decision===decision){ delete TRIAGE[key]; }
  else {
    var r = rowByKey(key) || {};
    TRIAGE[key] = { decision:decision,
      design: S.mode==='design'?key:r.design,
      asdrawn: S.mode==='design'?r.asdrawn:key,
      ts: new Date().toISOString() };
  }
  localStorage.setItem('minerva_triage', JSON.stringify(TRIAGE));
  renderTable(); renderStats();
  if(S.selected===key){ var rr=rowByKey(key); if(rr) showMeta(rr); }
}

/* ---------- layer tree ---------- */
function buildLayerTree(){
  var groups = {};
  DATA.layers.forEach(function(l){
    var g = (l.id.match(/^(\d+)/)||['','?'])[1];
    (groups[g]=groups[g]||[]).push(l);
  });
  var html='';
  Object.keys(groups).sort().forEach(function(g){
    var items = groups[g];
    html += '<div class="lgrp"><div class="ghead" data-g="'+g+'">'+
      '<span class="caret">▼</span><input type="checkbox" checked '+
      'class="gchk" data-g="'+g+'" onclick="event.stopPropagation()"> group '+g+
      ' <span class="muted">('+items.length+')</span></div><div class="litems" data-g="'+g+'">';
    items.forEach(function(l){
      html += '<label><input type="checkbox" checked class="lchk" data-idx="'+l.idx+'"> '+
        esc(l.id)+'</label>';
    });
    html += '</div></div>';
  });
  el('ltree').innerHTML = html;
  document.querySelectorAll('#ltree .ghead').forEach(function(h){
    h.onclick=function(){
      var box=h.nextElementSibling;
      var open = box.style.display!=='none';
      box.style.display = open?'none':'';
      h.querySelector('.caret').textContent = open?'▶':'▼';
    };
  });
  document.querySelectorAll('#ltree .lchk').forEach(function(cb){
    cb.onchange=function(){ setLayer(parseInt(cb.getAttribute('data-idx'),10), cb.checked); };
  });
  document.querySelectorAll('#ltree .gchk').forEach(function(cb){
    cb.onchange=function(){
      var g=cb.getAttribute('data-g');
      document.querySelectorAll('#ltree .lchk').forEach(function(l){
        var idx=parseInt(l.getAttribute('data-idx'),10);
        var lg=(DATA.layers[idx].id.match(/^(\d+)/)||['',''])[1];
        if(lg===g){ l.checked=cb.checked; setLayer(idx, cb.checked); }
      });
    };
  });
}
function setLayer(idx, show){
  var cls = 'hide-'+idx;
  PANELS.forEach(function(p){ p.pan.classList.toggle(cls, !show); });
}
function setAllLayers(show){
  document.querySelectorAll('#ltree .lchk, #ltree .gchk').forEach(function(cb){ cb.checked=show; });
  for(var i=0;i<NLAYERS;i++) setLayer(i, show);
}

/* ---------- panels: pan + zoom ---------- */
var PANELS = [];
function initPanels(){
  PANELS = [];
  document.querySelectorAll('.svgwrap').forEach(function(wrap){
    var pan = wrap.querySelector('.svgpan');
    if(!pan) return;
    var p = { wrap:wrap, pan:pan, scale:1, tx:0, ty:0, dragging:false, sx:0, sy:0 };
    PANELS.push(p);
    wrap.addEventListener('wheel', function(e){
      e.preventDefault();
      var f = e.deltaY<0?1.12:0.89;
      var rect = wrap.getBoundingClientRect();
      var mxs = e.clientX-rect.left, mys = e.clientY-rect.top;
      var ns = Math.min(12, Math.max(0.2, p.scale*f));
      p.tx = mxs - (mxs-p.tx)*(ns/p.scale);
      p.ty = mys - (mys-p.ty)*(ns/p.scale);
      p.scale = ns; applyPan(p);
    }, {passive:false});
    wrap.addEventListener('mousedown', function(e){
      if(e.target.closest('.tag-hit')) return;
      p.dragging=true; p.sx=e.clientX-p.tx; p.sy=e.clientY-p.ty; wrap.style.cursor='grabbing';
    });
    window.addEventListener('mouseup', function(){ p.dragging=false; wrap.style.cursor='grab'; });
    window.addEventListener('mousemove', function(e){
      if(p.dragging){ p.tx=e.clientX-p.sx; p.ty=e.clientY-p.sy; applyPan(p); }
    });
    // marker clicks
    pan.querySelectorAll('.tag-hit').forEach(function(hit){
      hit.addEventListener('click', function(e){
        e.stopPropagation();
        var tag = hit.parentNode.getAttribute('data-tag');
        onMarkerClick(tag);
      });
    });
  });
}
function applyPan(p){ p.pan.style.transform='translate('+p.tx+'px,'+p.ty+'px) scale('+p.scale+')'; }
function zoomPanel(which, f){
  PANELS.forEach(function(p,i){
    if(which!=null && i!==which) return;
    if(f===0){ p.scale=1; p.tx=0; p.ty=0; } else { p.scale=Math.min(12,Math.max(0.2,p.scale*f)); }
    applyPan(p);
  });
}
function onMarkerClick(tag){
  // map as-drawn tag -> current-mode key
  var key;
  if(S.mode==='design'){
    var hit = DATA.designRows.filter(function(r){return r.asdrawn===tag;})[0];
    if(!hit){ // switch to as-drawn mode to show it
      setMode('asdrawn'); key=tag;
    } else key=hit.design;
  } else key=tag;
  // ensure visible (clear flag filters that would hide it)
  selectKey(key, true);
}

/* ---------- mode / sheet / compare switching ---------- */
function setMode(mode){
  S.mode=mode; S.selected=null; S.filters={tiers:{},types:{},bands:{},search:el('search').value,flag:S.filters.flag};
  document.querySelectorAll('#mode-seg button').forEach(function(b){ b.classList.toggle('on', b.getAttribute('data-m')===mode); });
  buildFilterChips(); renderTable(); renderStats(); setHash();
}
function setSheet(sheet){
  if(sheet==='COMPARE'){ S.compare=true; }
  else { S.compare=false; S.sheet=sheet; }
  document.querySelectorAll('#sheet-seg button').forEach(function(b){ b.classList.toggle('on', b.getAttribute('data-s')===sheet); });
  renderPanels(); setHash();
}
function renderPanels(){
  var cont = el('panels');
  cont.innerHTML='';
  var list = S.compare ? ['QCELL','RFCELL'] : [S.sheet];
  list.forEach(function(sh){ cont.appendChild(makePanel(sh)); });
  initPanels();
  // restore marker visibility
  applyMarkerVis();
  // re-apply layer hide state
  document.querySelectorAll('#ltree .lchk').forEach(function(cb){
    setLayer(parseInt(cb.getAttribute('data-idx'),10), cb.checked);
  });
}
function makePanel(sheet){
  var wrap = document.createElement('div'); wrap.className='panel'; wrap.setAttribute('data-sheet',sheet);
  var svg = SVGS[sheet];
  var layerOpts = DATA.layers.map(function(l){ return '<option value="'+l.idx+'">'+esc(l.id)+'</option>'; }).join('');
  wrap.innerHTML =
    '<div class="panel-head"><span class="ptitle">'+sheet+'</span><span class="sp"></span>'+
      '<button title="zoom in" onclick="zoomBySheet(\''+sheet+'\',1.25)">+</button>'+
      '<button title="zoom out" onclick="zoomBySheet(\''+sheet+'\',0.8)">−</button>'+
      '<button title="reset" onclick="zoomBySheet(\''+sheet+'\',0)">⟲</button>'+
      '<select title="export single layer as SVG" onchange="exportLayer(\''+sheet+'\',this.value);this.value=\'\'">'+
        '<option value="">export layer…</option>'+layerOpts+'</select>'+
      '<button title="export this view as SVG" onclick="exportViewSVG(\''+sheet+'\')">⬇SVG</button></div>'+
    (svg ? '<div class="svgwrap"><div class="svgpan">'+svg+'</div></div>'
         : '<div class="svgwrap empty">Atlas SVG for '+sheet+' not found.<br>Run <code>./make.sh</code>.</div>');
  return wrap;
}
function zoomBySheet(sheet,f){
  PANELS.forEach(function(p){ if(p.wrap.parentNode.getAttribute('data-sheet')===sheet){ 
    if(f===0){p.scale=1;p.tx=0;p.ty=0;} else {p.scale=Math.min(12,Math.max(0.2,p.scale*f));} applyPan(p);
  }});
}

/* ---------- markers ---------- */
function toggleMarkers(on){
  S.showMarkers=on; applyMarkerVis();
}
function applyMarkerVis(){
  PANELS.forEach(function(p){
    var ov=p.pan.querySelector('#tag-overlay');
    if(ov) ov.classList.toggle('show', S.showMarkers);
  });
}

/* ---------- export ---------- */
function download(name, text, mime){
  var blob=new Blob([text],{type:mime||'text/plain'});
  var a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download=name;
  document.body.appendChild(a); a.click(); a.remove();
}
function exportCSV(){
  var rows = sortRows(rowsForMode().filter(passFilters));
  var cols = S.mode==='design'
    ? ['design','asdrawn','type','band','tier','confidence','sheet','validation','location','reasons']
    : ['asdrawn','design','type','sheet','tier','confidence','layer','role','isa','reasons'];
  var out=[cols.join(',')];
  rows.forEach(function(r){
    out.push(cols.map(function(c){
      var v = c==='reasons' ? (r.reasons||[]).join('; ') : (r[c]==null?'':r[c]);
      v=String(v).replace(/"/g,'""');
      return /[",\n]/.test(v) ? '"'+v+'"' : v;
    }).join(','));
  });
  download('crossmap_'+S.mode+'.csv', out.join('\n'), 'text/csv');
}
function exportTriage(){
  var seeds={};
  Object.keys(TRIAGE).forEach(function(k){
    var t=TRIAGE[k];
    if(t.decision==='confirm' && t.design && t.asdrawn) seeds[t.design]=t.asdrawn;
  });
  var doc={version:1, wave:'W008', generated:new Date().toISOString(),
    note:'Feed KNOWN_SEEDS into build_w006_crossmap.py to promote confirmed pairs to HIGH.',
    decisions:TRIAGE, known_seeds:seeds};
  download('triage_decisions.json', JSON.stringify(doc,null,2), 'application/json');
}
function panFor(sheet){
  var arr=PANELS.filter(function(p){return p.wrap.parentNode.getAttribute('data-sheet')===sheet;});
  return arr[0];
}
function cleanClone(sheet){
  var p=panFor(sheet); if(!p) return null;
  var svg=p.pan.querySelector('svg').cloneNode(true);
  var ov=svg.querySelector('#tag-overlay'); if(ov) ov.remove();
  return svg;
}
function exportViewSVG(sheet){
  var svg=cleanClone(sheet); if(!svg){ alert('No SVG for '+sheet); return; }
  // drop currently-hidden layers
  for(var i=0;i<NLAYERS;i++){
    var cb=document.querySelector('#ltree .lchk[data-idx="'+i+'"]');
    if(cb && !cb.checked){
      svg.querySelectorAll('.lyr-'+(i<10?'0'+i:i)).forEach(function(e){ e.remove(); });
    }
  }
  download(sheet+'_view.svg', new XMLSerializer().serializeToString(svg), 'image/svg+xml');
}
function exportLayer(sheet, idxStr){
  if(idxStr==='') return;
  var idx=parseInt(idxStr,10);
  var svg=cleanClone(sheet); if(!svg){ alert('No SVG for '+sheet); return; }
  var keep='lyr-'+(idx<10?'0'+idx:idx);
  svg.querySelectorAll('[class*="lyr-"]').forEach(function(e){
    if(!e.classList.contains(keep)) e.remove();
  });
  download(sheet+'_'+DATA.layers[idx].id+'.svg', new XMLSerializer().serializeToString(svg), 'image/svg+xml');
}

/* ---------- search ---------- */
function doSearch(q){
  S.filters.search=q.trim();
  renderTable(); renderStats();
  if(S.filters.search){
    var rows=rowsForMode().filter(passFilters);
    if(rows.length){ selectKey(pk(rows[0]), true); }
  }
  setHash();
}

/* ---------- deep-link hash ---------- */
function setHash(){
  var h=[];
  h.push('mode='+S.mode);
  h.push('sheet='+(S.compare?'COMPARE':S.sheet));
  if(S.selected) h.push('tag='+encodeURIComponent(S.selected));
  if(S.filters.search) h.push('q='+encodeURIComponent(S.filters.search));
  if(S.filters.flag!=='all') h.push('flag='+S.filters.flag);
  history.replaceState(null,'','#'+h.join('&'));
}
function readHash(){
  var h=location.hash.replace(/^#/,''); if(!h) return;
  var p={}; h.split('&').forEach(function(kv){ var a=kv.split('='); p[a[0]]=decodeURIComponent(a[1]||''); });
  if(p.mode) S.mode=p.mode;
  if(p.flag){ S.filters.flag=p.flag; }
  if(p.q){ S.filters.search=p.q; }
  if(p.sheet==='COMPARE') S.compare=true; else if(p.sheet) S.sheet=p.sheet;
  return p;
}

/* ---------- boot ---------- */
function boot(){
  var p=readHash();
  // top controls
  document.querySelectorAll('#mode-seg button').forEach(function(b){ b.onclick=function(){ setMode(b.getAttribute('data-m')); }; b.classList.toggle('on', b.getAttribute('data-m')===S.mode); });
  document.querySelectorAll('#sheet-seg button').forEach(function(b){ b.onclick=function(){ setSheet(b.getAttribute('data-s')); };
    b.classList.toggle('on', b.getAttribute('data-s')===(S.compare?'COMPARE':S.sheet)); });
  el('search').value=S.filters.search||'';
  el('search').oninput=function(){ doSearch(this.value); };
  document.querySelectorAll('input[name="flag"]').forEach(function(r){
    r.checked = r.value===S.filters.flag;
    r.onchange=function(){ if(r.checked){ S.filters.flag=r.value; renderTable(); renderStats(); setHash(); } };
  });
  el('mk-toggle').onchange=function(){ toggleMarkers(this.checked); };
  el('btn-csv').onclick=exportCSV;
  el('btn-triage').onclick=exportTriage;
  el('btn-clear-tri').onclick=function(){ if(confirm('Clear all triage decisions?')){ TRIAGE={}; localStorage.removeItem('minerva_triage'); renderTable(); renderStats(); } };
  el('la-on').onclick=function(){ setAllLayers(true); };
  el('la-off').onclick=function(){ setAllLayers(false); };
  el('menu-toggle').onclick=function(){ el('side').classList.toggle('open'); };
  el('meta-tri').querySelectorAll('button').forEach(function(b){
    b.onclick=function(){ var key=el('meta-tri').getAttribute('data-key'); setTriage(key, b.getAttribute('data-d')); };
  });

  buildFilterChips(); buildLayerTree(); renderPanels(); renderTable(); renderStats();
  if(p && p.tag){ setTimeout(function(){ selectKey(p.tag, true); }, 60); }
}
"""


_HTML = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>MINERVA W008 — Interactive Cross-Map Viewer</title>
<style>__CSS__
__LAYER_HIDE_RULES__</style></head>
<body>
<div id="topbar">
  <button id="menu-toggle" class="tbtn" title="menu">☰</button>
  <h1>MINERVA Cross-Map <span class="badge">W008</span>
    <span class="sub muted">&nbsp;design ↔ as-drawn</span></h1>
  <span class="seg" id="mode-seg">
    <button data-m="design" class="on">Design</button>
    <button data-m="asdrawn">As-drawn</button></span>
  <span class="seg" id="sheet-seg">
    <button data-s="QCELL" class="on">QCELL</button>
    <button data-s="RFCELL">RFCELL</button>
    <button data-s="COMPARE">Compare</button></span>
  <input id="search" placeholder="search tag, type, band, location…"/>
  <span class="grow"></span>
  <button class="tbtn" id="btn-csv" title="export filtered table as CSV">⬇ CSV</button>
  <button class="tbtn" id="btn-triage" title="export triage decisions (KNOWN_SEEDS)">⬇ Triage</button>
</div>

<div id="body">
  <div id="side">
    <h2>Overview · <span id="viscount" class="muted"></span></h2>
    <div class="stat-grid" id="stats"></div>

    <h2>Quick views</h2>
    <div class="qv">
      <label><input type="radio" name="flag" value="all" checked> all</label>
      <label><input type="radio" name="flag" value="unmapped"> unmapped / unclaimed only</label>
      <label><input type="radio" name="flag" value="review"> needs review (MEDIUM/LOW)</label>
      <label><input type="radio" name="flag" value="confirmed"> confirmed (triaged)</label>
    </div>

    <h2>Tier</h2><div class="chips" id="f-tiers"></div>
    <h2>Type</h2><div class="chips" id="f-types"></div>
    <div id="f-bands-wrap"><h2>Circuit band</h2><div class="chips" id="f-bands"></div></div>

    <h2>SVG markers</h2>
    <label class="qv"><input type="checkbox" id="mk-toggle"> show tag markers on drawing</label>

    <h2>Layers (21)</h2>
    <div id="ltree"></div>
    <div class="ltools">
      <button id="la-on">all on</button><button id="la-off">all off</button>
    </div>

    <h2>Triage</h2>
    <button class="ltools" style="width:100%;padding:6px;background:#33212a;color:#f0b6b6;border:1px solid #5a3340;border-radius:5px" id="btn-clear-tri">clear all decisions</button>
    <p class="muted" style="margin-top:14px">Heuristic, confidence-scored map — read-only. Decisions persist locally &amp; export as <code>triage_decisions.json</code> for <code>KNOWN_SEEDS</code>. Wheel = zoom, drag = pan, click a marker or row to link.</p>
  </div>

  <div id="main">
    <div id="panels"></div>
    <div id="tablewrap">
      <table>
        <thead id="thead"></thead>
        <tbody id="rows"></tbody>
      </table>
    </div>
  </div>
</div>

<div id="meta">
  <h3 id="meta-title"></h3><span class="close" onclick="hideMeta()" style="position:absolute;top:12px;right:14px">×</span>
  <div id="meta-kv"></div>
  <div class="reasons" id="meta-reasons"></div>
  <div class="mtri" id="meta-tri" data-key="">
    <button class="confirm" data-d="confirm">✓ Confirm</button>
    <button class="defer" data-d="defer">~ Defer</button>
    <button class="reject" data-d="reject">✗ Reject</button>
  </div>
</div>

<script type="text/html" id="svg-QCELL">__SVG_QCELL__</script>
<script type="text/html" id="svg-RFCELL">__SVG_RFCELL__</script>
<script>
var DATA = __DATA__;
var SVGS = {};
['QCELL','RFCELL'].forEach(function(s){ var e=document.getElementById('svg-'+s); var t=e?e.textContent.trim():''; SVGS[s]= t? t : null; });
__JS__
boot();
</script>
</body></html>"""


def build_html():
    crossmap = _load_json(CROSSMAP)
    if not crossmap:
        raise SystemExit("W006 crossmap not found -- run build_w006_crossmap first.")
    confidence = _load_json(CONFIDENCE) or {}
    catalog = _load_json(CATALOG) or {}
    register = _load_register_yaml(REGISTER_YAML)
    layers = _load_layers(LAYERS_YAML)

    mappings = crossmap.get("mappings", [])
    mappings_by_design = {m["design_tag"]: m for m in mappings}
    mappings_by_asdrawn = {m["asdrawn_tag"]: m for m in mappings}
    asdrawn_to_design = crossmap.get("asdrawn_to_design", {})

    # If register is empty (no yaml/parser), synthesise from the crossmap's design list.
    if not register:
        seen = set()
        for m in mappings:
            register.append({"design_tag": m["design_tag"], "type": m.get("type", ""),
                             "circuit_band": m.get("design_band", "")})
            seen.add(m["design_tag"])
        for u in confidence.get("unmapped_design", []):
            dt = u.get("design_tag") if isinstance(u, dict) else u
            if dt and dt not in seen:
                register.append({"design_tag": dt,
                                 "type": (u.get("type") if isinstance(u, dict) else dt[:2]),
                                 "circuit_band": (u.get("band") if isinstance(u, dict) else "")})

    design_rows = _design_rows(register, mappings_by_design)
    asdrawn_rows = _asdrawn_rows(catalog, asdrawn_to_design, mappings_by_asdrawn)
    markers = _markers(catalog)

    svgs = {}
    for sh in SHEETS:
        raw = _embed_svg(sh)
        svgs[sh] = _inject_overlay(raw, markers.get(sh, [])) if raw else ""

    data = {
        "meta": {
            "design_total": len(design_rows),
            "asdrawn_total": len(asdrawn_rows),
            "mapped": len(mappings),
        },
        "layers": layers,
        "designRows": design_rows,
        "asdrawnRows": asdrawn_rows,
        "sheets": SHEETS,
    }

    layer_hide_rules = "".join(
        f".svgpan.hide-{i} .lyr-{i:02d}{{display:none!important}}"
        for i in range(len(layers)))

    html_doc = (_HTML
                .replace("__CSS__", _CSS)
                .replace("__LAYER_HIDE_RULES__", layer_hide_rules)
                .replace("__SVG_QCELL__", svgs.get("QCELL", ""))
                .replace("__SVG_RFCELL__", svgs.get("RFCELL", ""))
                .replace("__DATA__", json.dumps(data))
                .replace("__JS__", _JS))

    os.makedirs(PUBLISH, exist_ok=True)
    out = os.path.join(PUBLISH, "interactive_viewer.html")
    with open(out, "w") as fh:
        fh.write(html_doc)

    stats = {
        "design_rows": len(design_rows),
        "asdrawn_rows": len(asdrawn_rows),
        "mapped": len(mappings),
        "high": sum(1 for r in design_rows if r["tier"] == "HIGH"),
        "medium": sum(1 for r in design_rows if r["tier"] == "MEDIUM"),
        "low": sum(1 for r in design_rows if r["tier"] == "LOW"),
        "unmapped": sum(1 for r in design_rows if not r["asdrawn"]),
        "markers_qcell": len(markers.get("QCELL", [])),
        "markers_rfcell": len(markers.get("RFCELL", [])),
        "layers": len(layers),
        "bytes": len(html_doc),
    }
    return out, stats


def main():
    out, stats = build_html()
    print(">>> W008 interactive viewer written")
    print(f"    {out}")
    print(f"    design_rows={stats['design_rows']} asdrawn_rows={stats['asdrawn_rows']} "
          f"mapped={stats['mapped']}")
    print(f"    HIGH={stats['high']} MEDIUM={stats['medium']} LOW={stats['low']} "
          f"unmapped={stats['unmapped']}")
    print(f"    markers QCELL={stats['markers_qcell']} RFCELL={stats['markers_rfcell']} "
          f"layers={stats['layers']} size={stats['bytes']//1024}KB")
    return out


if __name__ == "__main__":
    main()
