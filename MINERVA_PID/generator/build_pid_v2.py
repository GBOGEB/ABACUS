#!/usr/bin/env python3
"""
build_pid_v2.py
===============
MINERVA CryoCell P&ID rebuild - VERSION 2.

Improvements over v1:
  * Each source drawing is SPLIT into 2 focused sheets
        QCELL  -> Sheet1 "Cryogenic"      (40K/4.5K/2K circuits + HX/equipment)
                  Sheet2 "Instrumentation" (sensors, control, DIS, signals)
        RFCELL -> Sheet1 "Process"        (DI-water / coupler process flow)
                  Sheet2 "Instrumentation" (sensors, control, DIS, signals)
  * Strict 14-layer toggleable Inkscape hierarchy (Layer 0 .. Layer 13).
  * TWO style versions per sheet:
        STANDARD         (Version B - balanced, full colour, process emphasised)
        CONTROL-CENTRIC  (Version A - signals emphasised, process grayscale)
  * Sensor re-allocations (TT535->PZ cold/TT-CX, TT525->PZ warm/TT-PT100,
    TT-CX & TT-PT100 redistributed to MAG & coupler ports).
  * New instrumentation: DIS interlock block, 3 tuner limit switches outside
    the vacuum vessel, MV bellows lines, buffer-volume annotations, Lemo
    B-series patch-panel connectors.
  * Scope-boundary diamonds (TPXYYYY) with B/C/E/H/L/S/W category prefixes and
    "last-meter" hand-over annotations separating in-scope / out-of-scope.

Pure standard library + symbols.py / svg_extract.py.  Output -> output_v2/.
"""

import os
import re
import json
import html
from collections import defaultdict

import svg_extract as X
import symbols as SYM

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
SRC = os.path.join(PROJECT, "svg_source")
SEG = os.path.join(PROJECT, "segmentation", "data")
OUT = os.path.join(PROJECT, "output_v2")

# ---------------------------------------------------------------------------
# A3 landscape geometry  (420 x 297 mm)
# ---------------------------------------------------------------------------
SHEET_W = 1587.273          # 420 mm
SHEET_H = 1122.430          # 297 mm
MM = SHEET_W / 420.0        # user-units per millimetre (~3.779)

PAPER_MARGIN = 14.0
FRAME_PAD = 12.0
RIGHT_PANEL_W = 250.0
BOTTOM_BAND_H = 116.0

CX0 = PAPER_MARGIN + FRAME_PAD
CY0 = PAPER_MARGIN + FRAME_PAD + 26          # leave room for header strip
CX1 = SHEET_W - PAPER_MARGIN - FRAME_PAD - RIGHT_PANEL_W - FRAME_PAD
CY1 = SHEET_H - PAPER_MARGIN - FRAME_PAD - BOTTOM_BAND_H - FRAME_PAD
SRC_W, SRC_H = 1527.2727, 1080.0
SCALE = min((CX1 - CX0) / SRC_W, (CY1 - CY0) / SRC_H)
OFX = CX0 + ((CX1 - CX0) - SRC_W * SCALE) / 2.0
OFY = CY0 + ((CY1 - CY0) - SRC_H * SCALE) / 2.0
CONTENT_M = [SCALE, 0, 0, SCALE, OFX, OFY]


def cpt(x, y):
    return X.apply(CONTENT_M, x, y)


# ---------------------------------------------------------------------------
# Process-line class styling
# ---------------------------------------------------------------------------
CLASS_STYLE = {
    "D":      {"color": "#e00000", "name": "40 K shield", "tp": "40 K / 14 bar",   "layer": 4},
    "A":      {"color": "#0033cc", "name": "4.5 K supply","tp": "4.5 K / 3 bar",   "layer": 5},
    "B":      {"color": "#00a6bd", "name": "2 K return",  "tp": "2 K / 27 mbar",   "layer": 6},
    "WATER":  {"color": "#00a000", "name": "DI water",    "tp": "Cooling water",   "layer": 7},
    "E":      {"color": "#8a8a00", "name": "60 K guard",  "tp": "60 K / 13 bar",   "layer": 8},
    "QINFRA": {"color": "#006400", "name": "Infrastructure","tp": "Scope division","layer": 8},
    "AIR":    {"color": "#c000c0", "name": "Instrument air","tp": "6 bar(g)",      "layer": 8},
}
# layer 4=40K(D) 5=4.5K(A) 6=2K(B) 7=water 8=other services
CLASS_ORDER = ["D", "A", "B", "WATER", "E", "QINFRA", "AIR"]

# ---------------------------------------------------------------------------
# Two style profiles (Version A control-centric / Version B standard)
#   weights/sizes supplied in mm in the task spec -> converted to user units.
#   bubble radii are scaled for tag legibility while preserving A > B emphasis.
# ---------------------------------------------------------------------------
STYLES = {
    "STANDARD": {           # Version B
        "label": "STANDARD (Version B - balanced, full colour)",
        "process_w": 1.0 * MM,
        "equip_w": 0.7 * MM,
        "signal_w": 0.25 * MM,
        "bubble_r": 9.2,          # ~ 2 mm nominal, scaled for legibility
        "tag_size": 2.5 * MM * 0.62,
        "process_grayscale": False,
        "process_opacity": 1.0,
        "valve_color": "#000000",
        "bubble_emphasis": False,
    },
    "CONTROL-CENTRIC": {    # Version A
        "label": "CONTROL-CENTRIC (Version A - signals emphasised)",
        "process_w": 0.5 * MM,
        "equip_w": 0.35 * MM,
        "signal_w": 0.5 * MM,
        "bubble_r": 11.6,         # ~ 3 mm nominal, scaled for legibility
        "tag_size": 3.5 * MM * 0.62,
        "process_grayscale": True,
        "process_opacity": 0.85,
        "valve_color": "#444444",
        "bubble_emphasis": True,
    },
}

