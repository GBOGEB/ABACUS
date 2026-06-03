#!/usr/bin/env python3
"""
symbols.py
==========
ISA-5.1 / ISO-10628 compliant symbol primitives for the MINERVA P&ID rebuild.

Every helper returns an SVG fragment (string) drawn in *content* user-space
coordinates (the original 1527.27 x 1080 frame).  Geometry is intentionally
schematic and standards-based, not a pixel copy of the source.
"""

import math
import html

# ---------------------------------------------------------------------------
# ISA 5.1 measured-variable (first letter) + function (succeeding letters)
# ---------------------------------------------------------------------------
ISA_FIRST = {
    "T": "Temperature", "P": "Pressure", "L": "Level", "F": "Flow",
    "E": "Voltage / Electrical", "H": "Hand (manual)", "A": "Analysis",
    "S": "Speed / Safety", "V": "Vibration", "W": "Weight / Force",
    "R": "Radiation", "Q": "Quantity", "M": "Moisture", "B": "Burner",
}
ISA_SUCCEED = {
    "T": "Transmitter", "I": "Indicator", "C": "Controller", "R": "Recorder",
    "S": "Switch", "V": "Valve", "E": "Element (sensor)", "G": "Gauge / Glass",
    "Y": "Relay / Compute", "A": "Alarm", "H": "High", "L": "Low",
    "Z": "Driver / Actuator",
}

# Prefix -> (long meaning, isa note, default bubble role)
PREFIX_INFO = {
    "TT": ("Temperature Transmitter", "T=temperature, T=transmitter", "sensor"),
    "TE": ("Temperature Element", "T=temperature, E=element", "sensor"),
    "PT": ("Pressure Transmitter", "P=pressure, T=transmitter", "sensor"),
    "PI": ("Pressure Indicator", "P=pressure, I=indicator", "sensor"),
    "PZ": ("Pressure Safety / Special", "P=pressure, Z=safety", "safety"),
    "LT": ("Level Transmitter", "L=level, T=transmitter", "sensor"),
    "LS": ("Level Switch", "L=level, S=switch", "sensor"),
    "LI": ("Level Indicator", "L=level, I=indicator", "sensor"),
    "FT": ("Flow Transmitter", "F=flow, T=transmitter", "sensor"),
    "FI": ("Flow Indicator", "F=flow, I=indicator", "sensor"),
    "FZ": ("Flow Safety / Special", "F=flow, Z=safety", "safety"),
    "EH": ("Electric Heater", "E=electrical, H=hand/heater", "actuator"),
    "EHx": ("Electric Heater (template)", "E=electrical, H=heater", "actuator"),
    "SM": ("Speed / Special Monitor", "S=speed, M=monitor", "sensor"),
    "RS": ("Radiation Switch", "R=radiation, S=switch", "sensor"),
    "AP": ("Analysis Probe / Antenna", "A=analysis, P=probe", "sensor"),
    "CV": ("Control Valve", "C=control, V=valve", "valve"),
    "HV": ("Hand Valve", "H=hand, V=valve", "valve"),
    "SV": ("Safety / Solenoid Valve", "S=safety, V=valve", "safety-valve"),
    "RV": ("Relief Valve", "R=relief, V=valve", "safety-valve"),
    "PL": ("Pressure Limiter", "P=pressure, L=limiter", "safety"),
    "HL": ("Heat Load (annotation)", "heat-load callout", "note"),
}


def esc(s):
    return html.escape(str(s), quote=True)


def _text(x, y, s, size=7.5, anchor="middle", weight="normal",
          fill="#000000", family="Arial, Helvetica, sans-serif", style=""):
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-family="{family}" '
            f'font-size="{size:.2f}" font-weight="{weight}" '
            f'text-anchor="{anchor}" fill="{fill}"{style}>{esc(s)}</text>')


# ---------------------------------------------------------------------------
# Instrument bubbles (ISA 5.1)
# ---------------------------------------------------------------------------

