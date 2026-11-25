"""Render local HTML pages with Playwright (Chromium) and save screenshots; report console errors.

The render sub-assembly for HTML (K-HTML-02 style check): page loads, no console errors, screenshot at a given width.

    python -I -X utf8 DMAIC_V3/binary_engines/html_shot.py <page.html> [<page.html> ...] [--width 1280] [--mobile]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from estate_spec import ESTATE  # noqa: E402

OUT = ESTATE / "deep" / "_check"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pages", nargs="+")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--mobile", action="store_true", help="also render at 390 px wide")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    report = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for page_path in map(Path, a.pages):
            for w in [a.width] + ([390] if a.mobile else []):
                page = browser.new_page(viewport={"width": w, "height": a.height})
                errors = []
                page.on(
                    "console",
                    lambda m: errors.append(m.text) if m.type == "error" else None,
                )
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.goto(page_path.resolve().as_uri())
                page.wait_for_timeout(400)
                shot = OUT / f"shot_{page_path.stem[:40]}_{w}.png"
                page.screenshot(path=str(shot))
                overflow = page.evaluate(
                    "document.documentElement.scrollWidth > window.innerWidth"
                )
                report.append(
                    {
                        "page": page_path.name,
                        "width": w,
                        "console_errors": errors,
                        "horizontal_overflow": overflow,
                        "shot": shot.name,
                    }
                )
                page.close()
        browser.close()
    print(json.dumps(report, indent=1))
    return 1 if any(r["console_errors"] for r in report) else 0


if __name__ == "__main__":
    raise SystemExit(main())
