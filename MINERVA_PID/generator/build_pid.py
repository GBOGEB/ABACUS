#!/usr/bin/env python3
"""
build_pid.py
============
Rebuilds the MINERVA cryogenic P&ID sheets as clean, layered, ISA-5.1 /
ISO-10628 compliant SVG drawings on an A3 landscape sheet.

Pipeline
--------
1. Extract source geometry with resolved CTM (svg_extract).
2. Load the structured segmentation (instruments / equipment / safety /
   vacuum) produced earlier in the project.
3. Compose a fresh SVG with a strict 7-layer Inkscape hierarchy:
     L1  Border / title block / background
     L2  Equipment & vessels
     L3  Process lines  (sub-layers A / B / D / E / WATER / QINFRA / AIR)
     L4  Vacuum barriers & boundaries
     L5  Instrumentation symbols (ISA bubbles / valves)
     L6  ISA 5.1 tags & labels
     L7  Legend & annotations
4. Original process-line geometry is re-emitted with canonical class colours
   and standard line weights; instrument bubbles are re-drawn fresh from the
   segmentation coordinates.

Outputs improved SVGs to output/.
"""

import os
import re
import json
import html
from collections import defaultdict, Counter

import svg_extract as X
import symbols as SYM

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
SRC = os.path.join(PROJECT, "svg_source")
SEG = os.path.join(PROJECT, "segmentation", "data")
OUT = os.path.join(PROJECT, "output")
os.makedirs(OUT, exist_ok=True)

SHEETS = {
    "QCELL-LB": {
        "src": "PFD-PID MINERVA QCELL-LB.svg",
        "seg": "QCELL-LB_segmentation.json",
        "title": "MINERVA CryoCell - QCELL / LB Cryogenic Flow Scheme",
        "drawing_no": "SCK CEN/84836013",
    },
    "RFCELL": {
        "src": "PFD-PID MINERVA RFCELL seen by ACR.svg",
        "seg": "RFCELL_segmentation.json",
        "title": "MINERVA CryoCell - RFCELL (DI-Water / Coupler) seen by ACR",
        "drawing_no": "SCK CEN/84836013",
    },
}

# ---------------------------------------------------------------------------
# A3 landscape sheet geometry (user units == mm-proportional, A3 ratio)
# ---------------------------------------------------------------------------
SHEET_W = 1587.273          # 420 mm
SHEET_H = 1122.430          # 297 mm  (ratio 1.41414)
PAPER_MARGIN = 14.0         # paper edge -> outer frame line
FRAME_PAD = 12.0            # frame line -> content / panels
RIGHT_PANEL_W = 246.0       # legend column on the right
BOTTOM_BAND_H = 118.0       # title-block / class-legend band

# content region (where the original drawing is mapped)
CX0 = PAPER_MARGIN + FRAME_PAD
CY0 = PAPER_MARGIN + FRAME_PAD
CX1 = SHEET_W - PAPER_MARGIN - FRAME_PAD - RIGHT_PANEL_W - FRAME_PAD
CY1 = SHEET_H - PAPER_MARGIN - FRAME_PAD - BOTTOM_BAND_H - FRAME_PAD
SRC_W, SRC_H = 1527.2727, 1080.0
SCALE = min((CX1 - CX0) / SRC_W, (CY1 - CY0) / SRC_H)
OFX = CX0 + ((CX1 - CX0) - SRC_W * SCALE) / 2.0
OFY = CY0 + ((CY1 - CY0) - SRC_H * SCALE) / 2.0
CONTENT_M = [SCALE, 0, 0, SCALE, OFX, OFY]     # content matrix