def bubble(cx, cy, prefix, number, role="sensor", is_safety=False,
           family="LB", r=13.0):
    """Return an ISA 5.1 instrument bubble fragment.

    family: 'LB' -> LB cryo (white fill), 'RF' -> RFCELL (salmon fill),
            'LBI' -> LBI-specific (light-blue fill).
    Protection / safety instruments get a dashed outline (ISA interlock).
    """
    fill = {"LB": "#ffffff", "RF": "#ffd9d9", "LBI": "#dbe9ff"}.get(family, "#ffffff")
    dash = ' stroke-dasharray="3,2"' if is_safety else ""
    parts = []
    # field-mounted discrete instrument = plain circle
    parts.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" '
                 f'fill="{fill}" stroke="#000000" stroke-width="0.9"{dash}/>')
    # two-line tag: letters over number (ISA convention)
    parts.append(_text(cx, cy - 1.2, prefix, size=6.6, weight="bold"))
    parts.append(_text(cx, cy + 6.0, number, size=6.6))
    return "".join(parts)


def bubble_v3(cx, cy, prefix, number, r=11.0, fill="#ffffff", location="field",
              is_safety=False, mono=False, tag_size=6.6, lw=0.95):
    """ISA-5.1 instrument bubble with location/accessibility modifier.

    location:
      'field'  -> plain circle (field mounted)
      'front'  -> solid horizontal line through bubble (front-of-panel)
      'rear'   -> dashed horizontal line (behind panel / not accessible)
      'shared' -> square-around-circle (shared display / PLC)
    is_safety -> dashed outline (SIS / interlock).
    mono=True -> always white fill, black stroke (monochrome plot).
    """
    if mono:
        fill = "#ffffff"
    dash = ' stroke-dasharray="3,2"' if is_safety else ""
    parts = []
    if location == "shared":
        h = r + 2.0
        parts.append(f'<rect x="{cx-h:.2f}" y="{cy-h:.2f}" width="{2*h:.2f}" '
                     f'height="{2*h:.2f}" fill="{fill}" stroke="#000000" '
                     f'stroke-width="{lw:.2f}"{dash}/>')
    parts.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="{fill}" '
                 f'stroke="#000000" stroke-width="{lw:.2f}"{dash}/>')
    if location == "front":
        parts.append(f'<line x1="{cx-r:.2f}" y1="{cy:.2f}" x2="{cx+r:.2f}" '
                     f'y2="{cy:.2f}" stroke="#000000" stroke-width="{lw:.2f}"/>')
    elif location == "rear":
        parts.append(f'<line x1="{cx-r:.2f}" y1="{cy:.2f}" x2="{cx+r:.2f}" '
                     f'y2="{cy:.2f}" stroke="#000000" stroke-width="{lw:.2f}" '
                     f'stroke-dasharray="2,1.5"/>')
    if number:
        parts.append(_text(cx, cy - 0.8, prefix, size=tag_size, weight="bold"))
        parts.append(_text(cx, cy + tag_size, number, size=tag_size))
    else:
        parts.append(_text(cx, cy + 2, prefix, size=tag_size, weight="bold"))
    return "".join(parts)


def bubble_square(cx, cy, prefix, number, half=12.0):
    """Shared-display / PLC function: bubble inside a square."""
    parts = [f'<rect x="{cx-half:.2f}" y="{cy-half:.2f}" width="{2*half:.2f}" '
             f'height="{2*half:.2f}" fill="#ffffff" stroke="#000000" stroke-width="0.9"/>',
             f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{half-2:.2f}" fill="none" '
             f'stroke="#000000" stroke-width="0.8"/>',
             _text(cx, cy - 1.2, prefix, size=6.6, weight="bold"),
             _text(cx, cy + 6.0, number, size=6.6)]
    return "".join(parts)


# ---------------------------------------------------------------------------
# Valves
# ---------------------------------------------------------------------------

