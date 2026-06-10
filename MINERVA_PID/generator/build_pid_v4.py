#!/usr/bin/env python3
"""
build_pid_v3.py
===============
MINERVA CryoCell P&ID rebuild - VERSION 3 (refinement of v2).

Goals driven by reviewer feedback on v2:
  * SPACE   - replace v2's large right-side legend panel with a compact
              full-width bottom title block (~30 mm) + a *toggleable* legend
              overlay, maximising usable drawing area.
  * LEGIBLE - all text sized in true millimetres for A3 plotting:
              main tags >= 2.5 mm, secondary 2.0 mm, callouts 2.2 mm,
              legend 1.8 mm.
  * PIPING HIERARCHY - per cryogenic class the piping is split into
              PRIMARY (trunk, 1.0 mm) and BRANCH (0.7 mm) sub-layers; the
              secondary (water) circuit is 0.5 mm and out-of-scope services
              are 0.35 mm grey dashed.
  * SIGNALS - instrument signals separated onto three dedicated layers,
              each with a visually distinct 0.25 mm pattern
              (pneumatic = dashed+cross-tick, electric = dotted,
               hydraulic = dash-dot).
  * LAYERS  - new consistent hierarchical Inkscape layer naming
              (00_Background_TitleBlock ... 17_Notes_TOGGLEABLE).
  * MONO    - every sheet also produced in a pure black-and-white `_MONO`
              variant (line-style differentiation, white-fill instruments).
  * VIEWS   - five named default-view presets embedded as <metadata>.

Variants per sheet: STANDARD, STANDARD_MONO, CONTROL-CENTRIC,
CONTROL-CENTRIC_MONO  ->  4 sheets x 4 = 16 SVG.

Pure standard library + symbols.py / svg_extract.py.  Output -> output_v3/.
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
OUT = os.path.join(PROJECT, "output_v4")
VERSION = "v4.0"

# ---------------------------------------------------------------------------
# A3 landscape geometry  (420 x 297 mm)
# ---------------------------------------------------------------------------
SHEET_W = 1587.273          # 420 mm
SHEET_H = 1122.430          # 297 mm
MM = SHEET_W / 420.0        # user-units per millimetre (~3.779)

# millimetre helper -> user units
def mm(v):
    return v * MM

PAPER_MARGIN = mm(6.0)      # paper edge -> outer frame
FRAME_PAD = mm(2.5)         # outer frame -> inner frame
TITLE_H = mm(30.0)          # compact bottom title block band
HEADER_H = mm(7.0)          # thin header strip at top of drawing area

# Content (drawing) area - everything above the title block, full width.
CX0 = PAPER_MARGIN + FRAME_PAD + mm(1.5)
CY0 = PAPER_MARGIN + FRAME_PAD + HEADER_H
CX1 = SHEET_W - PAPER_MARGIN - FRAME_PAD - mm(1.5)
CY1 = SHEET_H - PAPER_MARGIN - FRAME_PAD - TITLE_H - mm(1.5)

SRC_W, SRC_H = 1527.2727, 1080.0
SCALE = min((CX1 - CX0) / SRC_W, (CY1 - CY0) / SRC_H)
OFX = CX0 + ((CX1 - CX0) - SRC_W * SCALE) / 2.0
OFY = CY0 + ((CY1 - CY0) - SRC_H * SCALE) / 2.0
CONTENT_M = [SCALE, 0, 0, SCALE, OFX, OFY]


def cpt(x, y):
    return X.apply(CONTENT_M, x, y)


# ---------------------------------------------------------------------------
# Text sizes (TRUE millimetres -> user units) - A3 legibility minimums
# ---------------------------------------------------------------------------
T_MAIN = mm(2.6)        # main equipment / line tags  (>= 2.5 mm)
T_BUBBLE = mm(2.0)      # instrument bubble text       (secondary 2.0 mm)
T_CALLOUT = mm(2.2)     # line / note callouts         (2.2 mm)
T_LEGEND = mm(1.8)      # legend text                  (1.8 mm)
T_SMALL = mm(1.6)       # fine print (title-block keys)


# ---------------------------------------------------------------------------
# Process-line class styling (cryogenic + services)
# ---------------------------------------------------------------------------
CLASS_STYLE = {
    "D":      {"color": "#e00000", "name": "40 K shield",   "tp": "40 K / 14 bar"},
    "A":      {"color": "#0033cc", "name": "4.5 K supply",  "tp": "4.5 K / 3 bar"},
    "B":      {"color": "#00a6bd", "name": "2 K return",    "tp": "2 K / 27 mbar"},
    "WATER":  {"color": "#00a000", "name": "DI cooling water","tp": "Secondary"},
    "E":      {"color": "#8a8a00", "name": "60 K guard",    "tp": "60 K / 13 bar"},
    "QINFRA": {"color": "#006400", "name": "Infrastructure","tp": "Out of scope"},
    "AIR":    {"color": "#c000c0", "name": "Instrument air","tp": "6 bar(g)"},
}
# cryogenic classes that get a PRIMARY/BRANCH split
CRYO_CLASSES = ["D", "A", "B"]
SECONDARY_CLASSES = ["WATER"]
OUTSIDE_CLASSES = ["E", "QINFRA", "AIR"]

GRAY = "#9a9a9a"
MONO_BLACK = "#000000"

# ---------------------------------------------------------------------------
# Style profiles
# ---------------------------------------------------------------------------
STYLES = {
    "STANDARD": {
        "label": "STANDARD - balanced, full colour, process emphasised",
        "primary_w": mm(1.0),
        "branch_w": mm(0.7),
        "secondary_w": mm(0.5),
        "outside_w": mm(0.35),
        "equip_w": mm(0.5),
        "signal_w": mm(0.25) * 1.0,
        "bubble_r": mm(3.0),
        "process_grayscale": False,
        "process_opacity": 1.0,
        "valve_color": "#000000",
    },
    "CONTROL-CENTRIC": {
        "label": "CONTROL-CENTRIC - signals emphasised, process greyed back",
        "primary_w": mm(0.6),
        "branch_w": mm(0.45),
        "secondary_w": mm(0.4),
        "outside_w": mm(0.3),
        "equip_w": mm(0.35),
        "signal_w": mm(0.4),
        "bubble_r": mm(3.4),
        "process_grayscale": True,
        "process_opacity": 0.8,
        "valve_color": "#444444",
    },
}

# Signal patterns must stay >=0.25 mm but be readable; min 0.9 uu for plot.
def signal_width(style):
    return max(mm(0.25), 0.9)


def process_color(cls, style, mono):
    if mono:
        return MONO_BLACK
    if style["process_grayscale"]:
        return GRAY
    return CLASS_STYLE[cls]["color"]


# ---------------------------------------------------------------------------
# Hierarchical layer names (Phase 2E)
# ---------------------------------------------------------------------------
LAYER_NAMES = [
    "00_Background_TitleBlock",
    "01_Scope_Boundaries",
    "02_Structure_Reference",
    "03_Equipment_Vessels",
    "04A_Piping_PRIMARY_40K",
    "04B_Piping_BRANCHES_40K",
    "05A_Piping_PRIMARY_4p5K",
    "05B_Piping_BRANCHES_4p5K",
    "06A_Piping_PRIMARY_2K",
    "06B_Piping_BRANCHES_2K",
    "07_Piping_SECONDARY_Water",
    "08_Piping_OUTSIDE_SCOPE",
    "09_Valves_Mechanical",
    "08B_Valves_HORIZONTAL_OVERLAY",   # tracked-asset horizontal valve row
    "10_Signals_Pneumatic",
    "11_Signals_Electric",
    "12_Signals_Hydraulic",
    "13_Instruments_Sensors",
    "14_Instruments_Control_DIS",
    "04C_Piping_LINENAMES",            # inline on-line names (mono legibility)
    "02B_TerminalPoints_EDGE",         # AD_01.10 edge terminal points
    "12_Tags_Instruments",             # white-boxed tags, front-most content
    "16_Legend_INTERACTIVE",           # toggleable colour/signal legend
    "17_Notes_TOGGLEABLE",
]

# Layers that are hidden by default (toggleable overlays / alternate views).
HIDDEN_BY_DEFAULT = {
    "08B_Valves_HORIZONTAL_OVERLAY",
    "16_Legend_INTERACTIVE",
    "17_Notes_TOGGLEABLE",
}

CLASS_PRIMARY_LAYER = {"D": "04A_Piping_PRIMARY_40K",
                       "A": "05A_Piping_PRIMARY_4p5K",
                       "B": "06A_Piping_PRIMARY_2K"}
CLASS_BRANCH_LAYER = {"D": "04B_Piping_BRANCHES_40K",
                      "A": "05B_Piping_BRANCHES_4p5K",
                      "B": "06B_Piping_BRANCHES_2K"}

# ---------------------------------------------------------------------------
# Default-view presets (Phase 2G) - layers visible in each named view
# ---------------------------------------------------------------------------
ALL_LAYERS = set(LAYER_NAMES)
# Process piping layers (exclude the horizontal-valve overlay which also starts with 08)
PIPING_LAYERS = {n for n in LAYER_NAMES
                 if n.startswith(("04", "05", "06", "07", "08")) and "Valves" not in n}
SIGNAL_LAYERS = {"10_Signals_Pneumatic", "11_Signals_Electric", "12_Signals_Hydraulic"}
CRYO_PRIMARY = {"04A_Piping_PRIMARY_40K", "05A_Piping_PRIMARY_4p5K",
                "06A_Piping_PRIMARY_2K"}
ALWAYS = {"00_Background_TitleBlock", "01_Scope_Boundaries",
          "03_Equipment_Vessels", "12_Tags_Instruments"}

DEFAULT_VIEWS = {
    "DEFAULT_FULL": sorted(ALL_LAYERS - HIDDEN_BY_DEFAULT),
    "DEFAULT_PROCESS": sorted(ALWAYS | PIPING_LAYERS | {"02_Structure_Reference",
                              "02B_TerminalPoints_EDGE", "04C_Piping_LINENAMES",
                              "09_Valves_Mechanical", "13_Instruments_Sensors"}),
    "DEFAULT_CONTROL": sorted(ALWAYS | SIGNAL_LAYERS |
                              {"13_Instruments_Sensors", "14_Instruments_Control_DIS",
                               "08_Piping_OUTSIDE_SCOPE"}),
    "DEFAULT_MAIN": sorted(ALWAYS | CRYO_PRIMARY |
                           {"07_Piping_SECONDARY_Water", "09_Valves_Mechanical",
                            "04C_Piping_LINENAMES", "02B_TerminalPoints_EDGE",
                            "03_Equipment_Vessels"}),
    "PRINT_MONO": sorted((ALL_LAYERS - HIDDEN_BY_DEFAULT) | {"04C_Piping_LINENAMES"}),
}


# ---------------------------------------------------------------------------
# Sheet definitions
# ---------------------------------------------------------------------------
SHEETS = {
    "QCELL-LB": {
        "src": "PFD-PID MINERVA QCELL-LB.svg",
        "seg": "QCELL-LB_segmentation.json",
        "project": "MINERVA CryoCell - SCK CEN",
        "drawing_no": "=NA.PS01_PFB712",
        "mmd": "411066",
        "fam": "LB",
        "sub": "QCELL",
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
        "drawing_no": "=NA.PS01_PFB713",
        "mmd": "411066",
        "fam": "RF",
        "sub": "RFCELL",
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

# instrument prefixes treated as valves
VALVE_PREFIX = {"CV": "control", "HV": "manual", "SV": "solenoid",
                "RV": "relief", "MV": "manual", "PL": "relief"}
PROCESS_INLINE = {"FT", "FI", "PT", "PI", "LT", "LI"}

# signal classification by instrument prefix
SIGNAL_KIND = {
    "CV": "pneumatic", "SV": "electric",
    "TT": "electric", "TE": "electric", "PT": "electric", "PI": "electric",
    "LT": "electric", "LI": "electric", "LS": "electric", "FT": "electric",
    "FI": "electric", "PZ": "electric", "EH": "electric", "EHx": "electric",
    "SM": "electric", "RS": "electric", "AP": "electric",
    "RV": "hydraulic", "PL": "hydraulic", "HV": "hydraulic", "MV": "hydraulic",
}

GEOM_KEEP = {
    "path": ["d"], "line": ["x1", "y1", "x2", "y2"],
    "polyline": ["points"], "polygon": ["points"],
    "rect": ["x", "y", "width", "height", "rx", "ry"],
    "circle": ["cx", "cy", "r"], "ellipse": ["cx", "cy", "rx", "ry"],
}


def esc(s):
    return html.escape(str(s), quote=True)


def extract_defs(src_path):
    raw = open(src_path, encoding="utf-8").read()
    markers = re.findall(r"<marker\b.*?</marker>", raw, flags=re.S)
    if not markers:
        return ""
    return "<defs>\n" + "\n".join(markers) + "\n</defs>"


def mono_defs(defs):
    """Recolour marker fills/strokes to black for monochrome variants.

    The defs contain only arrowhead / junction-dot markers, so recolouring
    every colour literal to black is exactly what the mono plot needs.
    'none' has no colour literal and is left untouched.
    """
    out = re.sub(r"#[0-9a-fA-F]{3,6}", "#000000", defs)
    out = re.sub(r"rgb\([^)]*\)", "#000000", out)
    return out


def carry_markers(style):
    out = []
    for part in (style or "").split(";"):
        k = part.split(":", 1)[0].strip()
        if k.startswith("marker"):
            out.append(part.strip())
    return ";".join(out)


def layer(name, body, visible=True):
    disp = "inline" if visible else "none"
    return (f'<g inkscape:groupmode="layer" id="{name}" '
            f'inkscape:label="{esc(name)}" style="display:{disp}">\n{body}\n</g>')


# ---------------------------------------------------------------------------
# Geometry metric (PRIMARY vs BRANCH heuristic)
# ---------------------------------------------------------------------------
_NUM = re.compile(r"-?\d+\.?\d*(?:[eE]-?\d+)?")


def elem_metric(e):
    """Approximate on-sheet length of an element (used to rank trunk vs branch)."""
    a = e.attrs
    sc = X.avg_scale(e.ctm)
    if e.tag == "line":
        try:
            dx = float(a.get("x2", 0)) - float(a.get("x1", 0))
            dy = float(a.get("y2", 0)) - float(a.get("y1", 0))
            return (dx * dx + dy * dy) ** 0.5 * sc
        except ValueError:
            return 0.0
    if e.tag in ("path", "polyline", "polygon"):
        src = a.get("d") or a.get("points") or ""
        nums = [float(n) for n in _NUM.findall(src)]
        xs = nums[0::2]
        ys = nums[1::2]
        if len(xs) >= 2 and len(ys) >= 2:
            diag = ((max(xs) - min(xs)) ** 2 + (max(ys) - min(ys)) ** 2) ** 0.5
            return diag * sc
    if e.tag == "rect":
        try:
            return (float(a.get("width", 0)) + float(a.get("height", 0))) * sc
        except ValueError:
            return 0.0
    return 0.0


# ---------------------------------------------------------------------------
# Geometry re-emission
# ---------------------------------------------------------------------------

def serialize(el, mode, style, mono, cls=None, faded=False, kind="primary"):
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
        col = process_color(cls, style, mono)
        if kind == "primary":
            w = style["primary_w"]
        elif kind == "branch":
            w = style["branch_w"]
        elif kind == "secondary":
            w = style["secondary_w"]
        else:
            w = style["outside_w"]
        op = style["process_opacity"]
        extra = ""
        if kind == "outside":
            extra = ";stroke-dasharray:5,3"
            if not mono:
                col = GRAY
        if faded:
            col, op = (MONO_BLACK if mono else GRAY), 0.45
            w = max(w * 0.7, mm(0.3))
        css = (f"fill:none;stroke:{col};stroke-width:{w:.2f};stroke-opacity:{op};"
               f"stroke-linecap:round;stroke-linejoin:round{extra}")
        mk = carry_markers(attrs.get("style"))
        if mk:
            css += ";" + mk
        parts.append(f' style="{css}"')
    elif mode == "process_node":
        col = process_color(cls, style, mono)
        if faded:
            col = MONO_BLACK if mono else GRAY
        parts.append(f' style="fill:{col};stroke:none;fill-opacity:{0.5 if faded else 1}"')
    elif mode == "process_fill":
        col = process_color(cls, style, mono)
        fo = 0.0 if mono else 0.14
        parts.append(f' style="fill:{col};fill-opacity:{fo};stroke:{col};'
                     f'stroke-width:0.6;stroke-opacity:0.5"')
    elif mode == "structure":
        w = style["equip_w"]
        col = ("#000000" if mono else "#bbbbbb") if faded else \
              ("#000000" if mono else "#666666")
        op = 0.5 if faded else 0.85
        parts.append(f' style="fill:none;stroke:{col};stroke-width:{w:.2f};'
                     f'stroke-opacity:{op}"')
    parts.append("/>")
    return "".join(parts)


# ---------------------------------------------------------------------------
# Sensor re-allocation (kept from v2)
# ---------------------------------------------------------------------------
REALLOC = {
    "TT535": ("PZ", "TT-CX",    "coldest part of Piezo (PZ)"),
    "TT525": ("PZ", "TT-PT100", "warmest part of Piezo (PZ)"),
}
MAG_COUPLER_SENSORS = [
    ("TT-CX",    "MAG cold port",        "TT-CX on MAG (cold)"),
    ("TT-PT100", "MAG warm port",        "TT-PT100 on MAG (warm)"),
    ("TT-CX",    "Coupler port (cold)",  "TT-CX coupler thermalisation"),
    ("TT-PT100", "Coupler port (warm)",  "TT-PT100 coupler thermalisation"),
]


def apply_reallocation(seg):
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
    prefix = (inst.get("prefix") or "").upper()
    if prefix in VALVE_PREFIX:
        return "valve"
    if prefix in PROCESS_INLINE:
        return "process"
    if prefix in ("HL",):
        return "control"
    return "sensor"


def family_of(inst, default_fam):
    lay = (inst.get("layer") or "").upper()
    if "LBI" in lay:
        return "LBI"
    if "RFCELL" in lay:
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


def draw_valves(insts, style, mono):
    body = []
    vcol = "#000000" if mono else style["valve_color"]
    for inst in insts:
        if instrument_sheet_role(inst) != "valve":
            continue
        cx, cy = cpt(inst["x"], inst["y"])
        prefix = (inst.get("prefix") or "").upper()
        kind = VALVE_PREFIX[prefix]
        body.append(SYM.valve(cx, cy, kind=kind, size=mm(2.0), color=vcol))
        if prefix == "MV":
            body.append(SYM.bellows(cx + mm(5), cy, length=mm(5), amp=mm(0.9), n=5,
                                    color=vcol, w=signal_width(style)))
    return "\n".join(body)


def draw_valve_tags(insts):
    body = []
    for inst in insts:
        if instrument_sheet_role(inst) != "valve":
            continue
        cx, cy = cpt(inst["x"], inst["y"])
        tag = inst.get("tag") or ""
        if not tag:
            continue
        # white-boxed tag below the valve so it never overlaps piping
        body.append(SYM.tag_with_box(cx, cy + mm(4.8), tag, size=T_MAIN,
                                     pad=mm(0.5), weight="bold", box_sw=mm(0.1)))
    return "\n".join(body)


def draw_instruments(insts, style, default_fam, roles, mono):
    """Return (bubbles, tags). HL heat-loads drawn as triangles."""
    bub, tags = [], []
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
        if prefix == "HL":
            bub.append(SYM.heat_load(cx, cy, "#000000" if mono else "#008000"))
            continue
        fam = family_of(inst, default_fam)
        if mono:
            fill = "#ffffff"
        else:
            fill = {"LB": "#ffffff", "RF": "#ffe2e2", "LBI": "#dbe9ff"}.get(fam, "#ffffff")
        # location modifier: switches/transmitters field; PZ/SV safety = rear/dashed
        location = "field"
        if prefix in ("PZ", "SV", "RV", "PL"):
            location = "front"
        bub.append(SYM.bubble_v3(cx, cy, prefix, number, r=r, fill=fill,
                                 location=location, is_safety=is_safety, mono=mono,
                                 tag_size=T_BUBBLE * 0.92, lw=mm(0.3)))
        # re-allocated highlight ring
        if inst.get("_realloc_from"):
            ring = "#000000" if mono else "#c01010"
            bub.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r+mm(0.8):.2f}" '
                       f'fill="none" stroke="{ring}" stroke-width="0.8" '
                       f'stroke-dasharray="2,1.5"/>')
        st = inst.get("_sensor_type")
        if st:
            tags.append(SYM.tag_with_box(cx, cy + r + T_BUBBLE + 1, st,
                                         size=T_BUBBLE * 0.85, pad=mm(0.5),
                                         weight="bold", box_sw=mm(0.1),
                                         fill="#000000" if mono else "#c01010"))
    return "\n".join(bub), "\n".join(tags)


def draw_signals(insts, style, mono, kinds):
    """Short typed signal stubs from each instrument bubble (one of 3 layers)."""
    body = []
    w = signal_width(style)
    r = style["bubble_r"]
    for inst in insts:
        role = instrument_sheet_role(inst)
        if role not in ("sensor", "valve", "process"):
            continue
        prefix = (inst.get("prefix") or "").upper()
        kind = SIGNAL_KIND.get(prefix)
        if kind not in kinds:
            continue
        cx, cy = cpt(inst["x"], inst["y"])
        col = "#000000" if mono else \
            {"pneumatic": "#7a00a0", "electric": "#00529b",
             "hydraulic": "#a06a00"}.get(kind, "#000000")
        # stub upward (toward control bus / DIS)
        body.append(SYM.signal_line(cx, cy - r, cx, cy - r - mm(4.0),
                                    kind=kind, color=col, w=w))
    return "\n".join(body)


# ---------------------------------------------------------------------------
# Phase 3 - inline on-line names (mono legibility)
# ---------------------------------------------------------------------------
import math as _math

# pipe-name text + synthetic line-spec per process class (AD_01.10 style)
LINE_NAME_TEXT = {
    "D":     "40K PRIMARY",
    "A":     "4.5K PRIMARY",
    "B":     "2K PRIMARY",
    "WATER": "CW SUPPLY/RETURN",
}
LINE_SPEC = {
    "D":     "40K-3\"-PAC1-DA",
    "A":     "4K5-2\"-PAC1-AA",
    "B":     "2K0-4\"-PAC1-BA",
    "WATER": "CWS-2\"-PWC1-WA",
}


def _elem_endpoints_sheet(e):
    """Return ((x1,y1),(x2,y2)) of an element's principal axis in sheet coords."""
    a = e.attrs
    final = X.mat_mul(CONTENT_M, e.ctm)
    if e.tag == "line":
        try:
            p1 = X.apply(final, float(a.get("x1", 0)), float(a.get("y1", 0)))
            p2 = X.apply(final, float(a.get("x2", 0)), float(a.get("y2", 0)))
            return p1, p2
        except ValueError:
            return None
    if e.tag in ("path", "polyline", "polygon"):
        src = a.get("d") or a.get("points") or ""
        nums = [float(n) for n in _NUM.findall(src)]
        xs, ys = nums[0::2], nums[1::2]
        if len(xs) >= 2 and len(ys) >= 2:
            p1 = X.apply(final, xs[0], ys[0])
            p2 = X.apply(final, xs[-1], ys[-1])
            return p1, p2
    return None


