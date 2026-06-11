#!/usr/bin/env python3
"""Phase 8 - generate the interactive HTML viewer pages + thumbnails.

Writes index.html (landing + sheet picker) and one viewer page per sheet,
plus PNG thumbnails, into output_v4/HTML_INTERACTIVE/.
The JS/CSS engine (pid-viewer.js, search.js, viewer.css) is authored separately.
"""
import os
import cairosvg
from PIL import Image

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(PROJECT, "output_v4", "HTML_INTERACTIVE")
ASSETS = os.path.join(HTML, "assets")
THUMBS = os.path.join(ASSETS, "thumbs")
os.makedirs(THUMBS, exist_ok=True)

SHEETS = [
    {"base": "QCELL-Sheet1-Cryogenic", "cell": "QCELL / LB",
     "title": "Cryogenic Circuits (40 K / 4.5 K / 2 K + HX)",
     "dwg": "=NA.PS01_PFB712", "kind": "Cryogenic process"},
    {"base": "QCELL-Sheet2-Instrumentation", "cell": "QCELL / LB",
     "title": "Instrumentation & Control",
     "dwg": "=NA.PS01_PFB712", "kind": "Instrumentation"},
    {"base": "RFCELL-Sheet1-Process", "cell": "RFCELL (ACR)",
     "title": "Process Flow (DI-Water / Coupler)",
     "dwg": "=NA.PS01_PFB713", "kind": "Process"},
    {"base": "RFCELL-Sheet2-Instrumentation", "cell": "RFCELL (ACR)",
     "title": "Instrumentation & Control",
     "dwg": "=NA.PS01_PFB713", "kind": "Instrumentation"},
]

TOPBAR = """    <div class="topbar">
      <span class="title">MINERVA CryoCell P&amp;ID <small>v4.0</small></span>
      <span class="title">&nbsp;|&nbsp; {cell} &mdash; {title}</span>
      <span class="spacer"></span>
      <span class="seg">
        <button class="btn small" data-style="STANDARD">Standard</button>
        <button class="btn small" data-style="CONTROL-CENTRIC">Control-centric</button>
      </span>
      <button class="btn small" id="btnMono">Mono: OFF</button>
      <button class="btn small" id="btnPng">Export PNG</button>
      <a class="btn small" href="index.html">&larr; All sheets</a>
    </div>"""

SIDEBAR = """    <aside class="sidebar">
      <div class="section">
        <h4>Preset views</h4>
        <div class="seg">
          <button class="btn small" data-view="DEFAULT_FULL">Full</button>
          <button class="btn small" data-view="DEFAULT_PROCESS">Process</button>
          <button class="btn small" data-view="DEFAULT_CONTROL">Control</button>
          <button class="btn small" data-view="DEFAULT_MAIN">Main</button>
          <button class="btn small" data-view="PRINT_MONO">Print/mono</button>
        </div>
      </div>
      <div class="section">
        <h4>Find a tag</h4>
        <div class="search">
          <input id="searchInput" placeholder="e.g. CV500, TT, 2K PRIMARY, TP" />
          <button class="btn small" id="searchBtn">Go</button>
          <button class="btn small" id="searchClear">x</button>
        </div>
        <div id="searchResults"></div>
      </div>
      <div class="section">
        <h4>Layers</h4>
        <div id="layerPanel"></div>
        <p class="legendNote">Amber labels are hidden by default (overlays).
        Toggle <b>Legend</b> for the colour/signal key, and
        <b>Horizontal valve overlay</b> for the tracked-asset valve row.</p>
      </div>
    </aside>"""

STAGE = """    <main class="stage" id="stage">
      <div class="canvasWrap" id="canvasWrap"></div>
      <div class="zoomctl">
        <button class="btn" id="btnZin">+</button>
        <button class="btn" id="btnZout">&minus;</button>
        <button class="btn" id="btnFit" title="Fit">&#9633;</button>
      </div>
      <div class="hint">Scroll to <b>zoom</b>, drag to <b>pan</b>.
      <span class="kbd">Fit</span> resets. Search highlights &amp; jumps to a tag.</div>
    </main>"""


def page_html(s):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{s['cell']} - {s['title']} | MINERVA P&amp;ID v4</title>
<link rel="stylesheet" href="css/viewer.css" />
</head>
<body>
  <div class="app">
{TOPBAR.format(cell=s['cell'], title=s['title'])}
{SIDEBAR}
{STAGE}
  </div>
  <script>window.SHEET = {{ base: "{s['base']}", dir: "assets",
    title: "{s['cell']} - {s['title']}" }};</script>
  <script src="js/pid-viewer.js"></script>
  <script src="js/search.js"></script>
</body>
</html>
"""


def index_html(cards):
    card_html = "\n".join(cards)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>MINERVA CryoCell P&amp;ID v4.0 - Interactive Viewer</title>
<link rel="stylesheet" href="css/viewer.css" />
</head>
<body>
  <div class="landing">
    <h1>MINERVA CryoCell &mdash; P&amp;ID v4.0</h1>
    <div class="sub">SCK CEN &middot; MYRRHA / MINERVA Phase 1 &middot; consultant Mott MacDonald
      &middot; standard AD_01.16 / ANSI-ISA-5.1 / ISO 10628</div>
    <div class="cards">
{card_html}
    </div>
    <div class="badgerow">
      <span class="badge">24 toggleable layers</span>
      <span class="badge">5 preset views</span>
      <span class="badge">colour &amp; monochrome</span>
      <span class="badge">2 style profiles</span>
      <span class="badge">tag search</span>
      <span class="badge">PNG export</span>
      <span class="badge">YAML metadata embedded</span>
    </div>
    <p class="legendNote" style="margin-top:22px">
      Open any sheet to toggle layers, switch colour/mono, apply preset views,
      search for a tag, zoom/pan, and export a PNG. Each SVG also carries a
      Jekyll-style YAML front-matter block (in a metadata CDATA section) and a
      &lt;metadata&gt; default-views descriptor.</p>
  </div>
</body>
</html>
"""


def main():
    cards = []
    for s in SHEETS:
        svg = os.path.join(ASSETS, f"{s['base']}_STANDARD_v4.svg")
        thumb = os.path.join(THUMBS, f"{s['base']}.png")
        cairosvg.svg2png(url=svg, write_to=thumb, output_width=640)
        # downscale to keep files small
        im = Image.open(thumb); im.thumbnail((640, 460)); im.save(thumb)
        rel = f"assets/thumbs/{s['base']}.png"
        cards.append(f"""      <a class="card" href="{s['base']}.html">
        <div class="thumb"><img src="{rel}" alt="{s['base']}" /></div>
        <div class="meta"><h3>{s['cell']} &mdash; {s['title']}</h3>
          <p>{s['kind']} &middot; dwg {s['dwg']}</p></div>
      </a>""")
        open(os.path.join(HTML, f"{s['base']}.html"), "w").write(page_html(s))
        print("page", s['base'] + ".html")
    open(os.path.join(HTML, "index.html"), "w").write(index_html(cards))
    print("index.html + 4 sheet pages written to", os.path.relpath(HTML, PROJECT))


if __name__ == "__main__":
    main()
