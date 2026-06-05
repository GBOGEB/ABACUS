"""
================================================================================
 Module : parser.py
 Purpose: Colour-line-first decomposition of the MINERVA QCELL / RFCELL P&ID
          SVG drawings. Extracts every drawn element's colour & style with the
          CORRECT inline-style precedence, clusters colours to canonical
          process codes by colour-distance, and builds the colour line model.
 Current Wave : W002 - Colour Line Decomposition & Validation
 Status : ACTIVE
 Inputs  : data/svg/*.svg  (real QCELL + RFCELL P&ID exports)
 Outputs : data/model/colour_inventory.json
           data/model/line_model.json
           data/model/lines/*.json   (one file per canonical process colour)
 Notes   : Pure standard library. Geometry/arrow tracing & sequential ordering
           are DEFERRED to W004 (see canonical_name 'arrows_detected' /
           'sequential_components' fields == "DEFERRED_W004").
================================================================================
"""

from __future__ import annotations

import json
import math
import os
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

SVG_NS = "http://www.w3.org/2000/svg"
DRAWABLE = {"path", "line", "polyline", "polygon", "rect", "circle", "ellipse"}

# ---------------------------------------------------------------------------
# Canonical colour anchors -> process codes.
# Mapping per task spec (colour-distance CLUSTERING, not exact hex):
#   BLUE   -> A / A'   (4.5 K main line ; A' internal branch = darker/navy blue)
#   CYAN   -> B / B'   (2 K internal line)
#   GREEN  -> W        (coupler line, splits from BLUE A inside QM)
#   GREY   -> V        (vent line, per module, to outside)
#   OLIVE  -> S        (S line)
#   RED/ORANGE -> D/E  (warm/cold manifold lines)
#   BLACK  -> structure/boundary/symbols/unknown
#   other  -> unknown
# ---------------------------------------------------------------------------
CANONICAL_ANCHORS = [
    # (anchor_name, (r,g,b), process_code, role, canonical_name, temp_note)
    ("blue",        (0x00, 0x00, 0xff), "A",        "primary_process",  "blue_A",            "4.5 K main process line"),
    ("navy",        (0x00, 0x00, 0x80), "A_prime",  "internal_branch",  "blue_A",            "4.5 K internal branch (A')"),
    ("cyan",        (0x00, 0xff, 0xff), "B",        "internal_branch",  "cyan_B_2K",         "2 K internal line"),
    ("teal",        (0x00, 0x80, 0x80), "B_prime",  "internal_branch",  "cyan_B_2K",         "2 K internal branch (B')"),
    ("green",       (0x00, 0xff, 0x00), "W",        "primary_process",  "green_W_coupler",   "Coupler line (splits from BLUE A inside QM)"),
    ("darkgreen",   (0x00, 0x80, 0x00), "W",        "internal_branch",  "green_W_coupler",   "Coupler internal branch"),
    ("olive",       (0x80, 0x80, 0x00), "S",        "warm_line",        "olive_S_line",      "S line (warm)"),
    ("red",         (0xff, 0x00, 0x00), "D",        "manifold",         "red_orange_D_E",    "Warm/cold manifold line (D)"),
    ("orange",      (0xff, 0x80, 0x00), "E",        "manifold",         "red_orange_D_E",    "Warm/cold manifold line (E)"),
    ("grey",        (0x99, 0x99, 0x99), "V",        "vent_line",        "grey_V_vent",       "Vent line (per module, to outside)"),
    ("grey2",       (0x80, 0x80, 0x80), "V",        "vent_line",        "grey_V_vent",       "Vent line variant"),
    ("black",       (0x00, 0x00, 0x00), "unknown",  "scope_boundary",   "unknown_black_or_other", "Structure/boundary/symbol (not validated as a process colour)"),
]

# magenta and any far colour fall through to this bucket
UNKNOWN_BUCKET = ("unknown", "unknown", "unknown", "unknown_black_or_other",
                  "Unresolved colour - not in canonical mapping")

# Colour-distance threshold (RGB Euclidean). Beyond this -> unknown bucket.
MAX_ANCHOR_DISTANCE = 90.0


# ---------------------------------------------------------------------------
# Low level helpers
# ---------------------------------------------------------------------------
def _local(tag: str) -> str:
    return tag.split("}")[-1]