# ---------------------------------------------------------------------------
# Canonical class styling (consistent with legend)
# ---------------------------------------------------------------------------
CLASS_STYLE = {
    "A":      {"color": "#0033cc", "w": 2.2, "dash": None,       "name": "Class A", "tp": "4.5 K / 3 bar",      "desc": "LHe supply"},
    "B":      {"color": "#00a6bd", "w": 2.2, "dash": None,       "name": "Class B", "tp": "3.5 K / 27 mbar",    "desc": "2 K LP return"},
    "D":      {"color": "#e00000", "w": 2.2, "dash": None,       "name": "Class D", "tp": "40 K / 14 bar",      "desc": "Thermal shield"},
    "E":      {"color": "#8a8a00", "w": 2.2, "dash": None,       "name": "Class E", "tp": "60 K / 13 bar",      "desc": "60 K return / guard"},
    "WATER":  {"color": "#00a000", "w": 1.8, "dash": None,       "name": "Water",   "tp": "DI cooling water",   "desc": "Coupler / FREIA"},
    "QINFRA": {"color": "#006400", "w": 1.7, "dash": "7,4",      "name": "QINFRA",  "tp": "Scope division",     "desc": "Infrastructure"},
    "AIR":    {"color": "#c000c0", "w": 1.4, "dash": "6,3,1.5,3","name": "Inst. air","tp": "6 (5-7) bar(g)",   "desc": "Pneumatic signal"},
}
CLASS_ORDER = ["A", "B", "D", "E", "WATER", "QINFRA", "AIR"]

GEOM_KEEP = {
    "path": ["d"],
    "line": ["x1", "y1", "x2", "y2"],
    "polyline": ["points"], "polygon": ["points"],
    "rect": ["x", "y", "width", "height", "rx", "ry"],
    "circle": ["cx", "cy", "r"],
    "ellipse": ["cx", "cy", "rx", "ry"],
}


def esc(s):
    return html.escape(str(s), quote=True)


def extract_defs(src_path):
    """Grab <defs>..</defs> blocks verbatim so markers/gradients resolve."""
    raw = open(src_path, encoding="utf-8").read()
    return "\n".join(re.findall(r"<defs\b.*?</defs>", raw, flags=re.S))


# ---------------------------------------------------------------------------
# Re-emission of source geometry
# ---------------------------------------------------------------------------

def carry_markers(style):
    out = []
    for part in (style or "").split(";"):
        k = part.split(":", 1)[0].strip()
        if k.startswith("marker"):
            out.append(part.strip())
    return ";".join(out)


def serialize(el, mode, cls=None):
    """Serialize an extracted Element under the content matrix."""
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
        st = CLASS_STYLE[cls]
        style = (f"fill:none;stroke:{st['color']};stroke-width:{st['w']};"
                 f"stroke-linecap:round;stroke-linejoin:round")
        if st["dash"]:
            style += f";stroke-dasharray:{st['dash']}"
        mk = carry_markers(attrs.get("style"))
        if mk:
            style += ";" + mk
        parts.append(f' style="{style}"')
    elif mode == "process_node":
        st = CLASS_STYLE[cls]
        parts.append(f' style="fill:{st["color"]};stroke:none"')
    elif mode == "process_fill":
        st = CLASS_STYLE[cls]
        parts.append(f' style="fill:{st["color"]};fill-opacity:0.22;'
                     f'stroke:{st["color"]};stroke-width:0.8;stroke-opacity:0.6"')
    elif mode == "boundary":
        parts.append(' style="fill:none;stroke:#222222;stroke-width:1.1;'
                     'stroke-dasharray:5,3"')
    else:  # structure - keep original look, clamp width
        stroke = el.stroke or "#000000"
        fill = el.fill if el.fill else "none"
        w = el.width if el.width else 0.8
        w = max(0.4, min(w, 2.2))
        style = f"fill:{fill};stroke:{stroke};stroke-width:{w}"
        mk = carry_markers(attrs.get("style"))
        if mk:
            style += ";" + mk
        parts.append(f' style="{style}"')
    parts.append("/>")
    return "".join(parts)