def draw_line_names(process, style, mono, per_class=4):
    """Place inline pipe-name labels on the longest runs of each class.

    Labels sit in white boxes on the pipe, follow the pipe direction, and are
    colour-matched (black in mono).  This is what keeps the monochrome plot
    readable without relying on colour alone (user feedback)."""
    body = []
    for cls in CRYO_CLASSES + SECONDARY_CLASSES:
        runs = []
        for m, e in process.get(cls, []):
            if m != "process":
                continue
            pts = _elem_endpoints_sheet(e)
            if not pts:
                continue
            (x1, y1), (x2, y2) = pts
            length = _math.hypot(x2 - x1, y2 - y1)
            if length < mm(14):
                continue
            runs.append((length, (x1 + x2) / 2.0, (y1 + y2) / 2.0, x1, y1, x2, y2))
        runs.sort(reverse=True)
        col = "#000000" if mono else CLASS_STYLE[cls]["color"]
        label = LINE_NAME_TEXT.get(cls, cls)
        for i, (length, mx, my, x1, y1, x2, y2) in enumerate(runs[:per_class]):
            ang = _math.degrees(_math.atan2(y2 - y1, x2 - x1))
            if ang > 90:
                ang -= 180
            elif ang < -90:
                ang += 180
            # alternate between the line name and the line spec along the run
            text = label if i % 2 == 0 else LINE_SPEC.get(cls, label)
            body.append(SYM.line_label(mx, my, text, size=mm(2.2), pad=mm(0.6),
                                       color=col, angle=ang))
    return "\n".join(body)


