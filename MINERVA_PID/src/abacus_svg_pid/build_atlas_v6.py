"""
================================================================================
 Module : build_atlas_v6.py
 Purpose: PHASE 4 output - produce the 13-layer architecture deliverables:
          (1) annotated *_13layers.svg per sheet (each drawable element tagged
              IN PLACE with its layer class so transforms/order are preserved),
          (2) rendered *_13layers.pdf,
          (3) publish/layered_atlas_v6.html - an interactive viewer with 13
              toggleable layers driven by CSS class visibility.
 Current Wave : W003 + W004
 Status : ACTIVE
 Inputs  : data/svg/*.svg
 Outputs : output_v6/{QCELL,RFCELL}/*_13layers.svg + .pdf
           publish/layered_atlas_v6.html
 Notes   : Elements are NOT relocated in the DOM (that would break CTMs); they
           are annotated with class="lyr-NN" and the HTML toggles visibility.
================================================================================
"""

from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET

from abacus_svg_pid import build_w003_w004 as B
from abacus_svg_pid import geometry as Geo
from abacus_svg_pid import parser as P

ROOT = B.ROOT
SVG_DIR = B.SVG_DIR
OUT_V6 = os.path.join(ROOT, "output_v6")
PUBLISH = os.path.join(ROOT, "publish")

SVG_NS = "http://www.w3.org/2000/svg"
INK_NS = "http://www.inkscape.org/namespaces/inkscape"

LAYER_IDS = B.LAYER_ORDER  # 21 named layers (13 logical groups, sublayered)


def _local(tag):
    return tag.split("}")[-1]


def _classify_element_layer(el, parent_layer_label):
    """Reuse the geometry classifier on a live element to get its layer."""
    tag = _local(el.tag)
    stroke = P.normalise_colour(P.style_value(el, "stroke"))
    fill = P.normalise_colour(P.style_value(el, "fill"))
    eff = stroke if (stroke and stroke.startswith("#")) else (
        fill if (fill and fill.startswith("#")) else None)
    cls = P.classify_colour(eff) if eff else {"process_code": "none",
                                              "family": "none"}
    style = P.parse_style(el.attrib.get("style", ""))
    dash = style.get("stroke-dasharray") or el.attrib.get("stroke-dasharray") or "none"
    has_marker = bool(style.get("marker-end") or style.get("marker-start"))

    # build a lightweight stand-in matching geometry.assign_layer expectations
    class _E:
        pass
    e = _E()
    e.shape = _shape_of(tag, el, has_marker)
    e.process_code = cls.get("process_code")
    e.family = cls.get("family")
    e.dash = dash
    e.width_px = e.height_px = 20  # heat-load size unknown here; treat as large
    return Geo.G.assign_layer(e) if hasattr(Geo, "G") else B.assign_layer(e)


def _shape_of(tag, el, has_marker):
    if has_marker:
        return "arrow"
    if tag in ("circle", "ellipse"):
        r = el.attrib.get("r") or el.attrib.get("rx") or "0"
        try:
            return "dot" if float(r) <= 5 else "bubble"
        except ValueError:
            return "bubble"
    if tag == "rect":
        return "rect"
    if tag == "path":
        d = el.attrib.get("d", "")
        if d.strip().lower().endswith("z") and len(re.findall(r"[MLlmHhVvCcQq]", d)) <= 5:
            return "triangle"
        return "line" if len(re.findall(r"[MLlmHhVvCcQq]", d)) <= 2 else "path"
    if tag in ("line", "polyline"):
        return "line"
    if tag == "polygon":
        return "triangle"
    return tag


def annotate(svg_path, out_path):
    ET.register_namespace("", SVG_NS)
    ET.register_namespace("inkscape", INK_NS)
    tree = ET.parse(svg_path)
    root = tree.getroot()
    counts = {}

    def walk(el):
        tag = _local(el.tag)
        if tag in P.DRAWABLE:
            lyr = B.assign_layer(_FakeFromVal(el))
            idx = LAYER_IDS.index(lyr) if lyr in LAYER_IDS else 99
            cls = f"lyr-{idx:02d}"
            existing = el.attrib.get("class", "")
            el.set("class", (existing + " " + cls).strip())
            counts[lyr] = counts.get(lyr, 0) + 1
        elif tag == "text":
            el.set("class", (el.attrib.get("class", "") + " lyr-18").strip())
            counts["11_Text_ColorCoded"] = counts.get("11_Text_ColorCoded", 0) + 1
        for child in list(el):
            walk(child)

    walk(root)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    tree.write(out_path, encoding="utf-8", xml_declaration=True)
    return counts


