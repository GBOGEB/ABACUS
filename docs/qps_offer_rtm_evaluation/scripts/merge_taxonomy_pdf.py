"""
merge_taxonomy_pdf.py -- renders /tmp/print_taxonomy.html (portrait) and
/tmp/print_domain_summary.html (landscape) to PDF via headless Chromium
(Playwright), then merges them into one mixed-orientation PDF.

This is the render+merge step build_pdf_export.py's own docstring always
described but never saved as a script (standing gap, closed this round).
Run build_pdf_export.py first to (re)generate the two source HTML files.

Usage:
    python3 build_pdf_export.py /tmp/nav_data_vN.json
    python3 merge_taxonomy_pdf.py QPS_Taxonomy_and_Domain_Summary.pdf
"""
import sys
from playwright.sync_api import sync_playwright
from pypdf import PdfWriter

OUT = sys.argv[1] if len(sys.argv) > 1 else "QPS_Taxonomy_and_Domain_Summary.pdf"

with sync_playwright() as p:
    browser = p.chromium.launch()

    page = browser.new_page()
    page.goto("file:///tmp/print_taxonomy.html")
    page.wait_for_timeout(200)
    page.pdf(path="/tmp/_taxonomy_portrait.pdf", format="A4", landscape=False,
             print_background=True, margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
    page.close()

    page2 = browser.new_page()
    page2.goto("file:///tmp/print_domain_summary.html")
    page2.wait_for_timeout(200)
    page2.pdf(path="/tmp/_domain_landscape.pdf", format="A4", landscape=True,
              print_background=True, margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
    page2.close()

    browser.close()

writer = PdfWriter()
for f in ("/tmp/_taxonomy_portrait.pdf", "/tmp/_domain_landscape.pdf"):
    writer.append(f)
with open(OUT, "wb") as fh:
    writer.write(fh)

print(f"wrote {OUT}")