# ---------------------------------------------------------------------------
# Phase 4 - valve horizontal-overlay row ("tracked asset" view)
# ---------------------------------------------------------------------------

def draw_valve_overlays(insts, style, mono):
    """Toggleable overlay: every valve repeated horizontally in a banner row
    near the top of the drawing, each linked by a thin grey leader back to its
    in-line (vertical) symbol."""
    valves = [i for i in insts if instrument_sheet_role(i) == "valve"
              and i.get("x") is not None]
    if not valves:
        return ""
    vcol = "#000000" if mono else style["valve_color"]
    body = []
    row_y = CY0 + mm(7)
    x0 = CX0 + mm(20)
    x1 = CX1 - mm(20)
    n = len(valves)
    step = (x1 - x0) / max(n, 1)
    # banner backdrop strip
    body.append(f'<rect x="{x0-mm(6):.2f}" y="{row_y-mm(7):.2f}" '
                f'width="{(x1-x0)+mm(12):.2f}" height="{mm(13):.2f}" rx="{mm(1):.2f}" '
                f'fill="#f4f4f4" fill-opacity="0.55" stroke="#9a9a9a" '
                f'stroke-width="0.3" stroke-dasharray="3,2"/>')
    body.append(SYM._text(x0 - mm(4), row_y - mm(8.5),
                          "HORIZONTAL VALVE OVERLAY (tracked assets)",
                          size=T_LEGEND, anchor="start", weight="bold",
                          fill="#000000" if mono else "#555555"))
    for i, v in enumerate(sorted(valves, key=lambda q: cpt(q["x"], q["y"])[0])):
        cx, cy = cpt(v["x"], v["y"])
        ox = x0 + (i + 0.5) * step
        prefix = (v.get("prefix") or "").upper()
        kind = VALVE_PREFIX.get(prefix, "manual")
        tag = v.get("tag") or (prefix + (v.get("number") or ""))
        body.append(SYM.valve_horizontal_overlay(ox, row_y, kind, tag,
                                                  size=mm(2.0), color=vcol,
                                                  from_xy=(cx, cy), ts=T_SMALL))
    return "\n".join(body)


