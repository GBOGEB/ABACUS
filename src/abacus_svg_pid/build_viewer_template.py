#!/usr/bin/env python3
"""
build_viewer_template.py -- Wave W008
=====================================

Holds the single PAGE string (HTML + CSS + JS) for the interactive viewer.
Kept separate from build_viewer.py so the build module stays readable.

Substitution is token-based (`__TOKEN__`) -- NOT str.format -- because the
CSS/JS contain many literal braces. build_viewer.py does plain .replace().

Tokens consumed here:
  __ROWS_JSON__ __FOUND_JSON__ __TABLE_ROWS__ __Q_PANE__ __R_PANE__ __HAS_R__
  __Q_VB__ __R_VB__ __S_DESIGN__ __S_ASDRAWN__ __S_MAPPED__ __S_HIGH__
  __S_MEDIUM__ __S_LOW__ __S_UNMAPPED__ __S_UNCLAIMED__ __S_LOCATABLE__
  __TC_HIGH__ __TC_MEDIUM__ __TC_LOW__ __TC_UNMAPPED__
"""

PAGE = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>MINERVA W008 - Interactive Cross-Map Viewer</title>
<style>
 *{box-sizing:border-box;}
 html,body{margin:0;height:100%;}
 body{font-family:Consolas,'DejaVu Sans Mono',monospace;color:#1b2733;
   display:flex;flex-direction:column;height:100vh;overflow:hidden;}
 /* ---- loading overlay ---- */
 #loading{position:fixed;inset:0;background:#1e2430;color:#e8edf4;z-index:50;
   display:flex;align-items:center;justify-content:center;font-size:15px;
   transition:opacity .35s;}
 #loading.hide{opacity:0;pointer-events:none;}
 #loading .spin{width:16px;height:16px;border:3px solid #5a6b7b;
   border-top-color:#d9a300;border-radius:50%;display:inline-block;
   margin-right:10px;animation:spin 0.8s linear infinite;}
 @keyframes spin{to{transform:rotate(360deg);}}
 /* ---- top bar ---- */
 #topbar{background:#1e2430;color:#e8edf4;display:flex;align-items:center;
   gap:10px;padding:8px 12px;flex:none;flex-wrap:wrap;}
 #topbar h1{font-size:13px;margin:0;white-space:nowrap;}
 #topbar .tag{background:#2a3340;color:#9fb0c4;font-size:9px;padding:2px 6px;
   border-radius:3px;}
 .tabbtn,.tool{background:#2a3340;color:#e8edf4;border:1px solid #3a4656;
   font-family:inherit;font-size:11px;padding:5px 9px;border-radius:4px;
   cursor:pointer;}
 .tabbtn.active{background:#d9a300;color:#1e2430;font-weight:bold;border-color:#d9a300;}
 .tool:hover,.tabbtn:hover{background:#3a4656;}
 #search{padding:6px 8px;border:0;border-radius:4px;font-family:inherit;
   font-size:12px;min-width:180px;flex:1;max-width:280px;}
 #typeFilter{padding:5px;border-radius:4px;border:0;font-family:inherit;font-size:11px;}
 .spacer{flex:1;}
 /* ---- layout ---- */
 #layout{flex:1;display:flex;overflow:hidden;}
 #side{width:300px;background:#222a36;color:#e8edf4;padding:12px;overflow:auto;
   flex:none;}
 #side h2{font-size:11px;margin:14px 0 6px;color:#9fb0c4;text-transform:uppercase;
   letter-spacing:.5px;}
 .statgrid{display:grid;grid-template-columns:1fr 1fr;gap:4px;font-size:11px;}
 .statgrid .k{color:#9fb0c4;}
 .statgrid .v{text-align:right;font-weight:bold;}
 .filters{display:flex;flex-wrap:wrap;gap:5px;margin:4px 0;}
 .fbtn{flex:1 1 44%;text-align:left;background:#2a3340;border:1px solid #3a4656;
   color:#e8edf4;font-family:inherit;font-size:11px;padding:5px 7px;border-radius:4px;
   cursor:pointer;display:flex;justify-content:space-between;}
 .fbtn .n{color:#9fb0c4;}
 .fbtn.active{background:#33404f;border-color:#d9a300;}
 .fbtn.dim{opacity:.45;}
 .swatch{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:5px;}
 #layers{columns:2;font-size:10px;}
 #layers label{display:block;cursor:pointer;margin:1px 0;}
 #breadcrumb{font-size:11px;color:#cfe;min-height:16px;word-break:break-all;}
 .mini{font-size:10px;color:#7d8ea3;line-height:1.45;}
 .linkbtn{background:none;border:0;color:#7fd1c4;cursor:pointer;font-size:11px;
   font-family:inherit;padding:2px 0;text-decoration:underline;display:block;}
 /* ---- main ---- */
 #main{flex:1;display:flex;flex-direction:column;overflow:hidden;}
 #viewer{flex:1;position:relative;background:#eef1f4;overflow:hidden;}
 #panes{display:flex;height:100%;width:100%;}
 .pane{flex:1;position:relative;background:#fff;overflow:hidden;
   border-right:2px solid #1e2430;min-width:0;}
 .pane:last-child{border-right:0;}
 .pane.empty{display:flex;align-items:center;justify-content:center;color:#888;
   text-align:center;font-size:13px;}
 #panes.single #paneR{display:none;}
 .pane-label{position:absolute;top:0;left:0;right:0;background:rgba(30,36,48,.82);
   color:#e8edf4;font-size:10px;padding:3px 8px;z-index:3;}
 .pane svg{width:100%;height:100%;display:block;cursor:grab;touch-action:none;}
 .pane svg.grabbing{cursor:grabbing;}
 .pidhit{outline:none;}
 .hl-box{fill:none;stroke:#e6194b;stroke-width:6;vector-effect:non-scaling-stroke;
   animation:pulse 1s ease-in-out infinite;}
 @keyframes pulse{0%,100%{stroke-opacity:1;}50%{stroke-opacity:.25;}}
 #zoomctl{position:absolute;right:10px;bottom:10px;display:flex;flex-direction:column;
   gap:4px;z-index:4;}
 #zoomctl button{width:30px;height:28px;font-size:14px;border:1px solid #c4ccd4;
   background:#fff;border-radius:4px;cursor:pointer;}
 #syncwrap{position:absolute;left:10px;bottom:10px;z-index:4;background:rgba(255,255,255,.9);
   padding:4px 8px;border-radius:4px;font-size:11px;display:none;}
 #panes.compare ~ #syncwrap,#viewer.compare #syncwrap{display:block;}
 /* ---- table ---- */
 #tablewrap{height:42%;overflow:auto;background:#f6f8fa;border-top:2px solid #1e2430;}
 table{border-collapse:collapse;width:100%;font-size:11px;}
 th,td{text-align:left;padding:4px 8px;border-bottom:1px solid #e1e6eb;white-space:nowrap;}
 th{position:sticky;top:0;background:#1e2430;color:#e8edf4;z-index:2;cursor:default;}
 td.reasons{color:#5a6b7b;white-space:normal;}
 tr.row:hover{background:#eef3f8;cursor:pointer;}
 tr.row.sel{background:#fff3cd!important;}
 tr.row.hidden{display:none;}
 .pill{color:#fff;padding:1px 6px;border-radius:8px;font-size:10px;}
 .c-loc{text-align:center;width:18px;}
 .vbtn{border:1px solid #c4ccd4;background:#fff;border-radius:3px;cursor:pointer;
   font-size:10px;padding:1px 5px;font-family:inherit;}
 .vbtn.on-confirm{background:#1b9e77;color:#fff;border-color:#1b9e77;}
 .vbtn.on-reject{background:#d62728;color:#fff;border-color:#d62728;}
 .vbtn.on-suggest{background:#7570b3;color:#fff;border-color:#7570b3;}
 .valbadge{font-size:9px;padding:1px 4px;border-radius:3px;color:#fff;}
 /* ---- popovers ---- */
 #meta{position:fixed;right:14px;bottom:14px;width:310px;background:#1e2430;
   color:#e8edf4;padding:12px;border-radius:6px;font-size:11px;display:none;
   box-shadow:0 4px 18px rgba(0,0,0,.4);z-index:20;}
 #meta h3{margin:0 0 6px;font-size:12px;}
 #meta .close{float:right;cursor:pointer;color:#9fb0c4;}
 #exportMenu{position:fixed;background:#1e2430;color:#e8edf4;border:1px solid #3a4656;
   border-radius:6px;padding:6px;display:none;z-index:30;box-shadow:0 4px 18px rgba(0,0,0,.4);}
 #exportMenu button{display:block;width:100%;text-align:left;background:none;border:0;
   color:#e8edf4;font-family:inherit;font-size:12px;padding:6px 10px;cursor:pointer;border-radius:4px;}
 #exportMenu button:hover{background:#33404f;}
 #exportMenu .sep{border-top:1px solid #3a4656;margin:4px 0;}
 .modal{position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:40;display:none;
   align-items:center;justify-content:center;}
 .modal.show{display:flex;}
 .modal .box{background:#fff;color:#1b2733;padding:20px;border-radius:8px;max-width:480px;
   font-size:12px;line-height:1.6;}
 .modal kbd{background:#222a36;color:#e8edf4;border-radius:3px;padding:1px 6px;font-size:11px;}
 #toast{position:fixed;left:50%;bottom:24px;transform:translateX(-50%);
   background:#1b9e77;color:#fff;padding:8px 16px;border-radius:6px;font-size:12px;
   z-index:60;opacity:0;transition:opacity .3s;pointer-events:none;}
 #toast.show{opacity:1;}
 @media print{#topbar,#side,#tablewrap,#zoomctl,#meta,#exportMenu,.pane-label,#syncwrap{display:none!important;}
   #tablewrap{display:none!important;} #viewer{height:100vh;}}
</style></head>
<body>
<div id="loading"><span class="spin"></span>Loading interactive viewer&hellip;</div>

<header id="topbar">
 <h1>MINERVA W008 Cross-Map Viewer</h1>
 <span class="tag">QCELL / RFCELL P&amp;ID</span>
 <button class="tabbtn active" id="tabSingle" onclick="setView('single')">Single</button>
 <button class="tabbtn" id="tabCompare" onclick="setView('compare')" title="QCELL vs RFCELL side-by-side">Compare</button>
 <input id="search" placeholder="search design / as-drawn tag (Ctrl+F)" oninput="applyFilters()" title="Dual-tag search: matches design OR as-drawn"/>
 <select id="typeFilter" onchange="applyFilters()" title="Filter by instrument type"><option value="">all types</option></select>
 <div class="spacer"></div>
 <button class="tool" onclick="toggleExport(event)" title="Export (Ctrl+E)">Export &#9662;</button>
 <button class="tool" onclick="showHelp()" title="Keyboard shortcuts">?</button>
</header>

<div id="layout">
 <aside id="side">
  <h2>Distribution (real W006 data)</h2>
  <div class="statgrid">
   <div class="k">design tags</div><div class="v">__S_DESIGN__</div>
   <div class="k">as-drawn real</div><div class="v">__S_ASDRAWN__</div>
   <div class="k">mapped</div><div class="v">__S_MAPPED__</div>
   <div class="k">unmapped</div><div class="v">__S_UNMAPPED__</div>
   <div class="k">as-drawn unclaimed</div><div class="v">__S_UNCLAIMED__</div>
   <div class="k">locatable in atlas</div><div class="v">__S_LOCATABLE__</div>
  </div>

  <h2>Triage filter</h2>
  <div class="filters">
   <button class="fbtn active" data-filter="ALL" onclick="setFilter('ALL')"><span>ALL</span><span class="n">__S_DESIGN__</span></button>
   <button class="fbtn" data-filter="MAPPED" onclick="setFilter('MAPPED')"><span>MAPPED</span><span class="n">__S_MAPPED__</span></button>
   <button class="fbtn dim" data-filter="HIGH" onclick="setFilter('HIGH')"><span><span class="swatch" style="background:__TC_HIGH__"></span>HIGH</span><span class="n">__S_HIGH__</span></button>
   <button class="fbtn" data-filter="MEDIUM" onclick="setFilter('MEDIUM')"><span><span class="swatch" style="background:__TC_MEDIUM__"></span>MEDIUM</span><span class="n">__S_MEDIUM__</span></button>
   <button class="fbtn" data-filter="LOW" onclick="setFilter('LOW')"><span><span class="swatch" style="background:__TC_LOW__"></span>LOW</span><span class="n">__S_LOW__</span></button>
   <button class="fbtn" data-filter="UNMAPPED" onclick="setFilter('UNMAPPED')"><span><span class="swatch" style="background:__TC_UNMAPPED__"></span>UNMAPPED</span><span class="n">__S_UNMAPPED__</span></button>
  </div>
  <p class="mini">Real W006 distribution has <b>0 HIGH</b> pairs (heuristic ceiling
   0.75 = MEDIUM). The HIGH filter is shown for completeness.</p>

  <h2>Validation</h2>
  <p class="mini">Confirm / reject / suggest each pair. Saved in your browser
   (localStorage) and exportable as JSON.</p>
  <button class="linkbtn" onclick="exportValidations()">&#8681; export validations JSON</button>
  <button class="linkbtn" onclick="resetValidations()">&#10227; reset validations</button>
  <div class="mini" id="valcount"></div>

  <h2>Layers (atlas v6)</h2>
  <div id="layers"></div>

  <h2>Selection</h2>
  <div id="breadcrumb">none</div>
 </aside>

 <main id="main">
  <div id="viewer">
   <div id="panes" class="single">
    __Q_PANE__
    __R_PANE__
   </div>
   <div id="zoomctl">
    <button onclick="zoomActive(0.8)" title="Zoom in (+)">+</button>
    <button onclick="zoomActive(1.25)" title="Zoom out (-)">&minus;</button>
    <button onclick="resetActive()" title="Reset view (0)">&#8634;</button>
   </div>
   <div id="syncwrap"><label><input type="checkbox" id="syncchk" checked onchange="SYNC=this.checked"/> sync zoom/pan</label></div>
  </div>
  <div id="tablewrap">
   <table>
    <thead><tr><th title="locatable">&#128269;</th><th>design</th><th>as-drawn</th>
      <th>type</th><th>tier</th><th>conf</th><th>validation</th><th>reasons</th></tr></thead>
    <tbody id="rows">__TABLE_ROWS__</tbody>
   </table>
  </div>
 </main>
</div>

<div id="meta"><span class="close" onclick="hideMeta()">&times;</span>
  <h3 id="meta-title"></h3><div id="meta-body"></div></div>

<div id="exportMenu">
 <button onclick="exportCSV()">Cross-map &rarr; CSV</button>
 <button onclick="exportJSON()">Cross-map &rarr; JSON (+validations)</button>
 <div class="sep"></div>
 <button onclick="exportPNG()">Current view &rarr; PNG</button>
 <button onclick="window.print()">Print / Save as PDF</button>
</div>

<div class="modal" id="helpModal" onclick="if(event.target===this)hideHelp()">
 <div class="box">
  <h3 style="margin-top:0">Keyboard shortcuts</h3>
  <div><kbd>Ctrl</kbd>+<kbd>F</kbd> focus search &nbsp; <kbd>Esc</kbd> clear / close</div>
  <div><kbd>Ctrl</kbd>+<kbd>E</kbd> export menu &nbsp; <kbd>Ctrl</kbd>+<kbd>L</kbd> toggle all layers</div>
  <div><kbd>+</kbd> / <kbd>-</kbd> zoom &nbsp; <kbd>0</kbd> reset view</div>
  <hr/>
  <p class="mini" style="color:#5a6b7b">Mouse: wheel = zoom to cursor, drag = pan.
   Click a row to highlight its as-drawn element in the QCELL atlas and frame it.
   &#128269; marks rows whose as-drawn tag is locatable in the embedded atlas.</p>
  <p class="mini" style="color:#5a6b7b">Honesty: all counts come from the real W006
   cross-map (reports/W006_crossmap_statistics.json). PDF = browser print. RFCELL
   has no W006 cross-map and is shown as a visual reference only.</p>
  <button class="tool" onclick="hideHelp()" style="margin-top:8px">close</button>
 </div>
</div>
<div id="toast"></div>

<script>
"use strict";
var ROWS = __ROWS_JSON__;
var FOUND = __FOUND_JSON__;          // as-drawn tags locatable in QCELL atlas
var FOUNDSET = {}; FOUND.forEach(function(t){FOUNDSET[t]=1;});
var HAS_R = __HAS_R__;
var LAYERS = 21;
var SYNC = true;
var curFilter = 'ALL';
var selDesign = null;

/* ---------------- pan / zoom controller (viewBox based) ---------------- */
function PanZoom(svg, vb0str){
  this.svg = svg;
  this.vb0 = vb0str.trim().split(/\s+/).map(Number);
  this.vb = this.vb0.slice();
  this.minW = this.vb0[2] / 40;
  this.maxW = this.vb0[2] * 6;
  this.apply();
  var self = this;
  svg.addEventListener('wheel', function(e){
    e.preventDefault();
    self.zoomAt(e.clientX, e.clientY, e.deltaY < 0 ? 0.85 : 1.18);
  }, {passive:false});
  var drag=false, lx=0, ly=0;
  svg.addEventListener('mousedown', function(e){drag=true;lx=e.clientX;ly=e.clientY;svg.classList.add('grabbing');});
  window.addEventListener('mouseup', function(){drag=false;svg.classList.remove('grabbing');});
  window.addEventListener('mousemove', function(e){
    if(!drag) return;
    self.panBy(e.clientX-lx, e.clientY-ly); lx=e.clientX; ly=e.clientY;
  });
}
PanZoom.prototype.apply = function(propagate){
  this.svg.setAttribute('viewBox', this.vb.join(' '));
  if(propagate !== false && SYNC && this.peer){ this.peer.setVB(this.vb); }
};
PanZoom.prototype.setVB = function(vb){ this.vb = vb.slice(); this.svg.setAttribute('viewBox', this.vb.join(' ')); };
PanZoom.prototype.reset = function(){ this.vb = this.vb0.slice(); this.apply(); };
PanZoom.prototype.zoomAt = function(cx, cy, f){
  var r = this.svg.getBoundingClientRect();
  var px = (cx - r.left)/r.width, py = (cy - r.top)/r.height;
  var nw = Math.min(this.maxW, Math.max(this.minW, this.vb[2]*f));
  var nh = nw * (this.vb[3]/this.vb[2]);
  var ux = this.vb[0] + px*this.vb[2], uy = this.vb[1] + py*this.vb[3];
  this.vb[0] = ux - px*nw; this.vb[1] = uy - py*nh; this.vb[2] = nw; this.vb[3] = nh;
  this.apply();
};
PanZoom.prototype.zoomCenter = function(f){
  var r = this.svg.getBoundingClientRect();
  this.zoomAt(r.left + r.width/2, r.top + r.height/2, f);
};
PanZoom.prototype.panBy = function(dxc, dyc){
  var r = this.svg.getBoundingClientRect();
  this.vb[0] -= dxc/r.width*this.vb[2];
  this.vb[1] -= dyc/r.height*this.vb[3];
  this.apply();
};
PanZoom.prototype.toBox = function(bb){
  var pad = Math.max(bb.width, bb.height)*0.8 + 18;
  var w = bb.width + 2*pad, h = bb.height + 2*pad;
  // keep aspect ratio of the original viewBox so nothing distorts
  var ar = this.vb0[2]/this.vb0[3];
  if(w/h < ar){ w = h*ar; } else { h = w/ar; }
  this.vb = [bb.x + bb.width/2 - w/2, bb.y + bb.height/2 - h/2, w, h];
  this.apply();
};

var PZ = {};   // pane id -> PanZoom
function svgOf(paneId){ var p=document.getElementById(paneId); return p?p.querySelector('svg'):null; }
function activePane(){ return (curView==='compare') ? 'paneQ' : 'paneQ'; }
function zoomActive(f){ if(PZ.paneQ) PZ.paneQ.zoomCenter(f); }
function resetActive(){ for(var k in PZ){ PZ[k].reset(); } clearHighlight(); }

/* ---------------- view mode ---------------- */
var curView = 'single';
function setView(v){
  curView = v;
  document.getElementById('panes').className = v;
  document.getElementById('viewer').classList.toggle('compare', v==='compare');
  document.getElementById('tabSingle').classList.toggle('active', v==='single');
  document.getElementById('tabCompare').classList.toggle('active', v==='compare');
  if(v==='compare' && !HAS_R){ toast('RFCELL atlas not embedded \u2014 compare unavailable'); }
}

/* ---------------- highlight ---------------- */
function svgPoint(svg,x,y){var p=svg.createSVGPoint();p.x=x;p.y=y;return p;}
function bboxInSvg(svg, el){
  var ctm = svg.getScreenCTM(); if(!ctm) return null;
  var inv = ctm.inverse(); var r = el.getBoundingClientRect();
  if(!r.width && !r.height) return null;
  var p1 = svgPoint(svg,r.left,r.top).matrixTransform(inv);
  var p2 = svgPoint(svg,r.right,r.bottom).matrixTransform(inv);
  return {x:Math.min(p1.x,p2.x), y:Math.min(p1.y,p2.y),
          width:Math.abs(p2.x-p1.x), height:Math.abs(p2.y-p1.y)};
}
function clearHighlight(){
  document.querySelectorAll('.hl-box').forEach(function(e){e.remove();});
  document.querySelectorAll('.pidhit').forEach(function(e){e.classList.remove('pidhit');});
}
function highlightTag(tag){
  clearHighlight();
  if(!tag) return false;
  var svg = svgOf('paneQ'); if(!svg) return false;
  var els = svg.querySelectorAll('[data-pidtag~="'+tag+'"]');
  if(!els.length) return false;
  var union=null;
  els.forEach(function(el){
    el.classList.add('pidhit');
    var bb = bboxInSvg(svg, el); if(!bb) return;
    if(!union){ union = {x:bb.x,y:bb.y,x2:bb.x+bb.width,y2:bb.y+bb.height}; }
    else { union.x=Math.min(union.x,bb.x); union.y=Math.min(union.y,bb.y);
           union.x2=Math.max(union.x2,bb.x+bb.width); union.y2=Math.max(union.y2,bb.y+bb.height); }
  });
  if(!union) return false;
  var box={x:union.x,y:union.y,width:union.x2-union.x,height:union.y2-union.y};
  var NS='http://www.w3.org/2000/svg';
  var rect=document.createElementNS(NS,'rect');
  rect.setAttribute('class','hl-box');
  var m=Math.max(box.width,box.height)*0.25+4;
  rect.setAttribute('x',box.x-m); rect.setAttribute('y',box.y-m);
  rect.setAttribute('width',box.width+2*m); rect.setAttribute('height',box.height+2*m);
  rect.setAttribute('rx',3);
  svg.appendChild(rect);
  if(PZ.paneQ) PZ.paneQ.toBox(box);
  return true;
}

/* ---------------- table / selection ---------------- */
function selectRow(i){
  var r = ROWS[i]; if(!r) return;
  selDesign = r.design;
  document.querySelectorAll('#rows tr.row').forEach(function(tr){
    tr.classList.toggle('sel', tr.getAttribute('data-i')==String(i));
  });
  var tr = document.querySelector('#rows tr[data-i="'+i+'"]');
  if(tr) tr.scrollIntoView({block:'nearest'});
  showMeta(i);
  // breadcrumb
  var bc = r.design + (r.asdrawn? ' \u2194 '+r.asdrawn : ' (unmapped)');
  document.getElementById('breadcrumb').textContent = bc + ' \u00b7 '+r.tier;
  // highlight in atlas
  if(r.asdrawn){
    var ok = highlightTag(r.asdrawn);
    if(!ok && FOUNDSET[r.asdrawn]===undefined){ /* not locatable, fine */ }
  } else { clearHighlight(); }
}
function showMeta(i){
  var r=ROWS[i]; if(!r) return;
  document.getElementById('meta-title').textContent =
    r.design + (r.asdrawn ? '  \u2194  '+r.asdrawn : '  (unmapped)');
  var loc = r.asdrawn && FOUNDSET[r.asdrawn]!==undefined;
  document.getElementById('meta-body').innerHTML =
    '<div>type: '+esc(r.type)+'</div>'+
    '<div>tier: '+r.tier+' &middot; confidence: '+r.confidence.toFixed(2)+'</div>'+
    '<div>as-drawn sheet: '+(esc(r.sheet)||'&mdash;')+'</div>'+
    '<div>locatable in atlas: '+(loc?'yes (highlighted)':'no')+'</div>'+
    '<div style="margin-top:6px;color:#9fb0c4;">'+r.reasons.map(esc).join('<br/>')+'</div>';
  document.getElementById('meta').style.display='block';
}
function hideMeta(){ document.getElementById('meta').style.display='none'; }
function esc(s){ return String(s==null?'':s).replace(/[&<>"]/g,function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }

/* ---------------- filters / search ---------------- */
function setFilter(f){
  curFilter=f;
  document.querySelectorAll('.fbtn').forEach(function(b){
    b.classList.toggle('active', b.getAttribute('data-filter')===f);
  });
  applyFilters();
}
function applyFilters(){
  var q=(document.getElementById('search').value||'').trim().toUpperCase();
  var typ=document.getElementById('typeFilter').value;
  var shown=0, first=null;
  document.querySelectorAll('#rows tr.row').forEach(function(tr){
    var d=(tr.getAttribute('data-design')||'').toUpperCase();
    var a=(tr.getAttribute('data-asdrawn')||'').toUpperCase();
    var t=tr.getAttribute('data-type')||'';
    var tier=tr.getAttribute('data-tier')||'';
    var okQ = !q || d.indexOf(q)>=0 || a.indexOf(q)>=0;
    var okT = !typ || t===typ;
    var okF = (curFilter==='ALL') ||
              (curFilter==='MAPPED' && a) ||
              (curFilter===tier);
    var vis = okQ && okT && okF;
    tr.classList.toggle('hidden', !vis);
    if(vis){ shown++; if(!first) first=tr; }
  });
  if(q && first){
    first.classList.add('sel');
    selectRow(parseInt(first.getAttribute('data-i'),10));
  }
}

/* ---------------- validations (localStorage) ---------------- */
var VKEY='w008_validations';
function loadVal(){ try{return JSON.parse(localStorage.getItem(VKEY)||'{}');}catch(e){return {};} }
function saveVal(v){ localStorage.setItem(VKEY, JSON.stringify(v)); updateValCount(v); }
function setVal(design, state){
  var v=loadVal();
  if(v[design]===state){ delete v[design]; } else { v[design]=state; }
  saveVal(v); renderValCell(design, v[design]);
}
function renderValCell(design, state){
  var td=document.querySelector('td.c-val[data-design="'+cssEsc(design)+'"]');
  if(!td) return;
  td.innerHTML='';
  [['confirm','\u2713'],['reject','\u2717'],['suggest','?']].forEach(function(pair){
    var b=document.createElement('button');
    b.className='vbtn'+(state===pair[0]?' on-'+pair[0]:'');
    b.textContent=pair[1]; b.title=pair[0];
    b.onclick=function(e){e.stopPropagation(); setVal(design, pair[0]);};
    td.appendChild(b);
  });
}
function cssEsc(s){ return String(s).replace(/["\\]/g,'\\$&'); }
function updateValCount(v){
  v=v||loadVal(); var n=Object.keys(v).length;
  document.getElementById('valcount').textContent = n+' validation'+(n===1?'':'s')+' saved';
}
function exportValidations(){
  var v=loadVal();
  download('w008_validations.json', JSON.stringify({wave:'W008',generated:new Date().toISOString(),validations:v}, null, 2), 'application/json');
  toast('validations exported');
}
function resetValidations(){
  localStorage.removeItem(VKEY); updateValCount({});
  document.querySelectorAll('#rows tr.row').forEach(function(tr){
    renderValCell(tr.getAttribute('data-design'), undefined);
  });
  toast('validations reset');
}

/* ---------------- export ---------------- */
function download(name, text, mime){
  var blob=new Blob([text], {type:mime||'text/plain'});
  var url=URL.createObjectURL(blob);
  var a=document.createElement('a'); a.href=url; a.download=name; a.click();
  setTimeout(function(){URL.revokeObjectURL(url);}, 1000);
}
function exportCSV(){
  var v=loadVal();
  var head=['design','asdrawn','type','tier','confidence','sheet','locatable','validation','reasons'];
  var lines=[head.join(',')];
  ROWS.forEach(function(r){
    var cells=[r.design, r.asdrawn, r.type, r.tier, r.confidence.toFixed(2), r.sheet,
      (r.asdrawn && FOUNDSET[r.asdrawn]!==undefined)?'yes':'no',
      v[r.design]||'', r.reasons.join('; ')];
    lines.push(cells.map(csvCell).join(','));
  });
  download('w008_crossmap.csv', lines.join('\n'), 'text/csv');
  hideExport(); toast('CSV exported');
}
function csvCell(s){ s=String(s==null?'':s); return /[",\n]/.test(s)?'"'+s.replace(/"/g,'""')+'"':s; }
function exportJSON(){
  var v=loadVal();
  var out=ROWS.map(function(r){
    return {design:r.design, asdrawn:r.asdrawn, type:r.type, tier:r.tier,
      confidence:r.confidence, sheet:r.sheet,
      locatable:(r.asdrawn && FOUNDSET[r.asdrawn]!==undefined),
      validation:v[r.design]||null, reasons:r.reasons};
  });
  download('w008_crossmap.json', JSON.stringify({wave:'W008',generated:new Date().toISOString(),rows:out}, null, 2), 'application/json');
  hideExport(); toast('JSON exported');
}
function exportPNG(){
  var svg=svgOf('paneQ'); if(!svg){ toast('no SVG to export'); return; }
  var clone=svg.cloneNode(true);
  clone.querySelectorAll('.hl-box').forEach(function(e){e.remove();});
  clone.setAttribute('xmlns','http://www.w3.org/2000/svg');
  var vb=svg.getAttribute('viewBox').split(/\s+/).map(Number);
  var W=2000, H=Math.round(W*vb[3]/vb[2]);
  clone.setAttribute('width',W); clone.setAttribute('height',H);
  var data=new XMLSerializer().serializeToString(clone);
  var img=new Image();
  img.onload=function(){
    var c=document.createElement('canvas'); c.width=W; c.height=H;
    var ctx=c.getContext('2d'); ctx.fillStyle='#fff'; ctx.fillRect(0,0,W,H);
    ctx.drawImage(img,0,0);
    try{
      c.toBlob(function(b){ var u=URL.createObjectURL(b); var a=document.createElement('a');
        a.href=u; a.download='qcell_view.png'; a.click(); setTimeout(function(){URL.revokeObjectURL(u);},1000);
        toast('PNG exported'); });
    }catch(e){ toast('PNG export failed: '+e.message); }
  };
  img.onerror=function(){ toast('PNG render failed'); };
  img.src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(data);
  hideExport();
}
function toggleExport(e){
  var m=document.getElementById('exportMenu');
  if(m.style.display==='block'){ m.style.display='none'; return; }
  var r=e.currentTarget.getBoundingClientRect();
  m.style.left=Math.min(r.left, window.innerWidth-200)+'px';
  m.style.top=(r.bottom+4)+'px'; m.style.display='block';
}
function hideExport(){ document.getElementById('exportMenu').style.display='none'; }

/* ---------------- misc UI ---------------- */
function toast(msg){
  var t=document.getElementById('toast'); t.textContent=msg; t.classList.add('show');
  clearTimeout(t._t); t._t=setTimeout(function(){t.classList.remove('show');}, 2200);
}
function showHelp(){ document.getElementById('helpModal').classList.add('show'); }
function hideHelp(){ document.getElementById('helpModal').classList.remove('show'); }

/* ---------------- layers ---------------- */
function buildLayers(){
  var lc=document.getElementById('layers');
  var rules='';
  for(var i=0;i<LAYERS;i++){
    (function(idx){
      var id='lyr-'+String(idx).padStart(2,'0');
      var lab=document.createElement('label');
      var cb=document.createElement('input'); cb.type='checkbox'; cb.checked=true;
      cb.dataset.layer=idx;
      cb.onchange=function(){
        document.querySelectorAll('.pane svg').forEach(function(s){
          s.classList.toggle('hide-'+idx, !cb.checked);
        });
      };
      lab.appendChild(cb);
      lab.appendChild(document.createTextNode(' '+id));
      lc.appendChild(lab);
      rules+='.pane svg.hide-'+idx+' .'+id+'{display:none!important}';
    })(i);
  }
  var st=document.createElement('style'); st.textContent=rules; document.head.appendChild(st);
}
function toggleAllLayers(){
  var boxes=document.querySelectorAll('#layers input');
  var anyOn=Array.prototype.some.call(boxes,function(b){return b.checked;});
  boxes.forEach(function(b){ b.checked=!anyOn; b.onchange(); });
}

/* ---------------- keyboard ---------------- */
document.addEventListener('keydown', function(e){
  if((e.ctrlKey||e.metaKey) && e.key.toLowerCase()==='f'){ e.preventDefault(); document.getElementById('search').focus(); return; }
  if((e.ctrlKey||e.metaKey) && e.key.toLowerCase()==='e'){ e.preventDefault(); var b=document.querySelector('#topbar .tool'); toggleExport({currentTarget:b}); return; }
  if((e.ctrlKey||e.metaKey) && e.key.toLowerCase()==='l'){ e.preventDefault(); toggleAllLayers(); return; }
  if(e.key==='Escape'){ hideMeta(); hideExport(); hideHelp(); var s=document.getElementById('search'); if(s.value){ s.value=''; applyFilters(); } clearHighlight(); return; }
  if(document.activeElement && document.activeElement.id==='search') return;
  if(e.key==='+'||e.key==='='){ zoomActive(0.8); }
  else if(e.key==='-'||e.key==='_'){ zoomActive(1.25); }
  else if(e.key==='0'){ resetActive(); }
});
document.addEventListener('click', function(e){
  var m=document.getElementById('exportMenu');
  if(m.style.display==='block' && !m.contains(e.target) && !/Export/.test(e.target.textContent||'')) hideExport();
});

/* ---------------- init ---------------- */
function init(){
  buildLayers();
  // type filter options
  var types={}; ROWS.forEach(function(r){ if(r.type) types[r.type]=1; });
  var sel=document.getElementById('typeFilter');
  Object.keys(types).sort().forEach(function(t){ var o=document.createElement('option'); o.value=t; o.textContent=t; sel.appendChild(o); });
  // table row wiring + validation cells
  var v=loadVal();
  document.querySelectorAll('#rows tr.row').forEach(function(tr){
    tr.addEventListener('click', function(){ selectRow(parseInt(tr.getAttribute('data-i'),10)); });
    renderValCell(tr.getAttribute('data-design'), v[tr.getAttribute('data-design')]);
  });
  updateValCount(v);
  // pan/zoom controllers
  var sq=svgOf('paneQ'); if(sq) PZ.paneQ=new PanZoom(sq, '__Q_VB__');
  if(HAS_R){ var sr=svgOf('paneR'); if(sr) PZ.paneR=new PanZoom(sr, '__R_VB__'); }
  if(PZ.paneQ && PZ.paneR){ PZ.paneQ.peer=PZ.paneR; PZ.paneR.peer=PZ.paneQ; }
  // hide loading
  setTimeout(function(){ document.getElementById('loading').classList.add('hide'); }, 150);
}
if(document.readyState!=='loading') init(); else window.addEventListener('DOMContentLoaded', init);
window.addEventListener('load', function(){ document.getElementById('loading').classList.add('hide'); });
</script>
</body></html>"""