def valve(cx, cy, kind="gate", size=11.0, color="#000000"):
    """Two-triangle (bow-tie) valve body. kind adds actuator decorations."""
    s = size
    body = (f'<path d="M {cx-s:.2f} {cy-s*0.7:.2f} L {cx:.2f} {cy:.2f} '
            f'L {cx-s:.2f} {cy+s*0.7:.2f} Z M {cx+s:.2f} {cy-s*0.7:.2f} '
            f'L {cx:.2f} {cy:.2f} L {cx+s:.2f} {cy+s*0.7:.2f} Z" '
            f'fill="#ffffff" stroke="{color}" stroke-width="1.0"/>')
    extra = ""
    if kind == "control":   # diaphragm actuator on top
        extra = (f'<line x1="{cx:.2f}" y1="{cy:.2f}" x2="{cx:.2f}" y2="{cy-s*1.7:.2f}" '
                 f'stroke="{color}" stroke-width="0.9"/>'
                 f'<path d="M {cx-s*0.7:.2f} {cy-s*1.7:.2f} q {s*0.7:.2f} {-s*0.9:.2f} '
                 f'{s*1.4:.2f} 0 Z" fill="#ffffff" stroke="{color}" stroke-width="0.9"/>')
    elif kind == "relief":  # angle relief / safety
        extra = (f'<line x1="{cx:.2f}" y1="{cy:.2f}" x2="{cx:.2f}" y2="{cy-s*1.8:.2f}" '
                 f'stroke="{color}" stroke-width="0.9"/>'
                 f'<path d="M {cx-s*0.5:.2f} {cy-s*1.8:.2f} l {s:.2f} {-s*0.5:.2f} '
                 f'l 0 {s:.2f} Z" fill="{color}"/>')
    elif kind == "solenoid":
        extra = (f'<rect x="{cx-s*0.5:.2f}" y="{cy-s*1.9:.2f}" width="{s:.2f}" '
                 f'height="{s*0.9:.2f}" fill="#ffffff" stroke="{color}" stroke-width="0.9"/>'
                 f'<line x1="{cx:.2f}" y1="{cy:.2f}" x2="{cx:.2f}" y2="{cy-s:.2f}" '
                 f'stroke="{color}" stroke-width="0.9"/>'
                 + _text(cx, cy - s*1.25, "S", size=6.0))
    elif kind == "manual":  # hand-wheel
        extra = (f'<line x1="{cx:.2f}" y1="{cy:.2f}" x2="{cx:.2f}" y2="{cy-s*1.4:.2f}" '
                 f'stroke="{color}" stroke-width="0.9"/>'
                 f'<line x1="{cx-s*0.6:.2f}" y1="{cy-s*1.4:.2f}" x2="{cx+s*0.6:.2f}" '
                 f'y2="{cy-s*1.4:.2f}" stroke="{color}" stroke-width="1.2"/>')
    return body + extra


# ---------------------------------------------------------------------------
# Equipment glyphs
# ---------------------------------------------------------------------------

def vessel(cx, cy, w=60, h=90, label="", color="#000000"):
    rx = w / 2.0
    parts = [f'<rect x="{cx-w/2:.2f}" y="{cy-h/2+rx:.2f}" width="{w:.2f}" '
             f'height="{h-w:.2f}" fill="#ffffff" stroke="{color}" stroke-width="1.2"/>',
             f'<path d="M {cx-w/2:.2f} {cy-h/2+rx:.2f} a {rx:.2f} {rx:.2f} 0 0 1 {w:.2f} 0" '
             f'fill="#ffffff" stroke="{color}" stroke-width="1.2"/>',
             f'<path d="M {cx-w/2:.2f} {cy+h/2-rx:.2f} a {rx:.2f} {rx:.2f} 0 0 0 {w:.2f} 0" '
             f'fill="#ffffff" stroke="{color}" stroke-width="1.2"/>']
    if label:
        parts.append(_text(cx, cy, label, size=8, weight="bold"))
    return "".join(parts)


def heat_exchanger(cx, cy, r=22, label="", color="#000000"):
    parts = [f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="#ffffff" '
             f'stroke="{color}" stroke-width="1.2"/>',
             f'<path d="M {cx-r:.2f} {cy:.2f} L {cx-r*0.4:.2f} {cy-r*0.6:.2f} '
             f'L {cx+r*0.4:.2f} {cy+r*0.6:.2f} L {cx+r:.2f} {cy:.2f}" '
             f'fill="none" stroke="{color}" stroke-width="1.1"/>']
    if label:
        parts.append(_text(cx, cy + r + 9, label, size=7.5, weight="bold"))
    return "".join(parts)


def cavity(cx, cy, w=46, h=30, label="", color="#aa4400", fill=None):
    """Schematic SRF cavity / coupler body (rounded block)."""
    if fill is None:
        fill = "#ffffff" if color == "#000000" else "#f3e2d8"
    parts = [f'<rect x="{cx-w/2:.2f}" y="{cy-h/2:.2f}" width="{w:.2f}" height="{h:.2f}" '
             f'rx="6" fill="{fill}" stroke="{color}" stroke-width="1.4"/>']
    if label:
        parts.append(_text(cx, cy + 3, label, size=7.5, weight="bold", fill=color))
    return "".join(parts)


def node(cx, cy, label="", r=4, color="#000000", fill="#000000"):
    parts = [f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="{fill}" '
             f'stroke="{color}" stroke-width="0.8"/>']
    if label:
        parts.append(_text(cx + r + 2, cy - r, label, size=6.5, anchor="start"))
    return "".join(parts)