# ---------------------------------------------------------------------------
# Phase 5 - AD_01.10 edge terminal points
# ---------------------------------------------------------------------------

def build_terminal_points_edge(seg, sheet_meta, mono):
    """Place terminal-point assemblies at the LEFT (FROM/incoming) and RIGHT
    (TO/outgoing) page edges, AD_01.10 style.  TP equipment whose x is left of
    the content mid-line goes to the left edge, the rest to the right edge."""
    tps = [e for e in seg.get("equipment", [])
           if e.get("kind") == "Terminal Point" and e.get("x") is not None]
    if not tps:
        return ""
    midx = (CX0 + CX1) / 2.0
    dwg_ref = sheet_meta.get("drawing_no", "=NA.PS01_PFB712")
    left, right = [], []
    for eq in tps:
        cx, _ = cpt(eq["x"], eq["y"])
        (left if cx < midx else right).append(eq)
    body = []
    line_no = 7800
    for side, items in (("in", left), ("out", right)):
        if not items:
            continue
        xedge = CX0 + mm(2) if side == "in" else CX1 - mm(2)
        # stack vertically, evenly spaced down the usable height
        y0 = CY0 + mm(26)
        y1 = CY1 - mm(14)
        step = (y1 - y0) / max(len(items), 1)
        for j, eq in enumerate(sorted(items, key=lambda q: cpt(q["x"], q["y"])[1])):
            line_no += 11
            y = y0 + (j + 0.5) * step
            cat = category_for(eq, seg)
            col = "#000000" if mono else SYM.SCOPE_CATEGORY[cat][1]
            nxt = NEXT_SYS.get(cat, "")
            tp_code = f"TP.PS01.{4000 + line_no % 1000}"
            system = CLASS_STYLE.get(_tp_class(eq), {}).get("name", "Service")
            body.append(SYM.terminal_point_edge(
                xedge, y, side, system, dwg_ref, line_no, tp_code,
                next_sys=nxt, category=cat, color=col, mono=mono,
                ts=T_SMALL * 0.92, scale=0.92))
    return "\n".join(body)


def _tp_class(eq):
    """Best-guess process class for a terminal point from its layer/label."""
    txt = ((eq.get("layer") or "") + " " + (eq.get("label") or "")).lower()
    if "water" in txt or "cw" in txt:
        return "WATER"
    if "40" in txt:
        return "D"
    if "4.5" in txt or "4k5" in txt:
        return "A"
    if "2k" in txt or " 2 " in txt:
        return "B"
    return "A"


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


def draw_equipment(seg, style, mono):
    body = []
    ew = style["equip_w"]
    ecol = "#000000" if mono else "#333333"
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
            body.append(SYM.cavity(cx, cy, w=mm(12), h=mm(7.4),
                                   label=label, color="#000000" if mono else "#aa4400"))
        elif g == "vessel":
            body.append(SYM.vessel(cx, cy, w=mm(9), h=mm(14), label=label, color=ecol))
        elif g == "hx":
            body.append(SYM.heat_exchanger(cx, cy, r=mm(4.8), label=label, color=ecol))
        elif g == "antenna":
            body.append(f'<line x1="{cx:.2f}" y1="{cy:.2f}" x2="{cx:.2f}" '
                        f'y2="{cy-mm(3.5):.2f}" stroke="{ecol}" stroke-width="{ew:.2f}"/>'
                        f'<circle cx="{cx:.2f}" cy="{cy-mm(3.5):.2f}" r="{mm(0.8):.2f}" '
                        f'fill="{ecol}"/>'
                        + SYM._text(cx, cy + mm(2.4), label, size=T_LEGEND * 0.85))
        else:
            body.append(SYM.node(cx, cy, label=label, r=mm(0.9), color=ecol, fill=ecol))
    return "\n".join(body)