# ---------------------------------------------------------------------------
# Layer wrappers
# ---------------------------------------------------------------------------

def layer(lid, label, body, extra=""):
    return (f'<g inkscape:groupmode="layer" id="{lid}" '
            f'inkscape:label="{esc(label)}"{extra}>\n{body}\n</g>')


def cpt(x, y):
    """Map content-space (original) coords to sheet coords."""
    return X.apply(CONTENT_M, x, y)


# ---------------------------------------------------------------------------
# Frame + title block (Layer 1)
# ---------------------------------------------------------------------------

def build_frame(sheet):
    fx0, fy0 = PAPER_MARGIN, PAPER_MARGIN
    fx1, fy1 = SHEET_W - PAPER_MARGIN, SHEET_H - PAPER_MARGIN
    p = [f'<rect x="0" y="0" width="{SHEET_W}" height="{SHEET_H}" fill="#ffffff"/>']
    # outer + inner frame
    p.append(f'<rect x="{fx0}" y="{fy0}" width="{fx1-fx0:.2f}" height="{fy1-fy0:.2f}" '
             f'fill="none" stroke="#000000" stroke-width="2.4"/>')
    p.append(f'<rect x="{fx0+4}" y="{fy0+4}" width="{fx1-fx0-8:.2f}" height="{fy1-fy0-8:.2f}" '
             f'fill="none" stroke="#000000" stroke-width="0.8"/>')
    # title block bottom-right
    tbw, tbh = RIGHT_PANEL_W + 2 * FRAME_PAD, BOTTOM_BAND_H
    tbx = fx1 - 4 - tbw
    tby = fy1 - 4 - tbh
    p.append(f'<rect x="{tbx:.2f}" y="{tby:.2f}" width="{tbw:.2f}" height="{tbh:.2f}" '
             f'fill="#ffffff" stroke="#000000" stroke-width="1.4"/>')
    # title block rows
    rows = [
        ("PROJECT", "MINERVA CryoCell - SCK CEN"),
        ("TITLE", sheet["title"]),
        ("DRAWING No.", sheet["drawing_no"]),
        ("STANDARD", "ISO 10628 / ISA-5.1  -  A3 (420x297 mm)"),
        ("REV / DATE", "v2.0  -  rebuilt 2025"),
    ]
    ry = tby
    rh = tbh / len(rows)
    for i, (k, v) in enumerate(rows):
        yy = ry + i * rh
        if i:
            p.append(f'<line x1="{tbx:.2f}" y1="{yy:.2f}" x2="{tbx+tbw:.2f}" '
                     f'y2="{yy:.2f}" stroke="#000000" stroke-width="0.7"/>')
        p.append(f'<line x1="{tbx+78:.2f}" y1="{yy:.2f}" x2="{tbx+78:.2f}" '
                 f'y2="{yy+rh:.2f}" stroke="#000000" stroke-width="0.7"/>')
        p.append(SYM._text(tbx + 5, yy + rh/2 + 3, k, size=6.6, anchor="start",
                           weight="bold", fill="#444444"))
        vv = v if len(v) <= 44 else v[:43] + "..."
        vsize = 7.2 if len(vv) <= 30 else 6.0
        p.append(SYM._text(tbx + 82, yy + rh/2 + 3, vv, size=vsize, anchor="start",
                           weight="bold"))
    # sheet header strip top-left
    p.append(SYM._text(fx0 + 12, fy0 + 22, "P&ID - " + sheet["title"], size=12,
                       anchor="start", weight="bold"))
    return "\n".join(p), (tbx, tby)


# ---------------------------------------------------------------------------
# Instruments / equipment (Layers 2,5,6)
# ---------------------------------------------------------------------------

VALVE_PREFIX = {"CV": "control", "HV": "manual", "SV": "solenoid", "RV": "relief"}


