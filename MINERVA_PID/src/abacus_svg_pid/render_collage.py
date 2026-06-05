"""
================================================================================
 Module : render_collage.py
 Purpose: Render the colour-line collage for the QCELL P&ID: the full drawing
          plus one ISOLATED view per canonical process line (every element NOT
          belonging to that colour family is dimmed to faint grey so the line
          stands out), then assemble an A3-landscape HTML atlas with a
          monochrome-safe title + legend per view.
 Current Wave : W002 - Colour Line Decomposition & Validation
 Status : ACTIVE
 Inputs  : data/svg/PFD-PID MINERVA QCELL-LB.svg
 Outputs : publish/assets/*.png , publish/colour_line_collage.html
 Notes   : Uses cairosvg for rasterising. Labels never rely on colour alone
           (each view is titled with the process code + canonical name + hex).
================================================================================
"""

from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from abacus_svg_pid import parser as P

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SVG = os.path.join(PROJECT_ROOT, "data", "svg", "PFD-PID MINERVA QCELL-LB.svg")
PUBLISH = os.path.join(PROJECT_ROOT, "publish")
ASSETS = os.path.join(PUBLISH, "assets")

SVG_NS = "http://www.w3.org/2000/svg"

# canonical views to isolate (canonical_name, label, hex swatch, blurb)
VIEWS = [
    ("blue_A",          "A / A'  - 4.5 K main + internal branch (BLUE/NAVY)", "#0000ff",
     "Primary 4.5 K process line and its internal branch A'."),
    ("cyan_B_2K",       "B / B'  - 2 K internal line (CYAN)",                 "#00ffff",
     "2 K internal line / branch."),
    ("green_W_coupler", "W  - Coupler line (GREEN)",                          "#00ff00",
     "Coupler line; splits from BLUE A inside the QM."),
    ("olive_S_line",    "S  - S line (OLIVE)",                                "#808000",
     "Warm S line."),
    ("grey_V_vent",     "V  - Vent line (GREY)",                              "#999999",
     "Vent line, per module, routed outside."),
    ("red_orange_D_E",  "D / E  - Manifold lines (RED/ORANGE)",              "#ff0000",
     "Warm/cold manifold lines."),
    ("unknown_black_or_other", "Structure / boundary / unresolved (BLACK + other)", "#000000",
     "Structure, symbols, scope boundaries, and unresolved colours (e.g. magenta)."),
]


def _local(tag):
    return tag.split("}")[-1]


def _emphasise_isolated(tree_bytes, canonical_name):
    """Return SVG bytes where only elements of `canonical_name` keep their
    colour; everything else is dimmed to faint grey, low opacity."""
    ET.register_namespace("", SVG_NS)
    root = ET.fromstring(tree_bytes)

    for el in root.iter():
        t = _local(el.tag)
        if t not in P.DRAWABLE:
            continue
        stroke = P.normalise_colour(P.style_value(el, "stroke"))
        fill = P.normalise_colour(P.style_value(el, "fill"))
        eff = None
        if stroke and stroke.startswith("#"):
            eff = stroke
        elif fill and fill.startswith("#"):
            eff = fill
        keep = False
        if eff:
            cls = P.classify_colour(eff)
            keep = (cls["canonical_name"] == canonical_name)
        if not keep:
            # dim it: faint grey, low opacity, thin
            style = P.parse_style(el.attrib.get("style", ""))
            style["opacity"] = "0.06"
            if "stroke" in style or el.attrib.get("stroke"):
                style["stroke"] = "#cccccc"
            if "fill" in style and style.get("fill") not in (None, "none"):
                style["fill"] = "#dddddd"
            el.set("style", ";".join(f"{k}:{v}" for k, v in style.items()))
    return ET.tostring(root)


