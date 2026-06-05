"""
================================================================================
 Module : geometry.py
 Purpose: CTM-resolved geometric extraction of EVERY drawable element in the
          QCELL / RFCELL P&ID SVGs. Computes absolute bounding boxes &
          centroids, classifies element SHAPE (dot / triangle / arrow /
          bubble / rect / line / path), and captures text nodes with their
          fill colour + absolute position. This is the geometric substrate
          for Wave W004 (pairing, flow tracing, nomenclature).
 Current Wave : W003 + W004
 Status : ACTIVE
 Inputs  : data/svg/*.svg
 Outputs : in-memory model consumed by build_w003_w004.py
 Notes   : Pure standard library. Affine/CTM maths reuse the proven approach
           from segmentation/segment_pid.py.
================================================================================
"""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from collections import Counter

from abacus_svg_pid import parser as P

SVG = "{http://www.w3.org/2000/svg}"
INK = "{http://www.inkscape.org/namespaces/inkscape}"

# ---------------------------------------------------------------------------
# Affine transform maths (reused approach from segment_pid.py)
# ---------------------------------------------------------------------------
def parse_transform(t):
    m = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
    if not t:
        return m
    for name, args in re.findall(r"(\w+)\s*\(([^)]*)\)", t):
        nums = [float(x) for x in re.findall(r"-?\d+\.?\d*(?:[eE]-?\d+)?", args)]
        m = mat_mul(m, _to_matrix(name, nums))
    return m


def _to_matrix(name, n):
    if name == "matrix" and len(n) == 6:
        return n[:]
    if name == "translate":
        return [1, 0, 0, 1, n[0] if n else 0.0, n[1] if len(n) > 1 else 0.0]
    if name == "scale":
        sx = n[0] if n else 1.0
        return [sx, 0, 0, n[1] if len(n) > 1 else sx, 0, 0]
    if name == "rotate" and n:
        a = math.radians(n[0])
        cos, sin = math.cos(a), math.sin(a)
        mt = [cos, sin, -sin, cos, 0, 0]
        if len(n) == 3:
            cx, cy = n[1], n[2]
            mt = mat_mul([1, 0, 0, 1, cx, cy], mt)
            mt = mat_mul(mt, [1, 0, 0, 1, -cx, -cy])
        return mt
    return [1, 0, 0, 1, 0, 0]


def mat_mul(m1, m2):
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return [a1 * a2 + c1 * b2, b1 * a2 + d1 * b2,
            a1 * c2 + c1 * d2, b1 * c2 + d1 * d2,
            a1 * e2 + c1 * f2 + e1, b1 * e2 + d1 * f2 + f1]


def apply(m, x, y):
    a, b, c, d, e, f = m
    return (a * x + c * y + e, b * x + d * y + f)


def avg_scale(m):
    """Average linear scale factor of a CTM (for radius/size mapping)."""
    a, b, c, d, _e, _f = m
    sx = math.hypot(a, b)
    sy = math.hypot(c, d)
    return (sx + sy) / 2.0 or 1.0


# ---------------------------------------------------------------------------
# Path point extraction (for bbox / centroid / vertex count)
# ---------------------------------------------------------------------------
_TOKEN = re.compile(r"([MmLlHhVvCcSsQqTtAaZz])|(-?\d*\.?\d+(?:[eE][-+]?\d+)?)")


def path_points(d):
    """Return a list of (x,y) anchor points from a path 'd' attribute.

    Approximate: handles M/L/H/V/C/S/Q/T absolute & relative by tracking the
    current point; for curves we keep the end point (and control endpoints).
    Good enough for bbox / centroid / vertex counting.
    """
    pts = []
    cmd = None
    cx = cy = 0.0
    start = None
    nums = []
    tokens = _TOKEN.findall(d or "")
    i = 0

    def flush(letter, vals):
        nonlocal cx, cy, start
        rel = letter.islower()
        L = letter.upper()
        k = 0
        if L == "M":
            while k + 1 < len(vals) + 1 and k + 1 <= len(vals):
                if k + 1 > len(vals) - 1 and (len(vals) - k) < 2:
                    break
                x, y = vals[k], vals[k + 1]
                cx, cy = (cx + x, cy + y) if rel else (x, y)
                pts.append((cx, cy))
                if start is None:
                    start = (cx, cy)
                k += 2
        elif L == "L" or L == "T":
            while k + 1 <= len(vals) - 1:
                x, y = vals[k], vals[k + 1]
                cx, cy = (cx + x, cy + y) if rel else (x, y)
                pts.append((cx, cy))
                k += 2
        elif L == "H":
            for x in vals:
                cx = cx + x if rel else x
                pts.append((cx, cy))
        elif L == "V":
            for y in vals:
                cy = cy + y if rel else y
                pts.append((cx, cy))
        elif L in ("C",):
            while k + 5 <= len(vals) - 1 + 1 and k + 5 < len(vals) + 1:
                if k + 6 > len(vals):
                    break
                x, y = vals[k + 4], vals[k + 5]
                cx, cy = (cx + x, cy + y) if rel else (x, y)
                pts.append((cx, cy))
                k += 6
        elif L in ("S", "Q"):
            step = 4
            while k + step <= len(vals):
                x, y = vals[k + step - 2], vals[k + step - 1]
                cx, cy = (cx + x, cy + y) if rel else (x, y)
                pts.append((cx, cy))
                k += step
        elif L == "A":
            step = 7
            while k + step <= len(vals):
                x, y = vals[k + 5], vals[k + 6]
                cx, cy = (cx + x, cy + y) if rel else (x, y)
                pts.append((cx, cy))
                k += step

    for letter, num in tokens:
        if letter:
            if cmd is not None and nums:
                flush(cmd, nums)
            nums = []
            cmd = letter
            if letter in ("Z", "z"):
                cmd = None
        else:
            nums.append(float(num))
    if cmd is not None and nums:
        flush(cmd, nums)
    return pts