def family_of(inst):
    layer = (inst.get("layer") or "").upper()
    tag = (inst.get("tag") or "").upper()
    if "RFCELL" in layer or "RF TEE" in layer or "CPLR" in layer and tag.endswith(("X11", "X12", "X21", "X22")):
        pass
    if inst.get("_sheet") == "RFCELL":
        return "RF"
    if "LBI" in layer or "QVB-LBI" in layer:
        return "LBI"
    return "LB"


def build_instruments(seg, sheet_key):
    """Return (symbols_body, tags_body)."""
    insts = list(seg.get("instruments", []))
    # merge safety devices not already present
    seen = {(i.get("tag"), round(i.get("x", 0)), round(i.get("y", 0))) for i in insts}
    for s in seg.get("safety_devices", []):
        key = (s.get("tag"), round(s.get("x", 0)), round(s.get("y", 0)))
        if key not in seen:
            insts.append(s)
            seen.add(key)

    sym, tags = [], []
    for inst in insts:
        if inst.get("x") is None or inst.get("y") is None:
            continue
        inst["_sheet"] = sheet_key
        cx, cy = cpt(inst["x"], inst["y"])
        prefix = (inst.get("prefix") or "").upper()
        number = inst.get("number") or ""
        tag = inst.get("tag") or (prefix + number)
        is_safety = bool(inst.get("is_safety"))
        r = 12.0 * SCALE * 1.18

        vkind = VALVE_PREFIX.get(prefix)
        if vkind:
            sym.append(SYM.valve(cx, cy, kind=vkind, size=8.5 * SCALE * 1.2))
            tags.append(SYM._text(cx, cy + 15 * SCALE + 2, tag, size=6.4, weight="bold"))
            continue

        fam = family_of(inst)
        fill = {"LB": "#ffffff", "RF": "#ffd9d9", "LBI": "#dbe9ff"}[fam]
        dash = ' stroke-dasharray="3,2"' if is_safety else ""
        sym.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="{fill}" '
                   f'stroke="#000000" stroke-width="0.9"{dash}/>')
        # ISA two-line tag (letters / number) inside bubble -> tags layer
        if number:
            tags.append(SYM._text(cx, cy - 0.6, prefix, size=5.9, weight="bold"))
            tags.append(SYM._text(cx, cy + 5.6, number, size=5.9))
        else:
            tags.append(SYM._text(cx, cy + 2.2, tag, size=5.6, weight="bold"))
    return "\n".join(sym), "\n".join(tags)


EQUIP_GLYPH = {
    "Coupler": "cavity", "Cavity": "cavity",
    "Cooling Water Tank": "vessel", "Tuner": "vessel",
    "Vessel / Valve body": "vessel", "Radiation shield": "vessel",
    "Heat Exchanger": "hx",
    "Connector/Coupler node": "node", "Terminal Point": "tp",
    "Pickup antenna": "antenna",
}


def build_equipment(seg):
    body = []
    for eq in seg.get("equipment", []):
        if eq.get("x") is None:
            continue
        cx, cy = cpt(eq["x"], eq["y"])
        kind = eq.get("kind", "")
        label = eq.get("label", "")
        g = EQUIP_GLYPH.get(kind, "node")
        if g == "cavity":
            body.append(SYM.cavity(cx, cy, w=44 * SCALE * 1.1, h=26 * SCALE * 1.1, label=label))
        elif g == "vessel":
            body.append(SYM.vessel(cx, cy, w=34 * SCALE, h=52 * SCALE, label=label))
        elif g == "hx":
            body.append(SYM.heat_exchanger(cx, cy, r=18 * SCALE, label=label))
        elif g == "tp":
            body.append(SYM.terminal_point(cx, cy, label=label, r=5.5 * SCALE * 1.2))
        elif g == "antenna":
            body.append(f'<line x1="{cx:.2f}" y1="{cy:.2f}" x2="{cx:.2f}" y2="{cy-13*SCALE:.2f}" '
                        f'stroke="#000" stroke-width="0.9"/>'
                        f'<circle cx="{cx:.2f}" cy="{cy-13*SCALE:.2f}" r="{3*SCALE:.2f}" '
                        f'fill="#000"/>' + SYM._text(cx, cy + 9, label, size=5.6))
        else:
            body.append(SYM.node(cx, cy, label=label, r=3.5 * SCALE * 1.2))
    return "\n".join(body)


