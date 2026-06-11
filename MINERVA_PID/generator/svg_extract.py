#!/usr/bin/env python3
"""
svg_extract.py
==============
Geometry extraction layer for the MINERVA P&ID rebuild.

Walks a source Inkscape SVG, accumulates the full CTM (Current Transformation
Matrix) for every node, and captures graphic primitives (path, line, polyline,
polygon, rect, circle, ellipse) together with:

  * the baked absolute transform (matrix) so geometry can be re-emitted exactly
  * resolved stroke / fill colour, stroke width, dash pattern
  * the owning Inkscape layer label
  * a derived "bin" used by the rebuild (process-line class, structure,
    instrument-bubble candidate, vacuum boundary ...)

Pure standard library.
"""

import os
import re
import math
import xml.etree.ElementTree as ET

SVG = "{http://www.w3.org/2000/svg}"
INK = "{http://www.inkscape.org/namespaces/inkscape}"

GRAPHIC_TAGS = {"path", "line", "polyline", "polygon", "rect", "circle", "ellipse"}

# ---------------------------------------------------------------------------
# Process-line colour -> class map (canonical legend colours)
# ---------------------------------------------------------------------------
CLASS_COLORS = {
    "#0000ff": "A",      # 4.5 K / 3 bar  (blue)
    "#0000fe": "A",
    "#00ffff": "B",      # 3.5 K / 27 mbar (cyan)
    "#00fefe": "B",
    "#ff0000": "D",      # 40 K / 14 bar  (red)
    "#fe0000": "D",
    "#808000": "E",      # 60 K / 13 bar / guard (olive)
    "#00ff00": "WATER",  # DI water (green)
    "#00fe00": "WATER",
    "#008000": "QINFRA", # infrastructure scope (dark green)
    "#ff00ff": "AIR",    # instrument air (magenta)
    "#fe00fe": "AIR",
    "#000080": "WATER",  # navy water loop -> water
}

# colours treated as structure / equipment outlines
STRUCTURE_COLORS = {
    "#000000", "#1a1a1a", "#999999", "#9b9b9b", "#898585",
    "#808080", "#4d4d4d", "#aa4400", "#bf512e", "#333333", "#666666",
}

# ---------------------------------------------------------------------------
# Transform handling
# ---------------------------------------------------------------------------

def transform_to_matrix(name, n):
    if name == "matrix" and len(n) == 6:
        return n[:]
    if name == "translate":
        return [1, 0, 0, 1, n[0] if n else 0.0, n[1] if len(n) > 1 else 0.0]
    if name == "scale":
        sx = n[0] if n else 1.0
        sy = n[1] if len(n) > 1 else sx
        return [sx, 0, 0, sy, 0, 0]
    if name == "rotate" and n:
        a = math.radians(n[0])
        c, s = math.cos(a), math.sin(a)
        mt = [c, s, -s, c, 0, 0]
        if len(n) == 3:
            cx, cy = n[1], n[2]
            mt = mat_mul([1, 0, 0, 1, cx, cy], mt)
            mt = mat_mul(mt, [1, 0, 0, 1, -cx, -cy])
        return mt
    if name == "skewX" and n:
        return [1, 0, math.tan(math.radians(n[0])), 1, 0, 0]
    if name == "skewY" and n:
        return [1, math.tan(math.radians(n[0])), 0, 1, 0, 0]
    return [1, 0, 0, 1, 0, 0]


def parse_transform(t):
    m = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
    if not t:
        return m
    for name, args in re.findall(r"(\w+)\s*\(([^)]*)\)", t):
        nums = [float(x) for x in re.findall(r"-?\d+\.?\d*(?:[eE]-?\d+)?", args)]
        m = mat_mul(m, transform_to_matrix(name, nums))
    return m


def mat_mul(m1, m2):
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return [
        a1 * a2 + c1 * b2, b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2, b1 * c2 + d1 * d2,
        a1 * e2 + c1 * f2 + e1, b1 * e2 + d1 * f2 + f1,
    ]


def apply(m, x, y):
    a, b, c, d, e, f = m
    return (a * x + c * y + e, b * x + d * y + f)


def avg_scale(m):
    a, b, c, d, _, _ = m
    sx = math.hypot(a, b)
    sy = math.hypot(c, d)
    return (sx + sy) / 2.0


def matrix_str(m):
    return "matrix(%s)" % ",".join("%.5f" % v for v in m)


# ---------------------------------------------------------------------------
# Style helpers
# ---------------------------------------------------------------------------

def style_dict(el):
    s = {}
    for part in (el.get("style") or "").split(";"):
        if ":" in part:
            k, v = part.split(":", 1)
            s[k.strip()] = v.strip()
    return s


