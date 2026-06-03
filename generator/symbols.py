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


def cavity(cx, cy, w=46, h=30, label="", color="#aa4400"):
    """Schematic SRF cavity / coupler body (rounded brown block)."""
    parts = [f'<rect x="{cx-w/2:.2f}" y="{cy-h/2:.2f}" width="{w:.2f}" height="{h:.2f}" '
             f'rx="6" fill="#f3e2d8" stroke="{color}" stroke-width="1.4"/>']
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