# ---------------------------------------------------------------------------
# Vacuum barriers (Layer 4 additions)
# ---------------------------------------------------------------------------

def build_vacuum_labels(seg):
    body = []
    for vb in seg.get("vacuum_barriers", []):
        if vb.get("type") == "label" and vb.get("x") is not None:
            cx, cy = cpt(vb["x"], vb["y"])
            body.append(SYM._text(cx, cy, vb.get("text", "vacuum barrier"),
                                  size=8, weight="bold", fill="#222222",
                                  style=' font-style="italic"'))
    return "\n".join(body)


# ---------------------------------------------------------------------------
# Legend panels (Layer 7)
# ---------------------------------------------------------------------------

def build_legend(tb_origin):
    fx1 = SHEET_W - PAPER_MARGIN
    px = fx1 - 4 - (RIGHT_PANEL_W + 2 * FRAME_PAD) + 0  # align with title block x
    # right legend panel spans from top frame to just above title block
    px0 = fx1 - 4 - RIGHT_PANEL_W - FRAME_PAD
    py0 = PAPER_MARGIN + 4
    pw = RIGHT_PANEL_W + FRAME_PAD
    ph = tb_origin[1] - 6 - py0
    p = [f'<rect x="{px0:.2f}" y="{py0:.2f}" width="{pw:.2f}" height="{ph:.2f}" '
         f'fill="#fbfbfb" stroke="#000000" stroke-width="1.2"/>']
    x = px0 + 12
    y = py0 + 22
    p.append(SYM._text(px0 + pw/2, y, "LEGEND  -  ISA 5.1 / ISO 10628", size=10,
                       weight="bold"))
    y += 8
    p.append(f'<line x1="{px0+6:.2f}" y1="{y:.2f}" x2="{px0+pw-6:.2f}" y2="{y:.2f}" '
             f'stroke="#000" stroke-width="0.8"/>')
    y += 20

    # --- Instrument symbols ---
    p.append(SYM._text(x, y, "INSTRUMENT BUBBLES (field mounted)", size=7.6,
                       anchor="start", weight="bold")); y += 16
    inst_key = [
        ("#ffffff", False, "LB cryo instrument"),
        ("#ffd9d9", False, "RFCELL instrument"),
        ("#dbe9ff", False, "LBI-specific instrument"),
        ("#ffffff", True,  "Protection / safety (dashed)"),
    ]
    for fill, dsh, lab in inst_key:
        dash = ' stroke-dasharray="3,2"' if dsh else ""
        p.append(f'<circle cx="{x+9:.2f}" cy="{y-2:.2f}" r="8" fill="{fill}" '
                 f'stroke="#000" stroke-width="0.9"{dash}/>')
        p.append(SYM._text(x + 22, y + 1, lab, size=7, anchor="start"))
        y += 20
    # tag explanation
    p.append(SYM._text(x, y, "Tag = [variable][function]-[loop]", size=6.6,
                       anchor="start", style=' font-style="italic"')); y += 11
    p.append(SYM._text(x, y, "e.g. TT-514: T=temperature, T=transmitter", size=6.3,
                       anchor="start", fill="#444")); y += 16

    # --- Valves & equipment ---
    p.append(f'<line x1="{px0+6:.2f}" y1="{y-6:.2f}" x2="{px0+pw-6:.2f}" y2="{y-6:.2f}" '
             f'stroke="#ccc" stroke-width="0.6"/>')
    p.append(SYM._text(x, y + 6, "VALVES & EQUIPMENT", size=7.6, anchor="start",
                       weight="bold")); y += 22
    vk = [("manual", "Hand valve (HV)"), ("control", "Control valve (CV)"),
          ("solenoid", "Solenoid valve (SV)"), ("relief", "Relief valve (RV)")]
    for kind, lab in vk:
        p.append(f'<g transform="translate({x+9:.2f},{y-2:.2f})">'
                 + SYM.valve(0, 0, kind=kind, size=7) + '</g>')
        p.append(SYM._text(x + 26, y + 1, lab, size=7, anchor="start"))
        y += 22
    # vessel + cavity + HX + heat load + TP
    p.append(f'<g transform="translate({x+9:.2f},{y:.2f})">' + SYM.vessel(0, 0, w=14, h=22) + '</g>')
    p.append(SYM._text(x + 26, y + 3, "Vessel / tank", size=7, anchor="start")); y += 26
    p.append(f'<g transform="translate({x+9:.2f},{y:.2f})">' + SYM.cavity(0, 0, w=20, h=12) + '</g>')
    p.append(SYM._text(x + 26, y + 2, "Cavity / coupler body", size=7, anchor="start")); y += 22
    p.append(f'<g transform="translate({x+9:.2f},{y:.2f})">' + SYM.heat_exchanger(0, 0, r=9) + '</g>')
    p.append(SYM._text(x + 26, y + 2, "Heat exchanger", size=7, anchor="start")); y += 22
    p.append(SYM.heat_load(x + 9, y - 2, "#008000"))
    p.append(SYM._text(x + 26, y + 1, "Heat-load callout (HL)", size=7, anchor="start")); y += 20
    p.append(f'<g transform="translate({x+9:.2f},{y-2:.2f})">' + SYM.terminal_point(0, 0, r=6) + '</g>')
    p.append(SYM._text(x + 26, y + 1, "Terminal / scope point", size=7, anchor="start")); y += 22
    # boundary
    p.append(f'<line x1="{x:.2f}" y1="{y-2:.2f}" x2="{x+18:.2f}" y2="{y-2:.2f}" '
             f'stroke="#222" stroke-width="1.1" stroke-dasharray="5,3"/>')
    p.append(SYM._text(x + 26, y + 1, "Vacuum barrier / scope boundary", size=6.6, anchor="start"))
    return "\n".join(p)