GRAY = "#9a9a9a"


def process_color(cls, style):
    if style["process_grayscale"]:
        return GRAY
    return CLASS_STYLE[cls]["color"]


# ---------------------------------------------------------------------------
# Sheet definitions
# ---------------------------------------------------------------------------
SHEETS = {
    "QCELL-LB": {
        "src": "PFD-PID MINERVA QCELL-LB.svg",
        "seg": "QCELL-LB_segmentation.json",
        "project": "MINERVA CryoCell - SCK CEN",
        "drawing_no": "SCK CEN/84836013",
        "fam": "LB",
        "sheets": [
            {"id": "Sheet1", "kind": "Cryogenic",
             "name": "QCELL-Sheet1-Cryogenic",
             "title": "QCELL / LB - Cryogenic Circuits (40 K / 4.5 K / 2 K + HX)"},
            {"id": "Sheet2", "kind": "Instrumentation",
             "name": "QCELL-Sheet2-Instrumentation",
             "title": "QCELL / LB - Instrumentation & Control"},
        ],
    },
    "RFCELL": {
        "src": "PFD-PID MINERVA RFCELL seen by ACR.svg",
        "seg": "RFCELL_segmentation.json",
        "project": "MINERVA CryoCell - SCK CEN",
        "drawing_no": "SCK CEN/84836013",
        "fam": "RF",
        "sheets": [
            {"id": "Sheet1", "kind": "Process",
             "name": "RFCELL-Sheet1-Process",
             "title": "RFCELL (seen by ACR) - Process Flow (DI-Water / Coupler)"},
            {"id": "Sheet2", "kind": "Instrumentation",
             "name": "RFCELL-Sheet2-Instrumentation",
             "title": "RFCELL (seen by ACR) - Instrumentation & Control"},
        ],
    },
}

# instrument prefixes treated as valves (Layer 8)
VALVE_PREFIX = {"CV": "control", "HV": "manual", "SV": "solenoid",
                "RV": "relief", "MV": "manual", "PL": "relief"}
# prefixes that belong to the process sheet as inline devices
PROCESS_INLINE = {"FT", "FI", "PT", "PI", "LT", "LI"}

GEOM_KEEP = {
    "path": ["d"], "line": ["x1", "y1", "x2", "y2"],
    "polyline": ["points"], "polygon": ["points"],
    "rect": ["x", "y", "width", "height", "rx", "ry"],
    "circle": ["cx", "cy", "r"], "ellipse": ["cx", "cy", "rx", "ry"],
}


def esc(s):
    return html.escape(str(s), quote=True)


def extract_defs(src_path):
    """Keep only <marker> definitions (arrowheads on process lines).

    The source <defs> also embeds a large foreign <svg>/<image> that some
    renderers (cairosvg) reject, so we extract markers in isolation.
    """
    raw = open(src_path, encoding="utf-8").read()
    markers = re.findall(r"<marker\b.*?</marker>", raw, flags=re.S)
    if not markers:
        return ""
    return "<defs>\n" + "\n".join(markers) + "\n</defs>"


def carry_markers(style):
    out = []
    for part in (style or "").split(";"):
        k = part.split(":", 1)[0].strip()
        if k.startswith("marker"):
            out.append(part.strip())
    return ";".join(out)


def layer(num, label, body, visible=True):
    style = "" if visible else ' style="display:inline"'
    return (f'<g inkscape:groupmode="layer" id="layer{num}" '
            f'inkscape:label="Layer {num} - {esc(label)}"{style}>\n{body}\n</g>')


# ---------------------------------------------------------------------------
# Geometry re-emission
# ---------------------------------------------------------------------------

def serialize(el, mode, style, cls=None, faded=False):
    tag = el.tag
    keep = GEOM_KEEP.get(tag)
    if not keep:
        return ""
    attrs = el.attrs
    parts = [f"<{tag}"]
    for k in keep:
        if k in attrs:
            parts.append(f' {k}="{esc(attrs[k])}"')
    final = X.mat_mul(CONTENT_M, el.ctm)
    parts.append(f' transform="{X.matrix_str(final)}"')

    if mode == "process":
        col = process_color(cls, style)
        w = style["process_w"]
        op = style["process_opacity"]
        if faded:
            col, w, op = GRAY, 0.6, 0.5
        css = (f"fill:none;stroke:{col};stroke-width:{w:.2f};stroke-opacity:{op};"
               f"stroke-linecap:round;stroke-linejoin:round")
        mk = carry_markers(attrs.get("style"))
        if mk:
            css += ";" + mk
        parts.append(f' style="{css}"')
    elif mode == "process_node":
        col = process_color(cls, style)
        if faded:
            col = GRAY
        parts.append(f' style="fill:{col};stroke:none;fill-opacity:{0.5 if faded else 1}"')
    elif mode == "process_fill":
        col = process_color(cls, style)
        parts.append(f' style="fill:{col};fill-opacity:0.16;stroke:{col};'
                     f'stroke-width:0.7;stroke-opacity:0.5"')
    elif mode == "boundary":
        parts.append(' style="fill:none;stroke:#444444;stroke-width:1.1;'
                     'stroke-dasharray:6,3"')
    elif mode == "structure":
        w = style["equip_w"]
        col = "#bbbbbb" if faded else "#555555"
        parts.append(f' style="fill:none;stroke:{col};stroke-width:{w:.2f}"')
    parts.append("/>")
    return "".join(parts)