def render():
    os.makedirs(ASSETS, exist_ok=True)
    try:
        import cairosvg
    except Exception as exc:  # pragma: no cover
        print("cairosvg unavailable:", exc)
        return None

    with open(SVG, "rb") as fh:
        raw = fh.read()

    rendered = []

    # full drawing
    full_png = os.path.join(ASSETS, "full.png")
    cairosvg.svg2png(bytestring=raw, write_to=full_png, output_width=1600)
    rendered.append(("FULL DRAWING", "full.png", "#333333",
                     "Complete QCELL P&ID (all colour lines together)."))

    for cname, label, swatch, blurb in VIEWS:
        iso = _emphasise_isolated(raw, cname)
        out = os.path.join(ASSETS, f"{cname}.png")
        try:
            cairosvg.svg2png(bytestring=iso, write_to=out, output_width=1600)
            rendered.append((label, f"{cname}.png", swatch, blurb))
        except Exception as exc:
            print("render failed for", cname, exc)
    return rendered


def build_html(rendered):
    cards = []
    for title, img, swatch, blurb in rendered:
        cards.append(f"""
    <section class="view">
      <h2><span class="swatch" style="background:{swatch}"></span>{title}</h2>
      <p class="blurb">{blurb}</p>
      <img src="assets/{img}" alt="{title}"/>
    </section>""")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>QCELL P&amp;ID - Colour Line Collage (W002)</title>
<style>
  @page {{ size: A3 landscape; margin: 10mm; }}
  body {{ font-family: "Segoe UI", Arial, sans-serif; margin: 0; padding: 18px;
          background:#f7f7f7; color:#111; }}
  header {{ border-bottom:3px solid #111; margin-bottom:14px; padding-bottom:8px; }}
  header h1 {{ margin:0; font-size:22px; }}
  header p {{ margin:4px 0 0; font-size:12px; color:#444; }}
  .legend {{ display:flex; flex-wrap:wrap; gap:10px; margin:10px 0 18px; font-size:11px; }}
  .legend span {{ display:inline-flex; align-items:center; gap:5px; padding:2px 6px;
                  border:1px solid #ccc; background:#fff; }}
  .legend i {{ width:14px; height:14px; display:inline-block; border:1px solid #333; }}
  .view {{ background:#fff; border:1px solid #ccc; margin-bottom:18px; padding:10px;
           page-break-inside:avoid; break-inside:avoid; }}
  .view h2 {{ font-size:15px; margin:0 0 4px; display:flex; align-items:center; gap:8px; }}
  .swatch {{ width:16px; height:16px; display:inline-block; border:1px solid #111; }}
  .blurb {{ font-size:11px; color:#555; margin:0 0 8px; }}
  .view img {{ width:100%; height:auto; border:1px solid #e0e0e0; background:#fff; }}
</style>
</head>
<body>
<header>
  <h1>MINERVA QCELL P&amp;ID &mdash; Colour Line Collage</h1>
  <p>Wave W002 &middot; Colour-line-first decomposition &middot; full drawing + isolated process-line views.
     Labels are monochrome-safe (each view names its process code, canonical name and hex; colour is supplementary).</p>
</header>
<div class="legend">
  <span><i style="background:#0000ff"></i>A / A' &mdash; 4.5 K main (BLUE/NAVY)</span>
  <span><i style="background:#00ffff"></i>B / B' &mdash; 2 K internal (CYAN)</span>
  <span><i style="background:#00ff00"></i>W &mdash; coupler (GREEN)</span>
  <span><i style="background:#808000"></i>S &mdash; S line (OLIVE)</span>
  <span><i style="background:#999999"></i>V &mdash; vent (GREY)</span>
  <span><i style="background:#ff0000"></i>D / E &mdash; manifold (RED/ORANGE)</span>
  <span><i style="background:#000000"></i>Structure / unresolved (BLACK + other)</span>
</div>
{''.join(cards)}
<footer style="font-size:10px;color:#888;margin-top:20px;border-top:1px solid #ccc;padding-top:6px;">
  Generated by abacus_svg_pid (W002). Arrows &amp; sequential ordering DEFERRED_W004.
</footer>
</body>
</html>"""
    out = os.path.join(PUBLISH, "colour_line_collage.html")
    with open(out, "w") as fh:
        fh.write(html)
    return out


if __name__ == "__main__":
    rendered = render()
    if rendered:
        path = build_html(rendered)
        print("collage written:", path)
        print("views:", len(rendered))