_NAMED = {
    "black": "#000000", "white": "#ffffff", "red": "#ff0000",
    "blue": "#0000ff", "green": "#008000", "lime": "#00ff00",
    "cyan": "#00ffff", "aqua": "#00ffff", "magenta": "#ff00ff",
    "fuchsia": "#ff00ff", "yellow": "#ffff00", "olive": "#808000",
    "navy": "#000080", "gray": "#808080", "grey": "#808080",
}


def norm_color(v):
    if not v:
        return None
    v = v.strip().lower()
    if v in ("none", "transparent"):
        return None
    if v in _NAMED:
        return _NAMED[v]
    if v.startswith("#"):
        if len(v) == 4:  # #rgb -> #rrggbb
            v = "#" + "".join(ch * 2 for ch in v[1:])
        return v[:7]
    m = re.match(r"rgb\(\s*(\d+)\D+(\d+)\D+(\d+)", v)
    if m:
        return "#%02x%02x%02x" % tuple(int(x) for x in m.groups())
    return None


def get_color(el, prop):
    st = style_dict(el)
    return norm_color(st.get(prop) or el.get(prop))


def get_width(el):
    st = style_dict(el)
    w = st.get("stroke-width") or el.get("stroke-width")
    if not w:
        return None
    m = re.match(r"(-?\d+\.?\d*)", w)
    return float(m.group(1)) if m else None


def get_dash(el):
    st = style_dict(el)
    return st.get("stroke-dasharray") or el.get("stroke-dasharray") or "none"


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------

class Element:
    __slots__ = ("tag", "attrs", "ctm", "stroke", "fill", "width", "dash",
                 "layer", "bin", "cls", "abs_r", "cx", "cy")

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))


class Extractor:
    def __init__(self, path):
        self.path = path
        self.tree = ET.parse(path)
        self.root = self.tree.getroot()
        self.elements = []
        self.viewBox = self.root.get("viewBox")
        self._walk(self.root, [1, 0, 0, 1, 0, 0], "(root)")

    def _layer_label(self, el, current):
        if el.get(INK + "groupmode") == "layer":
            return el.get(INK + "label") or el.get("id") or current
        return current

    def _walk(self, el, ctm, layer):
        local = parse_transform(el.get("transform"))
        cur = mat_mul(ctm, local)
        layer = self._layer_label(el, layer)
        tag = el.tag.replace(SVG, "")
        if tag in GRAPHIC_TAGS:
            self._capture(el, tag, cur, layer)
        for child in el:
            self._walk(child, cur, layer)

    def _capture(self, el, tag, ctm, layer):
        stroke = get_color(el, "stroke")
        fill = get_color(el, "fill")
        width = get_width(el)
        dash = get_dash(el)
        cx = cy = abs_r = None
        if tag in ("circle", "ellipse"):
            cx0 = float(el.get("cx", 0) or 0)
            cy0 = float(el.get("cy", 0) or 0)
            if tag == "circle":
                r = float(el.get("r", 0) or 0)
            else:
                r = (float(el.get("rx", 0) or 0) + float(el.get("ry", 0) or 0)) / 2.0
            cx, cy = apply(ctm, cx0, cy0)
            abs_r = r * avg_scale(ctm)
        e = Element(tag=tag, attrs=dict(el.attrib), ctm=ctm, stroke=stroke,
                    fill=fill, width=width, dash=dash, layer=layer,
                    cx=cx, cy=cy, abs_r=abs_r)
        self._classify(e)
        self.elements.append(e)

    def _classify(self, e):
        """Assign a coarse bin used by the rebuild."""
        s = e.stroke
        e.cls = None
        # Process line class by stroke colour
        if s in CLASS_COLORS:
            e.bin = "process"
            e.cls = CLASS_COLORS[s]
            return
        # Instrument-bubble candidate: small stroked circle/ellipse
        if e.tag in ("circle", "ellipse") and e.abs_r and 4.0 <= e.abs_r <= 20.0:
            e.bin = "bubble"
            return
        # Filled shape using a process colour (no real stroke):
        #  - small circle/ellipse  -> pipe junction node
        #  - larger area           -> coloured zone / pipe block
        if e.fill in CLASS_COLORS:
            e.cls = CLASS_COLORS[e.fill]
            if e.tag in ("circle", "ellipse") and e.abs_r and e.abs_r <= 6.0:
                e.bin = "process_node"
            else:
                e.bin = "process_fill"
            return
        # Dashed structural boundary -> vacuum / scope boundary
        if e.dash and e.dash != "none" and (s in STRUCTURE_COLORS or s is None):
            e.bin = "boundary"
            return
        if s in STRUCTURE_COLORS or (s is None and e.fill):
            e.bin = "structure"
            return
        e.bin = "other"


def load(path):
    return Extractor(path)


if __name__ == "__main__":
    import sys
    from collections import Counter
    ex = load(sys.argv[1])
    print("viewBox:", ex.viewBox, "elements:", len(ex.elements))
    print("bins:", Counter(e.bin for e in ex.elements))
    print("classes:", Counter(e.cls for e in ex.elements if e.cls))