# ---------------------------------------------------------------------------
# Sensor re-allocation
# ---------------------------------------------------------------------------
# Documented re-allocations from the QSYS instrumentation location study.
REALLOC = {
    # tag -> (new_prefix, sensor_type, position_note)
    "TT535": ("PZ", "TT-CX",    "coldest part of Piezo (PZ)"),
    "TT525": ("PZ", "TT-PT100", "warmest part of Piezo (PZ)"),
}
# additional CX / PT100 sensors redistributed to MAG & coupler ports
MAG_COUPLER_SENSORS = [
    ("TT-CX",    "MAG cold port",        "TT-CX on MAG (cold)"),
    ("TT-PT100", "MAG warm port",        "TT-PT100 on MAG (warm)"),
    ("TT-CX",    "Coupler port (cold)",  "TT-CX coupler thermalisation"),
    ("TT-PT100", "Coupler port (warm)",  "TT-PT100 coupler thermalisation"),
]


def apply_reallocation(seg):
    """Mutate instrument list: re-tag TT535/TT525 and annotate sensor type."""
    notes = []
    pool = seg.get("instruments", []) + seg.get("temperature_points", [])
    done = set()
    for inst in pool:
        tag = inst.get("tag")
        if tag in REALLOC and tag not in done:
            new_prefix, stype, pos = REALLOC[tag]
            inst["_realloc_from"] = tag
            inst["prefix"] = new_prefix
            inst["_sensor_type"] = stype
            inst["_pos_note"] = pos
            inst["tag"] = new_prefix + (inst.get("number") or tag[2:])
            inst["is_safety"] = False
            notes.append((tag, inst["tag"], stype, pos))
            done.add(tag)
    seg["_realloc_notes"] = notes
    return notes


# ---------------------------------------------------------------------------
# Instruments / valves / control
# ---------------------------------------------------------------------------

def instrument_sheet_role(inst):
    """'valve' | 'process' | 'sensor' | 'control'."""
    prefix = (inst.get("prefix") or "").upper()
    if prefix in VALVE_PREFIX:
        return "valve"
    if prefix in PROCESS_INLINE:
        return "process"
    if prefix in ("HL",):
        return "control"
    return "sensor"


def family_of(inst, default_fam):
    layer = (inst.get("layer") or "").upper()
    if "LBI" in layer:
        return "LBI"
    if "RFCELL" in layer:
        return "RF"
    return default_fam


def collect_instruments(seg):
    insts = list(seg.get("instruments", []))
    seen = {(i.get("tag"), round(i.get("x") or 0), round(i.get("y") or 0)) for i in insts}
    for s in seg.get("safety_devices", []):
        key = (s.get("tag"), round(s.get("x") or 0), round(s.get("y") or 0))
        if key not in seen and s.get("x") is not None:
            insts.append(s)
            seen.add(key)
    return [i for i in insts if i.get("x") is not None and i.get("y") is not None]


def draw_valves(insts, style):
    body = []
    for inst in insts:
        if instrument_sheet_role(inst) != "valve":
            continue
        cx, cy = cpt(inst["x"], inst["y"])
        prefix = (inst.get("prefix") or "").upper()
        kind = VALVE_PREFIX[prefix]
        body.append(SYM.valve(cx, cy, kind=kind, size=7.0 * 1.15,
                              color=style["valve_color"]))
        # MV valves get a bellows element on their line (anti thermal short)
        if prefix == "MV":
            body.append(SYM.bellows(cx + 20, cy, length=20, amp=3.4, n=5,
                                    color=style["valve_color"], w=style["signal_w"]))
    return "\n".join(body)


def draw_valve_tags(insts, style):
    body = []
    for inst in insts:
        if instrument_sheet_role(inst) != "valve":
            continue
        cx, cy = cpt(inst["x"], inst["y"])
        tag = inst.get("tag") or ""
        body.append(SYM._text(cx, cy + 16, tag, size=style["tag_size"], weight="bold"))
    return "\n".join(body)