def parse_style(style: str) -> dict:
    """Parse an SVG inline style="k:v;k:v" string into a dict."""
    out = {}
    for part in (style or "").split(";"):
        if ":" in part:
            k, v = part.split(":", 1)
            out[k.strip().lower()] = v.strip()
    return out


def style_value(elem, key: str):
    """Resolve a CSS/style property with CORRECT precedence.

    Inline style="..." MUST override the presentation attribute, so we read
    the style dict FIRST, then fall back to the attribute:
        style.get(key) or elem.attrib.get(key)
    (The reverse order was the bug this wave fixes.)
    """
    st = parse_style(elem.attrib.get("style", ""))
    return st.get(key) or elem.attrib.get(key)


_HEX3 = re.compile(r"^#([0-9a-fA-F]{3})$")
_HEX6 = re.compile(r"^#([0-9a-fA-F]{6})$")
_RGB = re.compile(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", re.I)


def normalise_colour(value):
    """Return a normalised lowercase #rrggbb hex, or a keyword (none/url/etc)."""
    if not value:
        return None
    v = value.strip().lower()
    if v in ("none", "transparent") or v.startswith("url(") or v.startswith("context"):
        return v
    m = _HEX6.match(v)
    if m:
        return "#" + m.group(1).lower()
    m = _HEX3.match(v)
    if m:
        h = m.group(1)
        return "#" + "".join(c * 2 for c in h).lower()
    m = _RGB.match(v)
    if m:
        return "#{:02x}{:02x}{:02x}".format(*(int(x) for x in m.groups()))
    return v  # named colour like 'black' etc.


_NAMED = {
    "black": "#000000", "white": "#ffffff", "red": "#ff0000",
    "green": "#008000", "blue": "#0000ff", "cyan": "#00ffff",
    "magenta": "#ff00ff", "yellow": "#ffff00", "gray": "#808080",
    "grey": "#808080", "olive": "#808000", "navy": "#000080",
}


def hex_to_rgb(hexstr):
    """Convert a #rrggbb (or named) colour to an (r,g,b) tuple, or None."""
    if not hexstr:
        return None
    h = _NAMED.get(hexstr, hexstr)
    m = _HEX6.match(h)
    if not m:
        return None
    h = m.group(1)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def colour_distance(c1, c2):
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1, c2)))


def classify_colour(hexstr):
    """Cluster a hex colour to the nearest canonical anchor by RGB distance.

    Returns a dict describing the canonical assignment.
    """
    rgb = hex_to_rgb(hexstr)
    if rgb is None:
        code, role, _, cname, note = ("unknown", "unknown", None,
                                      "unknown_black_or_other",
                                      "Non-resolvable colour")
        return {"anchor": None, "process_code": code, "role": role,
                "canonical_name": cname, "temp_note": note, "distance": None}

    best = None
    best_d = None
    for name, anchor_rgb, code, role, cname, note in CANONICAL_ANCHORS:
        d = colour_distance(rgb, anchor_rgb)
        if best_d is None or d < best_d:
            best_d = d
            best = (name, code, role, cname, note)

    if best_d is not None and best_d <= MAX_ANCHOR_DISTANCE:
        name, code, role, cname, note = best
        # black family -> structure; everything else -> resolved process colour
        family = "structure" if name == "black" else "process"
        return {"anchor": name, "process_code": code, "role": role,
                "canonical_name": cname, "temp_note": note,
                "distance": round(best_d, 2), "family": family}

    # Too far from every anchor -> unknown bucket (e.g. magenta = truly other)
    code, role, _x, cname, note = UNKNOWN_BUCKET
    return {"anchor": None, "process_code": code, "role": role,
            "canonical_name": cname, "temp_note": note,
            "distance": round(best_d, 2) if best_d is not None else None,
            "family": "unresolved_other"}


# ---------------------------------------------------------------------------
# Element + text extraction
# ---------------------------------------------------------------------------
def _translate_from_transform(transform):
    """Best-effort: pull a translate(x,y) offset from a transform string."""
    if not transform:
        return (0.0, 0.0)
    m = re.search(r"translate\(\s*([-\d.eE]+)[ ,]+([-\d.eE]+)\s*\)", transform)
    if m:
        return (float(m.group(1)), float(m.group(2)))
    m = re.search(r"matrix\(\s*[-\d.eE]+[ ,]+[-\d.eE]+[ ,]+[-\d.eE]+[ ,]+"
                  r"[-\d.eE]+[ ,]+([-\d.eE]+)[ ,]+([-\d.eE]+)\s*\)", transform)
    if m:
        return (float(m.group(1)), float(m.group(2)))
    return (0.0, 0.0)


