"""Synthetic fixtures (no proprietary content).

``make_group_font_fixture``: a two-slide PPTX for OOXML geometry and font regression.
  Slide 1: groups nested 3 deep; the outer group is scaled non-uniformly (ext != chExt) and offset; the middle
  group is rotated 30 deg; the inner group is flipped horizontally; leaves carry their own rotation; one shape
  crosses the slide edge; one shape is flipped vertically.
  Slide 2: font inheritance: title placeholder (theme major), body placeholder (theme minor via master), plain
  text box (presentation default), explicit run font, autoshape with a style fontRef.
  Theme fonts are replaced with distinctive faces (Georgia/Verdana) so defaults cannot pass by coincidence.
  PowerPoint's own answer for this file is committed as ``tests/svg_engine/data/powerpoint_com_oracle_fixture.json``.

``synthetic_layered_svg``: an Inkscape-style SVG exercising every layer case the PDF builder must handle.
"""
from __future__ import annotations

import io
import re
import zipfile

A = "http://schemas.openxmlformats.org/drawingml/2006/main"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"


def make_group_font_fixture(out):
    from lxml import etree
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.util import Mm

    prs = Presentation()
    prs.slide_width, prs.slide_height = Mm(338.667), Mm(190.5)
    s1 = prs.slides.add_slide(prs.slide_layouts[6])

    def rect(shapes, name, x, y, w, h, rot=0, text=None):
        sp = shapes.add_shape(MSO_SHAPE.RECTANGLE, Mm(x), Mm(y), Mm(w), Mm(h))
        sp.name = name
        sp.rotation = rot
        if text:
            sp.text_frame.text = text
        return sp

    outer = s1.shapes.add_group_shape()
    outer.name = "G_outer"
    rect(outer.shapes, "R_outer_a", 20, 20, 40, 20, text="outer a")
    middle = outer.shapes.add_group_shape()
    middle.name = "G_middle"
    rect(middle.shapes, "R_mid_a", 80, 40, 30, 15, rot=15, text="mid a")
    inner = middle.shapes.add_group_shape()
    inner.name = "G_inner"
    rect(inner.shapes, "R_in_a", 90, 70, 20, 10, text="inner a")
    rect(inner.shapes, "R_in_b", 115, 75, 12, 18, rot=-20, text="inner b")
    rect(s1.shapes, "R_overflow", 300, 150, 60, 30, text="overflow")  # crosses the right and bottom edges
    rect(s1.shapes, "R_flipV", 200, 30, 30, 12, text="flipV")

    s2 = prs.slides.add_slide(prs.slide_layouts[1])  # title + content
    s2.shapes.title.text = "Title inherits major"
    s2.placeholders[1].text_frame.text = "Body inherits minor"
    tb = s2.shapes.add_textbox(Mm(20), Mm(150), Mm(120), Mm(15))
    tb.name = "TB_default"
    tb.text_frame.text = "Textbox default"
    tb2 = s2.shapes.add_textbox(Mm(160), Mm(150), Mm(120), Mm(15))
    tb2.name = "TB_explicit"
    r = tb2.text_frame.paragraphs[0].add_run()
    r.text = "Explicit Courier"
    r.font.name = "Courier New"
    auto = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Mm(250), Mm(40), Mm(60), Mm(30))
    auto.name = "AS_styled"
    auto.text_frame.text = "Autoshape fontRef"

    buf = io.BytesIO()
    prs.save(buf)
    # Post-process the XML: outer group scale, middle rotation, inner flip, R_flipV flip; distinctive theme fonts.
    zin = zipfile.ZipFile(io.BytesIO(buf.getvalue()))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "ppt/slides/slide1.xml":
                x = etree.fromstring(data)

                def grp(name):
                    return next(g for g in x.iter(f"{{{P}}}grpSp") if g.find("./{*}nvGrpSpPr/{*}cNvPr").get("name") == name)

                def xf(g):
                    return g.find("./{*}grpSpPr/{%s}xfrm" % A)
                o = xf(grp("G_outer"))
                ext, off = o.find("{%s}ext" % A), o.find("{%s}off" % A)
                ext.set("cx", str(int(int(ext.get("cx")) * 1.25)))
                ext.set("cy", str(int(int(ext.get("cy")) * 0.8)))
                off.set("x", str(int(off.get("x")) + 360000 * 5))
                off.set("y", str(int(off.get("y")) + 360000 * 2))
                xf(grp("G_middle")).set("rot", str(30 * 60000))
                xf(grp("G_inner")).set("flipH", "1")
                for sp in x.iter(f"{{{P}}}sp"):
                    if sp.find("./{*}nvSpPr/{*}cNvPr").get("name") == "R_flipV":
                        sp.find("./{*}spPr/{%s}xfrm" % A).set("flipV", "1")
                data = etree.tostring(x, xml_declaration=True, encoding="UTF-8", standalone=True)
            if re.fullmatch(r"ppt/theme/theme\d+\.xml", item.filename):
                x = etree.fromstring(data)
                x.find(".//{%s}majorFont/{%s}latin" % (A, A)).set("typeface", "Georgia")
                x.find(".//{%s}minorFont/{%s}latin" % (A, A)).set("typeface", "Verdana")
                data = etree.tostring(x, xml_declaration=True, encoding="UTF-8", standalone=True)
            zout.writestr(item, data)
    return out


