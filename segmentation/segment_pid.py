#!/usr/bin/env python3
"""
segment_pid.py
==============
Comprehensive P&ID segmentation engine for the MINERVA CryoCell flow schemes.

Parses the source SVG P&IDs and segments all process-logic elements into
structured categories:

  1. Process lines (by color class A/B/D/E + utility/guard) with T/P specs
  2. Equipment / components (vessels, pumps, valves, HX, couplers, cavities ...)
  3. Instrumentation (ISA 5.1 tags: TT, PT, LT, FT, LS, CV, HV, SV, EH ...)
  4. Vacuum barriers + temperature / pressure measurement points
  5. Safety devices & interlocks
  6. Color-to-meaning mapping + color-group segmentation
  7. Layer-by-layer breakdown for reconstruction

Outputs JSON + CSV per category under segmentation/data/ and segmentation/layers/.

Pure standard-library (xml.etree, re, json, csv) — no external deps.
"""

import xml.etree.ElementTree as ET
import re
import os
import json
import csv
import math
from collections import Counter, defaultdict

# ---------------------------------------------------------------------------
# Namespaces
# ---------------------------------------------------------------------------
SVG = "{http://www.w3.org/2000/svg}"
INK = "{http://www.inkscape.org/namespaces/inkscape}"

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
SRC_DIR = os.path.join(PROJECT, "svg_source")
DATA_DIR = os.path.join(HERE, "data")
LAYER_DIR = os.path.join(HERE, "layers")
for d in (DATA_DIR, LAYER_DIR):
    os.makedirs(d, exist_ok=True)

SVG_FILES = {
    "QCELL-LB": "PFD-PID MINERVA QCELL-LB.svg",
    "RFCELL": "PFD-PID MINERVA RFCELL seen by ACR.svg",
}

# ---------------------------------------------------------------------------
# Reference knowledge (legend + nomenclature derived)
# ---------------------------------------------------------------------------

# Process line classes from the drawing legend, bound to color codes that are
# used for the main process piping in the QCELL-LB sheet.
LINE_CLASSES = {
    "A": {"name": "Class A", "temperature": "4.5 K", "pressure": "3 bar",
          "color": "#0000ff", "color_name": "blue",
          "description": "Supercritical / liquid helium supply (4.5 K, 3 bar)"},
    "B": {"name": "Class B", "temperature": "3.5 K", "pressure": "27 mbar (spec 28 mbar)",
          "color": "#00ffff", "color_name": "cyan",
          "description": "2 K / low-pressure helium return (3.5 K, ~27 mbar)"},
    "D": {"name": "Class D", "temperature": "40 K", "pressure": "14 bar",
          "color": "#ff0000", "color_name": "red",
          "description": "Thermal-shield / 40 K helium circuit (40 K, 14 bar)"},
    "E": {"name": "Class E", "temperature": "60 K", "pressure": "13 bar",
          "color": "#808000", "color_name": "olive",
          "description": "60 K helium return / He-guard family (60 K, 13 bar)"},
}

# Color-to-meaning map (stroke colors). Confidence noted where inferred.
COLOR_MEANINGS = {
    "#0000ff": ("Process line A", "4.5 K / 3 bar helium supply", "high"),
    "#00ffff": ("Process line B", "3.5 K / 27 mbar helium (2 K return)", "high"),
    "#ff0000": ("Process line D", "40 K / 14 bar thermal-shield helium", "high"),
    "#808000": ("He-guard / Class E header", "292 K 1.15 bar guard or 60 K/13 bar return", "medium"),
    "#00ff00": ("Coupler / utility water lines", "DI cooling water to couplers / FREIA", "high"),
    "#008000": ("QINFRA scope piping", "infrastructure scope-division lines", "medium"),
    "#ff00ff": ("Instrument air", "pneumatic / instrument-air signal lines", "high"),
    "#000080": ("Water loop (navy)", "RFCELL water-loop / process line", "medium"),
    "#000000": ("Structure / outlines / text", "generic geometry, borders, labels", "high"),
    "#1a1a1a": ("Dark strokes / text", "near-black strokes and annotations", "high"),
    "#ffffff": ("Fills", "white fills / backgrounds", "high"),
    "#f2f2f2": ("Vacuum / shading", "devices-under-vacuum light shading", "medium"),
    "#999999": ("Grey structure", "mechanical structure / shading", "medium"),
    "#808080": ("Grey shading", "mid-grey shading", "medium"),
    "#4d4d4d": ("Dark-grey structure", "structural strokes (RFCELL)", "medium"),
    "#aa4400": ("Cavity / coupler body", "cavity/coupler metal body (brown)", "medium"),
    "#bf512e": ("Cavity / coupler body", "cavity/coupler metal body (brown)", "medium"),
    "#d35f5f": ("RFCELL instrument bubble", "salmon instrument fill", "low"),
    "#ffaaaa": ("RFCELL instrument bubble", "salmon instrument fill", "low"),
    "#ffcc00": ("Highlight / heat", "amber highlight / heat annotation", "low"),
    "#f37f35": ("Heat / highlight", "orange heat annotation", "low"),
    "#ff9a00": ("Heat / highlight", "orange heat annotation", "low"),
}