def terminal_point(cx, cy, label="", r=6, color="#000000"):
    parts = [f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="#ffffff" '
             f'stroke="{color}" stroke-width="1.0"/>',
             f'<line x1="{cx-r*0.7:.2f}" y1="{cy-r*0.7:.2f}" x2="{cx+r*0.7:.2f}" '
             f'y2="{cy+r*0.7:.2f}" stroke="{color}" stroke-width="0.8"/>']
    if label:
        parts.append(_text(cx, cy - r - 2, label, size=6, weight="bold"))
    return "".join(parts)


def heat_load(cx, cy, color="#008000"):
    """ISA-style filled triangle heat-load marker (per source legend)."""
    s = 5.5
    return (f'<path d="M {cx:.2f} {cy-s:.2f} L {cx+s:.2f} {cy+s:.2f} '
            f'L {cx-s:.2f} {cy+s:.2f} Z" fill="{color}" stroke="{color}" '
            f'stroke-width="0.5"/>')


# ---------------------------------------------------------------------------
# v2 additions: scope diamonds, bellows, DIS interlock, limit switch, Lemo
# ---------------------------------------------------------------------------

# Scope-boundary category letters per SCK CEN standard AD_01.16
#   Termination-point diamond carries: TP / <category><unique no.> / <next system>
SCOPE_CATEGORY = {
    "B": ("Building", "#7a3b00"),
    "C": ("Civil", "#5d4037"),
    "E": ("Electrical", "#b8860b"),
    "G": ("Compressed gasses", "#0066a6"),
    "H": ("HVAC", "#008080"),
    "L": ("Liquid waste", "#1f7a1f"),
    "S": ("Solid waste", "#6d4c41"),
    "W": ("Water", "#00a000"),
}


def scope_diamond(cx, cy, code, size=9.0, color="#a000a0", text_size=5.6,
                  label_below=True):
    """ISA scope / terminal-point diamond carrying a TPXYYYY interface code.

    Simple single-cell diamond (kept for legend / compatibility).
    """
    s = size
    parts = [
        f'<path d="M {cx:.2f} {cy-s:.2f} L {cx+s:.2f} {cy:.2f} '
        f'L {cx:.2f} {cy+s:.2f} L {cx-s:.2f} {cy:.2f} Z" '
        f'fill="#ffffff" stroke="{color}" stroke-width="1.1"/>'
    ]
    if label_below:
        parts.append(_text(cx, cy + s + text_size + 1, code, size=text_size,
                           weight="bold", fill=color))
    else:
        parts.append(_text(cx, cy + 2.0, code, size=text_size - 1.2, weight="bold",
                           fill=color))
    return "".join(parts)


def scope_diamond_3c(cx, cy, cat_code, next_sys="", size=13.0, color="#a000a0",
                     text_size=4.6):
    """AD_01.16 termination-point diamond: 3 stacked compartments.

      top    = 'TP'
      middle = category letter + unique number (e.g. 'G1001')
      bottom = next system / process the line continues into (ZZZ)

    The diamond marks the 'last-meter' hand-over boundary between in-scope
    and out-of-scope assets.
    """
    s = size
    # diamond outline
    parts = [
        f'<path d="M {cx:.2f} {cy-s:.2f} L {cx+s:.2f} {cy:.2f} '
        f'L {cx:.2f} {cy+s:.2f} L {cx-s:.2f} {cy:.2f} Z" '
        f'fill="#ffffff" stroke="{color}" stroke-width="1.2"/>'
    ]
    # two horizontal dividers at +/- s/3 (chord lines inside the diamond)
    for frac in (-1.0 / 3.0, 1.0 / 3.0):
        yy = cy + frac * s
        half = s * (1.0 - abs(frac))      # half-width of diamond at this height
        parts.append(f'<line x1="{cx-half:.2f}" y1="{yy:.2f}" '
                     f'x2="{cx+half:.2f}" y2="{yy:.2f}" '
                     f'stroke="{color}" stroke-width="0.6"/>')
    parts.append(_text(cx, cy - s / 3.0 + text_size / 2.0, "TP",
                       size=text_size, weight="bold", fill=color))
    parts.append(_text(cx, cy + text_size / 2.0 - 0.3, cat_code,
                       size=text_size, weight="bold", fill="#000000"))
    parts.append(_text(cx, cy + s / 3.0 + text_size / 2.0 + 0.3,
                       (next_sys or "\u2014")[:6], size=text_size - 0.6,
                       fill="#333333"))
    return "".join(parts)