def extract_elements(svg_path):
    """Walk the SVG. Return (elements, texts).

    elements: list of dicts with stroke/fill colour + width + id + tag.
    texts   : list of dicts with content + approximate (x,y).
    """
    tree = ET.parse(svg_path)
    root = tree.getroot()

    elements = []
    texts = []

    # Track a running translate offset per ancestor chain (best-effort).
    def walk(node, off_x, off_y):
        t = _local(node.tag)
        dx, dy = _translate_from_transform(node.attrib.get("transform"))
        ox, oy = off_x + dx, off_y + dy

        if t in DRAWABLE:
            stroke = normalise_colour(style_value(node, "stroke"))
            fill = normalise_colour(style_value(node, "fill"))
            sw = style_value(node, "stroke-width")
            # effective process colour: prefer a real stroke, else the fill
            eff = None
            if stroke and stroke not in ("none", "transparent") and stroke.startswith("#"):
                eff = stroke
            elif fill and fill not in ("none", "transparent") and fill.startswith("#"):
                eff = fill
            elements.append({
                "id": node.attrib.get("id", ""),
                "tag": t,
                "stroke": stroke,
                "fill": fill,
                "stroke_width": sw,
                "effective_colour": eff,
            })

        if t in ("text", "tspan"):
            content = (node.text or "").strip()
            if content:
                tx = node.attrib.get("x")
                ty = node.attrib.get("y")
                try:
                    px = float(tx) + ox if tx is not None else ox
                    py = float(ty) + oy if ty is not None else oy
                except ValueError:
                    px, py = ox, oy
                texts.append({"text": content, "x": px, "y": py,
                              "id": node.attrib.get("id", "")})

        for child in list(node):
            walk(child, ox, oy)

    walk(root, 0.0, 0.0)
    return elements, texts


# ---------------------------------------------------------------------------
# Inventory + model building
# ---------------------------------------------------------------------------
def build_colour_inventory(all_elements):
    """Build colour_inventory.json content.

    Records every unique (stroke_hex, stroke_width) pair with occurrence count
    and example element IDs, plus its canonical classification.
    """
    pairs = defaultdict(lambda: {"count": 0, "example_ids": []})
    for el in all_elements:
        key = (el["stroke"], el["stroke_width"])
        rec = pairs[key]
        rec["count"] += 1
        if len(rec["example_ids"]) < 5 and el["id"]:
            rec["example_ids"].append(el["id"])

    inventory = []
    for (stroke, sw), rec in sorted(pairs.items(),
                                    key=lambda kv: -kv[1]["count"]):
        cls = classify_colour(stroke) if stroke and stroke.startswith("#") else {
            "anchor": None, "process_code": "non_colour", "role": "n/a",
            "canonical_name": None, "temp_note": stroke, "distance": None}
        inventory.append({
            "stroke_hex": stroke,
            "stroke_width": sw,
            "occurrences": rec["count"],
            "example_element_ids": rec["example_ids"],
            "canonical_process_code": cls["process_code"],
            "canonical_name": cls["canonical_name"],
            "colour_distance_to_anchor": cls["distance"],
        })
    return inventory


# Boundary / mechanical-section keywords to scan in text labels.
BOUNDARY_KEYWORDS = {
    "QM": ["qm", "q-m", "q module", "quadrupole module"],
    "Jumper": ["jumper", "jumper box", "jb"],
    "QVB": ["qvb", "valve box", "vacuum barrier"],
    "QINFRA": ["qinfra", "q-infra", "infra"],
    "vacuum_barrier": ["vacuum barrier", "vac barrier", "vacuum"],
}


def detect_boundaries(texts):
    found = defaultdict(list)
    for tnode in texts:
        low = tnode["text"].lower()
        for boundary, kws in BOUNDARY_KEYWORDS.items():
            for kw in kws:
                if kw in low:
                    found[boundary].append(tnode["text"])
                    break
    return {k: sorted(set(v)) for k, v in found.items()}