# ISA 5.1 instrument tag prefix dictionary (measured variable + function)
ISA_PREFIX = {
    "TT": ("Temperature Transmitter", "temperature", "sensor"),
    "TE": ("Temperature Element", "temperature", "sensor"),
    "TI": ("Temperature Indicator", "temperature", "indicator"),
    "PT": ("Pressure Transmitter", "pressure", "sensor"),
    "PI": ("Pressure Indicator", "pressure", "indicator"),
    "PZ": ("Pressure (special / safety)", "pressure", "sensor"),
    "PL": ("Pressure Limiter", "pressure", "safety"),
    "LT": ("Level Transmitter", "level", "sensor"),
    "LS": ("Level Switch", "level", "switch"),
    "LE": ("Level Element / probe", "level", "sensor"),
    "LI": ("Level Indicator", "level", "indicator"),
    "FT": ("Flow Transmitter", "flow", "sensor"),
    "FE": ("Flow Element", "flow", "sensor"),
    "FV": ("Flow / Stop Valve", "flow", "valve"),
    "CV": ("Control Valve", "control", "valve"),
    "HV": ("Hand (Manual) Valve", "control", "valve"),
    "MV": ("Manual / Motorised Valve", "control", "valve"),
    "PV": ("Pressure Regulating Valve", "pressure", "valve"),
    "SV": ("Safety / Solenoid Valve", "safety", "valve"),
    "RV": ("Relief Valve", "safety", "valve"),
    "RD": ("Rupture Disc", "safety", "device"),
    "EH": ("Electric Heater", "heat", "actuator"),
    "HL": ("Heat Load annotation", "heat", "annotation"),
    "HX": ("Heat Exchanger", "process", "equipment"),
    "AA": ("Analysis / Alarm", "analysis", "alarm"),
    "AD": ("Analysis Device", "analysis", "device"),
    "AP": ("Antenna / Analysis Probe", "analysis", "device"),
    "ED": ("Element Device", "analysis", "device"),
    "SM": ("Special Measurement", "analysis", "device"),
    "RS": ("Special / status", "analysis", "device"),
    "CF": ("CF-flange callout", "mechanical", "annotation"),
    "AK": ("Antenna / connector", "mechanical", "annotation"),
    "KW": ("Connector / coupler", "mechanical", "annotation"),
}

SAFETY_PREFIXES = {"SV", "RV", "RD", "PL", "PZ"}
TAG_RE = re.compile(r"^([A-Z]{2})\s?[-]?\s?([0-9x]{1,4}[A-Za-z]?)$")

# ---------------------------------------------------------------------------
# Transform handling -> absolute coordinates
# ---------------------------------------------------------------------------

def parse_transform(t):
    """Return a 2x3 affine matrix [a,b,c,d,e,f] for an SVG transform string."""
    m = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
    if not t:
        return m
    for name, args in re.findall(r"(\w+)\s*\(([^)]*)\)", t):
        nums = [float(x) for x in re.findall(r"-?\d+\.?\d*(?:[eE]-?\d+)?", args)]
        m = mat_mul(m, transform_to_matrix(name, nums))
    return m


def transform_to_matrix(name, n):
    if name == "matrix" and len(n) == 6:
        return n[:]
    if name == "translate":
        tx = n[0] if n else 0.0
        ty = n[1] if len(n) > 1 else 0.0
        return [1, 0, 0, 1, tx, ty]
    if name == "scale":
        sx = n[0] if n else 1.0
        sy = n[1] if len(n) > 1 else sx
        return [sx, 0, 0, sy, 0, 0]
    if name == "rotate" and n:
        a = math.radians(n[0])
        cos, sin = math.cos(a), math.sin(a)
        mt = [cos, sin, -sin, cos, 0, 0]
        if len(n) == 3:  # rotate about point
            cx, cy = n[1], n[2]
            mt = mat_mul([1, 0, 0, 1, cx, cy], mt)
            mt = mat_mul(mt, [1, 0, 0, 1, -cx, -cy])
        return mt
    return [1, 0, 0, 1, 0, 0]