# ---------------------------------------------------------------------------
# Signal / instrument-connection lines (ISA 5.1 / AD_01.16)
#   All instrument signals are drawn thin (0.25 mm).  Three visually-distinct
#   patterns are provided so a black-and-white plot still differentiates them.
# ---------------------------------------------------------------------------

def signal_line(x1, y1, x2, y2, kind="electric", color="#000000", w=0.95):
    """Return an instrument-signal connection line.

    kind:
      'electric'  -> dotted (fine dot pattern)
      'pneumatic' -> dashed with cross-ticks (// hatch) per AD_01.16
      'hydraulic' -> dash-dot (L / dash-dot pattern)
      'software'  -> dotted with circles (kept dotted-fine for clarity)
      'capillary' -> dash with x marks
    """
    base = (f'fill:none;stroke:{color};stroke-width:{w:.2f};'
            f'stroke-linecap:round')
    if kind == "electric":
        dash = ';stroke-dasharray:0.1,3'        # dotted
    elif kind == "pneumatic":
        dash = ';stroke-dasharray:7,3'          # long dashes (cross-ticks added)
    elif kind == "hydraulic":
        dash = ';stroke-dasharray:9,2.5,1.5,2.5'  # dash-dot
    elif kind == "software":
        dash = ';stroke-dasharray:0.1,3.5'
    elif kind == "capillary":
        dash = ';stroke-dasharray:5,2,1,2'
    else:
        dash = ''
    parts = [f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
             f'style="{base}{dash}"/>']
    # pneumatic gets // cross-tick hatch marks along the line
    if kind == "pneumatic":
        length = math.hypot(x2 - x1, y2 - y1)
        if length > 1e-6:
            ux, uy = (x2 - x1) / length, (y2 - y1) / length
            nx, ny = -uy, ux          # normal
            step = 14.0
            t = step / 2.0
            tick = 3.0
            while t < length:
                mx, my = x1 + ux * t, y1 + uy * t
                # double tick (//) slanted
                for off in (-1.4, 1.4):
                    bx, by = mx + ux * off, my + uy * off
                    parts.append(
                        f'<line x1="{bx-nx*tick-ux*tick:.2f}" '
                        f'y1="{by-ny*tick-uy*tick:.2f}" '
                        f'x2="{bx+nx*tick+ux*tick:.2f}" '
                        f'y2="{by+ny*tick+uy*tick:.2f}" '
                        f'stroke="{color}" stroke-width="{max(0.5,w*0.8):.2f}"/>')
                t += step
    return "".join(parts)


def bellows(cx, cy, length=22.0, amp=4.0, n=5, color="#000000", w=1.0,
            horizontal=True):
    """Mechanical bellows / expansion element (anti thermal short-circuit)."""
    pts = []
    if horizontal:
        x0 = cx - length / 2.0
        step = length / n
        for i in range(n + 1):
            x = x0 + i * step
            y = cy + (amp if i % 2 else -amp)
            pts.append((x, y))
        d = "M %.2f %.2f " % (x0, cy) + " ".join("L %.2f %.2f" % p for p in pts) \
            + " L %.2f %.2f" % (cx + length / 2.0, cy)
    else:
        y0 = cy - length / 2.0
        step = length / n
        for i in range(n + 1):
            y = y0 + i * step
            x = cx + (amp if i % 2 else -amp)
            pts.append((x, y))
        d = "M %.2f %.2f " % (cx, y0) + " ".join("L %.2f %.2f" % p for p in pts) \
            + " L %.2f %.2f" % (cx, cy + length / 2.0)
    return (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w:.2f}" '
            f'stroke-linejoin="round"/>')


def limit_switch(cx, cy, number="", size=9.0, color="#000000", text_size=5.6):
    """ISA limit switch: bubble with 'LS' and an external roller/lever stub."""
    parts = [
        f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{size:.2f}" fill="#ffffff" '
        f'stroke="{color}" stroke-width="1.0"/>',
        # lever + roller stub (mechanical actuation)
        f'<line x1="{cx:.2f}" y1="{cy-size:.2f}" x2="{cx+size*0.9:.2f}" '
        f'y2="{cy-size*1.7:.2f}" stroke="{color}" stroke-width="1.0"/>',
        f'<circle cx="{cx+size*0.9:.2f}" cy="{cy-size*1.7:.2f}" r="{size*0.22:.2f}" '
        f'fill="#ffffff" stroke="{color}" stroke-width="0.8"/>',
        _text(cx, cy - 0.6, "LS", size=text_size, weight="bold", fill=color),
    ]
    if number:
        parts.append(_text(cx, cy + text_size + 0.5, number, size=text_size, fill=color))
    return "".join(parts)


