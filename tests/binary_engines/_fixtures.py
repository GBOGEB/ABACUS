"""Synthetic fixtures for the binary-engine tests. Nothing here comes from a real document.

The smoke folder holds one file of each of ten types, a duplicate and two versions of one handover ZIP. File names
are built from the strongest keyword of the first four configured epics, so the classifier is tested against the
configuration that is loaded (the neutral example in the tests) and this file names nothing itself.
"""

from __future__ import annotations

import os
import shutil
import zipfile
from pathlib import Path

SMOKE_FILES = 12


def fixture_names() -> dict:
    from estate_spec import EPICS

    if len(EPICS) < 4:
        raise ValueError(
            "the smoke fixture needs at least four epics in the configuration"
        )
    kw = [max(e[2].items(), key=lambda kv: kv[1])[0] for e in EPICS[:4]]
    return {
        "docx": f"{kw[0]}_smoke_note_v1.docx",
        "xlsx": f"{kw[0]}_smoke_table.xlsx",
        "pptx": f"{kw[1]}_smoke_deck.pptx",
        "pdf": f"{kw[2]}_smoke.pdf",
        "md": f"{kw[3]}_smoke_notes.md",
        "md_copy": f"{kw[3]}_smoke_notes (1).md",
        "zip_v1": f"{kw[0]}_handover_v1.zip",
        "zip_v2": f"{kw[0]}_handover_v2.zip",
        "epics": [e[0] for e in EPICS[:4]],
    }


def build_smoke(root: Path) -> dict:
    """Write the smoke folder (replacing it) and return fixture_names()."""
    import docx
    import fitz
    import openpyxl
    from PIL import Image

    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    names = fixture_names()
    d = docx.Document()
    d.add_heading("smoke document", 1)
    d.add_heading("Scope", 2)
    d.add_paragraph("item", style="List Bullet")
    d.add_paragraph("step", style="List Number")
    d.save(root / names["docx"])
    wb = openpyxl.Workbook()
    wb.active["A1"] = 1
    wb.active["A2"] = "=A1*2"
    wb.save(root / names["xlsx"])
    build_deck(root / names["pptx"], "loop A")
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "smoke pdf")
    pdf.set_toc([[1, "Intro", 1]])
    pdf.save(root / names["pdf"])
    (root / names["md"]).write_text(
        "# Notes\n\n## Lane\n\n- a\n  - b\n1. one\n", "utf-8"
    )
    (root / "plain_smoke_text.txt").write_text("plain smoke text\n", "utf-8")
    (root / "web_smoke.html").write_text(
        "<html><head><title>web</title></head><body><h1>WEB</h1></body></html>", "utf-8"
    )
    (root / "vector_smoke.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><text x="1" y="5">P-101</text></svg>',
        "utf-8",
    )
    Image.new("RGB", (8, 8), "teal").save(root / "smoke_image.png")
    for version, stamp in (("v1", 1_700_000_000), ("v2", 1_700_100_000)):
        path = root / names[f"zip_{version}"]
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("handover/MANIFEST.md", f"manifest {version}")
            for part in "abcd":
                zf.writestr(f"handover/{part}.txt", part)
        os.utime(path, (stamp, stamp))
    shutil.copy(root / names["md"], root / names["md_copy"])
    return names


def build_deck(path: Path, label: str, extra_words: str = "") -> None:
    """One slide: two boxes joined by a bound connector, and a text box."""
    from pptx import Presentation
    from pptx.enum.shapes import MSO_CONNECTOR
    from pptx.util import Inches

    pres = Presentation()
    slide = pres.slides.add_slide(pres.slide_layouts[6])
    a = slide.shapes.add_shape(1, Inches(1), Inches(1), Inches(1), Inches(1))
    b = slide.shapes.add_shape(1, Inches(4), Inches(1), Inches(1), Inches(1))
    a.text_frame.text = "PUMP P-101"
    b.text_frame.text = "TANK T-201"
    box = slide.shapes.add_textbox(Inches(1), Inches(3), Inches(6), Inches(1))
    box.text_frame.text = (label + " " + extra_words).strip()
    connector = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, 0, 0, 1, 1)
    connector.begin_connect(a, 3)
    connector.end_connect(b, 1)
    pres.save(path)