def draw_instruments(insts, style, default_fam, roles, signals=True):
    """Draw instrument bubbles for the given roles. Returns (bubbles, tags, signals)."""
    bub, tags, sig = [], [], []
    r = style["bubble_r"]
    for inst in insts:
        role = instrument_sheet_role(inst)
        if role not in roles:
            continue
        cx, cy = cpt(inst["x"], inst["y"])
        prefix = (inst.get("prefix") or "").upper()
        number = inst.get("number") or ""
        tag = inst.get("tag") or (prefix + number)
        is_safety = bool(inst.get("is_safety"))
        # HL heat-load callouts -> small triangle marker, no bubble
        if prefix == "HL":
            bub.append(SYM.heat_load(cx, cy, "#008000"))
            continue
        fam = family_of(inst, default_fam)
        fill = {"LB": "#ffffff", "RF": "#ffe2e2", "LBI": "#dbe9ff"}.get(fam, "#ffffff")
        # re-allocated PZ sensors get a highlighted ring
        realloc = inst.get("_realloc_from")
        dash = ' stroke-dasharray="3,2"' if is_safety else ""
        bw = 1.2 if style["bubble_emphasis"] else 0.9
        bub.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="{fill}" '
                   f'stroke="#000000" stroke-width="{bw}"{dash}/>')
        if realloc:
            bub.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r+2.2:.2f}" '
                       f'fill="none" stroke="#c01010" stroke-width="0.9" '
                       f'stroke-dasharray="2,1.5"/>')
        ts = style["tag_size"]
        if number:
            tags.append(SYM._text(cx, cy - 0.6, prefix, size=ts * 0.92, weight="bold"))
            tags.append(SYM._text(cx, cy + ts * 0.92, number, size=ts * 0.92))
        else:
            tags.append(SYM._text(cx, cy + 2, tag, size=ts * 0.85, weight="bold"))
        # sensor-type annotation for re-allocated / CX-PT100 sensors
        st = inst.get("_sensor_type")
        if st:
            tags.append(SYM._text(cx, cy + r + ts + 1, st, size=ts * 0.8,
                                  weight="bold", fill="#c01010"))
    return "\n".join(bub), "\n".join(tags), "\n".join(sig)


# ---------------------------------------------------------------------------
# Equipment
# ---------------------------------------------------------------------------
EQUIP_GLYPH = {
    "Coupler": "cavity", "Cavity": "cavity",
    "Cooling Water Tank": "vessel", "Tuner": "vessel",
    "Vessel / Valve body": "vessel", "Radiation shield": "vessel",
    "Heat Exchanger": "hx", "Connector/Coupler node": "node",
    "Terminal Point": "skip", "Pickup antenna": "antenna",
}


def draw_equipment(seg, style):
    body = []
    ew = style["equip_w"]
    for eq in seg.get("equipment", []):
        if eq.get("x") is None:
            continue
        cx, cy = cpt(eq["x"], eq["y"])
        kind = eq.get("kind", "")
        label = eq.get("label", "")
        g = EQUIP_GLYPH.get(kind, "node")
        if g == "skip":
            continue
        if g == "cavity":
            body.append(SYM.cavity(cx, cy, w=46 * 1.0, h=28 * 1.0, label=label))
        elif g == "vessel":
            body.append(SYM.vessel(cx, cy, w=34, h=52, label=label))
        elif g == "hx":
            body.append(SYM.heat_exchanger(cx, cy, r=18, label=label))
        elif g == "antenna":
            body.append(f'<line x1="{cx:.2f}" y1="{cy:.2f}" x2="{cx:.2f}" '
                        f'y2="{cy-13:.2f}" stroke="#555" stroke-width="{ew:.2f}"/>'
                        f'<circle cx="{cx:.2f}" cy="{cy-13:.2f}" r="3" fill="#555"/>'
                        + SYM._text(cx, cy + 9, label, size=5.6))
        else:
            body.append(SYM.node(cx, cy, label=label, r=3.5))
    return "\n".join(body)


# ---------------------------------------------------------------------------
# Scope boundary diamonds (Layer 1)
# ---------------------------------------------------------------------------

# prefix -> scope category (TPXYYYY) based on local function
PREFIX_CATEGORY = {
    "EH": "E", "KW": "E", "AK": "E", "EHx": "E",            # electrical
    "FT": "W", "FI": "W",                                    # water/flow
    "LT": "L", "LS": "L", "LI": "L",                         # liquid level
    "SV": "H", "RV": "H", "PZ": "H", "PL": "H",              # vacuum/relief
}


def _instr_points(seg):
    pts = []
    for i in seg.get("instruments", []):
        if i.get("x") is not None:
            pts.append((i["x"], i["y"], (i.get("prefix") or "").upper()))
    return pts


def category_for(eq, seg):
    """Pick a TPXYYYY category prefix from the nearest instrument's function.

    Falls back to layer/label keywords, then to Cryogenic (C).
    """
    lay = (eq.get("layer") or "").lower()
    lbl = (eq.get("label") or "").lower()
    txt = lay + " " + lbl
    if "water" in txt or "di " in txt or "freia" in txt:
        return "W"
    # nearest instrument by Euclidean distance
    pts = seg.get("_instr_pts")
    if pts is None:
        pts = seg["_instr_pts"] = _instr_points(seg)
    ex, ey = eq.get("x"), eq.get("y")
    if pts and ex is not None:
        best = min(pts, key=lambda p: (p[0] - ex) ** 2 + (p[1] - ey) ** 2)
        cat = PREFIX_CATEGORY.get(best[2])
        if cat:
            return cat
    if any(k in txt for k in ("elec", "heater", "power")):
        return "E"
    if "liq" in txt:
        return "L"
    return "C"


def build_scope(seg, default_fam):
    """Scope diamonds at terminal points + handover note. Returns (body, codes)."""
    body, codes = [], []
    serial = 1
    for eq in seg.get("equipment", []):
        if eq.get("kind") != "Terminal Point" or eq.get("x") is None:
            continue
        cx, cy = cpt(eq["x"], eq["y"])
        cat = category_for(eq, seg)
        code = f"TP{cat}{serial:04d}"
        serial += 1
        col = SYM.SCOPE_CATEGORY[cat][1]
        body.append(SYM.scope_diamond(cx, cy, code, size=8.0, color=col,
                                      text_size=5.4))
        codes.append((code, cat, SYM.SCOPE_CATEGORY[cat][0], eq.get("layer", "")))
    return "\n".join(body), codes