# ---------------------------------------------------------------------------
# Scope boundary diamonds (Layer 01) - AD_01.16 3-compartment
# ---------------------------------------------------------------------------
# prefix -> AD_01.16 scope category (B/C/E/G/H/L/S/W)
PREFIX_CATEGORY = {
    "EH": "E", "EHx": "E", "KW": "E", "AK": "E",            # electrical
    "FT": "W", "FI": "W",                                    # water/flow
    "LT": "L", "LS": "L", "LI": "L",                         # liquid waste/level
    "SV": "H", "RV": "H", "PZ": "G", "PL": "G",              # vacuum/relief, gas
    "TT": "G", "PT": "G",                                    # cryogenic gas circuits
}
# next-system hint by category
NEXT_SYS = {"E": "PWR", "W": "CWS", "L": "DRN", "H": "HVAC",
            "G": "He", "B": "BLDG", "C": "CIV", "S": "WASTE"}


def _instr_points(seg):
    pts = []
    for i in seg.get("instruments", []):
        if i.get("x") is not None:
            pts.append((i["x"], i["y"], (i.get("prefix") or "").upper()))
    return pts


def category_for(eq, seg):
    lay = (eq.get("layer") or "").lower()
    lbl = (eq.get("label") or "").lower()
    txt = lay + " " + lbl
    if "water" in txt or "di " in txt or "freia" in txt:
        return "W"
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
    return "G"


def build_scope(seg, mono):
    body, codes = [], []
    serial = {}
    for eq in seg.get("equipment", []):
        if eq.get("kind") != "Terminal Point" or eq.get("x") is None:
            continue
        cx, cy = cpt(eq["x"], eq["y"])
        cat = category_for(eq, seg)
        serial[cat] = serial.get(cat, 1000) + 1
        num = serial[cat]
        cat_code = f"{cat}{num}"
        code = f"TP-{cat_code}"
        col = "#000000" if mono else SYM.SCOPE_CATEGORY[cat][1]
        body.append(SYM.scope_diamond_3c(cx, cy, cat_code, next_sys=NEXT_SYS.get(cat, ""),
                                         size=mm(3.4), color=col, text_size=T_LEGEND * 0.78))
        codes.append((code, cat, SYM.SCOPE_CATEGORY[cat][0], eq.get("layer", "")))
    return "\n".join(body), codes


# ---------------------------------------------------------------------------
# Control instrumentation (Layer 14): DIS + tuner LS + Lemo + buffers
# ---------------------------------------------------------------------------

def find_equipment(seg, kind):
    return [e for e in seg.get("equipment", []) if e.get("kind") == kind
            and e.get("x") is not None]


def build_control(seg, mono):
    ctrl, notes = [], []
    accent = "#000000" if mono else "#c01010"
    dx = CX1 - mm(46)
    dy = CY0 + mm(2)
    ctrl.append(SYM.dis_block(
        dx, dy, w=mm(44), h=mm(26),
        color="#000000", accent=accent,
        inputs=["Vacuum OK (QVE)", "Cryo OK (2K/4.5K)", "Utilities OK"],
        output="MASTER INTERLOCK -> RF"))

    tuners = find_equipment(seg, "Tuner")
    if tuners:
        bx, by = cpt(tuners[0]["x"], tuners[0]["y"])
    else:
        bx, by = CX0 + mm(34), CY1 - mm(34)
    for i in range(3):
        lx = bx + (i - 1) * mm(9)
        ly = by - mm(19)
        ctrl.append(SYM.limit_switch(lx, ly, number=f"LS-T{i+1}", size=mm(2.4),
                                     text_size=T_LEGEND * 0.85))
        ctrl.append(f'<line x1="{lx:.2f}" y1="{ly+mm(2.4):.2f}" x2="{lx:.2f}" '
                    f'y2="{by-mm(5):.2f}" stroke="#000" stroke-width="0.7" '
                    f'stroke-dasharray="2,2"/>')
    notes.append(SYM._text(bx, by - mm(25), "Tuner limit switches (x3) - mounted "
                           "OUTSIDE vacuum vessel", size=T_LEGEND, weight="bold",
                           fill="#000000" if mono else "#c01010"))

    lemo_x = CX0 + mm(11)
    lemo_y = CY1 - mm(10)
    for i in range(3):
        ctrl.append(SYM.lemo_connector(lemo_x + i * mm(8), lemo_y,
                                       label=("Lemo B (HV/PZ)" if i == 0 else ""),
                                       size=mm(1.9), text_size=T_LEGEND * 0.82))
    notes.append(SYM._text(lemo_x - mm(1.5), lemo_y - mm(4.5),
                           "Patch panel - Lemo B-series (HV pins for Piezo / PZ)",
                           size=T_LEGEND, anchor="start", weight="bold",
                           fill="#000000" if mono else "#003"))
    return "\n".join(ctrl), "\n".join(notes)


def build_annotations(mono):
    body = []
    gcol = "#000000" if mono else "#005500"
    nb, h = SYM.note_box(CX0 + mm(1.5), CY0 + mm(1.5),
                         ["Liquid buffer: 7 L min", "Vapour buffer: 5 L min"],
                         w=mm(34), title="BUFFER VOLUMES", color=gcol,
                         text_size=T_LEGEND)
    body.append(nb)
    rcol = "#000000" if mono else "#7a0000"
    hb, _ = SYM.note_box(CX0 + mm(1.5), CY0 + mm(1.5) + h + mm(2),
                         ["Diamonds (TP / cat / next) mark the",
                          "'last-meter' hand-over between",
                          "in-scope and out-of-scope assets."],
                         w=mm(34), title="SCOPE HAND-OVER", color=rcol,
                         text_size=T_LEGEND * 0.9)
    body.append(hb)
    return "\n".join(body)


# ---------------------------------------------------------------------------
# Frame + compact bottom title block (Layer 00)
# ---------------------------------------------------------------------------

