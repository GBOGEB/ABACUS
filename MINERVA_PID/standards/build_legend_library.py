#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_legend_library.py
=======================
Authoritative symbol-library builder for the MINERVA / MYRRHA P&ID standard.

Source of truth
---------------
SCK CEN drawing  ``106889-PID00 / MYR100PTF-0521`` --
"MYRRHA - MINERVA  MINERVA P&IDs  GENERAL LEGEND SHEET" (Rev. A, 16/11/2023),
file ``AD_01.16  SUP - PID General Legend Sheet.pdf`` (10 PDF pages = 9 legend
sheets + cover).  Standards basis declared on the sheets:

  * Instrument letter codes      -> subordinate to ISA-5.1-2022 Table 4.1
  * Instrument symbolic repr.    -> subordinate to ISA-5.1-2022 Table 5.1.1
  * Electrical symbols (Sheet 7) -> IEC 60617 (publication 617) unless "*"
  * Piping / process layout      -> ISO 10628 house style
  * Tag numbering                -> SCK CEN/36557490 + mnemonics SCK CEN/36793249

Outputs (written next to this script, in pid_project/standards/)
  * legend_symbols.json   - structured catalogue (every symbol + metadata,
                            naming conventions, colour/stroke spec, usage)
  * symbol_library.svg    - reusable <defs> of <symbol> elements (use via <use>)
  * symbol_library_preview.png - rendered contact-sheet for visual QA (cairosvg)

The script is pure-stdlib (json / xml via string building); cairosvg is only
used for the optional PNG preview and is imported lazily.