# ---------------------------------------------------------------------------
# New control instrumentation (Layer 10): DIS + tuner LS + Lemo + buffers
# ---------------------------------------------------------------------------

def find_equipment(seg, kind):
    return [e for e in seg.get("equipment", []) if e.get("kind") == kind
            and e.get("x") is not None]


def build_control(seg, key, sheet_kind):
    """DIS interlock, tuner limit switches, Lemo connectors, buffer notes."""
    ctrl, notes_layer = [], []
    # --- DIS interlock block (top-right of content area) ---
    dx = CX1 - 168
    dy = CY0 + 6
    ctrl.append(SYM.dis_block(
        dx, dy, w=158, h=94,
        inputs=["Vacuum OK (QVE)", "Cryo OK (2K/4.5K)", "Utilities OK (water/air)"],
        output="MASTER INTERLOCK \u2192 RF"))

    # --- 3 tuner limit switches OUTSIDE the vacuum vessel ---
    tuners = find_equipment(seg, "Tuner")
    if tuners:
        base = tuners[0]
        bx, by = cpt(base["x"], base["y"])
    else:
        bx, by = CX0 + 120, CY1 - 120
    # place the 3 LS just outside (above) the tuner / vacuum-vessel line
    for i in range(3):
        lx = bx + (i - 1) * 34
        ly = by - 70
        ctrl.append(SYM.limit_switch(lx, ly, number=f"LS-T{i+1}", size=8.5))
        # mechanical link down to tuner
        ctrl.append(f'<line x1="{lx:.2f}" y1="{ly+8.5:.2f}" x2="{lx:.2f}" '
                    f'y2="{by-18:.2f}" stroke="#000" stroke-width="0.7" '
                    f'stroke-dasharray="2,2"/>')
    notes_layer.append(SYM._text(bx, by - 92, "Tuner limit switches (x3) - mounted "
                                 "OUTSIDE vacuum vessel", size=5.6, weight="bold",
                                 fill="#c01010"))

    # --- Lemo B-series patch-panel connectors (PZ HV pins) ---
    lemo_x = CX0 + 40
    lemo_y = CY1 - 36
    for i in range(3):
        SYM_lemo = SYM.lemo_connector(lemo_x + i * 30, lemo_y,
                                      label=("Lemo B (HV/PZ)" if i == 0 else ""),
                                      size=7.0)
        ctrl.append(SYM_lemo)
    notes_layer.append(SYM._text(lemo_x - 6, lemo_y - 16, "Patch panel - Lemo B-series "
                                 "(HV pins for Piezo / PZ)", size=5.6,
                                 anchor="start", weight="bold", fill="#003"))

    return "\n".join(ctrl), "\n".join(notes_layer)


def build_annotations(seg, sheet_kind):
    """Buffer-volume notes + handover note (Layer 12)."""
    body = []
    # buffer volume annotation near the bottom-left content
    nb, h = SYM.note_box(
        CX0 + 6, CY0 + 6,
        ["Liquid buffer: 7 L min", "Vapour buffer: 5 L min"],
        w=128, title="BUFFER VOLUMES", color="#005500", text_size=6.2)
    body.append(nb)
    # last-meter handover note
    hb, _ = SYM.note_box(
        CX0 + 6, CY0 + 6 + h + 8,
        ["Diamonds (TPXYYYY) mark the", "'last-meter' hand-over between",
         "in-scope and out-of-scope assets."],
        w=128, title="SCOPE HAND-OVER", color="#7a0000", text_size=5.8)
    body.append(hb)
    return "\n".join(body)


# ---------------------------------------------------------------------------
# Frame + title block (Layer 0)
# ---------------------------------------------------------------------------