def build_frame(sheet_meta, sheet, style_name, style, mono):
    fx0, fy0 = PAPER_MARGIN, PAPER_MARGIN
    fx1, fy1 = SHEET_W - PAPER_MARGIN, SHEET_H - PAPER_MARGIN
    p = [f'<rect x="0" y="0" width="{SHEET_W}" height="{SHEET_H}" fill="#ffffff"/>']
    p.append(f'<rect x="{fx0:.2f}" y="{fy0:.2f}" width="{fx1-fx0:.2f}" '
             f'height="{fy1-fy0:.2f}" fill="none" stroke="#000000" stroke-width="2.0"/>')
    ix0, iy0 = fx0 + FRAME_PAD, fy0 + FRAME_PAD
    ix1, iy1 = fx1 - FRAME_PAD, fy1 - FRAME_PAD
    p.append(f'<rect x="{ix0:.2f}" y="{iy0:.2f}" width="{ix1-ix0:.2f}" '
             f'height="{iy1-iy0:.2f}" fill="none" stroke="#000000" stroke-width="0.7"/>')

    # ---- compact full-width bottom title block band ----
    tbx0 = ix0
    tby0 = iy1 - TITLE_H
    tbw = ix1 - ix0
    p.append(f'<rect x="{tbx0:.2f}" y="{tby0:.2f}" width="{tbw:.2f}" '
             f'height="{TITLE_H:.2f}" fill="#ffffff" stroke="#000000" '
             f'stroke-width="1.2"/>')
    # column x-fractions
    cols = [0.0, 0.16, 0.30, 0.62, 0.80, 1.0]
    cx = [tbx0 + f * tbw for f in cols]
    for x in cx[1:-1]:
        p.append(f'<line x1="{x:.2f}" y1="{tby0:.2f}" x2="{x:.2f}" '
                 f'y2="{tby0+TITLE_H:.2f}" stroke="#000000" stroke-width="0.7"/>')

    def cell_title(x, y, t):
        return SYM._text(x + mm(1.2), y + mm(2.6), t, size=T_SMALL * 0.9,
                         anchor="start", weight="bold", fill="#666666")

    def cell_val(x, y, t, size=None, dy=mm(6.0)):
        return SYM._text(x + mm(1.2), y + dy, t, size=size or T_CALLOUT,
                         anchor="start", weight="bold")

    # col0 consultant
    p.append(cell_title(cx[0], tby0, "CONSULTANT"))
    p.append(cell_val(cx[0], tby0, "Mott MacDonald", size=T_CALLOUT))
    p.append(SYM._text(cx[0] + mm(1.2), tby0 + mm(10), "Bristol, UK", size=T_SMALL,
                       anchor="start", fill="#444"))
    # col1 client
    p.append(cell_title(cx[1], tby0, "CLIENT"))
    p.append(cell_val(cx[1], tby0, "SCK CEN", size=T_CALLOUT))
    p.append(SYM._text(cx[1] + mm(1.2), tby0 + mm(10),
                       "Boeretang 200, 2400 Mol, BE", size=T_SMALL * 0.85,
                       anchor="start", fill="#444"))
    p.append(SYM._text(cx[1] + mm(1.2), tby0 + mm(14), "MYRRHA / MINERVA Phase 1",
                       size=T_SMALL * 0.85, anchor="start", fill="#444"))
    # col2 revision table
    p.append(cell_title(cx[2], tby0, "REVISIONS"))
    revs = [("Rev", "Date", "Description", "App'd"),
            ("C1", "2026-06", "v3 refinement - layers/legibility", "ACR"),
            ("B1", "2026-05", "v2 split sheets", "ACR"),
            ("A1", "2026-04", "First issue", "ACR")]
    ry = tby0 + mm(4.2)
    rcw = (cx[3] - cx[2])
    for i, row in enumerate(revs):
        yy = ry + i * mm(5.6)
        wcol = [0.10, 0.22, 0.78, 1.0]
        for j, txt in enumerate(row):
            xx = cx[2] + wcol[j] * 0  # placeholder
        p.append(SYM._text(cx[2] + mm(1.2), yy, row[0], size=T_SMALL,
                            anchor="start", weight="bold" if i == 0 else "normal"))
        p.append(SYM._text(cx[2] + rcw * 0.13, yy, row[1], size=T_SMALL,
                            anchor="start"))
        p.append(SYM._text(cx[2] + rcw * 0.34, yy, row[2][:30], size=T_SMALL * 0.9,
                            anchor="start"))
        p.append(SYM._text(cx[2] + rcw * 0.90, yy, row[3], size=T_SMALL,
                            anchor="start"))
    # col3 approvals
    p.append(cell_title(cx[3], tby0, "APPROVALS"))
    appr = [("Designed", "QSYS"), ("Drawn", "ACR"), ("Checked", "ACR"),
            ("Approved", "PM")]
    for i, (k, v) in enumerate(appr):
        yy = tby0 + mm(6.0) + i * mm(5.4)
        p.append(SYM._text(cx[3] + mm(1.2), yy, k, size=T_SMALL,
                            anchor="start", fill="#555"))
        p.append(SYM._text(cx[3] + mm(11), yy, v, size=T_SMALL, anchor="start",
                            weight="bold"))
    # col4 main block (title / drawing no / scale / suitability / size / rev)
    bx = cx[4]
    p.append(SYM._text(bx + mm(1.2), tby0 + mm(3.4), sheet_meta["project"],
                       size=T_CALLOUT, anchor="start", weight="bold"))
    p.append(SYM._text(bx + mm(1.2), tby0 + mm(7.4), sheet["title"][:42],
                       size=T_SMALL, anchor="start"))
    rows = [("DWG No.", sheet_meta["drawing_no"]),
            ("MMD Proj.", sheet_meta["mmd"]),
            ("Scale", "NTS"),
            ("Suitability", "S2 - FOR ACCEPTANCE"),
            ("Security", "RESTRICTED"),
            ("Size / Std", "A3 / ISO10628 / ISA-5.1"),
            ("Sheet", f'{sheet["id"]} of 2  -  {sheet["kind"]}'),
            ("Variant", style_name + ("_MONO" if mono else ""))]
    for i, (k, v) in enumerate(rows):
        yy = tby0 + mm(10.5) + i * mm(2.5)
        p.append(SYM._text(bx + mm(1.2), yy, k, size=T_SMALL * 0.82, anchor="start",
                           fill="#555"))
        p.append(SYM._text(bx + mm(13), yy, v, size=T_SMALL * 0.82, anchor="start",
                           weight="bold"))

    # header strip (top of drawing area)
    p.append(SYM._text(ix0 + mm(2), iy0 + mm(5), "P&ID  -  " + sheet["title"],
                       size=mm(3.2), anchor="start", weight="bold"))
    badge = style_name + ("  /  MONO" if mono else "")
    bcol = "#000000" if mono else ("#c01010" if "CONTROL" in style_name else "#0033cc")
    p.append(SYM._text(ix1 - mm(2), iy0 + mm(5), badge, size=mm(2.8), anchor="end",
                       weight="bold", fill=bcol))
    return "\n".join(p), (tbx0, tby0)


# ---------------------------------------------------------------------------
# Toggleable legend (Layer 16) - compact, top-right overlay
# ---------------------------------------------------------------------------