def mat_mul(m1, m2):
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return [
        a1 * a2 + c1 * b2,
        b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2,
        b1 * c2 + d1 * d2,
        a1 * e2 + c1 * f2 + e1,
        b1 * e2 + d1 * f2 + f1,
    ]


def apply(m, x, y):
    a, b, c, d, e, f = m
    return (a * x + c * y + e, b * x + d * y + f)


# ---------------------------------------------------------------------------
# Style helpers
# ---------------------------------------------------------------------------

def style_dict(el):
    s = {}
    raw = el.get("style") or ""
    for part in raw.split(";"):
        if ":" in part:
            k, v = part.split(":", 1)
            s[k.strip()] = v.strip()
    return s


def get_color(el, prop):
    s = style_dict(el)
    val = s.get(prop) or el.get(prop)
    if val and val.startswith("#"):
        return val.lower()
    return None


def first_xy(d):
    m = re.match(r"\s*[Mm]\s*(-?\d+\.?\d*)[ ,]+(-?\d+\.?\d*)", d or "")
    return (float(m.group(1)), float(m.group(2))) if m else None


# ---------------------------------------------------------------------------
# Core walker
# ---------------------------------------------------------------------------

class SvgModel:
    def __init__(self, key, path):
        self.key = key
        self.path = path
        self.tree = ET.parse(path)
        self.root = self.tree.getroot()
        self.texts = []        # dicts: text, x, y, layer, fill
        self.bubbles = []      # ellipse/circle instrument bubbles
        self.paths = []        # colored stroke paths
        self.layers = []       # ordered layer dicts
        self.color_counter = Counter()
        self._walk()

    def _walk(self):
        # iterate with layer + transform context
        self._recurse(self.root, [1, 0, 0, 1, 0, 0], layer="(root)", depth=0)
        # build ordered layer list
        seen = {}
        for g in self.root.iter(SVG + "g"):
            if g.get(INK + "groupmode") == "layer":
                lbl = g.get(INK + "label") or g.get("id") or "(unnamed)"
                seen.setdefault(g.get("id"), lbl)

    def _recurse(self, el, ctm, layer, depth):
        tag = el.tag.replace(SVG, "")
        # update layer if this group is an inkscape layer
        if tag == "g" and el.get(INK + "groupmode") == "layer":
            layer = el.get(INK + "label") or el.get("id") or layer
            self.layers.append({"id": el.get("id"), "label": el.get(INK + "label"), "depth": depth})
        # update transform
        local = parse_transform(el.get("transform"))
        ctm = mat_mul(ctm, local)

        # color accounting
        for prop in ("stroke", "fill"):
            c = get_color(el, prop)
            if c:
                self.color_counter[c] += 1

        if tag == "text":
            self._handle_text(el, ctm, layer)
        elif tag in ("ellipse", "circle"):
            self._handle_bubble(el, tag, ctm, layer)
        elif tag == "path":
            self._handle_path(el, ctm, layer)

        for child in list(el):
            self._recurse(child, ctm, layer, depth + 1)

    def _handle_text(self, el, ctm, layer):
        # gather text content (text + tspans)
        content = "".join(el.itertext())
        content = content.strip()
        if not content:
            return
        try:
            x = float(el.get("x", "nan"))
            y = float(el.get("y", "nan"))
        except ValueError:
            x = y = float("nan")
        if math.isnan(x):
            # try first tspan coords
            for tsp in el.iter(SVG + "tspan"):
                if tsp.get("x"):
                    x = float(re.split(r"[ ,]", tsp.get("x"))[0])
                    y = float(re.split(r"[ ,]", tsp.get("y") or "0")[0])
                    break
        ax, ay = apply(ctm, x, y) if not math.isnan(x) else (None, None)
        # capture individual tspan tokens with their own coordinates so that
        # tags stored as separate tspans inside one <text> (e.g. EH514 + TT514)
        # are kept distinct rather than concatenated.
        tokens = []
        for tsp in el.iter(SVG + "tspan"):
            tt = (tsp.text or "").strip()
            if not tt:
                continue
            tx, ty = ax, ay
            if tsp.get("x"):
                try:
                    rawx = float(re.split(r"[ ,]", tsp.get("x"))[0])
                    rawy = float(re.split(r"[ ,]", tsp.get("y") or str(y))[0])
                    tx, ty = apply(ctm, rawx, rawy)
                    tx, ty = round(tx, 2), round(ty, 2)
                except ValueError:
                    pass
            tokens.append({"text": tt, "x": tx, "y": ty,
                           "fill": get_color(tsp, "fill")})
        if not tokens:
            tokens = [{"text": content,
                       "x": None if ax is None else round(ax, 2),
                       "y": None if ay is None else round(ay, 2),
                       "fill": get_color(el, "fill")}]
        self.texts.append({
            "text": content,
            "x": None if ax is None else round(ax, 2),
            "y": None if ay is None else round(ay, 2),
            "layer": layer,
            "fill": get_color(el, "fill"),
            "tokens": tokens,
        })

    def _handle_bubble(self, el, tag, ctm, layer):
        if tag == "ellipse":
            cx = float(el.get("cx", 0)); cy = float(el.get("cy", 0))
            rx = float(el.get("rx", 0)); ry = float(el.get("ry", 0))
        else:
            cx = float(el.get("cx", 0)); cy = float(el.get("cy", 0))
            rx = ry = float(el.get("r", 0))
        ax, ay = apply(ctm, cx, cy)
        self.bubbles.append({
            "shape": tag,
            "cx": round(ax, 2), "cy": round(ay, 2),
            "rx": round(rx, 2), "ry": round(ry, 2),
            "layer": layer,
            "fill": get_color(el, "fill"),
            "stroke": get_color(el, "stroke"),
        })

    def _handle_path(self, el, ctm, layer):
        stroke = get_color(el, "stroke")
        if not stroke:
            return
        d = el.get("d") or ""
        s = first_xy(d)
        start = None
        if s:
            ax, ay = apply(ctm, s[0], s[1])
            start = (round(ax, 2), round(ay, 2))
        st = style_dict(el)
        self.paths.append({
            "stroke": stroke,
            "start": start,
            "dash": st.get("stroke-dasharray", "none"),
            "width": st.get("stroke-width"),
            "layer": layer,
            "length_hint": len(d),
        })