def build_class_legend(tb_origin):
    """Process-line class legend in the bottom band (left of title block)."""
    fx0 = PAPER_MARGIN
    fy1 = SHEET_H - PAPER_MARGIN
    bx0 = fx0 + 6
    bx1 = tb_origin[0] - 8
    by0 = tb_origin[1]
    bh = BOTTOM_BAND_H
    p = [f'<rect x="{bx0:.2f}" y="{by0:.2f}" width="{bx1-bx0:.2f}" height="{bh:.2f}" '
         f'fill="#ffffff" stroke="#000000" stroke-width="1.2"/>']
    p.append(SYM._text(bx0 + 8, by0 + 18, "PROCESS LINE CLASSES (colour = service)",
                       size=9, anchor="start", weight="bold"))
    # two-column layout
    items = [(c, CLASS_STYLE[c]) for c in CLASS_ORDER]
    col_w = (bx1 - bx0 - 16) / 2.0
    row_h = 21
    y0 = by0 + 34
    for i, (c, st) in enumerate(items):
        col = i % 2
        row = i // 2
        lx = bx0 + 10 + col * col_w
        ly = y0 + row * row_h
        dash = f' stroke-dasharray="{st["dash"]}"' if st["dash"] else ""
        p.append(f'<line x1="{lx:.2f}" y1="{ly:.2f}" x2="{lx+34:.2f}" y2="{ly:.2f}" '
                 f'stroke="{st["color"]}" stroke-width="{st["w"]+0.6}"{dash}/>')
        lbl = f'{st["name"]}  -  {st["tp"]}  ({st["desc"]})'
        p.append(SYM._text(lx + 42, ly + 3, lbl, size=7.2, anchor="start"))
    return "\n".join(p)