SYNTHETIC_LAYERED_SVG = b"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
     width="160mm" height="80mm" viewBox="0 0 160 80">
  <defs id="defs1"><linearGradient id="grad1"><stop offset="0" stop-color="#4477aa"/><stop offset="1" stop-color="#66ccee"/></linearGradient></defs>
  <g inkscape:groupmode="layer" id="base" inkscape:label="Base">
    <rect id="r_base" x="4" y="4" width="60" height="34" fill="url(#grad1)"/>
    <g inkscape:groupmode="layer" id="base_detail_on" inkscape:label="Detail">
      <circle id="c_detail" cx="24" cy="20" r="9" fill="#ee6677"/>
    </g>
    <rect id="r_base_after" x="40" y="12" width="30" height="16" fill="#228833"/>
    <g inkscape:groupmode="layer" id="base_detail_off" inkscape:label="Detail" style="display:none">
      <rect id="r_detail_hidden" x="8" y="26" width="50" height="10" fill="#ccbb44"/>
    </g>
  </g>
  <g inkscape:groupmode="layer" id="annot" inkscape:label="Annotations">
    <g id="ordinary_wrapper" transform="translate(76,4)">
      <rect id="r_wrapped" x="0" y="0" width="34" height="34" fill="#aa3377"/>
      <g inkscape:groupmode="layer" id="annot_nested" inkscape:label="Nested in ordinary group">
        <path id="p_nested" d="M 4 30 L 17 4 L 30 30 Z" fill="#bbbbbb"/>
      </g>
    </g>
  </g>
  <g inkscape:groupmode="layer" id="hidden_root" inkscape:label="Hidden root" style="display:none">
    <rect id="r_hidden_root" x="4" y="44" width="60" height="30" fill="#4477aa"/>
    <g inkscape:groupmode="layer" id="hidden_root_child" inkscape:label="Child of hidden root">
      <rect id="r_hidden_child" x="14" y="50" width="20" height="18" fill="#ee6677"/>
    </g>
  </g>
  <g inkscape:groupmode="layer" id="alt_scope" inkscape:label="Alternative scope" style="display:none">
    <rect id="r_alt" x="120" y="44" width="34" height="30" fill="#228833"/>
  </g>
</svg>
"""
"""Covers: a visible root with visible and hidden child layers sharing one label (identity must be the id);
paint interleaved before and after a nested layer; a layer nested inside an ordinary group; a source-hidden
root with a visible child; a hidden alternative-scope root for a page preset; and a gradient in ``defs``.
No text: CI fonts differ from workstation fonts."""


def synthetic_layered_svg() -> bytes:
    return SYNTHETIC_LAYERED_SVG


SYNTHETIC_PAGE_PRESETS = {
    1: {"title": "As authored", "skip_subtrees": [], "force_on": []},
    2: {"title": "Alternative scope", "skip_subtrees": ["annot"], "force_on": ["alt_scope"]},
}
