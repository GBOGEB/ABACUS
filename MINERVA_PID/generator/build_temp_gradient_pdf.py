#!/usr/bin/env python3
"""Build TEMPERATURE_GRADIENT_VISUALIZATION.pdf -- a purpose-drawn A4-landscape
vector visualisation of the MINERVA cryogenic temperature ladder and the Line W
warm-return gradient (4.5 K -> 300 K)."""
import os
import cairosvg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "output_v5", "TEMPERATURE_GRADIENT_VISUALIZATION.pdf")

W, H = 1123.0, 794.0   # A4 landscape px @96dpi-ish


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def txt(x, y, s, size=14, anchor="start", weight="normal", fill="#111111"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="Arial, Helvetica, '
            f'sans-serif" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" fill="{fill}">{esc(s)}</text>')


body = []
body.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>')
body.append(f'<rect x="14" y="14" width="{W-28}" height="{H-28}" fill="none" '
            f'stroke="#0B2147" stroke-width="2"/>')
# header
body.append(f'<rect x="14" y="14" width="{W-28}" height="56" fill="#0B2147"/>')
body.append(txt(34, 50, "MINERVA CryoCell  -  Temperature Gradient Visualisation",
                size=24, weight="bold", fill="#ffffff"))
body.append(txt(W-34, 50, "P&ID v5", size=16, anchor="end", weight="bold",
                fill="#00A6BD"))
body.append(txt(34, 92, "Cryogenic temperature ladder of the distribution "
                "lines and the Line W warm-return gradient", size=14,
                fill="#444444"))

# ----- temperature ladder (vertical) -----
lad_x = 90
lad_y0 = 140
lad_y1 = 470
# log-ish scale markers: 2K bottom-cold..300K
levels = [
    (300, "300 K", "ambient / USER side (QRB handover)", "#d00000"),
    (60,  "60 K",  "Line E - thermal shield outlet",     "#FF0000"),
    (40,  "40 K",  "Line D - thermal shield inlet",      "#FF8000"),
    (4.5, "4.5 K", "Line A - 4.5 K primary helium",      "#0000FF"),
    (2.0, "2 K",   "Line B - 2 K superfluid helium",     "#00A6BD"),
]
import math
def ypos(t):
    # log scale between 2 and 300
    lo, hi = math.log10(2.0), math.log10(300.0)
    return lad_y1 - (lad_y1 - lad_y0) * (math.log10(t) - lo) / (hi - lo)

# gradient bar (cold bottom -> warm top)
body.append('<defs><linearGradient id="ladder" x1="0" y1="1" x2="0" y2="0">'
            '<stop offset="0" stop-color="#00A6BD"/>'
            '<stop offset="0.35" stop-color="#0000FF"/>'
            '<stop offset="0.6" stop-color="#FF8000"/>'
            '<stop offset="0.75" stop-color="#FF0000"/>'
            '<stop offset="1" stop-color="#d00000"/></linearGradient>'
            '<linearGradient id="wbar" x1="0" y1="0" x2="1" y2="0">'
            '<stop offset="0" stop-color="#00a6bd"/>'
            '<stop offset="0.5" stop-color="#00d000"/>'
            '<stop offset="1" stop-color="#d00000"/></linearGradient></defs>')
body.append(txt(lad_x - 26, lad_y0 - 16, "TEMPERATURE LADDER", size=14,
                weight="bold", fill="#0B2147"))
body.append(f'<rect x="{lad_x}" y="{lad_y0}" width="34" height="{lad_y1-lad_y0}" '
            f'rx="4" fill="url(#ladder)" stroke="#333" stroke-width="0.8"/>')
for t, lab, desc, col in levels:
    y = ypos(t)
    body.append(f'<line x1="{lad_x+34}" y1="{y:.1f}" x2="{lad_x+70}" '
                f'y2="{y:.1f}" stroke="{col}" stroke-width="2"/>')
    body.append(f'<circle cx="{lad_x+70}" cy="{y:.1f}" r="4" fill="{col}"/>')
    body.append(txt(lad_x+80, y-2, lab, size=14, weight="bold", fill=col))
    body.append(txt(lad_x+135, y-1, desc, size=12.5, fill="#333333"))