class _FakeFromVal:
    """Adapter so build_w003_w004.assign_layer can read a live ET element."""
    def __init__(self, el):
        tag = _local(el.tag)
        stroke = P.normalise_colour(P.style_value(el, "stroke"))
        fill = P.normalise_colour(P.style_value(el, "fill"))
        eff = stroke if (stroke and stroke.startswith("#")) else (
            fill if (fill and fill.startswith("#")) else None)
        cls = P.classify_colour(eff) if eff else {"process_code": "none",
                                                  "family": "none"}
        style = P.parse_style(el.attrib.get("style", ""))
        self.shape = _shape_of(tag, el,
                               bool(style.get("marker-end") or style.get("marker-start")))
        self.process_code = cls.get("process_code")
        self.family = cls.get("family")
        self.dash = style.get("stroke-dasharray") or el.attrib.get("stroke-dasharray") or "none"
        self.width_px = self.height_px = 20
        self.cx = self.cy = 0


def render_pdf(svg_path, pdf_path):
    try:
        import cairosvg
        cairosvg.svg2pdf(url=svg_path, write_to=pdf_path)
        return True
    except Exception as exc:
        print("PDF render failed:", exc)
        return False


def build_atlas_html(annotated):
    """annotated: list of (sheet, rel_svg_path, counts)."""
    # read first annotated SVG inline for the interactive viewer (QCELL)
    qcell = next((a for a in annotated if a[0] == "QCELL"), annotated[0])
    with open(qcell[1]) as fh:
        svg_inline = fh.read()
    # strip xml declaration for inline embedding
    svg_inline = re.sub(r"<\?xml[^>]*\?>", "", svg_inline).strip()

    toggles = []
    for i, lyr in enumerate(LAYER_IDS):
        toggles.append(
            f'<label><input type="checkbox" checked onchange="tog(this,{i})"/> '
            f'{lyr}</label>')
    # text layer toggle (lyr-18)
    toggles.append('<label><input type="checkbox" checked onchange="togText(this)"/> '
                   '11_Text_ColorCoded</label>')

    style_rules = "\n".join(f".hide-{i} .lyr-{i:02d}{{display:none!important}}"
                            for i in range(len(LAYER_IDS)))
    html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>
<title>QCELL P&amp;ID - 13-Layer Atlas v6 (W003/W004)</title>
<style>
 @page{{size:A3 landscape;margin:8mm;}}
 body{{font-family:Consolas,'DejaVu Sans Mono',monospace;margin:0;display:flex;height:100vh;}}
 #panel{{width:280px;background:#1e2430;color:#e8edf4;padding:14px;overflow:auto;flex:none;}}
 #panel h1{{font-size:15px;margin:0 0 8px;}}
 #panel p{{font-size:11px;color:#9fb0c4;}}
 #panel label{{display:block;font-size:11px;margin:3px 0;cursor:pointer;}}
 #stage{{flex:1;overflow:auto;background:#fff;}}
 #stage svg{{width:100%;height:auto;}}
 .hint{{font-size:10px;color:#7d8ea3;margin-top:10px;}}
 {style_rules}
 .hideText .lyr-18{{display:none!important}}
</style></head>
<body>
<div id="panel">
 <h1>13-Layer Atlas v6</h1>
 <p>MINERVA QCELL &middot; Wave W003+W004. Toggle layers to declutter. Heat loads &amp; spec dots are isolated layers.</p>
 {''.join(toggles)}
 <div class="hint">Annotated SVG: classes lyr-00..lyr-20 (+lyr-18 text). PDF/SVG exports in output_v6/.</div>
</div>
<div id="stage">{svg_inline}</div>
<script>
 var stage=document.getElementById('stage');
 function tog(cb,i){{ stage.classList.toggle('hide-'+i, !cb.checked); }}
 function togText(cb){{ stage.classList.toggle('hideText', !cb.checked); }}
</script>
</body></html>"""
    os.makedirs(PUBLISH, exist_ok=True)
    out = os.path.join(PUBLISH, "layered_atlas_v6.html")
    with open(out, "w") as fh:
        fh.write(html)
    return out


def run():
    annotated = []
    for fname in sorted(os.listdir(SVG_DIR)):
        if not fname.lower().endswith(".svg"):
            continue
        key = "QCELL" if "QCELL" in fname.upper() else "RFCELL"
        out_svg = os.path.join(OUT_V6, key, f"{key}_13layers.svg")
        counts = annotate(os.path.join(SVG_DIR, fname), out_svg)
        pdf = os.path.join(OUT_V6, key, f"{key}_13layers.pdf")
        render_pdf(out_svg, pdf)
        annotated.append((key, out_svg, counts))
    html = build_atlas_html(annotated)
    return {"annotated": [(a[0], a[2]) for a in annotated], "atlas_html": html}


def main():
    """CLI entrypoint: annotate each source SVG into the 13-layer atlas."""
    os.makedirs(OUT_V6, exist_ok=True)
    result = run()
    for key, counts in result["annotated"]:
        print(f"{key}: {counts}")
    print(f"atlas_html: {result['atlas_html']}")
    return result


if __name__ == "__main__":
    main()