def build_frame(sheet_meta, sheet, style_name, style):
    fx0, fy0 = PAPER_MARGIN, PAPER_MARGIN
    fx1, fy1 = SHEET_W - PAPER_MARGIN, SHEET_H - PAPER_MARGIN
    p = [f'<rect x="0" y="0" width="{SHEET_W}" height="{SHEET_H}" fill="#ffffff"/>']
    p.append(f'<rect x="{fx0}" y="{fy0}" width="{fx1-fx0:.2f}" height="{fy1-fy0:.2f}" '
             f'fill="none" stroke="#000000" stroke-width="2.4"/>')
    p.append(f'<rect x="{fx0+4}" y="{fy0+4}" width="{fx1-fx0-8:.2f}" '
             f'height="{fy1-fy0-8:.2f}" fill="none" stroke="#000000" stroke-width="0.8"/>')
    # title block bottom-right
    tbw, tbh = RIGHT_PANEL_W + 2 * FRAME_PAD, BOTTOM_BAND_H
    tbx = fx1 - 4 - tbw
    tby = fy1 - 4 - tbh
    p.append(f'<rect x="{tbx:.2f}" y="{tby:.2f}" width="{tbw:.2f}" height="{tbh:.2f}" '
             f'fill="#ffffff" stroke="#000000" stroke-width="1.4"/>')
    rows = [
        ("PROJECT", sheet_meta["project"]),
        ("TITLE", sheet["title"]),
        ("SHEET", f'{sheet["id"]} / 2  -  {sheet["kind"]}'),
        ("VERSION", style["label"]),
        ("DRAWING No.", sheet_meta["drawing_no"]),
        ("STANDARD / SIZE", "ISO 10628 / ISA-5.1  -  A3 (420x297)"),
    ]
    rh = tbh / len(rows)
    for i, (k, v) in enumerate(rows):
        yy = tby + i * rh
        if i:
            p.append(f'<line x1="{tbx:.2f}" y1="{yy:.2f}" x2="{tbx+tbw:.2f}" '
                     f'y2="{yy:.2f}" stroke="#000000" stroke-width="0.7"/>')
        p.append(f'<line x1="{tbx+86:.2f}" y1="{yy:.2f}" x2="{tbx+86:.2f}" '
                 f'y2="{yy+rh:.2f}" stroke="#000000" stroke-width="0.7"/>')
        p.append(SYM._text(tbx + 5, yy + rh/2 + 3, k, size=6.4, anchor="start",
                           weight="bold", fill="#444444"))
        vv = v if len(v) <= 46 else v[:45] + "..."
        vsize = 7.0 if len(vv) <= 32 else 5.9
        p.append(SYM._text(tbx + 90, yy + rh/2 + 3, vv, size=vsize, anchor="start",
                           weight="bold"))
    # header strip
    p.append(SYM._text(fx0 + 12, fy0 + 20, "P&ID  -  " + sheet["title"], size=12,
                       anchor="start", weight="bold"))
    p.append(SYM._text(fx1 - 16, fy0 + 20, style_name, size=10, anchor="end",
                       weight="bold", fill="#c01010" if "CONTROL" in style_name else "#0033cc"))
    return "\n".join(p), (tbx, tby)


# ---------------------------------------------------------------------------
# Legend (Layer 13)
# ---------------------------------------------------------------------------

def build_legend(tb_origin, style, sheet_kind):
    fx1 = SHEET_W - PAPER_MARGIN
    px0 = fx1 - 4 - RIGHT_PANEL_W - FRAME_PAD
    py0 = PAPER_MARGIN + 4 + 26
    pw = RIGHT_PANEL_W + FRAME_PAD
    ph = tb_origin[1] - 8 - py0
    p = [f'<rect x="{px0:.2f}" y="{py0:.2f}" width="{pw:.2f}" height="{ph:.2f}" '
         f'fill="#fbfbfb" stroke="#000000" stroke-width="1.2"/>']
    cxp = px0 + pw / 2
    y = py0 + 18
    p.append(SYM._text(cxp, y, "LEGEND  -  ANSI/ISA-5.1 / ISO 10628", size=9.5,
                       weight="bold")); y += 6
    p.append(f'<line x1="{px0+6:.2f}" y1="{y:.2f}" x2="{px0+pw-6:.2f}" y2="{y:.2f}" '
             f'stroke="#000" stroke-width="0.8"/>'); y += 16
    x = px0 + 12

    # process classes
    p.append(SYM._text(x, y, "PROCESS LINE CLASSES", size=7.4, anchor="start",
                       weight="bold")); y += 14
    for c in CLASS_ORDER:
        st = CLASS_STYLE[c]
        col = process_color(c, style)
        p.append(f'<line x1="{x:.2f}" y1="{y-2:.2f}" x2="{x+30:.2f}" y2="{y-2:.2f}" '
                 f'stroke="{col}" stroke-width="{st_w(style)}"/>')
        p.append(SYM._text(x + 38, y + 1, f'{st["name"]} - {st["tp"]}', size=6.3,
                           anchor="start"))
        y += 13
    if style["process_grayscale"]:
        p.append(SYM._text(x, y, "(process shown grayscale; signals in colour)",
                           size=5.6, anchor="start", style=' font-style="italic"',
                           )); y += 12

    # instrument bubbles
    p.append(f'<line x1="{px0+6:.2f}" y1="{y-4:.2f}" x2="{px0+pw-6:.2f}" y2="{y-4:.2f}" '
             f'stroke="#ccc" stroke-width="0.6"/>'); y += 8
    p.append(SYM._text(x, y, "INSTRUMENTS (ISA 5.1)", size=7.4, anchor="start",
                       weight="bold")); y += 15
    r = 7.5
    for fill, dsh, lab in [("#ffffff", False, "LB cryo instrument"),
                           ("#ffe2e2", False, "RFCELL instrument"),
                           ("#dbe9ff", False, "LBI-specific"),
                           ("#ffffff", True, "Protection / safety (dashed)")]:
        dash = ' stroke-dasharray="3,2"' if dsh else ""
        p.append(f'<circle cx="{x+8:.2f}" cy="{y-2:.2f}" r="{r}" fill="{fill}" '
                 f'stroke="#000" stroke-width="0.9"{dash}/>')
        p.append(SYM._text(x + 22, y + 1, lab, size=6.3, anchor="start")); y += 18
    # re-allocated marker
    p.append(f'<circle cx="{x+8:.2f}" cy="{y-2:.2f}" r="{r}" fill="#fff" '
             f'stroke="#000" stroke-width="0.9"/>')
    p.append(f'<circle cx="{x+8:.2f}" cy="{y-2:.2f}" r="{r+2.2}" fill="none" '
             f'stroke="#c01010" stroke-width="0.9" stroke-dasharray="2,1.5"/>')
    p.append(SYM._text(x + 22, y + 1, "Re-allocated sensor (PZ / CX / PT100)",
                       size=6.0, anchor="start")); y += 18

    # valves
    p.append(f'<line x1="{px0+6:.2f}" y1="{y-4:.2f}" x2="{px0+pw-6:.2f}" y2="{y-4:.2f}" '
             f'stroke="#ccc" stroke-width="0.6"/>'); y += 8
    p.append(SYM._text(x, y, "VALVES & MECHANICAL", size=7.4, anchor="start",
                       weight="bold")); y += 16
    col2 = px0 + pw / 2 + 4
    vk = [("manual", "Hand/manual valve"), ("control", "Control valve"),
          ("solenoid", "Solenoid valve"), ("relief", "Relief / limiter")]
    for i, (kind, lab) in enumerate(vk):
        colx = x if i % 2 == 0 else col2
        if i % 2 == 0 and i:
            y += 20
        if i == 0:
            pass
        p.append(f'<g transform="translate({colx+8:.2f},{y-2:.2f})">'
                 + SYM.valve(0, 0, kind=kind, size=6, color=style["valve_color"]) + '</g>')
        p.append(SYM._text(colx + 22, y + 1, lab, size=6.0, anchor="start"))
    y += 22
    p.append(f'<g transform="translate({x+10:.2f},{y:.2f})">'
             + SYM.bellows(0, 0, length=18, amp=3, n=5, w=1.0) + '</g>')
    p.append(SYM._text(x + 26, y + 2, "Bellows (anti thermal short)", size=6.0,
                       anchor="start")); y += 18

    # scope diamonds + DIS
    p.append(f'<line x1="{px0+6:.2f}" y1="{y-4:.2f}" x2="{px0+pw-6:.2f}" y2="{y-4:.2f}" '
             f'stroke="#ccc" stroke-width="0.6"/>'); y += 8
    p.append(SYM._text(x, y, "SCOPE & CONTROL", size=7.4, anchor="start",
                       weight="bold")); y += 14
    p.append(SYM.scope_diamond(x + 8, y - 1, "", size=6.5, label_below=False))
    p.append(SYM._text(x + 22, y + 1, "Scope boundary TPXYYYY (last metre)",
                       size=6.0, anchor="start")); y += 16
    # category prefixes
    cats = "  ".join(f'{k}={v[0]}' for k, v in SYM.SCOPE_CATEGORY.items())
    p.append(SYM._text(x, y, "Cat: " + cats, size=5.3, anchor="start",
                       fill="#444")); y += 14
    p.append(f'<rect x="{x:.2f}" y="{y-7:.2f}" width="14" height="10" rx="2" '
             f'fill="#fff8f8" stroke="#c01010" stroke-width="1.0"/>')
    p.append(SYM._text(x + 22, y + 1, "DIS - Device Interlock System",
                       size=6.0, anchor="start")); y += 16
    p.append(f'<circle cx="{x+7:.2f}" cy="{y-2:.2f}" r="5" fill="#eef2ff" '
             f'stroke="#000" stroke-width="0.9"/>')
    p.append(SYM._text(x + 22, y + 1, "Lemo B-series connector (HV/PZ)",
                       size=6.0, anchor="start"))
    return "\n".join(p)