# ----- Line W warm-return gradient (horizontal) -----
wx0, wy = 90, 600
ww = W - 180
wh = 40
body.append(txt(wx0, wy - 22, "LINE W  -  WPS WARM RETURN GRADIENT  "
                "(~2.5 g/s  -  DN20  -  SS304)", size=15, weight="bold",
                fill="#006400"))
body.append(f'<rect x="{wx0}" y="{wy}" width="{ww}" height="{wh}" rx="5" '
            f'fill="url(#wbar)" stroke="#222" stroke-width="1"/>')
marks = [
    (0.00, "4.5 K", "QCELL side (cold end)\nleaves the cold box"),
    (0.50, "warming", "electrical heater /\nambient heat gain"),
    (1.00, "300 K", "USER side (warm end)\nQRB handover (NA.CP03)"),
]
for t, a, b in marks:
    mx = wx0 + ww * t
    anchor = "start" if t == 0 else ("end" if t == 1 else "middle")
    body.append(f'<line x1="{mx:.1f}" y1="{wy}" x2="{mx:.1f}" y2="{wy+wh}" '
                f'stroke="#000" stroke-width="1.2"/>')
    body.append(txt(mx, wy+wh+24, a, size=14, anchor=anchor, weight="bold"))
    for i, ln in enumerate(b.split("\n")):
        body.append(txt(mx, wy+wh+44+i*16, ln, size=11.5, anchor=anchor,
                        fill="#555555"))
# flow arrows along W
for k in range(1, 6):
    mx = wx0 + ww * k / 6.0
    body.append(f'<polygon points="{mx-7:.1f},{wy+wh/2-7:.1f} {mx+7:.1f},'
                f'{wy+wh/2:.1f} {mx-7:.1f},{wy+wh/2+7:.1f}" fill="#ffffff" '
                f'fill-opacity="0.8"/>')

# note panel (right of ladder)
nx, ny = 560, 150
body.append(f'<rect x="{nx}" y="{ny}" width="{W-28-nx-10}" height="300" rx="6" '
            f'fill="#f3f6fb" stroke="#cfd8e6" stroke-width="1"/>')
body.append(txt(nx+18, ny+30, "Why Line W has a gradient", size=15,
                weight="bold", fill="#0B2147"))
notes = [
    "Line W returns helium from the cold cryomodule back to the warm",
    "piping system (WPS). It must be re-warmed from cryogenic to ambient",
    "before reaching the user-side QRB handover.",
    "",
    "\u2022  Cold end  : 4.5 K, leaving the 4.5 K circuit / cold box",
    "\u2022  Mid-run   : electrical trim heater + ambient heat in-leak",
    "\u2022  Warm end  : ~300 K (ambient) at the QRB handover (NA.CP03)",
    "",
    "Design data:  ~2.5 g/s  \u00b7  6 bar  \u00b7  DN20  \u00b7  SS304",
    "",
    "The same gradient strip appears on every production sheet",
    "(layer 15_Temperature_Gradient) and in the MAIN-LINES schematic.",
]
for i, ln in enumerate(notes):
    body.append(txt(nx+18, ny+58+i*20, ln, size=12.5, fill="#333333"))

body.append(txt(34, H-26, "SCK CEN / Mott MacDonald  \u00b7  MYRRHA / MINERVA "
                "Phase 1  \u00b7  MMD 411066  \u00b7  RESTRICTED", size=10,
                fill="#777777"))

svg = (f'<?xml version="1.0" encoding="UTF-8"?>\n'
       f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
       f'viewBox="0 0 {W} {H}">\n' + "\n".join(body) + "\n</svg>\n")

tmp = "/tmp/_temp_gradient_v5.svg"
open(tmp, "w").write(svg)
cairosvg.svg2pdf(url=tmp, write_to=OUT)
print("wrote", OUT)
