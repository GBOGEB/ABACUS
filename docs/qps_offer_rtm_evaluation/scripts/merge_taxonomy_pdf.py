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
import sys, tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright
from pypdf import PdfWriter

OUT = sys.argv[1] if len(sys.argv) > 1 else "QPS_Taxonomy_and_Domain_Summary.pdf"

# Same TMP_DIR resolution as build_pdf_export.py -- must agree on the same
# real path. Hardcoded POSIX "/tmp/..." file:// URLs previously failed here
# on Windows (net::ERR_FILE_NOT_FOUND): Chromium's file:// resolver does not
# do the drive-relative remap Python's own open("/tmp/...") does. as_uri()
# builds a correct file:// URL for whatever platform this actually runs on.
TMP_DIR = Path(tempfile.gettempdir())
TAXONOMY_HTML_PATH = TMP_DIR / "print_taxonomy.html"
DOMAIN_SUMMARY_HTML_PATH = TMP_DIR / "print_domain_summary.html"
TAXONOMY_PDF_PATH = TMP_DIR / "_taxonomy_portrait.pdf"
DOMAIN_PDF_PATH = TMP_DIR / "_domain_landscape.pdf"

with sync_playwright() as p:
    browser = p.chromium.launch()

    page = browser.new_page()
    page.goto(TAXONOMY_HTML_PATH.as_uri())
    page.wait_for_timeout(200)
    page.pdf(path=str(TAXONOMY_PDF_PATH), format="A4", landscape=False,
             print_background=True, margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
    page.close()

    page2 = browser.new_page()
    page2.goto(DOMAIN_SUMMARY_HTML_PATH.as_uri())
    page2.wait_for_timeout(200)
    page2.pdf(path=str(DOMAIN_PDF_PATH), format="A4", landscape=True,
              print_background=True, margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
    page2.close()

    browser.close()

writer = PdfWriter()
for f in (TAXONOMY_PDF_PATH, DOMAIN_PDF_PATH):
    writer.append(str(f))
with open(OUT, "wb") as fh:
    writer.write(fh)

print(f"wrote {OUT}")