# ---------------------------------------------------------------------------
# Assemble one sheet
# ---------------------------------------------------------------------------

def build_sheet(key):
    sheet = SHEETS[key]
    src_path = os.path.join(SRC, sheet["src"])
    ex = X.load(src_path)
    seg = json.load(open(os.path.join(SEG, sheet["seg"])))
    defs = extract_defs(src_path)

    # bin geometry
    process = defaultdict(list)       # cls -> list of (mode, element)
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
        # 'bubble' bin intentionally dropped (redrawn fresh)

    # ---- Layer 1: frame / title block ----
    frame_body, tb_origin = build_frame(sheet)
    L1 = layer("layer-frame", "L1 - Border / Title block", frame_body)

    # ---- Layer 2: equipment & vessels ----
    struct_body = "\n".join(s for s in (serialize(e, "structure") for e in structure) if s)
    equip_body = build_equipment(seg)
    L2 = layer("layer-equipment", "L2 - Equipment & Vessels",
               struct_body + "\n" + equip_body)

    # ---- Layer 3: process lines (sub-layers) ----
    sub = []
    for cls in CLASS_ORDER:
        els = process.get(cls, [])
        if not els:
            continue
        # draw fills first, then nodes, then lines on top
        order = {"process_fill": 0, "process_node": 1, "process": 2}
        els = sorted(els, key=lambda me: order.get(me[0], 3))
        body = "\n".join(s for s in (serialize(e, mode, cls) for mode, e in els) if s)
        st = CLASS_STYLE[cls]
        sub.append(layer(f"layer-line-{cls}",
                         f"L3.{cls} - {st['name']} ({st['tp']})", body))
    L3 = layer("layer-process", "L3 - Process Lines", "\n".join(sub))

    # ---- Layer 4: vacuum barriers & boundaries ----
    bnd_body = "\n".join(s for s in (serialize(e, "boundary") for e in boundary) if s)
    vac_body = build_vacuum_labels(seg)
    L4 = layer("layer-vacuum", "L4 - Vacuum Barriers & Boundaries",
               bnd_body + "\n" + vac_body)

    # ---- Layers 5 & 6: instruments + tags ----
    sym_body, tag_body = build_instruments(seg, key)
    L5 = layer("layer-instruments", "L5 - Instrumentation Symbols", sym_body)
    L6 = layer("layer-tags", "L6 - ISA 5.1 Tags & Labels", tag_body)

    # ---- Layer 7: legend & annotations ----
    legend_body = build_legend(tb_origin) + "\n" + build_class_legend(tb_origin)
    L7 = layer("layer-legend", "L7 - Legend & Annotations", legend_body)

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
     xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.0.dtd"
     width="420mm" height="297mm"
     viewBox="0 0 {SHEET_W} {SHEET_H}"
     version="1.1">
<title>{esc(sheet["title"])}</title>
<sodipodi:namedview inkscape:document-units="mm" units="mm"/>
{defs}
{L1}
{L2}
{L3}
{L4}
{L5}
{L6}
{L7}
</svg>
'''
    out_path = os.path.join(OUT, f"PID_{key}_improved.svg")
    open(out_path, "w", encoding="utf-8").write(svg)
    counts = {c: len(process.get(c, [])) for c in CLASS_ORDER}
    print(f"[{key}] -> {out_path}")
    print(f"   scale={SCALE:.4f} structure={len(structure)} boundary={len(boundary)} "
          f"process={counts} instruments={len(seg.get('instruments', []))} "
          f"equipment={len(seg.get('equipment', []))}")
    return out_path


def main():
    for key in SHEETS:
        build_sheet(key)


if __name__ == "__main__":
    main()