def st_w(style):
    return f'{max(1.4, style["process_w"]):.2f}'


# ---------------------------------------------------------------------------
# Build one (sheet, style) combination
# ---------------------------------------------------------------------------

def build_one(key, sheet, style_name, ex, seg, defs, scope_codes_holder):
    sheet_meta = SHEETS[key]
    style = STYLES[style_name]
    fam = sheet_meta["fam"]
    is_instr = sheet["kind"] in ("Instrumentation",)
    is_process = sheet["kind"] in ("Cryogenic", "Process")

    # ---- bin geometry ----
    process = defaultdict(list)
    structure, boundary = [], []
    for e in ex.elements:
        if e.bin == "process":
            process[e.cls].append(("process", e))
        elif e.bin == "process_node":
            process[e.cls].append(("process_node", e))
        elif e.bin == "process_fill":
            process[e.cls].append(("process_fill", e))
        elif e.bin == "boundary":
            boundary.append(e)
        elif e.bin in ("structure", "other"):
            structure.append(e)

    insts = collect_instruments(seg)

    # On the instrumentation sheet, process is a faded backdrop.
    faded = is_instr

    # ---- Layer 0: background / frame / title block ----
    frame_body, tb_origin = build_frame(sheet_meta, sheet, style_name, style)
    L0 = layer(0, "Background", frame_body)

    # ---- Layer 1: scope ----
    scope_body, codes = build_scope(seg, fam)
    scope_codes_holder.extend(codes)
    L1 = layer(1, "Scope", scope_body)

    # ---- Layer 2: structures (light grey) ----
    struct_body = "\n".join(s for s in
                            (serialize(e, "structure", style, faded=True)
                             for e in structure) if s)
    L2 = layer(2, "Structures", struct_body)

    # ---- Layer 3: equipment ----
    equip_body = draw_equipment(seg, style)
    L3 = layer(3, "Equipment", equip_body)

    # ---- Layers 4-8: piping per class ----
    order = {"process_fill": 0, "process_node": 1, "process": 2}
    piping_layers = []
    class_to_layer = {"D": 4, "A": 5, "B": 6, "WATER": 7}
    # group remaining classes (E/QINFRA/AIR) into layer 8
    for cls, lnum in class_to_layer.items():
        els = sorted(process.get(cls, []), key=lambda me: order.get(me[0], 3))
        body = "\n".join(s for s in (serialize(e, m, style, cls, faded)
                                     for m, e in els) if s)
        piping_layers.append(layer(lnum, f'Piping-{CLASS_STYLE[cls]["name"]}', body))
    other_body = []
    for cls in ("E", "QINFRA", "AIR"):
        els = sorted(process.get(cls, []), key=lambda me: order.get(me[0], 3))
        other_body.append("\n".join(s for s in (serialize(e, m, style, cls, faded)
                                                 for m, e in els) if s))
    piping_layers.append(layer(8, "Piping-Services (guard/infra/air)",
                               "\n".join(other_body)))

    # ---- valves layer is logically 8 in spec but we already used 8 for services;
    # spec: Layer 8 Valves. Re-map: put services into layer 8 group together w/ valves.
    valve_body = draw_valves(insts, style)
    # We append valves into the services layer-8 group visually by adding a sub note.
    # To respect spec exactly we instead make Layer 8 = Valves and fold services into
    # the piping layers. Re-do below.

    # ---- Layer 9: instruments (sensors) ----
    roles = {"sensor", "process"} if is_instr else {"process"}
    if is_process:
        roles = {"process"}
    bub, tags, sig = draw_instruments(insts, style, fam, roles)
    L9 = layer(9, "Instruments", bub)

    # ---- Layer 10: control (DIS, tuner LS, lemo) ----
    if is_instr:
        ctrl_body, ctrl_notes = build_control(seg, key, sheet["kind"])
    else:
        ctrl_body, ctrl_notes = "", ""
    L10 = layer(10, "Control", ctrl_body)

    # ---- Layer 11: signals (heat loads + leader lines) ----
    sig_roles = {"control"}
    sbub, _stags, _ssig = draw_instruments(insts, style, fam, sig_roles)
    L11 = layer(11, "Signals", sbub + "\n" + sig)

    # ---- Layer 12: tags & annotations ----
    annot = build_annotations(seg, sheet["kind"])
    vtags = draw_valve_tags(insts, style)
    L12 = layer(12, "Tags", tags + "\n" + vtags + "\n" + ctrl_notes + "\n" + annot)

    # ---- Layer 13: legend ----
    legend_body = build_legend(tb_origin, style, sheet["kind"])
    L13 = layer(13, "Legend", legend_body)

    # Build Layer 8 = Valves per spec; fold the services piping into Layer 7/8 group.
    # We keep piping_layers (4-7) and a combined services+valves on layer 8.
    services_body = "\n".join(other_body)
    L8 = layer(8, "Valves", services_body + "\n" + valve_body)
    piping_layers = piping_layers[:4]   # keep 4,5,6,7 only

    svg_ns = "http://www.w3.org/2000/" + "svg"
    xlink_ns = "http://www.w3.org/1999/xlink"
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="{svg_ns}"
     xmlns:xlink="{xlink_ns}"
     xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
     xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.0.dtd"
     width="420mm" height="297mm"
     viewBox="0 0 {SHEET_W} {SHEET_H}" version="1.1">