def nearest_texts_for_colour(colour_elements_count, texts, limit=12):
    """Lightweight tag association.

    Geometry/CTM tracing is DEFERRED_W004. Here we surface candidate process
    tags (pattern-like labels) found in the drawing so each line record has
    evidence_text seeds. We return label-like tokens (with digits / dashes).
    """
    candidates = []
    seen = set()
    tag_like = re.compile(r"[A-Za-z]{1,4}[-_ ]?\d", )
    for t in texts:
        txt = t["text"]
        if tag_like.search(txt) and txt not in seen:
            seen.add(txt)
            candidates.append(txt)
        if len(candidates) >= limit:
            break
    return candidates


# canonical_name -> filename used in data/model/lines/
LINE_FILES = {
    "blue_A": "blue_A.json",
    "cyan_B_2K": "cyan_B_2K.json",
    "green_W_coupler": "green_W_coupler.json",
    "grey_V_vent": "grey_V_vent.json",
    "olive_S_line": "olive_S_line.json",
    "red_orange_D_E": "red_orange_D_E.json",
    "unknown_black_or_other": "unknown_black_or_other.json",
}


def build_line_model(all_elements, texts, per_file_counts):
    """Build line_model.json: one record per canonical process line.

    Aggregates element counts per process_code and assembles all required
    fields. arrows_detected & sequential_components are DEFERRED_W004.
    """
    # group elements by (process_code, canonical_name)
    groups = defaultdict(lambda: {"count": 0, "colours": Counter(),
                                   "ids": [], "roles": Counter(),
                                   "temp": "", "name": ""})
    for el in all_elements:
        eff = el["effective_colour"]
        if not eff:
            continue
        cls = classify_colour(eff)
        key = (cls["process_code"], cls["canonical_name"])
        g = groups[key]
        g["count"] += 1
        g["colours"][eff] += 1
        g["roles"][cls["role"]] += 1
        g["temp"] = cls["temp_note"]
        g["name"] = cls["canonical_name"]
        if len(g["ids"]) < 15 and el["id"]:
            g["ids"].append(el["id"])

    seed_tags = nearest_texts_for_colour(None, texts)

    records = []
    line_no = 0
    for (code, cname), g in sorted(groups.items(),
                                   key=lambda kv: -kv[1]["count"]):
        line_no += 1
        primary_role = g["roles"].most_common(1)[0][0] if g["roles"] else "unknown"
        source_colour = g["colours"].most_common(1)[0][0] if g["colours"] else None
        confidence = "high" if code not in ("unknown",) else "low"
        records.append({
            "line_id": f"L{line_no:02d}",
            "canonical_name": cname,
            "source_colour": source_colour,
            "source_colour_variants": [c for c, _ in g["colours"].most_common()],
            "process_code": code,
            "temperature_pressure_note": g["temp"],
            "mechanical_section": "TBD (QM / Jumper / QVB / QINFRA - W004)",
            "role": primary_role,
            "inlet_side": "DEFERRED_W004",
            "outlet_side": "DEFERRED_W004",
            "arrows_detected": "DEFERRED_W004",
            "sequential_components": "DEFERRED_W004",
            "associated_tags": seed_tags if code not in ("unknown",) else [],
            "element_count": g["count"],
            "confidence": confidence,
            "evidence_svg_ids": g["ids"],
            "evidence_text": seed_tags[:6],
        })
    return records


def write_per_colour_files(line_records, out_dir):
    """Emit one JSON file per canonical process colour in data/model/lines/."""
    os.makedirs(out_dir, exist_ok=True)
    # ensure all 7 canonical files exist even if empty
    by_name = defaultdict(list)
    for rec in line_records:
        by_name[rec["canonical_name"]].append(rec)

    written = []
    for cname, fname in LINE_FILES.items():
        recs = by_name.get(cname, [])
        payload = {
            "canonical_name": cname,
            "records": recs,
            "total_elements": sum(r["element_count"] for r in recs),
            "note": "arrows & sequential components DEFERRED_W004",
        }
        path = os.path.join(out_dir, fname)
        with open(path, "w") as fh:
            json.dump(payload, fh, indent=2)
        written.append(fname)
    return written