All geometry is schematic and standards-based (it reproduces the *meaning* and
the distinguishing graphical features of each legend glyph) rather than being a
pixel copy of the CAD source.  Every <symbol> is drawn in its own viewBox in a
0..100 user-space grid so consumers can scale freely.
"""

import json
import os
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Global drawing / style specification (single source for the JSON + SVG)
# ---------------------------------------------------------------------------
STYLE = {
    "canvas": {
        "background": "#ffffff",
        "default_stroke": "#111111",
        "default_fill": "#ffffff",
        "font_family": "Arial, Helvetica, sans-serif",
    },
    # Stroke widths are quoted in *millimetres* on the legend; the table below
    # maps the legend line-weights to the user-space stroke-width we draw with
    # in the 0..100 symbol grid (≈ x2.2 of the mm value for visual parity).
    "line_weights_mm": {
        "primary": 1.0,
        "secondary": 0.5,
        "signal": 0.25,
        "hvac": 1.0,
    },
    "stroke_width_userspace": {
        "primary": 2.4,
        "secondary": 1.4,
        "signal": 0.9,
        "symbol": 1.8,
        "thin": 1.1,
    },
    "fills": {
        "instrument_field": "#ffffff",
        "filled_marker": "#111111",
        "vessel": "#ffffff",
    },
}

# SVG namespace, assembled from parts to keep it intact through tooling.
SVGNS = "http://" + "www.w3.org/2000/svg"

SW = STYLE["stroke_width_userspace"]
INK = STYLE["canvas"]["default_stroke"]
WHITE = STYLE["canvas"]["default_fill"]
FONT = STYLE["canvas"]["font_family"]


# ---------------------------------------------------------------------------
# Tiny SVG primitive helpers (return strings drawn in the symbol's viewBox)
# ---------------------------------------------------------------------------
def _ln(x1, y1, x2, y2, w=None, dash=None, color=INK):
    w = SW["symbol"] if w is None else w
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="{color}" stroke-width="{w:.2f}"{d} '
            f'stroke-linecap="round"/>')


def _rect(x, y, w, h, sw=None, fill=WHITE, rx=0, dash=None, color=INK):
    sw = SW["symbol"] if sw is None else sw
    d = f' stroke-dasharray="{dash}"' if dash else ""
    r = f' rx="{rx}"' if rx else ""
    return (f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}"{r} '
            f'fill="{fill}" stroke="{color}" stroke-width="{sw:.2f}"{d}/>')


def _circle(cx, cy, r, sw=None, fill=WHITE, dash=None, color=INK):
    sw = SW["symbol"] if sw is None else sw
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="{fill}" '
            f'stroke="{color}" stroke-width="{sw:.2f}"{d}/>')


def _poly(points, sw=None, fill=WHITE, closed=True, dash=None, color=INK):
    sw = SW["symbol"] if sw is None else sw
    d = f' stroke-dasharray="{dash}"' if dash else ""
    pts = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    tag = "polygon" if closed else "polyline"
    f = fill if closed else "none"
    return (f'<{tag} points="{pts}" fill="{f}" stroke="{color}" '
            f'stroke-width="{sw:.2f}"{d} stroke-linejoin="round"/>')


def _path(d, sw=None, fill="none", dash=None, color=INK):
    sw = SW["symbol"] if sw is None else sw
    da = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<path d="{d}" fill="{fill}" stroke="{color}" '
            f'stroke-width="{sw:.2f}"{da} stroke-linejoin="round" '
            f'stroke-linecap="round"/>')


def _txt(x, y, s, size=11, anchor="middle", weight="normal", color=INK,
         style=""):
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-family="{FONT}" '
            f'font-size="{size:.1f}" font-weight="{weight}" '
            f'text-anchor="{anchor}" fill="{color}"{style}>{s}</text>')


# ---------------------------------------------------------------------------
# Re-usable composite glyph builders
# ---------------------------------------------------------------------------
def bowtie(cx=50, cy=55, hw=30, hh=20, stub=True, fill=WHITE):
    """Generic two-triangle (hour-glass) valve body, horizontal run."""
    parts = []
    if stub:
        parts.append(_ln(cx - hw - 20, cy, cx - hw, cy))
        parts.append(_ln(cx + hw, cy, cx + hw + 20, cy))
    parts.append(_poly([(cx - hw, cy - hh), (cx, cy), (cx - hw, cy + hh)], fill=fill))
    parts.append(_poly([(cx + hw, cy - hh), (cx, cy), (cx + hw, cy + hh)], fill=fill))
    return "".join(parts)


def stem(cx, top_y, cy=55):
    return _ln(cx, cy, cx, top_y)


# ============================================================================
#  SYMBOL DRAWING FUNCTIONS
#  Each returns (inner_svg, viewbox_w, viewbox_h).  Drawn in a 0..W / 0..H grid.
# ============================================================================
DRAW = {}          # id -> callable -> (inner, w, h)


def reg(symbol_id):
    def deco(fn):
        DRAW[symbol_id] = fn
        return fn
    return deco


# ---- 1. LINE TYPES (Sheet 1) ----------------------------------------------
LW = 140  # line sample width
LH = 28
MY = LH / 2


def _line_sample(extra="", w_key="symbol", dash=None):
    return _ln(6, MY, LW - 6, MY, w=SW[w_key], dash=dash) + extra


@reg("line-primary")
def _():
    arrow = _poly([(LW - 20, MY - 6), (LW - 6, MY), (LW - 20, MY + 6)], fill=INK)
    return _ln(6, MY, LW - 14, MY, w=SW["primary"]) + arrow, LW, LH


@reg("line-secondary")
def _():
    arrow = _poly([(LW - 20, MY - 5), (LW - 6, MY), (LW - 20, MY + 5)], fill=INK)
    return _ln(6, MY, LW - 14, MY, w=SW["secondary"]) + arrow, LW, LH


@reg("line-primary-future")
def _():
    arrow = _poly([(LW - 20, MY - 6), (LW - 6, MY), (LW - 20, MY + 6)], fill=INK)
    return _ln(6, MY, LW - 14, MY, w=SW["primary"], dash="14,4,2,4") + arrow, LW, LH


@reg("line-secondary-future")
def _():
    arrow = _poly([(LW - 20, MY - 5), (LW - 6, MY), (LW - 20, MY + 5)], fill=INK)
    return _ln(6, MY, LW - 14, MY, w=SW["secondary"], dash="12,3,2,3") + arrow, LW, LH


@reg("line-electrical-signal")
def _():
    return _line_sample(w_key="signal", dash="9,6"), LW, LH


@reg("line-pneumatic-signal")
def _():
    base = _ln(6, MY, LW - 6, MY, w=SW["signal"])
    ticks = ""
    for x in (44, 96):
        ticks += _ln(x - 6, MY + 7, x + 6, MY - 7, w=SW["thin"])
        ticks += _ln(x - 1, MY + 7, x + 11, MY - 7, w=SW["thin"])
    return base + ticks, LW, LH


@reg("line-hydraulic-signal")
def _():
    base = _ln(6, MY, LW - 6, MY, w=SW["signal"])
    marks = ""
    for x in (40, 96):
        marks += _path(f"M {x} {MY} L {x} {MY+7} L {x+9} {MY+7}", sw=SW["thin"])
    return base + marks, LW, LH


@reg("line-software-signal")
def _():
    base = _ln(6, MY, LW - 6, MY, w=SW["signal"])
    rings = _circle(46, MY, 4, sw=SW["thin"]) + _circle(96, MY, 4, sw=SW["thin"])
    return base + rings, LW, LH


@reg("line-em-sonic-signal")
def _():
    base = _ln(6, MY, LW - 6, MY, w=SW["signal"])
    wave = _path(f"M 56 {MY} q 6 -8 12 0 q 6 8 12 0", sw=SW["thin"])
    return base + wave, LW, LH


@reg("line-capillary")
def _():
    base = _ln(6, MY, LW - 6, MY, w=SW["signal"])
    xs = ""
    for x in (44, 96):
        xs += _ln(x - 5, MY - 5, x + 5, MY + 5, w=SW["thin"])
        xs += _ln(x - 5, MY + 5, x + 5, MY - 5, w=SW["thin"])
    return base + xs, LW, LH


@reg("line-hose")
def _():
    return _path(f"M 6 {MY} q 9 -9 18 0 q 9 9 18 0 q 9 -9 18 0 q 9 9 18 0 "
                 f"q 9 -9 18 0 q 9 9 18 0 q 9 -9 18 0", sw=SW["symbol"]), LW, LH


@reg("line-pipe-insulated")
def _():
    base = _ln(6, MY, LW - 6, MY, w=SW["primary"])
    hatch = ""
    for x in range(18, LW - 12, 12):
        hatch += _ln(x, MY - 8, x + 8, MY + 0, w=SW["thin"])
    return base + hatch, LW, LH


@reg("line-tracer")
def _():
    base = _ln(6, MY - 4, LW - 6, MY - 4, w=SW["symbol"])
    trace = _ln(6, MY + 4, LW - 6, MY + 4, w=SW["thin"], dash="10,6")
    return base + trace, LW, LH


@reg("line-jacketed")
def _():
    return (_rect(20, MY - 7, LW - 40, 14, sw=SW["thin"]) +
            _ln(6, MY, 20, MY, w=SW["symbol"]) +
            _ln(LW - 20, MY, LW - 6, MY, w=SW["symbol"])), LW, LH


@reg("line-heated-insulated")
def _():
    base = _ln(6, MY, LW - 6, MY, w=SW["primary"])
    hatch = ""
    for x in range(18, LW - 12, 12):
        hatch += _ln(x, MY - 8, x + 8, MY, w=SW["thin"])
    tr = _ln(6, MY + 7, LW - 6, MY + 7, w=SW["thin"], dash="9,6")
    return base + hatch + tr, LW, LH


@reg("line-hvac-supply")
def _():
    return _ln(6, MY, LW - 6, MY, w=SW["primary"]), LW, LH


@reg("line-hvac-return")
def _():
    return _ln(6, MY, LW - 6, MY, w=SW["primary"], dash="16,5,3,5"), LW, LH


@reg("conn-connected-lines")
def _():
    return (_ln(50, 6, 50, LH - 6, w=SW["symbol"]) +
            _path(f"M 20 {MY} q 30 -10 60 0", sw=SW["symbol"])), 100, LH


@reg("conn-non-connected-lines")
def _():
    return (_ln(50, 6, 50, MY - 4, w=SW["symbol"]) +
            _ln(50, MY + 4, 50, LH - 6, w=SW["symbol"]) +
            _path(f"M 24 {MY} q 26 -12 52 0", sw=SW["symbol"])), 100, LH


# ---- 2. INSTRUMENT BUBBLES (Sheet 2 - ISA 5.1 Table 5.1.1 matrix) ---------
# type column: A=BPCS (square+circle), B=SIS (square+circle+diagonals),
#              C=computer/software (hexagon), D=discrete (circle), oval=2 instr.
# location row line through middle: 1 none, 2 single solid, 3 single dashed,
#              4 double solid, 5 double dashed.
BW = 64
BH = 64
BCX = BW / 2
BCY = BH / 2
BR = 22


def _loc_lines(row):
    """Horizontal accessibility line(s) across a bubble of half-width BR."""
    x0, x1 = BCX - BR, BCX + BR
    if row == 1:
        return ""
    if row == 2:
        return _ln(x0, BCY, x1, BCY, w=SW["thin"])
    if row == 3:
        return _ln(x0, BCY, x1, BCY, w=SW["thin"], dash="5,3")
    if row == 4:
        return (_ln(x0, BCY - 3, x1, BCY - 3, w=SW["thin"]) +
                _ln(x0, BCY + 3, x1, BCY + 3, w=SW["thin"]))
    if row == 5:
        return (_ln(x0, BCY - 3, x1, BCY - 3, w=SW["thin"], dash="5,3") +
                _ln(x0, BCY + 3, x1, BCY + 3, w=SW["thin"], dash="5,3"))
    return ""


def _bubble_factory(col, row):
    def fn():
        parts = []
        if col == "A":   # square enclosing a circle
            parts.append(_rect(BCX - BR, BCY - BR, 2 * BR, 2 * BR, sw=SW["symbol"]))
            parts.append(_circle(BCX, BCY, BR, sw=SW["symbol"]))
        elif col == "B":  # SIS: square + circle + diagonals
            parts.append(_rect(BCX - BR, BCY - BR, 2 * BR, 2 * BR, sw=SW["symbol"]))
            parts.append(_circle(BCX, BCY, BR, sw=SW["symbol"]))
            parts.append(_ln(BCX - BR, BCY - BR, BCX + BR, BCY + BR, w=SW["thin"]))
            parts.append(_ln(BCX - BR, BCY + BR, BCX + BR, BCY - BR, w=SW["thin"]))
        elif col == "C":  # hexagon
            r = BR + 2
            pts = [(BCX - r, BCY), (BCX - r / 2, BCY - r * 0.9),
                   (BCX + r / 2, BCY - r * 0.9), (BCX + r, BCY),
                   (BCX + r / 2, BCY + r * 0.9), (BCX - r / 2, BCY + r * 0.9)]
            parts.append(_poly(pts, sw=SW["symbol"]))
        elif col == "D":  # discrete plain circle
            parts.append(_circle(BCX, BCY, BR, sw=SW["symbol"]))
        parts.append(_loc_lines(row))
        return "".join(parts), BW, BH
    return fn


for _c in ("A", "B", "C", "D"):
    for _r in range(1, 6):
        reg(f"inst-{_c}{_r}")(_bubble_factory(_c, _r))


@reg("inst-discrete-oval")
def _():
    """Two-instrument shared discrete enclosure (stadium/oval)."""
    w, h = 96, 56
    return (_rect(8, h / 2 - 18, w - 16, 36, rx=18, sw=SW["symbol"]) +
            _ln(w / 2, h / 2 - 18, w / 2, h / 2 + 18, w=SW["thin"])), w, h


# ---- 3. VALVES (Sheet 3 - valve graphical symbols) ------------------------
VW = 100
VH = 100
VCY = 55


@reg("valve-generic")
def _():
    return bowtie(), VW, VH


@reg("valve-angle")
def _():
    # bottom-up + left-in angle valve
    return (_poly([(50, 55), (20, 38), (20, 72)], fill=WHITE) +
            _poly([(50, 55), (33, 85), (67, 85)], fill=WHITE) +
            _ln(0, 55, 20, 55) + _ln(50, 85, 50, 100)), VW, VH


@reg("valve-three-way")
def _():
    return (bowtie(stub=True) +
            _poly([(50, 55), (38, 80), (62, 80)], fill=WHITE) +
            _ln(50, 80, 50, 100)), VW, VH


@reg("valve-gate")
def _():
    return bowtie(), VW, VH


@reg("valve-globe")
def _():
    return bowtie() + _circle(50, 55, 9, sw=SW["thin"], fill=WHITE), VW, VH


@reg("valve-ball")
def _():
    return bowtie() + _circle(50, 55, 11, sw=SW["symbol"], fill=WHITE), VW, VH


@reg("valve-needle")
def _():
    return (bowtie() +
            _poly([(50, 40), (46, 55), (54, 55)], fill=INK)), VW, VH


@reg("valve-butterfly")
def _():
    return (bowtie() +
            _ln(50, 44, 50, 66, w=SW["symbol"]) +
            _circle(50, 44, 2.4, fill=INK, sw=0.6) +
            _circle(50, 66, 2.4, fill=INK, sw=0.6)), VW, VH


@reg("valve-check")
def _():
    # flow ball/disc against seat: triangle + bar
    return (_ln(0, 55, 100, 55) +
            _poly([(30, 40), (30, 70), (62, 55)], fill=WHITE) +
            _ln(64, 40, 64, 70, w=SW["symbol"])), VW, VH


@reg("valve-swing-check")
def _():
    return (_ln(0, 55, 100, 55) +
            _poly([(28, 42), (28, 68), (60, 55)], fill=INK) +
            _ln(64, 38, 64, 72, w=SW["symbol"])), VW, VH


@reg("valve-ball-check")
def _():
    return (_ln(0, 55, 100, 55) +
            bowtie(hw=24, hh=16, stub=False) +
            _circle(50, 55, 7, fill=INK, sw=0.6)), VW, VH


@reg("valve-globe-check")
def _():
    return (bowtie() + _circle(50, 55, 9, sw=SW["thin"]) +
            _poly([(40, 47), (40, 63), (56, 55)], fill=INK)), VW, VH


@reg("valve-safety")
def _():
    # bow-tie with offset stem + spring zig (angle relief)
    return (bowtie() + stem(50, 18) +
            _path("M 44 18 l 12 -6 l -12 -6 l 12 -6", sw=SW["thin"])), VW, VH


@reg("valve-safety-spring-angle")
def _():
    return (_poly([(50, 60), (24, 44), (24, 76)], fill=WHITE) +
            _ln(0, 60, 24, 60) +
            _ln(50, 60, 50, 20, w=SW["symbol"]) +
            _path("M 42 20 l 16 -5 l -16 -5 l 16 -5 l -16 -5", sw=SW["thin"]) +
            _ln(50, 60, 50, 100)), VW, VH


@reg("valve-pressure-reducing")
def _():
    return (bowtie() + stem(50, 22) +
            _path("M 40 22 q 10 -12 20 0", sw=SW["symbol"]) +
            _txt(50, 14, "", size=1)), VW, VH


@reg("valve-y-globe")
def _():
    return (_ln(0, 60, 100, 60) +
            _poly([(28, 48), (52, 60), (28, 72)], fill=WHITE) +
            _poly([(72, 48), (52, 60), (72, 72)], fill=WHITE) +
            _ln(52, 60, 70, 32, w=SW["symbol"]) +
            _circle(70, 30, 5, sw=SW["thin"])), VW, VH


@reg("valve-tilting-disk-check")
def _():
    return (_ln(0, 55, 100, 55) +
            bowtie(hw=24, hh=16, stub=False) +
            _ln(40, 44, 60, 66, w=SW["symbol"])), VW, VH


@reg("valve-piston-lift-check")
def _():
    return (_ln(0, 55, 100, 55) +
            bowtie(hw=24, hh=16, stub=False) +
            _rect(45, 44, 10, 22, sw=SW["thin"], fill=WHITE)), VW, VH


@reg("valve-y-piston-lift-check")
def _():
    return (_ln(0, 60, 100, 60) +
            _poly([(28, 48), (52, 60), (28, 72)], fill=WHITE) +
            _poly([(72, 48), (52, 60), (72, 72)], fill=WHITE) +
            _rect(46, 28, 12, 16, sw=SW["thin"], fill=WHITE) +
            _ln(52, 44, 52, 60, w=SW["symbol"])), VW, VH


@reg("valve-butterfly-check")
def _():
    return (_ln(0, 55, 100, 55) +
            _poly([(34, 42), (66, 42), (50, 68)], fill=WHITE)), VW, VH


@reg("valve-balancing")
def _():
    return (bowtie() +
            _ln(36, 40, 64, 40, w=SW["symbol"]) +
            _path("M 36 40 l 0 -8 M 64 40 l 0 -8", sw=SW["thin"])), VW, VH


@reg("valve-differential-pressure")
def _():
    return (bowtie() + stem(50, 22) +
            _path("M 41 22 l 18 0 M 41 16 l 18 0", sw=SW["thin"]) +
            _path("M 42 22 l 16 -6 l -16 -6 l 16 -6", sw=SW["thin"])), VW, VH


# ---- 4. ACTUATORS / ACTUATING ELEMENTS (Sheet 3) --------------------------
def _valve_with_top(top_svg):
    def fn():
        return bowtie() + stem(50, 33) + top_svg, VW, VH
    return fn


reg("act-diaphragm")(_valve_with_top(
    _path("M 32 33 q 18 -20 36 0 Z", sw=SW["symbol"])))
reg("act-piston")(_valve_with_top(
    _rect(40, 14, 20, 19, sw=SW["symbol"]) + _ln(50, 14, 50, 33, w=SW["thin"])))
reg("act-hydraulic")(_valve_with_top(
    _rect(40, 14, 20, 19, sw=SW["symbol"]) + _txt(50, 28, "H", size=12, weight="bold")))
reg("act-solenoid")(_valve_with_top(
    _rect(40, 14, 20, 19, sw=SW["symbol"]) + _txt(50, 28, "S", size=12, weight="bold")))
reg("act-manual")(_valve_with_top(
    _ln(34, 16, 66, 16, w=SW["symbol"]) + _ln(50, 16, 50, 33, w=SW["thin"])))


@reg("act-motor-electric")
def _():
    return bowtie() + stem(50, 30) + _circle(50, 18, 12, sw=SW["symbol"]) + \
        _txt(50, 22, "M", size=12, weight="bold"), VW, VH


@reg("act-motor-dc")
def _():
    return bowtie() + stem(50, 30) + _circle(50, 18, 12, sw=SW["symbol"]) + \
        _txt(50, 22, "M", size=11, weight="bold") + \
        _ln(40, 32, 60, 32, w=SW["thin"]), VW, VH


@reg("act-motor-pos-transmit")
def _():
    return bowtie() + stem(50, 30) + _circle(50, 18, 12, sw=SW["symbol"]) + \
        _txt(50, 22, "M", size=11, weight="bold") + \
        _circle(70, 18, 6, sw=SW["thin"]), VW, VH


def _self_acting(tag):
    def fn():
        return (bowtie() + stem(50, 33) +
                _path("M 32 33 q 18 -20 36 0 Z", sw=SW["symbol"]) +
                _ln(50, 18, 70, 12, w=SW["thin"]) +
                _circle(78, 12, 9, sw=SW["thin"]) +
                _txt(78, 15, tag, size=7, weight="bold")), VW, VH
    return fn


reg("act-self-fcv")(_self_acting("FCV"))
reg("act-self-pcv")(_self_acting("PCV"))
reg("act-self-tcv")(_self_acting("TCV"))
reg("act-self-lcv")(_self_acting("LCV"))


@reg("act-fixed-spring")
def _():
    return bowtie() + stem(50, 30) + \
        _path("M 42 30 l 16 -4 l -16 -4 l 16 -4 l -16 -4", sw=SW["thin"]), VW, VH


@reg("act-float")
def _():
    return bowtie() + stem(50, 33) + _circle(58, 26, 6, sw=SW["thin"]), VW, VH


@reg("act-weight")
def _():
    return bowtie() + stem(50, 26) + _circle(50, 20, 6, fill=INK, sw=0.6), VW, VH


@reg("act-high-speed")
def _():
    return bowtie() + stem(50, 24) + \
        _path("M 44 24 l 12 -8 l -12 0 l 12 -8", sw=SW["thin"]), VW, VH


def _fail(letter):
    def fn():
        return (bowtie() + stem(50, 14) +
                _rect(40, 14, 20, 19, sw=SW["symbol"]) +
                _txt(50, 28, letter, size=9, weight="bold")), VW, VH
    return fn


reg("act-fail-closed")(_fail("FC"))
reg("act-fail-open")(_fail("FO"))
reg("act-fail-as-is")(_fail("FA"))


# ---- 5. EQUIPMENT (Sheet 4) -----------------------------------------------
@reg("eq-pump-liquid")
def _():
    return _circle(50, 50, 30, sw=SW["symbol"]) + \
        _poly([(50, 20), (50, 80), (80, 50)], fill=WHITE, sw=SW["thin"]), 100, 100


@reg("eq-compressor-vacuum")
def _():
    return _circle(50, 50, 30, sw=SW["symbol"]), 100, 100


@reg("eq-pump-centrifugal")
def _():
    return _circle(50, 50, 30, sw=SW["symbol"]) + \
        _ln(20, 50, 50, 30, w=SW["thin"]) + _ln(20, 50, 50, 70, w=SW["thin"]), 100, 100


@reg("eq-turbo-compressor")
def _():
    return _circle(50, 50, 30, sw=SW["symbol"]) + _circle(50, 50, 10, sw=SW["thin"]), 100, 100


@reg("eq-blower-fan")
def _():
    return _circle(50, 50, 30, sw=SW["symbol"]) + \
        _path("M 50 50 q -18 -10 -22 -22 M 50 50 q 18 -10 22 -22 M 50 50 q 0 22 0 26",
              sw=SW["thin"]), 100, 100


@reg("eq-pump-cavity")
def _():
    return _circle(50, 50, 30, sw=SW["symbol"]) + \
        _path("M 30 50 q 7 -12 14 0 q 7 12 14 0", sw=SW["thin"]), 100, 100


@reg("eq-heat-exchanger-general")
def _():
    return _circle(50, 50, 30, sw=SW["symbol"]) + \
        _path("M 20 50 L 38 36 L 62 64 L 80 50", sw=SW["symbol"]), 100, 100


@reg("eq-heat-exchanger-u-tube")
def _():
    return _rect(20, 30, 60, 40, sw=SW["symbol"]) + \
        _path("M 30 38 L 70 38 q 8 0 8 6 q 0 6 -8 6 L 30 50", sw=SW["thin"]), 100, 100


@reg("eq-heat-exchanger-plate")
def _():
    return _rect(25, 30, 50, 40, sw=SW["symbol"]) + \
        _ln(25, 30, 75, 70, w=SW["thin"]) + _ln(75, 30, 25, 70, w=SW["thin"]), 100, 100


@reg("eq-electric-heater")
def _():
    return _rect(25, 35, 50, 30, sw=SW["symbol"]) + \
        _txt(34, 54, "E", size=12, weight="bold") + \
        _path("M 46 44 h 22 M 46 50 h 22 M 46 56 h 22", sw=SW["thin"]), 100, 100


@reg("eq-gas-filter")
def _():
    return _rect(35, 20, 30, 60, sw=SW["symbol"]) + \
        _ln(35, 35, 65, 35, w=SW["thin"]) + _ln(35, 65, 65, 65, w=SW["thin"]), 100, 100


@reg("eq-gas-filter-hepa")
def _():
    return _rect(30, 25, 40, 50, sw=SW["symbol"]) + \
        _txt(50, 53, "HEPA", size=9, weight="bold"), 100, 100


@reg("eq-liquid-filter")
def _():
    return _rect(35, 20, 30, 60, sw=SW["symbol"]) + \
        _ln(35, 50, 65, 50, w=SW["thin"], dash="4,3"), 100, 100


@reg("eq-mixed-bed-filter")
def _():
    return _rect(35, 20, 30, 60, sw=SW["symbol"]) + \
        _path("M 35 35 L 65 50 L 35 65 M 65 35 L 35 50 L 65 65", sw=SW["thin"]), 100, 100


@reg("eq-ion-exchanger")
def _():
    return _rect(30, 25, 40, 50, sw=SW["symbol"]) + \
        _txt(50, 53, "ION", size=9, weight="bold"), 100, 100


@reg("eq-charcoal-filter")
def _():
    return _rect(35, 20, 30, 60, sw=SW["symbol"]) + \
        _rect(46, 35, 8, 30, sw=SW["thin"]), 100, 100


@reg("eq-horizontal-tank")
def _():
    return _path("M 25 35 q -10 15 0 30 L 75 65 q 10 -15 0 -30 Z", sw=SW["symbol"]), 100, 100


@reg("eq-vertical-tank")
def _():
    return _path("M 35 30 q 15 -8 30 0 L 65 70 q -15 8 -30 0 Z", sw=SW["symbol"]), 100, 100


@reg("eq-conical-tank")
def _():
    return _poly([(30, 30), (70, 30), (70, 55), (50, 75), (30, 55)], sw=SW["symbol"]) + \
        _path("M 30 30 q 20 -8 40 0", sw=SW["thin"]), 100, 100


@reg("eq-hopper")
def _():
    return _poly([(28, 35), (72, 35), (50, 72)], sw=SW["symbol"]), 100, 100


@reg("eq-steam-generator")
def _():
    return _rect(30, 28, 40, 44, sw=SW["symbol"]) + _ln(30, 28, 70, 72, w=SW["thin"]), 100, 100


@reg("eq-chiller")
def _():
    return (_rect(28, 30, 44, 40, sw=SW["symbol"]) +
            _ln(28, 50, 72, 50, w=SW["thin"]) +
            _txt(50, 42, "COND", size=6) + _txt(50, 64, "EVAP", size=6) +
            _circle(50, 50, 7, sw=SW["thin"])), 100, 100


@reg("eq-rupture-disc")
def _():
    return _ln(50, 20, 50, 80, w=SW["symbol"]) + \
        _path("M 50 35 q 14 15 0 30", sw=SW["thin"]), 100, 100


@reg("eq-steam-trap")
def _():
    return _ln(0, 50, 100, 50) + _circle(50, 50, 14, sw=SW["symbol"]) + \
        _path("M 38 50 A 14 14 0 0 1 62 50 Z", fill=INK, sw=0.5), 100, 100


@reg("eq-viewing-glass")
def _():
    return _ln(0, 50, 100, 50) + _rect(34, 40, 32, 20, sw=SW["symbol"]) + \
        _circle(50, 50, 6, sw=SW["thin"]), 100, 100


@reg("eq-orifice-plate-line")
def _():
    return _ln(0, 50, 100, 50) + _ln(50, 30, 50, 70, w=SW["symbol"]) + \
        _ln(46, 38, 46, 62, w=SW["thin"]) + _ln(54, 38, 54, 62, w=SW["thin"]), 100, 100


# ---- 6. EQUIPMENT CONNECTIONS / END TYPES (Sheet 3) -----------------------
CW, CH = 110, 40
CCY = CH / 2


@reg("conn-threaded")
def _():
    return (_ln(8, CCY, 38, CCY) + _ln(72, CCY, 102, CCY) +
            _rect(38, CCY - 8, 34, 16, sw=SW["thin"], dash="4,2") +
            _ln(38, CCY - 10, 38, CCY + 10, w=SW["symbol"]) +
            _ln(72, CCY - 10, 72, CCY + 10, w=SW["symbol"])), CW, CH


@reg("conn-flanged-ends")
def _():
    return (_ln(8, CCY, 38, CCY) + _ln(72, CCY, 102, CCY) +
            _rect(38, CCY - 7, 34, 14, sw=SW["thin"]) +
            _ln(38, CCY - 12, 38, CCY + 12, w=SW["symbol"]) +
            _ln(72, CCY - 12, 72, CCY + 12, w=SW["symbol"])), CW, CH


@reg("conn-wafer")
def _():
    return (_ln(8, CCY, 40, CCY) + _ln(70, CCY, 102, CCY) +
            _rect(40, CCY - 7, 30, 14, sw=SW["thin"], dash="3,2") +
            _ln(40, CCY - 11, 40, CCY + 11, w=SW["symbol"]) +
            _ln(70, CCY - 11, 70, CCY + 11, w=SW["symbol"]) +
            _ln(55, CCY - 11, 55, CCY + 11, w=SW["thin"])), CW, CH


@reg("conn-welded-ends")
def _():
    return (_ln(8, CCY, 40, CCY) + _ln(70, CCY, 102, CCY) +
            _rect(40, CCY - 6, 30, 12, sw=SW["thin"], dash="3,2") +
            _circle(40, CCY, 3, fill=INK, sw=0.5) +
            _circle(70, CCY, 3, fill=INK, sw=0.5)), CW, CH


@reg("conn-quick-coupling")
def _():
    return (_ln(8, CCY, 40, CCY) +
            _rect(40, CCY - 6, 26, 12, sw=SW["thin"], dash="3,2") +
            _path(f"M 66 {CCY} l 10 0 l 0 -10 l 8 0", sw=SW["symbol"])), CW, CH


@reg("conn-hose")
def _():
    return (_ln(8, CCY, 40, CCY) + _ln(70, CCY, 102, CCY) +
            _rect(40, CCY - 6, 30, 12, sw=SW["thin"], dash="3,2") +
            _path(f"M 36 {CCY} l -6 -6 M 74 {CCY} l 6 6", sw=SW["thin"])), CW, CH


@reg("conn-flanged-connection")
def _():
    return (_ln(8, CCY, 50, CCY) + _ln(60, CCY, 102, CCY) +
            _ln(50, CCY - 12, 50, CCY + 12, w=SW["symbol"]) +
            _ln(60, CCY - 12, 60, CCY + 12, w=SW["symbol"])), CW, CH


@reg("conn-isolating-flange")
def _():
    return (_ln(8, CCY, 48, CCY) + _ln(62, CCY, 102, CCY) +
            _ln(48, CCY - 12, 48, CCY + 12, w=SW["symbol"]) +
            _ln(62, CCY - 12, 62, CCY + 12, w=SW["symbol"]) +
            _rect(52, CCY - 8, 6, 16, sw=SW["thin"], fill=INK)), CW, CH


@reg("conn-blind-flange")
def _():
    return (_ln(8, CCY, 60, CCY) +
            _ln(60, CCY - 13, 60, CCY + 13, w=SW["symbol"])), CW, CH


@reg("conn-screw-cap")
def _():
    return (_ln(8, CCY, 58, CCY) +
            _ln(58, CCY - 11, 58, CCY + 11, w=SW["symbol"]) +
            _ln(64, CCY - 11, 64, CCY + 11, w=SW["thin"])), CW, CH


@reg("conn-welded-cap")
def _():
    return (_ln(8, CCY, 60, CCY) +
            _path(f"M 60 {CCY-12} q 14 12 0 24", sw=SW["symbol"])), CW, CH


@reg("conn-reducer")
def _():
    return (_ln(8, CCY, 40, CCY) + _ln(70, CCY, 102, CCY) +
            _poly([(40, CCY - 12), (70, CCY - 6), (70, CCY + 6), (40, CCY + 12)],
                  sw=SW["symbol"])), CW, CH


# ---- 7. INTERFACES / SCOPE BOUNDARIES (Sheet 1) ---------------------------
@reg("iface-termination-point")
def _():
    return (_poly([(50, 20), (78, 50), (50, 80), (22, 50)], sw=SW["symbol"]) +
            _txt(50, 16, "TPXYYYY", size=8) +
            _txt(50, 92, "ZZZ", size=8)), 100, 100


@reg("iface-offpage-connector")
def _():
    w, h = 150, 46
    return (_poly([(10, 8), (118, 8), (140, 23), (118, 38), (10, 38)],
                  sw=SW["symbol"]) +
            _ln(10, 23, 118, 23, w=SW["thin"]) +
            _txt(40, 19, "XXXXX", size=8) +
            _txt(85, 19, "123456-PID01", size=8) +
            _txt(40, 34, "WWWWW", size=8)), w, h


@reg("iface-system-nfs")
def _():
    return (bowtie(cx=50, cy=30, hw=20, hh=13) +
            _ln(74, 30, 110, 30, w=SW["primary"], dash="14,6")), 120, 60


@reg("scope-design-limit")
def _():
    return (bowtie(cx=50, cy=24, hw=18, hh=12, stub=True) +
            _ln(50, 24, 50, 60, w=SW["thin"]) +
            _poly([(50, 60), (66, 76), (50, 92), (34, 76)], sw=SW["symbol"])), 100, 100


@reg("scope-code-jurisdiction")
def _():
    return (bowtie(cx=42, cy=24, hw=16, hh=11, stub=False) +
            _ln(8, 24, 26, 24) +
            _ln(58, 24, 78, 24, w=SW["primary"], dash="12,5") +
            _ln(42, 24, 42, 56, w=SW["thin"]) +
            _poly([(42, 56), (56, 70), (42, 84), (28, 70)], sw=SW["symbol"]) +
            _txt(20, 96, "ASME VIII", size=7, anchor="start") +
            _txt(96, 96, "ASME B31.3", size=7, anchor="end")), 110, 100


# ---- 8. FLOW / INSTRUMENT INLINE ELEMENTS (Sheet 3) -----------------------
def _inline_box(label, body_extra=""):
    def fn():
        return (_ln(0, 50, 28, 50) + _ln(72, 50, 100, 50) +
                _rect(28, 38, 44, 24, sw=SW["symbol"]) +
                (_txt(50, 55, label, size=11, weight="bold") if label else "") +
                body_extra), 100, 100
    return fn


reg("flow-sonic")(_inline_box("S"))
reg("flow-variable-area")(_inline_box("", _circle(50, 50, 10, sw=SW["thin"]) +
                                      _ln(44, 56, 56, 44, w=SW["thin"])))
reg("flow-coriolis")(_inline_box("", _path("M 38 50 q 6 -10 12 0 q 6 10 12 0",
                                           sw=SW["thin"])))
reg("flow-magnetic")(_inline_box("M"))
reg("flow-vortex")(_inline_box("", _path("M 40 44 q 6 6 0 12 q -6 6 0 12",
                                         sw=SW["thin"])))
reg("flow-radiation")(_inline_box("R"))


@reg("flow-orifice-generic")
def _():
    return (_ln(0, 50, 100, 50) + _ln(50, 32, 50, 68, w=SW["symbol"]) +
            _ln(44, 40, 44, 60, w=SW["thin"]) + _ln(56, 40, 56, 60, w=SW["thin"])), 100, 100


@reg("flow-nozzle")
def _():
    return (_ln(0, 50, 38, 50) + _ln(62, 50, 100, 50) +
            _path("M 38 38 L 62 46 L 62 54 L 38 62", sw=SW["symbol"])), 100, 100


@reg("flow-venturi")
def _():
    return (_ln(0, 50, 30, 50) + _ln(70, 50, 100, 50) +
            _poly([(30, 36), (50, 47), (70, 36)], sw=SW["symbol"], fill="none", closed=False) +
            _poly([(30, 64), (50, 53), (70, 64)], sw=SW["symbol"], fill="none", closed=False)), 100, 100


@reg("flow-positive-displacement")
def _():
    return (_ln(0, 50, 30, 50) + _ln(70, 50, 100, 50) +
            _rect(30, 40, 40, 20, rx=10, sw=SW["symbol"]) +
            _circle(42, 50, 5, sw=SW["thin"]) + _circle(58, 50, 5, sw=SW["thin"])), 100, 100


@reg("flow-turbine")
def _():
    return (_ln(0, 50, 30, 50) + _ln(70, 50, 100, 50) +
            _rect(30, 40, 40, 20, sw=SW["symbol"]) +
            _path("M 40 60 L 50 40 L 60 60 M 40 40 L 50 60 L 60 40", sw=SW["thin"])), 100, 100


# ---- 9. MISCELLANEOUS / SPECIALTY ITEMS (Sheet 5) -------------------------
@reg("misc-reducer")
def _():
    return (_ln(0, 50, 35, 50) + _ln(65, 50, 100, 50) +
            _poly([(35, 40), (65, 46), (65, 54), (35, 60)], sw=SW["symbol"]) +
            _txt(50, 30, "DN1/DN2", size=7)), 100, 70


@reg("misc-vfd")
def _():
    return _rect(28, 35, 44, 30, sw=SW["symbol"]) + _txt(50, 54, "VFD", size=10, weight="bold"), 100, 100


@reg("misc-flame-arrestor")
def _():
    return (_ln(0, 50, 100, 50) + _rect(38, 35, 24, 30, sw=SW["symbol"]) +
            _ln(50, 35, 50, 65, w=SW["thin"]) +
            _ln(44, 35, 44, 65, w=SW["thin"]) + _ln(56, 35, 56, 65, w=SW["thin"])), 100, 100


@reg("misc-dielectric-joint")
def _():
    return (_ln(0, 50, 40, 50) + _ln(60, 50, 100, 50) +
            _rect(40, 42, 20, 16, sw=SW["symbol"]) +
            _rect(46, 46, 8, 8, sw=SW["thin"])), 100, 100


@reg("misc-strainer-y")
def _():
    return (_ln(0, 50, 100, 50) +
            _ln(40, 50, 64, 74, w=SW["symbol"]) +
            _ln(64, 74, 72, 66, w=SW["thin"])), 100, 100


@reg("misc-strainer-t")
def _():
    return (_ln(0, 50, 100, 50) +
            _ln(50, 50, 50, 76, w=SW["symbol"]) +
            _ln(42, 76, 58, 76, w=SW["symbol"])), 100, 100


@reg("misc-strainer-cone")
def _():
    return (_ln(0, 50, 100, 50) +
            _poly([(40, 40), (60, 40), (50, 64)], sw=SW["symbol"])), 100, 100


@reg("misc-sampling-point")
def _():
    return (_ln(0, 50, 100, 50) + _rect(44, 40, 12, 20, sw=SW["symbol"]) +
            _ln(50, 40, 50, 26, w=SW["thin"])), 100, 100


@reg("misc-atmospheric-vent")
def _():
    return (_ln(50, 80, 50, 30, w=SW["symbol"]) +
            _poly([(42, 42), (50, 26), (58, 42)], sw=SW["thin"], fill="none", closed=False)), 100, 100


@reg("misc-spray-nozzle")
def _():
    return (_ln(0, 40, 100, 40) +
            _poly([(40, 40), (60, 40), (50, 30)], fill=INK, sw=0.5) +
            _path("M 42 56 l 4 8 M 50 58 l 0 8 M 58 56 l -4 8", sw=SW["thin"])), 100, 80


@reg("misc-agitator")
def _():
    return (_ln(50, 20, 50, 64, w=SW["symbol"]) +
            _ln(38, 64, 62, 64, w=SW["symbol"])), 100, 90


@reg("misc-compensator")
def _():
    return (_ln(0, 50, 38, 50) + _ln(62, 50, 100, 50) +
            _path("M 38 50 q 12 -16 24 0 q -12 16 0 0", sw=SW["symbol"])), 100, 100


@reg("misc-funnel")
def _():
    return (_poly([(36, 30), (64, 30), (52, 52)], sw=SW["symbol"], fill="none", closed=False) +
            _ln(52, 52, 52, 74, w=SW["symbol"])), 100, 100


@reg("misc-special-joint")
def _():
    return (_ln(0, 46, 100, 46, w=SW["symbol"]) +
            _ln(0, 56, 100, 56, w=SW["symbol"])), 100, 100


# ---- 10. HVAC SYMBOLS (Sheet 5) -------------------------------------------
@reg("hvac-shutoff-damper")
def _():
    return _rect(30, 30, 40, 40, sw=SW["symbol"]) + _ln(36, 64, 64, 36, w=SW["symbol"]), 100, 100


@reg("hvac-parallel-damper")
def _():
    return (_rect(30, 30, 40, 40, sw=SW["symbol"]) +
            _ln(36, 42, 64, 42, w=SW["thin"]) + _ln(36, 58, 64, 58, w=SW["thin"])), 100, 100


@reg("hvac-opposed-damper")
def _():
    return (_rect(30, 30, 40, 40, sw=SW["symbol"]) +
            _ln(36, 42, 64, 38, w=SW["thin"]) + _ln(36, 58, 64, 62, w=SW["thin"])), 100, 100


@reg("hvac-fan-general")
def _():
    return _circle(50, 50, 24, sw=SW["symbol"]) + \
        _path("M 50 50 q -14 -8 -18 -18 M 50 50 q 14 -8 18 -18 M 50 50 q 0 18 0 22",
              sw=SW["thin"]), 100, 100


@reg("hvac-radiator")
def _():
    return (_rect(32, 35, 36, 30, sw=SW["symbol"]) +
            _ln(40, 35, 40, 65, w=SW["thin"]) + _ln(48, 35, 48, 65, w=SW["thin"]) +
            _ln(56, 35, 56, 65, w=SW["thin"])), 100, 100


@reg("hvac-heating-coil")
def _():
    return (_rect(30, 32, 40, 36, sw=SW["symbol"]) +
            _ln(30, 68, 70, 32, w=SW["thin"]) + _txt(40, 44, "+", size=12)), 100, 100


@reg("hvac-cooling-coil")
def _():
    return (_rect(30, 32, 40, 36, sw=SW["symbol"]) +
            _ln(30, 32, 70, 68, w=SW["thin"]) + _txt(60, 44, "-", size=14)), 100, 100


@reg("hvac-filter")
def _():
    return (_poly([(26, 34), (66, 34), (74, 50), (66, 66), (26, 66)], sw=SW["symbol"]) +
            _txt(46, 53, "HEPA", size=8, weight="bold")), 100, 100


@reg("hvac-supply-terminal")
def _():
    return _rect(30, 38, 40, 24, sw=SW["symbol"]) + \
        _poly([(70, 38), (82, 50), (70, 62)], sw=SW["thin"], fill="none", closed=False), 100, 100


@reg("hvac-exhaust-terminal")
def _():
    return _rect(40, 38, 40, 24, sw=SW["symbol"]) + \
        _poly([(40, 38), (28, 50), (40, 62)], sw=SW["thin"], fill="none", closed=False), 100, 100


# ============================================================================
#  CATALOGUE METADATA  (every symbol + the reference-only standard sets)
# ============================================================================
def C(sid, name, desc, notation="", usage=""):
    """Helper to build a catalogue entry for a *drawn* symbol."""
    return {
        "id": sid, "name": name, "description": desc,
        "tag_notation": notation, "usage": usage, "drawn": sid in DRAW,
    }



# ---------------------------------------------------------------------------
# Naming-convention / tag-numbering metadata (Sheet 1)
# ---------------------------------------------------------------------------
NAMING_CONVENTIONS = {
    "general_tag_scheme": {
        "pattern": "W-X:Y-Z-1",
        "basis": "Subordinate to Primary Systems Naming Convention & "
                 "Terminology (SCK CEN/36557490)",
        "fields": {
            "W": "Section (1-6 characters)",
            "X": "Subsection (1-6 characters, when it exists in the section)",
            "Y": "Discipline (1-6 characters)",
            "Z": "Deviceclass (1-6 characters)",
            "1": "Index / running number",
        },
        "register_reference": "Primary Systems Naming Convention and "
                              "Terminology - Mnemonics (SCK CEN/36793249)",
    },
    "pipe_line_tag": {
        "pattern": "W-X:Y-Z-1 / S1-M1",
        "fields": {
            "W-X:Y-Z-1": "See general tag scheme",
            "S1": "Diameter",
            "M1": "Material",
        },
        "example": "THSITS-GSRSEL:HYD-PIPE-123 / DN40-SS316",
    },
    "instrument_tag": {
        "rule": "Instrument tag numbers are not shown explicitly; they are "
                "composed by taking (1) the first line of the tag number of "
                "the element they are attached to, then (2) the top and bottom "
                "part shown inside the instrument bubble, joined by '-'.",
        "examples": {
            "LS attached to THSITS-GSRSEL:PNE-VALVE-1002 (bubble LS/1001)":
                "THSITS-GSRSEL:PNE-LS-1001",
            "TT attached to THSITS-GSRSEL:PNE-PIPE-111 (bubble TT/202)":
                "THSITS-GSRSEL:PNE-TT-202",
        },
    },
    "nfs_tag": "See MINERVA NFS naming convention (non-primary systems).",
    "valve_lock_fail_codes": {
        "LC": "Locked closed", "LO": "Locked open",
        "NC": "Closed in normal operation", "NO": "Open in normal operation",
        "FC": "Fail to closed position", "FO": "Fail to open position",
        "FA": "Fail as it is",
    },
}

# ISA-5.1-2022 Table 4.1 letter code (as reproduced / subordinated on Sheet 2)
ISA_LETTER_CODE = {
    "A": {"first": "Analysis", "succeeding_readout": "Alarm"},
    "B": {"first": "Burner, combustion"},
    "C": {"succeeding_output": "Control", "modifier": "Close"},
    "D": {"first": "Density", "modifier_var": "Difference, differential",
          "modifier": "Deviation"},
    "E": {"first": "Voltage", "succeeding_readout": "Sensor, primary element"},
    "F": {"first": "Flow, flow rate", "modifier_var": "Ratio"},
    "G": {"succeeding_readout": "Glass, gauge, viewing device"},
    "H": {"first": "Hand", "modifier": "High"},
    "I": {"first": "Current", "succeeding_readout": "Indicate"},
    "J": {"first": "Power", "succeeding_readout": "Scan"},
    "K": {"first": "Time, schedule", "modifier_var": "Time rate of change",
          "succeeding_output": "Control station"},
    "L": {"first": "Level", "succeeding_readout": "Light", "modifier": "Low"},
    "M": {"first": "Moisture or humidity", "modifier": "Middle, intermediate"},
    "N": {"note": "User's choice"},
    "O": {"succeeding_readout": "Orifice, restriction", "modifier": "Open"},
    "P": {"first": "Pressure or vacuum",
          "succeeding_readout": "Point (test connection)"},
    "Q": {"first": "Quantity", "modifier_var": "Integrate, totalize",
          "succeeding_readout": "Integrate, totalize"},
    "R": {"first": "Radiation", "succeeding_readout": "Record",
          "modifier": "Run"},
    "S": {"first": "Speed, frequency", "modifier_var": "Safety",
          "succeeding_output": "Switch", "modifier": "Stop"},
    "T": {"first": "Temperature", "succeeding_output": "Transmit"},
    "U": {"first": "Multivariable", "succeeding_readout": "Multifunction",
          "succeeding_output": "Multifunction"},
    "V": {"first": "Vibration, mechanical analysis",
          "succeeding_output": "Valve, damper, louver"},
    "W": {"first": "Weight, force", "succeeding_readout": "Well, probe"},
    "X": {"first": "Unclassified", "modifier_var": "X-axis",
          "succeeding_readout": "Accessory devices, unclassified",
          "succeeding_output": "Unclassified", "modifier": "Unclassified"},
    "Y": {"first": "Event, state, presence", "modifier_var": "Y-axis",
          "succeeding_output": "Auxiliary devices"},
    "Z": {"first": "Position, dimension",
          "modifier_var": "Z-axis, safety instrumented system",
          "succeeding_output": "Driver, actuator, unclassified final "
                               "control element"},
}

# Bubble matrix axis meaning (Sheet 2, subordinate to ISA-5.1 Table 5.1.1)
BUBBLE_MATRIX = {
    "type_columns": {
        "A": "Shared display, shared control - Basic Process Control System "
             "(BPCS): square enclosing a circle",
        "B": "Shared display, shared control - Safety Instrumented System "
             "(SIS): square enclosing a circle, with diagonals",
        "C": "Computer systems and software: hexagon",
        "D": "Discrete visualisation of instruments: plain circle "
             "(elongated/stadium when two instruments share an enclosure)",
    },
    "location_rows": {
        "1": "Located in field; not panel/cabinet/console mounted; visible at "
             "field location; normally operator accessible (NO line)",
        "2": "Located in/on front of central or main panel/console; visible on "
             "panel front or video display; normally accessible (single solid line)",
        "3": "Located in rear of central/main panel or in cabinet behind panel; "
             "not visible on front; not normally accessible (single dashed line)",
        "4": "Located in/on front of secondary or local panel/console; visible "
             "on front; normally accessible (double solid line)",
        "5": "Located in rear of secondary/local panel or in field cabinet; not "
             "visible on front; not normally accessible (double dashed line)",
    },
}

# ---------------------------------------------------------------------------
# Catalogue: human metadata for every DRAWN symbol, grouped by category.
# ---------------------------------------------------------------------------
CATALOGUE = {
    "lines": {
        "source_sheet": "Sheet 1/9 - LINETYPES & HVAC LINETYPES",
        "symbols": [
            C("line-primary", "Primary line segment", "Main process pipe, line weight 1 mm, with flow arrow.", "LW=1mm", "Main/primary process piping."),
            C("line-secondary", "Secondary line segment", "Branch/secondary process pipe, line weight 0.5 mm, with flow arrow.", "LW=0,5mm", "Branch / secondary piping."),
            C("line-primary-future", "Primary line - future extension", "Future primary pipe (dash-dot), 1 mm.", "LW=1mm", "Proposed/future primary piping."),
            C("line-secondary-future", "Secondary line - future extension", "Future secondary pipe (dash-dot), 0.5 mm.", "LW=0,5mm", "Proposed/future secondary piping."),
            C("line-electrical-signal", "Electrical signal line", "Dashed thin signal line.", "LW=0,25mm", "Electrical instrument signal."),
            C("line-pneumatic-signal", "Pneumatic signal line", "Line with double cross-hatch ticks.", "LW=0,25mm", "Pneumatic instrument signal."),
            C("line-hydraulic-signal", "Hydraulic signal line", "Line with periodic L-marks.", "LW=0,25mm", "Hydraulic instrument signal."),
            C("line-software-signal", "Software / data signal line", "Line with small ring markers.", "LW=0,25mm", "Software / data link / system bus."),
            C("line-em-sonic-signal", "Guided electromagnetic or sonic signal", "Line with wave marker.", "", "Guided EM / sonic signal."),
            C("line-capillary", "Capillary tube", "Line with x cross marks.", "LW=0,25mm", "Filled thermal / capillary connection."),
            C("line-hose", "Hose", "Continuous wavy line.", "", "Flexible hose."),
            C("line-pipe-insulated", "Pipe, insulated", "Pipe with hatch band.", "", "Thermally insulated pipe."),
            C("line-tracer", "Tracer for heating or cooling", "Main line plus parallel dashed trace line.", "", "Heat/cool tracing."),
            C("line-jacketed", "Jacketed pipeline", "Pipe inside an outer jacket rectangle.", "", "Jacketed / double-wall pipe."),
            C("line-heated-insulated", "Piping, heated or cooled and insulated", "Hatched + traced pipe.", "", "Traced and insulated pipe."),
            C("line-hvac-supply", "HVAC air supply segment", "Solid 1 mm line.", "LW=1mm", "HVAC supply air duct/line."),
            C("line-hvac-return", "HVAC air return segment", "Dash-dot 1 mm line.", "LW=1mm", "HVAC return air duct/line."),
            C("conn-connected-lines", "Connected lines", "Lines crossing with a connection (loop bridge over junction).", "", "Show electrically/process connected crossing lines."),
            C("conn-non-connected-lines", "Non-connected lines", "Lines crossing with a gap/hop.", "", "Show crossing lines that are NOT connected."),
        ],
    },
    "instrumentation": {
        "source_sheet": "Sheet 2/9 - ISA-5.1 letter code + symbolic representation matrix; Sheet 3/9 - INSTRUMENT SYMBOLS",
        "bubble_matrix": BUBBLE_MATRIX,
        "letter_code": ISA_LETTER_CODE,
        "symbols": [
            C(f"inst-{c}{r}",
              f"{BUBBLE_MATRIX['type_columns'][c].split(':')[0].split(' - ')[-1]} / location {r}",
              f"{BUBBLE_MATRIX['type_columns'][c]} -- {BUBBLE_MATRIX['location_rows'][str(r)]}",
              "two-line tag: letters (top) / number (bottom)",
              "ISA-5.1 instrument bubble.")
            for c in ("A", "B", "C", "D") for r in range(1, 6)
        ] + [
            C("inst-discrete-oval", "Discrete - shared (two instruments)", "Stadium/oval enclosure holding two discrete instruments.", "", "Two instruments sharing one enclosure."),
            C("flow-sonic", "Sonic flow meter", "Inline box, 'S'.", "", "Sonic/ultrasonic flow element."),
            C("flow-variable-area", "Variable area flowmeter", "Inline box with float taper.", "", "Rotameter / VA flowmeter."),
            C("flow-coriolis", "Coriolis flow meter", "Inline box with bent-tube mark.", "", "Mass (Coriolis) flow element."),
            C("flow-magnetic", "Magnetic flow meter", "Inline box, 'M'.", "", "Magnetic flow element."),
            C("flow-vortex", "Vortex shedding flowmeter", "Inline box with vortex mark.", "", "Vortex flow element."),
            C("flow-radiation", "Radiation meter", "Inline box, 'R'.", "", "Radiation-based flow/level element."),
            C("flow-orifice-generic", "Generic orifice plate", "Plate bar across line.", "", "Generic orifice flow restriction."),
            C("flow-nozzle", "Flow nozzle", "Convergent nozzle in line.", "", "Flow nozzle primary element."),
            C("flow-venturi", "Venturi tube", "Convergent-divergent venturi.", "", "Venturi primary element."),
            C("flow-positive-displacement", "Positive displacement flow meter", "Rounded body with two lobes.", "", "PD flow meter."),
            C("flow-turbine", "Turbine flow meter", "Box with rotor mark.", "", "Turbine flow element."),
        ],
    },
    "valves": {
        "source_sheet": "Sheet 3/9 - VALVE GRAPHICAL SYMBOLS & ACTUATING ELEMENTS",
        "lock_fail_codes": NAMING_CONVENTIONS["valve_lock_fail_codes"],
        "symbols": [
            C("valve-generic", "Valve (generic)", "Two-triangle (hour-glass/bow-tie) body.", "X = LC/LO/NC/NO above body", "Generic isolation valve; add lock/fail code."),
            C("valve-gate", "Gate valve", "Plain bow-tie body.", "", "Gate (on/off) valve."),
            C("valve-globe", "Globe valve", "Bow-tie with open centre circle.", "", "Globe (throttling) valve."),
            C("valve-ball", "Ball valve", "Bow-tie with solid centre circle outline.", "", "Ball valve."),
            C("valve-needle", "Needle valve", "Bow-tie with needle wedge.", "", "Needle (fine throttle) valve."),
            C("valve-butterfly", "Butterfly valve", "Bow-tie with disc shaft.", "", "Butterfly valve."),
            C("valve-angle", "Angle valve", "90 deg angle body.", "", "Angle pattern valve."),
            C("valve-three-way", "Three-way valve", "Bow-tie with third (bottom) port.", "", "3-way diverting/mixing valve."),
            C("valve-check", "Check valve", "Disc against seat (flow one way).", "", "Non-return / check valve."),
            C("valve-swing-check", "Swing check valve", "Hinged disc.", "", "Swing check valve."),
            C("valve-ball-check", "Ball check valve", "Bow-tie with solid ball.", "", "Ball check valve."),
            C("valve-globe-check", "Check valve, globe type", "Globe body with check disc.", "", "Globe-type check valve."),
            C("valve-tilting-disk-check", "Tilting disk check valve", "Body with tilting disc line.", "", "Tilting-disk check valve."),
            C("valve-piston-lift-check", "Piston lift check valve", "Body with piston rectangle.", "", "Piston lift check valve."),
            C("valve-y-piston-lift-check", "'Y' pattern piston lift check valve", "Y body with piston.", "", "Y-pattern piston lift check valve."),
            C("valve-butterfly-check", "Butterfly check valve", "Wafer with check vane.", "", "Butterfly (dual-plate) check valve."),
            C("valve-y-globe", "Valve, globe 'Y' pattern type", "Y-pattern globe body.", "", "Y-pattern globe valve."),
            C("valve-safety", "Safety valve", "Bow-tie with spring stem.", "", "Safety valve."),
            C("valve-safety-spring-angle", "Safety valve, spring loaded (angle type)", "Angle body with spring.", "", "Spring-loaded angle safety/relief valve."),
            C("valve-pressure-reducing", "Pressure reducing valve", "Bow-tie with diaphragm dome.", "", "Self-acting pressure reducing valve."),
            C("valve-balancing", "Balancing valve", "Bow-tie with balancing bar.", "", "Balancing valve."),
            C("valve-differential-pressure", "Differential pressure valve", "Bow-tie with dP spring head.", "", "Differential pressure valve."),
        ],
    },
    "actuators": {
        "source_sheet": "Sheet 3/9 - ACTUATING ELEMENTS",
        "symbols": [
            C("act-diaphragm", "Diaphragm actuator (pneumatic)", "Valve + diaphragm dome.", "", "Pneumatic diaphragm actuator."),
            C("act-piston", "Piston actuator", "Valve + piston cylinder.", "", "Piston/cylinder actuator."),
            C("act-hydraulic", "Hydraulic fluid actuator", "Valve + 'H' cylinder.", "", "Hydraulic actuator."),
            C("act-solenoid", "Solenoid actuator", "Valve + 'S' box.", "", "Solenoid actuator."),
            C("act-manual", "Manual operation", "Valve + hand lever.", "", "Manual (hand) operation."),
            C("act-motor-electric", "Electric motor actuator", "Valve + 'M' circle.", "M", "Electric motor actuator (MOV)."),
            C("act-motor-dc", "D.C. electric motor", "Valve + 'M' circle with bar.", "M", "DC motor actuator."),
            C("act-motor-pos-transmit", "Electric motor operated with position transmitter", "Valve + 'M' + transmitter ring.", "M", "MOV with position transmitter."),
            C("act-self-fcv", "Self-acting flow control valve (FCV)", "Valve + diaphragm + FCV bubble.", "FCV", "Self-acting flow control."),
            C("act-self-pcv", "Self-acting pressure control valve (PCV)", "Valve + diaphragm + PCV bubble.", "PCV", "Self-acting pressure control."),
            C("act-self-tcv", "Self regulating temperature control valve (TCV)", "Valve + diaphragm + TCV bubble.", "TCV", "Self-regulating temperature control."),
            C("act-self-lcv", "Self regulating level control valve (LCV)", "Valve + diaphragm + LCV bubble.", "LCV", "Self-regulating level control."),
            C("act-fixed-spring", "Operation against fixed spring", "Valve + spring.", "", "Spring-return operation."),
            C("act-float", "Float operated", "Valve + float ball.", "", "Float operated valve."),
            C("act-weight", "Weight operated", "Valve + weight.", "", "Weight operated valve."),
            C("act-high-speed", "High speed actuator", "Valve + fast-action mark.", "", "High-speed actuator."),
            C("act-fail-closed", "Fail to closed position (FC)", "Valve + 'FC'.", "FC", "Fails closed on loss of signal/power."),
            C("act-fail-open", "Fail to open position (FO)", "Valve + 'FO'.", "FO", "Fails open on loss of signal/power."),
            C("act-fail-as-is", "Fail as it is (FA)", "Valve + 'FA'.", "FA", "Fails in last position."),
        ],
    },
    "equipment": {
        "source_sheet": "Sheet 4/9 - EQUIPMENT",
        "symbols": [
            C("eq-pump-liquid", "Pump, liquid type (general)", "Circle with flow triangle.", "", "General liquid pump."),
            C("eq-pump-centrifugal", "Pump, centrifugal type", "Circle with inlet vee.", "", "Centrifugal pump."),
            C("eq-pump-cavity", "Pump, progressive cavity type", "Circle with sine.", "", "Progressive cavity pump."),
            C("eq-compressor-vacuum", "Compressor / vacuum pump", "Plain circle.", "", "Compressor / vacuum pump."),
            C("eq-turbo-compressor", "Turbo compressor / turbo vacuum pump", "Circle with inner ring.", "", "Turbo compressor / vacuum pump."),
            C("eq-blower-fan", "Blower, fan", "Circle with blades.", "", "Blower / fan."),
            C("eq-heat-exchanger-general", "Heat exchanger (general) / condenser", "Circle with zig-zag.", "", "General heat exchanger / condenser."),
            C("eq-heat-exchanger-u-tube", "Heat exchanger with U-shaped tubes", "Shell with U-tube.", "", "U-tube shell & tube HX."),
            C("eq-heat-exchanger-plate", "Heat exchanger of plate type", "Box with cross.", "", "Plate heat exchanger."),
            C("eq-electric-heater", "Electric heater", "'E' box with elements.", "E", "Electric heater."),
            C("eq-steam-generator", "Steam generator", "Box with diagonal.", "", "Steam generator."),
            C("eq-chiller", "Chiller", "Condenser/evaporator stack.", "", "Chiller package."),
            C("eq-gas-filter", "Gas filter (general)", "Tall box with bands.", "", "General gas filter."),
            C("eq-gas-filter-hepa", "Gas filter HEPA", "Box labelled HEPA.", "HEPA", "HEPA gas filter."),
            C("eq-liquid-filter", "Liquid filter (general)", "Box with dashed band.", "", "General liquid filter."),
            C("eq-mixed-bed-filter", "Mixed bed filter", "Box with double cross.", "", "Mixed-bed filter."),
            C("eq-ion-exchanger", "Liquid bed filter, ion exchanger type", "Box labelled ION.", "ION", "Ion-exchange bed."),
            C("eq-charcoal-filter", "Activated charcoal filter", "Box with centre cartridge.", "", "Activated charcoal filter."),
            C("eq-horizontal-tank", "Horizontal tank (dished ends)", "Horizontal vessel.", "", "Horizontal tank/vessel."),
            C("eq-vertical-tank", "Vertical tank (dished ends)", "Vertical vessel.", "", "Vertical tank/vessel."),
            C("eq-conical-tank", "Tank with conical roof and flat bottom", "Roofed tank.", "", "Conical-roof tank."),
            C("eq-hopper", "Hopper", "Inverted triangle.", "", "Hopper."),
            C("eq-rupture-disc", "Rupture disc", "Line with bowed disc.", "", "Rupture / bursting disc."),
            C("eq-steam-trap", "Steam / air trap", "Circle with half-fill.", "", "Steam/air trap."),
            C("eq-viewing-glass", "Viewing glass", "Inline window with eye.", "", "Sight / viewing glass."),
            C("eq-orifice-plate-line", "Orifice plate (in line)", "Plate across line.", "", "Inline orifice plate."),
        ],
    },
    "connections": {
        "source_sheet": "Sheet 3/9 - (EQUIPMENT) CONNECTIONS",
        "symbols": [
            C("conn-threaded", "Threaded / screw ends", "Threaded end caps.", "", "Threaded/screwed pipe ends."),
            C("conn-flanged-ends", "Flanged ends", "Flange bars both ends.", "", "Flanged pipe ends."),
            C("conn-wafer", "Wafer type", "Wafer body between flanges.", "", "Wafer connection."),
            C("conn-welded-ends", "Welded ends", "Weld dots both ends.", "", "Welded pipe ends."),
            C("conn-quick-coupling", "With quick connection / coupling", "Quick-coupling end.", "", "Quick connect coupling."),
            C("conn-hose", "Hose connection", "Hose barb ends.", "", "Hose connection."),
            C("conn-flanged-connection", "Flanged connection", "Single flange pair.", "", "Flanged joint."),
            C("conn-isolating-flange", "Isolating flange", "Flange pair with isolator.", "", "Electrically isolating flange."),
            C("conn-blind-flange", "Blind flange", "Capped flange bar.", "", "Blind flange."),
            C("conn-screw-cap", "Screw cap", "Threaded end cap.", "", "Screwed cap."),
            C("conn-welded-cap", "Welded cap", "Domed welded cap.", "", "Welded cap."),
            C("conn-reducer", "Reducer", "Concentric/eccentric reducer.", "DN1/DN2", "Pipe size reducer."),
        ],
    },
    "interfaces_scope": {
        "source_sheet": "Sheet 1/9 - INTERFACES / CONNECTIONS, OFF PAGE CONNECTOR, DESIGN CONDITIONS & CODE JURISDICTION BREAKS",
        "termination_point_codes": {
            "B": "Building", "C": "Civil", "E": "Electrical",
            "G": "Compressed gasses", "H": "HVAC", "L": "Liquid waste",
            "S": "Solid waste", "W": "Water",
        },
        "symbols": [
            C("iface-termination-point", "Termination point (primary systems)", "Diamond 'TPXYYYY / ZZZ'. X = interface category (B/C/E/G/H/L/S/W), YYYY = unique number, ZZZ = next system/process.", "TPXYYYY / ZZZ", "Primary-system interface / termination point."),
            C("iface-offpage-connector", "Off-page connector (primary systems)", "Arrow box 'XXXXX | 123456-PID01 | WWWWW'. XXXXX=unique number/name, 123456-PID01=interconnecting P&ID, WWWWW=from/to process, ZZZZZ=medium.", "XXXXX / 123456-PID01 / WWWWW", "Continuation to/from another P&ID sheet."),
            C("iface-system-nfs", "Interface between systems (NFS)", "Valve + system boundary (PBS1).", "PBS1", "Boundary between systems (non-primary)."),
            C("scope-design-limit", "System and design conditions limit", "Valve with diamond marker on a stem.", "", "System / design-conditions scope boundary."),
            C("scope-code-jurisdiction", "Code jurisdiction break", "Valve + diamond + code letters (e.g. ASME VIII / ASME B31.3).", "ASME VIII | ASME B31.3", "Piping code jurisdiction / scope-of-supply break (* = supplier)."),
        ],
    },
    "misc_specialty": {
        "source_sheet": "Sheet 5/9 - MISCELLANEOUS SYMBOLS",
        "symbols": [
            C("misc-reducer", "Reducer", "Concentric reducer w/ DN1/DN2.", "DN1/DN2", "Line size change."),
            C("misc-vfd", "Variable frequency driver", "Box 'VFD'.", "VFD", "Variable frequency drive."),
            C("misc-flame-arrestor", "Flame arrestor", "Inline matrix box.", "", "Flame arrestor."),
            C("misc-dielectric-joint", "Dielectric joint", "Insulated inline box.", "", "Dielectric (isolating) joint."),
            C("misc-strainer-y", "'Y' type strainer", "Y leg off line.", "", "Y-type strainer."),
            C("misc-strainer-t", "'T' type strainer", "T leg off line.", "", "T-type strainer."),
            C("misc-strainer-cone", "Cone type strainer", "Cone in line.", "", "Conical (temporary) strainer."),
            C("misc-sampling-point", "Sampling point", "Inline sample take-off.", "", "Sampling connection."),
            C("misc-atmospheric-vent", "Atmospheric vent", "Up arrow to atmosphere.", "", "Vent to atmosphere."),
            C("misc-spray-nozzle", "Spray nozzle", "Nozzle with spray.", "", "Spray nozzle."),
            C("misc-agitator", "Agitator, stirrer (general)", "Shaft with blade.", "", "Agitator / stirrer."),
            C("misc-compensator", "Compensator", "Inline bellows expansion joint.", "", "Expansion compensator."),
            C("misc-funnel", "Funnel", "Funnel + drain.", "", "Funnel / tundish."),
            C("misc-special-joint", "Special joint", "Double parallel bar.", "", "Special joint."),
        ],
    },
    "hvac": {
        "source_sheet": "Sheet 5/9 - HVAC SYMBOLS",
        "symbols": [
            C("hvac-shutoff-damper", "Shut-off damper", "Box with diagonal blade.", "", "HVAC shut-off damper."),
            C("hvac-parallel-damper", "Parallel-blade damper", "Box with parallel blades.", "", "Parallel-blade damper."),
            C("hvac-opposed-damper", "Opposed-blade damper", "Box with opposed blades.", "", "Opposed-blade damper."),
            C("hvac-fan-general", "Fan (general)", "Circle with blades.", "", "HVAC fan."),
            C("hvac-radiator", "Radiator", "Finned box.", "", "Radiator."),
            C("hvac-heating-coil", "Water or steam heating coil", "Box '+' diagonal.", "", "Heating coil."),
            C("hvac-cooling-coil", "Cooling coil", "Box '-' diagonal.", "", "Cooling coil."),
            C("hvac-filter", "Filter (gen / HEPA / carb)", "Trapezoid labelled.", "HEPA/GEN/CARB", "HVAC filter."),
            C("hvac-supply-terminal", "Supply air terminal device", "Box with out arrow.", "", "Supply air terminal."),
            C("hvac-exhaust-terminal", "Exhaust air terminal device", "Box with in arrow.", "", "Exhaust air terminal."),
        ],
    },
}

# ---------------------------------------------------------------------------
# Reference-only standard sets (Sheets 6-9): catalogued but not redrawn here
# (they belong to electrical single-line / fire-detection drawings, outside the
#  core process-P&ID symbol scope, and follow the cited published standards).
# ---------------------------------------------------------------------------
REFERENCE_SETS = {
    "minerva_rib_line": {
        "source_sheet": "Sheet 6/9 - MINERVA RIB LINE SPECIFIC ELEMENTS",
        "standard": "MINERVA facility-specific",
        "items": ["Pillow seal", "Clamped connection", "Thin window",
                  "Cooled window", "Collimator", "Hall sensor", "Heat exchanger",
                  "Magnet", "Electrical insulator", "Inflatable bellow",
                  "Bellow", "Target"],
    },
    "minerva_beam_optics": {
        "source_sheet": "Sheet 6/9 - MINERVA BEAM OPTICS",
        "standard": "MINERVA facility-specific",
        "items": ["Beam position monitor", "Halo monitor", "Beam profile monitor",
                  "Tail monitor", "Quadrupole", "Wire scanner",
                  "Steering plates horizontal", "Steering plates vertical",
                  "Steering plates horizontal & vertical", "Faraday cup",
                  "Electrostatic bender", "Mirror", "Mirror motorized",
                  "Selectable slits", "Vertical slits", "Beam shutter",
                  "Beam dump", "Optical diagnostics (WLM/PM/EM)", "Laser",
                  "Dye laser head", "Laser cool unit (to water)",
                  "Laser cool unit (to air)", "Atomic beam unit (ABU)",
                  "Frequency convertor unit (FCU)", "Optical fibre switch"],
    },
    "electrical_iec60617": {
        "source_sheet": "Sheet 7/9 - ELECTRICAL SYMBOLS",
        "standard": "IEC 60617 (publication 617); items marked '*' are "
                    "non-standard; relay function numbers '**' per ANSI C37.2",
        "items": ["Direct current", "Alternating current", "Key interlock",
                  "Mechanical interlock", "Electrical interlock",
                  "Normally open*", "Normally closed*", "Ground",
                  "Generator (G)", "Motor", "Inductor/coil", "Battery",
                  "2/3-winding transformer", "Current transformer",
                  "Thermocouple", "RTD", "Signal converter", "Diode",
                  "Thyristor", "Rectifier/charger", "Inverter",
                  "Static transfer switch", "Fuse", "Fuse disconnector",
                  "Automatic circuit breaker", "Relay (various)",
                  "Make/break/time-delay contacts", "Push-button/limit/level/"
                  "flow/temperature switches", "Meters (A/V/W/VAR/Hz/...)",
                  "Horn/bell/siren/buzzer/loudspeaker", "Surge arrester"],
    },
    "fire_safety": {
        "source_sheet": "Sheets 8-9/9 - FIRE DETECTION, EXTINGUISHING & SAFETY",
        "standard": "Fire-detection / life-safety symbology (house standard)",
        "items": ["Emergency exits / evacuation arrows / assembly point",
                  "Fire extinguisher / hose reel / ladder / phone / alarm",
                  "First aid / AED / doctor / emergency shower / eyewash / "
                  "stretcher", "Fire separation E30/EI30/EI60/EI120",
                  "Extinguishing system & controls (XC10/GAS/EWP/...)",
                  "Optical/thermal/multicriteria/flame/gas/duct/beam detectors",
                  "Sounders / sirens / optical & optical-acoustic signals",
                  "Modules (input/output) / Zener barrier / fire station",
                  "Fire damper / aspirating smoke detection (ASD)"],
    },
}


# ============================================================================
#  EMITTERS
# ============================================================================
def build_svg():
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="{SVGNS}" '
        'xmlns:xlink="http://www.w3.org/1999/xlink" width="0" height="0" '
        'style="position:absolute" '
        'data-standard="106889-PID00 MINERVA GENERAL LEGEND SHEET Rev.A">',
        "  <!-- Reusable P&ID symbol library. Use any symbol with",
        '       <use href="#<id>" x=".." y=".." width=".." height=".."/>.',
        "       Geometry is schematic/standards-based (ISA-5.1-2022, ISO 10628,",
        "       IEC 60617) per the MINERVA General Legend Sheet. -->",
        "  <defs>",
    ]
    for sid in sorted(DRAW.keys()):
        inner, w, h = DRAW[sid]()
        parts.append(f'    <symbol id="{sid}" viewBox="0 0 {w:.0f} {h:.0f}" '
                     f'overflow="visible">{inner}</symbol>')
    parts.append("  </defs>")
    parts.append("</svg>")
    return "\n".join(parts)


def build_preview_svg():
    """A visible contact-sheet rendering every drawn symbol with its id."""
    lib = {sid: DRAW[sid]() for sid in DRAW}
    ids = sorted(lib.keys())
    cols = 6
    cell_w, cell_h = 200, 150
    rows = (len(ids) + cols - 1) // cols
    W = cols * cell_w + 40
    H = rows * cell_h + 80
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           f'<svg xmlns="{SVGNS}" '
           f'xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" font-family="{FONT}">',
           f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
           f'<text x="20" y="34" font-size="22" font-weight="bold" '
           f'fill="{INK}">MINERVA P&amp;ID Symbol Library - contact sheet '
           f'({len(ids)} drawn symbols)</text>']
    # inline the symbol defs once
    out.append('<defs>')
    for sid in ids:
        inner, w, h = lib[sid]
        out.append(f'<symbol id="{sid}" viewBox="0 0 {w:.0f} {h:.0f}" '
                   f'overflow="visible">{inner}</symbol>')
    out.append('</defs>')
    for i, sid in enumerate(ids):
        r, c = divmod(i, cols)
        x = 20 + c * cell_w
        y = 60 + r * cell_h
        _, w, h = lib[sid]
        # scale symbol to fit a 150x90 viewport, keep aspect
        vp_w, vp_h = 150, 88
        scale = min(vp_w / w, vp_h / h)
        dw, dh = w * scale, h * scale
        ux = x + (cell_w - 40 - dw) / 2 + 20
        uy = y + (96 - dh) / 2
        out.append(f'<rect x="{x}" y="{y}" width="{cell_w-30}" '
                   f'height="{cell_h-30}" fill="none" stroke="#cccccc"/>')
        out.append(f'<use href="#{sid}" xlink:href="#{sid}" x="{ux:.1f}" '
                   f'y="{uy:.1f}" width="{dw:.1f}" height="{dh:.1f}"/>')
        out.append(f'<text x="{x + (cell_w-30)/2:.0f}" y="{y+cell_h-40:.0f}" '
                   f'font-size="11" text-anchor="middle" fill="{INK}">{sid}</text>')
    out.append("</svg>")
    return "\n".join(out)


def build_json():
    drawn = sorted(DRAW.keys())
    catalog_count = sum(len(g["symbols"]) for g in CATALOGUE.values())
    return {
        "metadata": {
            "title": "MINERVA / MYRRHA P&ID Symbol Reference Library",
            "source_document": "AD_01.16 SUP - PID General Legend Sheet.pdf",
            "drawing_number": "106889-PID00",
            "doc_number": "MYR100PTF-0521",
            "owner": "SCK CEN (MYRRHA - MINERVA)",
            "revision": "A (Released)",
            "drawing_date": "2023-11-16",
            "sheet_size": "A1 (9 legend sheets)",
            "standards_basis": [
                "ANSI/ISA-5.1-2022 (instrument letter codes Table 4.1 & "
                "symbolic representation Table 5.1.1)",
                "ISO 10628 (process diagram house style)",
                "IEC 60617 / publication 617 (electrical symbols, Sheet 7)",
                "Tag numbering: SCK CEN/36557490; mnemonics SCK CEN/36793249",
                "ANSI C37.2 (relay function numbers)",
            ],
            "generated": datetime.date.today().isoformat(),
            "generator": "standards/build_legend_library.py",
            "drawn_symbol_count": len(drawn),
            "catalogued_symbol_count": catalog_count,
        },
        "style_spec": STYLE,
        "naming_conventions": NAMING_CONVENTIONS,
        "categories": CATALOGUE,
        "reference_only_sets": REFERENCE_SETS,
        "svg_library": {
            "file": "symbol_library.svg",
            "usage": "Reference a symbol via <use href=\"#<id>\"/> after "
                     "embedding or linking symbol_library.svg.",
            "drawn_ids": drawn,
        },
    }


def main():
    svg = build_svg()
    with open(os.path.join(HERE, "symbol_library.svg"), "w", encoding="utf-8") as f:
        f.write(svg)

    preview = build_preview_svg()
    pv_path = os.path.join(HERE, "symbol_library_preview.svg")
    with open(pv_path, "w", encoding="utf-8") as f:
        f.write(preview)

    data = build_json()
    with open(os.path.join(HERE, "legend_symbols.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # optional PNG preview
    try:
        import cairosvg
        cairosvg.svg2png(url=pv_path,
                         write_to=os.path.join(HERE, "symbol_library_preview.png"),
                         output_width=1300)
        png_ok = True
    except Exception as e:  # pragma: no cover
        png_ok = False
        print("PNG preview skipped:", e)

    print(f"drawn symbols     : {len(DRAW)}")
    print(f"catalogued symbols: {sum(len(g['symbols']) for g in CATALOGUE.values())}")
    print(f"reference sets    : {sum(len(r['items']) for r in REFERENCE_SETS.values())} items")
    print(f"PNG preview       : {'ok' if png_ok else 'skipped'}")
    print("outputs written to", HERE)


if __name__ == "__main__":
    main()