# ---------------------------------------------------------------------------
# Classification of text strings
# ---------------------------------------------------------------------------

def classify_tag(text):
    """Return (prefix, number, meta) if text matches an ISA tag, else None."""
    t = text.strip()
    # split multi-line; only single-token tags
    if "\n" in t or " " in t and not TAG_RE.match(t):
        # try first token
        tok = re.split(r"[\s\n]", t)[0]
    else:
        tok = t
    m = TAG_RE.match(tok)
    if not m:
        return None
    prefix, number = m.group(1), m.group(2)
    if prefix not in ISA_PREFIX:
        return None
    meaning, variable, role = ISA_PREFIX[prefix]
    return {
        "tag": tok,
        "prefix": prefix,
        "number": number,
        "meaning": meaning,
        "variable": variable,
        "role": role,
        "is_safety": prefix in SAFETY_PREFIXES,
    }


# Equipment label patterns (non-instrument identifiers)
EQUIP_PATTERNS = [
    (re.compile(r"^CAV[\.\- ]?[0-9A-Bx]+$", re.I), "Cavity"),
    (re.compile(r"^CPLR[\.\- ]?[0-9A-Bx]+$", re.I), "Coupler"),
    (re.compile(r"^HX[0-9]+$"), "Heat Exchanger"),
    (re.compile(r"^V[0-9]{3}$"), "Vessel / Valve body"),
    (re.compile(r"^TUN[\.\- ]?[A-B/]+$", re.I), "Tuner"),
    (re.compile(r"^CWT[\.\- ]?[A-B/]+$", re.I), "Cooling Water Tank"),
    (re.compile(r"^RAD$", re.I), "Radiation shield"),
    (re.compile(r"^K[0-9]+$"), "Connector/Coupler node"),
    (re.compile(r"^MV[0-9]+$"), "Manual valve node"),
    (re.compile(r"^TP#?[0-9]+$"), "Terminal Point"),
    (re.compile(r"^PICKUP[\-0-9]+$", re.I), "Pickup antenna"),
    (re.compile(r"^J[0-9]{3}$"), "Pumping system"),
    (re.compile(r"^RD[0-9]{3}$"), "Rupture disc"),
]


def classify_equipment(text):
    t = text.strip()
    for pat, kind in EQUIP_PATTERNS:
        if pat.match(t):
            return kind
    return None