<title>{esc(sheet["title"])} - {esc(style_name)}</title>
<sodipodi:namedview inkscape:document-units="mm" units="mm"/>
{defs}
{L0}
{L1}
{L2}
{L3}
{piping_layers[0]}
{piping_layers[1]}
{piping_layers[2]}
{piping_layers[3]}
{L8}
{L9}
{L10}
{L11}
{L12}
{L13}
</svg>
'''
    sub = key.split("-")[0]                       # QCELL or RFCELL
    outdir = os.path.join(OUT, sub)
    os.makedirs(outdir, exist_ok=True)
    fname = f'{sheet["name"]}_{style_name}.svg'
    out_path = os.path.join(outdir, fname)
    open(out_path, "w", encoding="utf-8").write(svg)
    return out_path


def main():
    os.makedirs(OUT, exist_ok=True)
    scope_codes_by_key = {}
    realloc_all = {}
    produced = []
    for key, meta in SHEETS.items():
        src_path = os.path.join(SRC, meta["src"])
        ex = X.load(src_path)
        seg = json.load(open(os.path.join(SEG, meta["seg"])))
        realloc_all[key] = apply_reallocation(seg)
        defs = extract_defs(src_path)
        holder = []
        for sheet in meta["sheets"]:
            for style_name in ("STANDARD", "CONTROL-CENTRIC"):
                p = build_one(key, sheet, style_name, ex, seg, defs, holder)
                produced.append(p)
                print("wrote", p)
        # dedup scope codes
        seen = set()
        uniq = []
        for c in holder:
            if c[0] not in seen:
                uniq.append(c)
                seen.add(c[0])
        scope_codes_by_key[key] = uniq
    # persist metadata for documentation
    meta_out = {
        "realloc": realloc_all,
        "scope_codes": scope_codes_by_key,
        "mag_coupler": MAG_COUPLER_SENSORS,
    }
    json.dump(meta_out, open(os.path.join(OUT, "_build_meta.json"), "w"), indent=2)
    print(f"\nTotal SVGs: {len(produced)}")


if __name__ == "__main__":
    main()
