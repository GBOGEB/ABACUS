#!/usr/bin/env python3
"""Render every v5 SVG to A3 PDF + a review PNG (alongside the SVG)."""
import glob
import os

import cairosvg

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "output_v5")

# A3 landscape in PostScript points (420 x 297 mm)
PT_W = 420 / 25.4 * 72.0
PT_H = 297 / 25.4 * 72.0


def main():
    svgs = sorted(glob.glob(os.path.join(OUT, "*", "*.svg")))
    for svg in svgs:
        base = svg[:-4]
        pdf = base + ".pdf"
        png = base + ".png"
        cairosvg.svg2pdf(url=svg, write_to=pdf,
                         output_width=PT_W, output_height=PT_H)
        cairosvg.svg2png(url=svg, write_to=png, output_width=2000)
        print("rendered", os.path.relpath(svg, OUT))
    print(f"\nTotal: {len(svgs)} SVG -> PDF + PNG")


if __name__ == "__main__":
    main()