# Temperature / pressure value patterns in annotation text
TEMP_RE = re.compile(r"(\d+\.?\d*)\s*[-–]?\s*(\d+\.?\d*)?\s*K\b")
PRES_RE = re.compile(r"(\d+\.?\d*)\s*(mbar|bar(?:\(g\)|a|g)?)\b", re.I)


def extract_measurements(text):
    temps = [m.group(0).strip() for m in TEMP_RE.finditer(text)]
    pres = [m.group(0).strip() for m in PRES_RE.finditer(text)]
    return temps, pres


# ---------------------------------------------------------------------------
# Build segmentation outputs for a single model
# ---------------------------------------------------------------------------

def segment_model(model):
    out = {
        "file": os.path.basename(model.path),
        "key": model.key,
        "instruments": [],
        "equipment": [],
        "temperature_points": [],
        "pressure_points": [],
        "safety_devices": [],
        "vacuum_barriers": [],
        "process_line_segments": defaultdict(list),
        "color_groups": defaultdict(int),
        "layers": [],
    }

    # --- text-driven classification (token / tspan level) ---
    seen_tag_keys = set()
    for t in model.texts:
        layer = t["layer"]
        # 1) classify each tspan token as a potential instrument/equipment tag
        token_was_tag = False
        for tok in t.get("tokens", []):
            toktxt = tok["text"]
            tag = classify_tag(toktxt)
            if tag:
                token_was_tag = True
                rec = {**tag, "x": tok["x"], "y": tok["y"], "layer": layer}
                # de-duplicate identical tag at identical location
                key = (tag["tag"], tok["x"], tok["y"])
                if key in seen_tag_keys:
                    continue
                seen_tag_keys.add(key)
                out["instruments"].append(rec)
                if tag["variable"] == "temperature":
                    out["temperature_points"].append(rec)
                if tag["variable"] == "pressure":
                    out["pressure_points"].append(rec)
                if tag["is_safety"]:
                    out["safety_devices"].append(rec)
                continue
            eq = classify_equipment(toktxt)
            if eq:
                out["equipment"].append({
                    "label": toktxt, "kind": eq,
                    "x": tok["x"], "y": tok["y"], "layer": layer})

        # 2) annotation-level measurements + barrier text on the full string
        txt = t["text"]
        temps, pres = extract_measurements(txt)
        for v in temps:
            out["temperature_points"].append({
                "tag": None, "value": v, "source_text": txt,
                "x": t["x"], "y": t["y"], "layer": layer, "variable": "temperature"})
        for v in pres:
            out["pressure_points"].append({
                "tag": None, "value": v, "source_text": txt,
                "x": t["x"], "y": t["y"], "layer": layer, "variable": "pressure"})
        if re.search(r"vacuum\s*barrier", txt, re.I):
            out["vacuum_barriers"].append({
                "type": "label", "text": txt,
                "x": t["x"], "y": t["y"], "layer": layer})

    # --- process line segments by color ---
    for p in model.paths:
        col = p["stroke"]
        out["color_groups"][col] += 1
        # map color to line class
        cls = None
        for k, v in LINE_CLASSES.items():
            if v["color"] == col:
                cls = k
                break
        if cls:
            out["process_line_segments"][cls].append({
                "start": p["start"], "layer": p["layer"],
                "dash": p["dash"], "width": p["width"]})
        elif col == "#00ff00":
            out["process_line_segments"]["WATER"].append({
                "start": p["start"], "layer": p["layer"],
                "dash": p["dash"], "width": p["width"]})

    # --- vacuum barriers from dashed boundaries + INVAC/VB layers ---
    for p in model.paths:
        lyr = (p["layer"] or "")
        dashed = p["dash"] not in (None, "none", "")
        if dashed and re.search(r"vac|invac|barrier|qvb", lyr, re.I):
            out["vacuum_barriers"].append({
                "type": "dashed-boundary", "start": p["start"],
                "layer": lyr, "dash": p["dash"]})

    # --- instrument bubbles (sensors) cross-reference ---
    out["instrument_bubbles"] = len(model.bubbles)

    # --- layers ---
    layer_counter = Counter(t["layer"] for t in model.texts)
    seen = set()
    for ly in model.layers:
        lbl = ly["label"] or ly["id"]
        if lbl in seen:
            continue
        seen.add(lbl)
        out["layers"].append({
            "id": ly["id"], "label": ly["label"],
            "depth": ly["depth"],
            "text_count": layer_counter.get(lbl, 0)})

    # convert defaultdicts
    out["process_line_segments"] = dict(out["process_line_segments"])
    out["color_groups"] = dict(out["color_groups"])
    return out