# ---------------------------------------------------------------------------
# Element model
# ---------------------------------------------------------------------------
class Element:
    __slots__ = ("eid", "tag", "shape", "colour", "process_code",
                 "canonical_name", "family", "cx", "cy", "x0", "y0",
                 "x1", "y1", "width_px", "height_px", "vertices", "layer",
                 "has_marker", "dash", "stroke_width", "raw_stroke", "raw_fill")

    def to_dict(self):
        return {
            "id": self.eid, "tag": self.tag, "shape": self.shape,
            "colour": self.colour, "process_code": self.process_code,
            "canonical_name": self.canonical_name, "family": self.family,
            "cx": self.cx, "cy": self.cy,
            "bbox": [self.x0, self.y0, self.x1, self.y1],
            "w": self.width_px, "h": self.height_px,
            "vertices": self.vertices, "layer": self.layer,
            "has_marker": self.has_marker, "dash": self.dash,
            "stroke_width": self.stroke_width,
        }


def _round(v, n=2):
    return None if v is None else round(v, n)


class GeometryModel:
    def __init__(self, key, path):
        self.key = key
        self.path = path
        self.root = ET.parse(path).getroot()
        self.elements = []   # list[Element]
        self.texts = []      # dicts: text, x, y, fill, layer, font, size
        self.layers = []
        # parse viewBox for robust drawing bounds
        vb = self.root.attrib.get("viewBox", "0 0 1527.2727 1080")
        try:
            parts = [float(x) for x in re.split(r"[ ,]+", vb.strip())]
            self.viewbox = parts if len(parts) == 4 else [0, 0, 1527.2727, 1080]
        except ValueError:
            self.viewbox = [0, 0, 1527.2727, 1080]
        self._walk(self.root, [1, 0, 0, 1, 0, 0], "(root)", 0)

    # -- helpers
    @staticmethod
    def _local(el):
        return el.tag.split("}")[-1]

    def _classify_shape(self, tag, el, verts, has_marker, w, h, scale):
        """Heuristic shape classification."""
        if has_marker:
            return "arrow"
        if tag in ("circle", "ellipse"):
            r = el.attrib.get("r") or el.attrib.get("rx") or "0"
            try:
                rad = float(r) * scale
            except ValueError:
                rad = 0
            if rad <= 5.0:
                return "dot"        # spec-change indicator
            return "bubble"         # instrument bubble
        if tag == "rect":
            return "rect"
        if tag in ("polygon",):
            return "triangle" if len(verts) in (3, 4) else "polygon"
        if tag == "path":
            n = len(verts)
            # closed small 3-4 vertex path -> triangle (heat load)
            d = el.attrib.get("d", "")
            closed = d.strip().lower().endswith("z")
            if closed and n in (3, 4, 5):
                # near-triangular if 3 distinct vertices
                return "triangle"
            if n <= 2:
                return "line"
            return "path"
        if tag in ("line", "polyline"):
            return "line"
        return tag

    def _walk(self, el, ctm, layer, depth):
        tag = self._local(el)
        if tag == "g" and el.get(INK + "groupmode") == "layer":
            layer = el.get(INK + "label") or el.get("id") or layer
            self.layers.append({"id": el.get("id"),
                                "label": el.get(INK + "label"),
                                "depth": depth})
        ctm = mat_mul(ctm, parse_transform(el.get("transform")))
        scale = avg_scale(ctm)

        if tag in P.DRAWABLE:
            self._handle_drawable(el, tag, ctm, scale, layer)
        elif tag == "text":
            self._handle_text(el, ctm, layer)

        for child in list(el):
            self._walk(child, ctm, layer, depth + 1)

    def _handle_drawable(self, el, tag, ctm, scale, layer):
        stroke = P.normalise_colour(P.style_value(el, "stroke"))
        fill = P.normalise_colour(P.style_value(el, "fill"))
        eff = None
        if stroke and stroke.startswith("#"):
            eff = stroke
        elif fill and fill.startswith("#"):
            eff = fill

        # gather local points
        pts = []
        if tag == "path":
            pts = path_points(el.attrib.get("d", ""))
        elif tag in ("circle", "ellipse"):
            cx = float(el.attrib.get("cx", 0) or 0)
            cy = float(el.attrib.get("cy", 0) or 0)
            pts = [(cx, cy)]
        elif tag == "rect":
            x = float(el.attrib.get("x", 0) or 0)
            y = float(el.attrib.get("y", 0) or 0)
            w = float(el.attrib.get("width", 0) or 0)
            h = float(el.attrib.get("height", 0) or 0)
            pts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
        elif tag in ("polygon", "polyline", "line"):
            raw = el.attrib.get("points") or ""
            nums = [float(n) for n in re.findall(r"-?\d+\.?\d*", raw)]
            pts = list(zip(nums[0::2], nums[1::2]))
            if tag == "line":
                pts = [(float(el.attrib.get("x1", 0)), float(el.attrib.get("y1", 0))),
                       (float(el.attrib.get("x2", 0)), float(el.attrib.get("y2", 0)))]

        abs_pts = [apply(ctm, x, y) for (x, y) in pts] if pts else []
        if abs_pts:
            xs = [p[0] for p in abs_pts]
            ys = [p[1] for p in abs_pts]
            x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
            cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
        else:
            x0 = y0 = x1 = y1 = cx = cy = None

        style = P.parse_style(el.attrib.get("style", ""))
        has_marker = bool(style.get("marker-end") or style.get("marker-start")
                          or el.attrib.get("marker-end") or el.attrib.get("marker-start"))
        dash = style.get("stroke-dasharray") or el.attrib.get("stroke-dasharray") or "none"

        w_px = _round(x1 - x0) if x0 is not None else None
        h_px = _round(y1 - y0) if y0 is not None else None
        shape = self._classify_shape(tag, el, abs_pts, has_marker, w_px, h_px, scale)

        cls = P.classify_colour(eff) if eff else {
            "process_code": "none", "canonical_name": None, "family": "none"}

        e = Element()
        e.eid = el.attrib.get("id", "")
        e.tag = tag
        e.shape = shape
        e.colour = eff
        e.process_code = cls.get("process_code")
        e.canonical_name = cls.get("canonical_name")
        e.family = cls.get("family")
        e.cx, e.cy = _round(cx), _round(cy)
        e.x0, e.y0, e.x1, e.y1 = _round(x0), _round(y0), _round(x1), _round(y1)
        e.width_px, e.height_px = w_px, h_px
        e.vertices = len(abs_pts)
        e.layer = layer
        e.has_marker = has_marker
        e.dash = dash
        e.stroke_width = style.get("stroke-width") or el.attrib.get("stroke-width")
        e.raw_stroke = stroke
        e.raw_fill = fill
        self.elements.append(e)

    def _handle_text(self, el, ctm, layer):
        content = "".join(el.itertext()).strip()
        if not content:
            return
        try:
            x = float(el.get("x", "nan"))
            y = float(el.get("y", "nan"))
        except ValueError:
            x = y = float("nan")
        if math.isnan(x):
            for tsp in el.iter(SVG + "tspan"):
                if tsp.get("x"):
                    x = float(re.split(r"[ ,]", tsp.get("x"))[0])
                    y = float(re.split(r"[ ,]", tsp.get("y") or "0")[0])
                    break
        ax, ay = apply(ctm, x, y) if not math.isnan(x) else (None, None)
        style = P.parse_style(el.attrib.get("style", ""))
        fill = P.normalise_colour(style.get("fill") or el.attrib.get("fill"))
        font = style.get("font-family") or el.attrib.get("font-family")
        size = style.get("font-size") or el.attrib.get("font-size")
        weight = style.get("font-weight") or el.attrib.get("font-weight")
        # rotation: detect vertical text via transform matrix angle
        a, b = ctm[0], ctm[1]
        angle = math.degrees(math.atan2(b, a))
        vertical = abs(abs(angle) - 90) < 25 or abs(abs(angle) - 270) < 25
        # also check tspan-level fills for per-token colour
        token_fills = []
        for tsp in el.iter(SVG + "tspan"):
            tf = P.normalise_colour(P.parse_style(tsp.attrib.get("style", "")).get("fill")
                                    or tsp.attrib.get("fill"))
            if tf:
                token_fills.append(tf)
        if not fill and token_fills:
            fill = token_fills[0]
        self.texts.append({
            "text": content,
            "x": _round(ax), "y": _round(ay),
            "fill": fill, "font_family": font, "font_size": size,
            "font_weight": weight, "vertical": vertical,
            "angle": round(angle, 1), "layer": layer,
            "id": el.attrib.get("id", ""),
        })