def build_legend(style, mono):
    """Enhanced interactive colour/signal legend (Phase 7).

    Renders a process-class TABLE (colour swatch, mono line-weight, service,
    temperature, pressure) plus a signal-type table and an ISA-5.1 / scope key,
    with explicit toggle instructions for the interactive viewer."""
    pw = mm(72)
    ph = mm(124)
    px0 = SHEET_W - PAPER_MARGIN - FRAME_PAD - pw - mm(2)
    py0 = CY0 + mm(2)
    p = [f'<rect x="{px0:.2f}" y="{py0:.2f}" width="{pw:.2f}" height="{ph:.2f}" '
         f'rx="3" fill="#ffffff" stroke="#000000" stroke-width="1.0" '
         f'fill-opacity="0.97"/>']
    x = px0 + mm(2.5)
    y = py0 + mm(5)
    p.append(SYM._text(px0 + pw / 2, y, "INTERACTIVE LEGEND", size=T_LEGEND * 1.15,
                       weight="bold"))
    y += mm(3)
    p.append(SYM._text(px0 + pw / 2, y, "toggle: layer \"16_Legend_INTERACTIVE\"",
                       size=T_LEGEND * 0.72, fill="#555"))
    y += mm(2)
    p.append(f'<line x1="{px0+mm(1.5):.2f}" y1="{y:.2f}" x2="{px0+pw-mm(1.5):.2f}" '
             f'y2="{y:.2f}" stroke="#000" stroke-width="0.6"/>')
    y += mm(4)
    # ---- process-class table ----
    p.append(SYM._text(x, y, "PROCESS CLASSES", size=T_LEGEND, anchor="start",
                       weight="bold"))
    y += mm(3.6)
    # column headers
    cxs = {"swatch": x, "service": x + mm(11), "temp": x + mm(36),
           "press": x + mm(50)}
    p.append(SYM._text(cxs["swatch"], y, "line", size=T_LEGEND * 0.68,
                       anchor="start", fill="#555"))
    p.append(SYM._text(cxs["service"], y, "service", size=T_LEGEND * 0.68,
                       anchor="start", fill="#555"))
    p.append(SYM._text(cxs["temp"], y, "temp", size=T_LEGEND * 0.68,
                       anchor="start", fill="#555"))
    p.append(SYM._text(cxs["press"], y, "press", size=T_LEGEND * 0.68,
                       anchor="start", fill="#555"))
    y += mm(2.6)
    table = [("D", "primary", "40 K", "14 bar"),
             ("A", "primary", "4.5 K", "3 bar"),
             ("B", "primary", "2 K", "27 mbar"),
             ("WATER", "secondary", "amb", "4 bar"),
             ("E", "outside", "60 K", "13 bar"),
             ("AIR", "outside", "amb", "6 bar(g)")]
    for cls, kind, temp, press in table:
        col = process_color(cls, style, mono)
        w = {"primary": style["primary_w"], "branch": style["branch_w"],
             "secondary": style["secondary_w"], "outside": style["outside_w"]}[kind]
        dash = ' stroke-dasharray="5,3"' if kind == "outside" else ""
        if kind == "outside" and not mono:
            col = GRAY
        p.append(f'<line x1="{cxs["swatch"]:.2f}" y1="{y-mm(0.5):.2f}" '
                 f'x2="{cxs["swatch"]+mm(9):.2f}" y2="{y-mm(0.5):.2f}" '
                 f'stroke="{col}" stroke-width="{w:.2f}"{dash}/>')
        # mono weight annotation under the swatch
        p.append(SYM._text(cxs["service"], y + mm(0.6),
                           CLASS_STYLE[cls]["name"][:13], size=T_LEGEND * 0.78,
                           anchor="start"))
        p.append(SYM._text(cxs["temp"], y + mm(0.6), temp, size=T_LEGEND * 0.78,
                           anchor="start"))
        p.append(SYM._text(cxs["press"], y + mm(0.6), press, size=T_LEGEND * 0.78,
                           anchor="start"))
        y += mm(3.4)
    p.append(SYM._text(x, y, "mono: colour replaced by line weight + on-line NAME",
                       size=T_LEGEND * 0.66, anchor="start", fill="#555"))
    y += mm(4.5)
    # ---- signal table ----
    p.append(SYM._text(x, y, "SIGNAL TYPES (0.25 mm)", size=T_LEGEND, anchor="start",
                       weight="bold"))
    y += mm(3.8)
    for kind, lab, col in [("pneumatic", "Pneumatic  (dash + //)", "#7a00a0"),
                           ("electric", "Electric  (dotted)", "#00529b"),
                           ("hydraulic", "Hydraulic  (dash-dot)", "#a06a00")]:
        c = "#000000" if mono else col
        p.append(SYM.signal_line(x, y - mm(0.6), x + mm(9), y - mm(0.6),
                                 kind=kind, color=c, w=signal_width(style)))
        p.append(SYM._text(x + mm(11), y + mm(0.6), lab, size=T_LEGEND * 0.86,
                           anchor="start"))
        y += mm(3.6)
    y += mm(1.5)
    # ---- instruments / scope key ----
    p.append(SYM._text(x, y, "INSTRUMENTS / SCOPE", size=T_LEGEND, anchor="start",
                       weight="bold"))
    y += mm(4)
    r = mm(2.0)
    p.append(SYM.bubble_v3(x + mm(3), y, "TT", "", r=r, location="field", mono=mono,
                           tag_size=T_LEGEND * 0.8, lw=mm(0.3)))
    p.append(SYM._text(x + mm(8), y + mm(0.6), "Field instrument (white box tag)",
                       size=T_LEGEND * 0.86, anchor="start"))
    y += mm(5)
    p.append(SYM.bubble_v3(x + mm(3), y, "PZ", "", r=r, location="front", mono=mono,
                           tag_size=T_LEGEND * 0.8, lw=mm(0.3)))
    p.append(SYM._text(x + mm(8), y + mm(0.6), "Panel / safety (line)",
                       size=T_LEGEND * 0.86, anchor="start"))
    y += mm(5)
    p.append(SYM.scope_diamond_3c(x + mm(3), y, "G1001", next_sys="He",
                                  size=mm(3.0), color="#000000" if mono else "#0066a6",
                                  text_size=T_LEGEND * 0.62))
    p.append(SYM._text(x + mm(8), y + mm(0.6), "TP scope diamond (edge = TP layer)",
                       size=T_LEGEND * 0.86, anchor="start"))
    y += mm(5.5)
    cats = ", ".join(f'{k}={v[0]}' for k, v in list(SYM.SCOPE_CATEGORY.items())[:4])
    cats2 = ", ".join(f'{k}={v[0]}' for k, v in list(SYM.SCOPE_CATEGORY.items())[4:])
    p.append(SYM._text(x, y, "Cat: " + cats, size=T_LEGEND * 0.72, anchor="start",
                       fill="#444"))
    y += mm(2.6)
    p.append(SYM._text(x, y, "     " + cats2, size=T_LEGEND * 0.72, anchor="start",
                       fill="#444"))
    return "\n".join(p)


# ---------------------------------------------------------------------------
# Metadata block (default views)
# ---------------------------------------------------------------------------

def build_metadata():
    lines = ['<metadata id="minerva-pid-meta">',
             '  <minerva:standard xmlns:minerva="https://sckcen.be/minerva/pid">'
             'ANSI/ISA-5.1-2022; ISO 10628; IEC 60617; SCK CEN AD_01.16</minerva:standard>',
             '  <minerva:defaultViews xmlns:minerva="https://sckcen.be/minerva/pid">']
    for vname, vis in DEFAULT_VIEWS.items():
        lines.append(f'    <view name="{vname}">')
        for ln in LAYER_NAMES:
            shown = "true" if ln in vis else "false"
            lines.append(f'      <layer name="{ln}" visible="{shown}"/>')
        lines.append('    </view>')
    lines.append('  </minerva:defaultViews>')
    lines.append('</metadata>')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Phase 9 - YAML 1.2 front matter (Jekyll-style) embedded as an XML comment
# ---------------------------------------------------------------------------

def _yaml_list(items, indent="    "):
    if not items:
        return " []"
    return "\n" + "\n".join(f"{indent}- {it}" for it in items)


def build_front_matter(sheet_meta, sheet, variant, mono, insts, seg):
    """Return a Jekyll-style YAML 1.2 front-matter block (as an SVG comment)."""
    today = "2026-06-03"
    instr_tags = sorted({(i.get("tag") or "").strip() for i in insts
                         if (i.get("tag") or "").strip()})
    tps = [e for e in seg.get("equipment", [])
           if e.get("kind") == "Terminal Point" and e.get("x") is not None]
    lines = ["---",
             f"title: {json.dumps(sheet['title'])}",
             f"drawing_number: {sheet_meta['drawing_no']}",
             "revision: v4.0",
             f"date: {today}",
             f"system: {json.dumps(sheet_meta['project'])}",
             f"cell: {sheet_meta['sub']}",
             f"variant: {variant}",
             f"monochrome: {'true' if mono else 'false'}",
             f"standard: SCK CEN AD_01.16 / ANSI-ISA-5.1 / ISO 10628",
             f"mmd_project: {sheet_meta['mmd']}",
             "layers:" + _yaml_list([f'"{n}"' for n in LAYER_NAMES]),
             "hidden_by_default:" + _yaml_list([f'"{n}"' for n in sorted(HIDDEN_BY_DEFAULT)]),
             "default_views:" + _yaml_list([f'"{v}"' for v in DEFAULT_VIEWS]),
             f"instruments:" + _yaml_list([f'"{t}"' for t in instr_tags[:60]]),
             f"terminal_points: {len(tps)}",
             "---"]
    body = "\n".join(lines)
    # XML comments may not legally contain "--", and Jekyll front matter uses
    # "---" fences, so the YAML is carried verbatim inside a CDATA section of a
    # private metadata element (fences preserved, XML stays well-formed).  A
    # short pointer comment is added for human readers of the raw file.
    body = body.replace("]]>", "]] >")
    return ('<!-- Jekyll YAML 1.2 front matter follows in the metadata CDATA below -->\n'
            '<metadata id="minerva-frontmatter">'
            '<minerva:frontmatter xmlns:minerva="https://sckcen.be/minerva/pid">'
            f'<![CDATA[\n{body}\n]]>'
            '</minerva:frontmatter></metadata>')