def dis_block(x, y, w=150, h=92, color="#000000", accent="#c01010",
              title="DIS", subtitle="Device Interlock System",
              inputs=None, output="MASTER INTERLOCK \u2192 RF"):
    """Aggregating interlock-logic block (DIS).

    Draws a rounded rectangle with a title bar, listed aggregated inputs on the
    left and a single master-interlock output arrow on the right.
    """
    inputs = inputs or ["Vacuum OK", "Cryo OK", "Utilities OK"]
    parts = [
        f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" rx="5" '
        f'fill="#fff8f8" stroke="{accent}" stroke-width="1.6"/>',
        f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="16" rx="5" '
        f'fill="{accent}"/>',
        _text(x + w / 2.0, y + 11.5, f"{title} \u2014 {subtitle}", size=7.0,
              weight="bold", fill="#ffffff"),
    ]
    # AND-gate glyph in centre
    gx, gy = x + w / 2.0 - 12, y + 34
    parts.append(
        f'<path d="M {gx:.2f} {gy:.2f} h 14 a 12 12 0 0 1 0 24 h -14 Z" '
        f'fill="#ffffff" stroke="{color}" stroke-width="1.0"/>')
    parts.append(_text(gx + 6, gy + 16, "&", size=8.5, weight="bold"))
    # inputs
    iy = y + 28
    for i, lab in enumerate(inputs):
        ly = iy + i * 13
        parts.append(f'<line x1="{x+6:.2f}" y1="{ly:.2f}" x2="{gx:.2f}" y2="{ly:.2f}" '
                     f'stroke="{color}" stroke-width="0.7" stroke-dasharray="3,2"/>')
        parts.append(_text(x + 8, ly - 2, lab, size=5.6, anchor="start", fill="#333"))
    # output arrow
    oy = y + 46
    ox = gx + 26
    parts.append(f'<line x1="{ox:.2f}" y1="{oy:.2f}" x2="{x+w-6:.2f}" y2="{oy:.2f}" '
                 f'stroke="{accent}" stroke-width="1.4"/>')
    parts.append(f'<path d="M {x+w-6:.2f} {oy:.2f} l -6 -3 l 0 6 Z" fill="{accent}"/>')
    parts.append(_text(x + w / 2.0 + 14, oy + 12, output, size=5.8, weight="bold",
                       fill=accent))
    return "".join(parts)


def lemo_connector(cx, cy, label="Lemo B (HV)", size=7.0, color="#000000",
                   text_size=5.4):
    """Patch-panel Lemo B-series connector glyph (circular multi-pin)."""
    parts = [
        f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{size:.2f}" fill="#eef2ff" '
        f'stroke="{color}" stroke-width="1.0"/>',
        f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{size*0.45:.2f}" fill="#ffffff" '
        f'stroke="{color}" stroke-width="0.7"/>',
    ]
    # 3 pin dots
    for ang in (90, 210, 330):
        a = math.radians(ang)
        px = cx + size * 0.62 * math.cos(a)
        py = cy - size * 0.62 * math.sin(a)
        parts.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="1.0" fill="{color}"/>')
    parts.append(_text(cx, cy + size + text_size + 0.5, label, size=text_size,
                       weight="bold", fill=color))
    return "".join(parts)


def note_box(x, y, lines, w=130, color="#005500", title=None, text_size=6.0):
    """Annotation note box (buffer volumes, handover notes, etc.)."""
    lh = text_size + 3.2
    h = lh * len(lines) + 10 + (lh if title else 0)
    parts = [f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" rx="3" '
             f'fill="#f5fff5" stroke="{color}" stroke-width="0.9"/>']
    ty = y + 8
    if title:
        ty += lh - 2
        parts.append(_text(x + 5, ty - 3, title, size=text_size + 0.6, anchor="start",
                           weight="bold", fill=color))
    for ln in lines:
        ty += lh
        parts.append(_text(x + 5, ty - 3, ln, size=text_size, anchor="start",
                           fill="#222"))
    return "".join(parts), h