# ---------------------------------------------------------------------------
# CSV writers
# ---------------------------------------------------------------------------

def write_csv(path, rows, fields):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def dump_outputs(key, seg):
    base = os.path.join(DATA_DIR, key)

    # JSON master per file
    with open(base + "_segmentation.json", "w") as f:
        json.dump(seg, f, indent=2)

    # instruments CSV
    write_csv(base + "_instruments.csv", seg["instruments"],
              ["tag", "prefix", "number", "meaning", "variable", "role",
               "is_safety", "x", "y", "layer"])
    # equipment CSV
    write_csv(base + "_equipment.csv", seg["equipment"],
              ["label", "kind", "x", "y", "layer"])
    # temperature points
    write_csv(base + "_temperature_points.csv", seg["temperature_points"],
              ["tag", "value", "meaning", "x", "y", "layer", "source_text"])
    # pressure points
    write_csv(base + "_pressure_points.csv", seg["pressure_points"],
              ["tag", "value", "meaning", "x", "y", "layer", "source_text"])
    # safety devices
    write_csv(base + "_safety_devices.csv", seg["safety_devices"],
              ["tag", "prefix", "meaning", "x", "y", "layer"])
    # vacuum barriers
    write_csv(base + "_vacuum_barriers.csv", seg["vacuum_barriers"],
              ["type", "text", "layer", "dash", "x", "y", "start"])
    # process line segments (flatten)
    pls_rows = []
    for cls, segs in seg["process_line_segments"].items():
        for s in segs:
            pls_rows.append({"line_class": cls, **s})
    write_csv(base + "_process_lines.csv", pls_rows,
              ["line_class", "start", "layer", "dash", "width"])
    # color groups
    cg_rows = []
    for col, cnt in sorted(seg["color_groups"].items(), key=lambda x: -x[1]):
        meaning = COLOR_MEANINGS.get(col, ("(unmapped)", "", "low"))
        cg_rows.append({"color": col, "count": cnt,
                        "group": meaning[0], "meaning": meaning[1],
                        "confidence": meaning[2]})
    write_csv(base + "_color_groups.csv", cg_rows,
              ["color", "count", "group", "meaning", "confidence"])
    # layers
    write_csv(base + "_layers.csv", seg["layers"],
              ["id", "label", "depth", "text_count"])
    return base


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    summary = {}
    all_segs = {}
    for key, fname in SVG_FILES.items():
        path = os.path.join(SRC_DIR, fname)
        if not os.path.exists(path):
            print("MISSING:", path)
            continue
        print(f"\n=== Parsing {key}: {fname} ===")
        model = SvgModel(key, path)
        seg = segment_model(model)
        all_segs[key] = seg
        dump_outputs(key, seg)

        # per-file color counter from full walk (more complete than path-only)
        full_colors = []
        for col, cnt in model.color_counter.most_common():
            meaning = COLOR_MEANINGS.get(col, ("(unmapped)", "", "low"))
            full_colors.append({"color": col, "count": cnt,
                                "group": meaning[0], "meaning": meaning[1],
                                "confidence": meaning[2]})
        write_csv(os.path.join(DATA_DIR, key + "_color_palette_full.csv"),
                  full_colors, ["color", "count", "group", "meaning", "confidence"])

        summary[key] = {
            "file": fname,
            "texts": len(model.texts),
            "instruments": len(seg["instruments"]),
            "unique_instrument_tags": len({i["tag"] for i in seg["instruments"]}),
            "equipment": len(seg["equipment"]),
            "temperature_points": len(seg["temperature_points"]),
            "pressure_points": len(seg["pressure_points"]),
            "safety_devices": len(seg["safety_devices"]),
            "vacuum_barriers": len(seg["vacuum_barriers"]),
            "instrument_bubbles": seg["instrument_bubbles"],
            "process_line_classes": {k: len(v) for k, v in seg["process_line_segments"].items()},
            "unique_colors": len(model.color_counter),
            "layers": len(seg["layers"]),
        }
        print(json.dumps(summary[key], indent=2))

    with open(os.path.join(DATA_DIR, "_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    with open(os.path.join(DATA_DIR, "_all_segmentation.json"), "w") as f:
        json.dump(all_segs, f, indent=2)
    print("\nDone. Outputs in", DATA_DIR)
    return summary, all_segs


if __name__ == "__main__":
    main()