# ---------------------------------------------------------------------------
# Build one (sheet, style, mono) combination
# ---------------------------------------------------------------------------

def build_one(key, sheet, style_name, mono, ex, seg, defs, scope_holder):
    sheet_meta = SHEETS[key]
    style = STYLES[style_name]
    fam = sheet_meta["fam"]
    is_instr = sheet["kind"] in ("Instrumentation",)
    is_process = sheet["kind"] in ("Cryogenic", "Process")
    faded = is_instr           # process is a faded backdrop on instrumentation sheets

    # ---- bin geometry ----
    process = defaultdict(list)
    structure = []
    for e in ex.elements:
        if e.bin == "process":
            process[e.cls].append(("process", e))
        elif e.bin == "process_node":
            process[e.cls].append(("process_node", e))
        elif e.bin == "process_fill":
            process[e.cls].append(("process_fill", e))
        elif e.bin in ("structure", "other"):
            structure.append(e)

    insts = collect_instruments(seg)

    # ---- primary/branch thresholds per cryo class ----
    thresholds = {}
    for cls in CRYO_CLASSES:
        lens = sorted(elem_metric(e) for m, e in process.get(cls, []) if m == "process")
        if lens:
            thresholds[cls] = lens[int(len(lens) * 0.55)]   # 55th percentile
        else:
            thresholds[cls] = 0.0

    layers_out = {}

    # 00 background
    frame_body, tb_origin = build_frame(sheet_meta, sheet, style_name, style, mono)
    layers_out["00_Background_TitleBlock"] = frame_body

    # 01 scope
    scope_body, codes = build_scope(seg, mono)
    scope_holder.extend(codes)
    layers_out["01_Scope_Boundaries"] = scope_body

    # 02 structures
    layers_out["02_Structure_Reference"] = "\n".join(
        s for s in (serialize(e, "structure", style, mono, faded=True)
                    for e in structure) if s)

    # 03 equipment
    layers_out["03_Equipment_Vessels"] = draw_equipment(seg, style, mono)

    # 04-06 cryo piping primary/branch
    order = {"process_fill": 0, "process_node": 1, "process": 2}
    for cls in CRYO_CLASSES:
        prim, branch = [], []
        for m, e in sorted(process.get(cls, []), key=lambda me: order.get(me[0], 3)):
            if m == "process":
                kind = "primary" if elem_metric(e) >= thresholds[cls] else "branch"
            else:
                kind = "primary"        # nodes/fills travel with the trunk layer
            frag = serialize(e, m, style, mono, cls, faded, kind=kind)
            if not frag:
                continue
            (prim if kind == "primary" else branch).append(frag)
        layers_out[CLASS_PRIMARY_LAYER[cls]] = "\n".join(prim)
        layers_out[CLASS_BRANCH_LAYER[cls]] = "\n".join(branch)

    # 07 secondary water
    sec = []
    for cls in SECONDARY_CLASSES:
        for m, e in sorted(process.get(cls, []), key=lambda me: order.get(me[0], 3)):
            frag = serialize(e, m, style, mono, cls, faded, kind="secondary")
            if frag:
                sec.append(frag)
    layers_out["07_Piping_SECONDARY_Water"] = "\n".join(sec)

    # 08 outside scope services
    outside = []
    for cls in OUTSIDE_CLASSES:
        for m, e in sorted(process.get(cls, []), key=lambda me: order.get(me[0], 3)):
            frag = serialize(e, m, style, mono, cls, faded, kind="outside")
            if frag:
                outside.append(frag)
    layers_out["08_Piping_OUTSIDE_SCOPE"] = "\n".join(outside)

    # 09 valves (in-line primary symbols)
    layers_out["09_Valves_Mechanical"] = draw_valves(insts, style, mono)

    # 08B valve horizontal overlay (tracked-asset row, hidden by default) - Phase 4
    layers_out["08B_Valves_HORIZONTAL_OVERLAY"] = draw_valve_overlays(insts, style, mono)

    # 10-12 signals
    layers_out["10_Signals_Pneumatic"] = draw_signals(insts, style, mono, {"pneumatic"})
    layers_out["11_Signals_Electric"] = draw_signals(insts, style, mono, {"electric"})
    layers_out["12_Signals_Hydraulic"] = draw_signals(insts, style, mono, {"hydraulic"})

    # 13 instrument sensors
    roles = {"sensor", "process"} if is_instr else {"process"}
    bub, itags = draw_instruments(insts, style, fam, roles, mono)
    layers_out["13_Instruments_Sensors"] = bub

    # 14 control / DIS
    if is_instr:
        ctrl_body, ctrl_notes = build_control(seg, mono)
    else:
        ctrl_body, ctrl_notes = "", ""
    layers_out["14_Instruments_Control_DIS"] = ctrl_body

    # 04C inline pipe names (mono legibility) - Phase 3
    layers_out["04C_Piping_LINENAMES"] = draw_line_names(process, style, mono)

    # 02B edge terminal points (AD_01.10 style) - Phase 5
    layers_out["02B_TerminalPoints_EDGE"] = build_terminal_points_edge(
        seg, sheet_meta, mono)

    # 12_Tags white-boxed instrument + valve tags (front-most) - Phase 2
    vtags = draw_valve_tags(insts)
    layers_out["12_Tags_Instruments"] = "\n".join([itags, vtags])

    # 16 enhanced interactive legend (toggleable, hidden by default) - Phase 7
    layers_out["16_Legend_INTERACTIVE"] = build_legend(style, mono)

    # 17 notes (toggleable)
    annot = build_annotations(mono)
    layers_out["17_Notes_TOGGLEABLE"] = "\n".join([annot, ctrl_notes])

    # ---- assemble in layer order ----
    body_layers = []
    for name in LAYER_NAMES:
        vis = name not in HIDDEN_BY_DEFAULT
        body_layers.append(layer(name, layers_out.get(name, ""), visible=vis))

    svg_ns = "http://www.w3.org/2000/" + "svg"
    xlink_ns = "http://www.w3.org/1999/xlink"
    defs = mono_defs(defs) if mono else defs
    variant = style_name + ("_MONO" if mono else "")
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="{svg_ns}"
     xmlns:xlink="{xlink_ns}"
     xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
     xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.0.dtd"
     width="420mm" height="297mm"
     viewBox="0 0 {SHEET_W} {SHEET_H}" version="1.1">
<title>{esc(sheet["title"])} - {esc(variant)}</title>
<desc>MINERVA CryoCell P&amp;ID v4.0 - {esc(sheet_meta["project"])} - variant {esc(variant)}</desc>
<sodipodi:namedview inkscape:document-units="mm" units="mm"/>
{build_front_matter(sheet_meta, sheet, variant, mono, insts, seg)}
{build_metadata()}
{defs}
{chr(10).join(body_layers)}
</svg>
'''
    outdir = os.path.join(OUT, sheet_meta["sub"])
    os.makedirs(outdir, exist_ok=True)
    fname = f'{sheet["name"]}_{variant}_v4.svg'
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
                for mono in (False, True):
                    p = build_one(key, sheet, style_name, mono, ex, seg, defs, holder)
                    produced.append(p)
                    print("wrote", os.path.relpath(p, PROJECT))
        seen, uniq = set(), []
        for c in holder:
            if c[0] not in seen:
                uniq.append(c)
                seen.add(c[0])
        scope_codes_by_key[key] = uniq
    meta_out = {
        "realloc": realloc_all,
        "scope_codes": scope_codes_by_key,
        "mag_coupler": MAG_COUPLER_SENSORS,
        "layer_names": LAYER_NAMES,
        "default_views": DEFAULT_VIEWS,
    }
    json.dump(meta_out, open(os.path.join(OUT, "_build_meta.json"), "w"), indent=2)
    print(f"\nTotal SVGs: {len(produced)}")


if __name__ == "__main__":
    main()
