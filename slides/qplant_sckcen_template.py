"""Generate a QPLANT/SCK CEN aligned PowerPoint template.

The template uses a consistent color palette, footer numbering, and
placeholder content that can be replaced with project-specific data.
"""

import argparse
from pathlib import Path
from pptx import Presentation
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

PRIMARY_COLOR = RGBColor(0, 63, 114)  # Deep blue used for title bars
ACCENT_COLOR = RGBColor(0, 134, 192)  # Cyan accent for callouts
SAND_COLOR = RGBColor(232, 231, 226)  # Light neutral background
TEXT_COLOR = RGBColor(34, 34, 34)

TITLE_FONT = "Calibri"
BODY_FONT = "Calibri"

SLIDE_WIDTH = Inches(13.33)
SLIDE_HEIGHT = Inches(7.5)


def _text_box(slide, left, top, width, height, text="", font_size=18, bold=False,
              color=TEXT_COLOR, align=PP_ALIGN.LEFT):
    box = slide.shapes.add_textbox(left, top, width, height)
    frame = box.text_frame
    frame.clear()
    p = frame.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.bold = bold
    p.font.name = BODY_FONT
    p.font.color.rgb = color
    p.alignment = align
    return frame


def _add_footer(slide, doc_number, slide_idx, total_slides):
    width = SLIDE_WIDTH
    height = SLIDE_HEIGHT

    # Thin line above footer
    line = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RECTANGLE,
        Inches(0.3),
        height - Inches(0.55),
        width - Inches(0.6),
        Inches(0.02),
    )
    line.fill.solid()
    line.fill.fore_color.rgb = PRIMARY_COLOR
    line.line.fill.background()

    _text_box(
        slide,
        Inches(0.3),
        height - Inches(0.5),
        width - Inches(1.6),
        Inches(0.35),
        text=f"Document: {doc_number}",
        font_size=12,
        color=PRIMARY_COLOR,
    )
    _text_box(
        slide,
        width - Inches(1.3),
        height - Inches(0.5),
        Inches(1.0),
        Inches(0.35),
        text=f"{slide_idx}/{total_slides}",
        font_size=12,
        align=PP_ALIGN.RIGHT,
        color=PRIMARY_COLOR,
    )


def _title_block(slide, title, subtitle=""):
    header = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RECTANGLE,
        Inches(0),
        Inches(0),
        SLIDE_WIDTH,
        Inches(1.5),
    )
    header.fill.solid()
    header.fill.fore_color.rgb = PRIMARY_COLOR
    header.line.fill.background()

    title_frame = _text_box(
        slide,
        Inches(0.6),
        Inches(0.35),
        SLIDE_WIDTH - Inches(1.2),
        Inches(0.8),
        text=title,
        font_size=38,
        bold=True,
        color=RGBColor(255, 255, 255),
    )
    title_frame.paragraphs[0].font.name = TITLE_FONT

    if subtitle:
        subtitle_frame = _text_box(
            slide,
            Inches(0.6),
            Inches(1.1),
            SLIDE_WIDTH - Inches(1.2),
            Inches(0.5),
            text=subtitle,
            font_size=18,
            color=RGBColor(220, 235, 247),
        )
        subtitle_frame.paragraphs[0].font.name = BODY_FONT


def _agenda_slide(prs, doc_number):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _title_block(slide, "Agenda", "Reusable section outline")

    content = slide.shapes.add_textbox(Inches(0.8), Inches(1.8), prs.slide_width - Inches(1.6), Inches(4.5))
    tf = content.text_frame
    tf.text = "1. Executive summary\n2. System scope and constraints\n3. Integration timeline\n4. Interfaces and dependencies\n5. Risks and mitigations\n6. Next actions"
    for p in tf.paragraphs:
        p.font.name = BODY_FONT
        p.font.size = Pt(22)
        p.font.color.rgb = TEXT_COLOR
    return slide


def _status_slide(prs, doc_number):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _title_block(slide, "Project status", "Drop in current data for weekly reviews")

    left_block = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RECTANGLE,
        Inches(0.6),
        Inches(1.8),
        prs.slide_width / 2 - Inches(0.9),
        Inches(3.5),
    )
    left_block.fill.solid()
    left_block.fill.fore_color.rgb = SAND_COLOR
    left_block.line.color.rgb = PRIMARY_COLOR

    left_tf = left_block.text_frame
    left_tf.text = "Highlights"  # heading
    left_tf.paragraphs[0].font.size = Pt(20)
    left_tf.paragraphs[0].font.bold = True
    left_tf.paragraphs[0].font.name = TITLE_FONT
    left_tf.paragraphs[0].font.color.rgb = PRIMARY_COLOR
    for bullet in [
        "Cryogenic loop sizing validated against SCK CEN purge parameters.",
        "Control cabinet design frozen; vendor RFQs issued.",
        "Integration test window confirmed with MYRRHA operations.",
    ]:
        p = left_tf.add_paragraph()
        p.text = bullet
        p.level = 1
        p.font.name = BODY_FONT
        p.font.size = Pt(16)
        p.font.color.rgb = TEXT_COLOR

    right_block = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RECTANGLE,
        prs.slide_width / 2 + Inches(0.3),
        Inches(1.8),
        prs.slide_width / 2 - Inches(0.9),
        Inches(3.5),
    )
    right_block.fill.solid()
    right_block.fill.fore_color.rgb = RGBColor(240, 247, 252)
    right_block.line.color.rgb = PRIMARY_COLOR

    right_tf = right_block.text_frame
    right_tf.text = "KPI snapshot"
    right_tf.paragraphs[0].font.size = Pt(20)
    right_tf.paragraphs[0].font.bold = True
    right_tf.paragraphs[0].font.name = TITLE_FONT
    right_tf.paragraphs[0].font.color.rgb = PRIMARY_COLOR
    for label, value in [
        ("Design maturity", "82% complete"),
        ("Interface agreements", "5/7 signed"),
        ("Risk exposure", "Low (2 open items)"),
    ]:
        p = right_tf.add_paragraph()
        p.text = f"{label}: {value}"
        p.level = 1
        p.font.name = BODY_FONT
        p.font.size = Pt(16)
        p.font.color.rgb = TEXT_COLOR

    return slide


def _architecture_slide(prs, doc_number):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _title_block(slide, "System architecture", "Replace shapes with updated diagrams")

    canvas = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
        Inches(0.8),
        Inches(1.8),
        prs.slide_width - Inches(1.6),
        Inches(4.0),
    )
    canvas.fill.solid()
    canvas.fill.fore_color.rgb = RGBColor(245, 249, 252)
    canvas.line.color.rgb = PRIMARY_COLOR

    # Sample blocks
    for idx, title in enumerate(["Helium storage", "Compression train", "Cold box", "Distribution to cryomodules"]):
        block = slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
            Inches(1.0 + idx * 1.8),
            Inches(2.3),
            Inches(1.5),
            Inches(1.2),
        )
        block.fill.solid()
        block.fill.fore_color.rgb = RGBColor(220, 235, 247)
        block.line.color.rgb = ACCENT_COLOR
        tf = block.text_frame
        tf.text = title
        tf.paragraphs[0].font.size = Pt(14)
        tf.paragraphs[0].font.name = BODY_FONT
        tf.paragraphs[0].font.bold = True
        tf.paragraphs[0].font.color.rgb = TEXT_COLOR

    caption = _text_box(
        slide,
        Inches(0.9),
        Inches(4.3),
        prs.slide_width - Inches(1.8),
        Inches(0.8),
        text="Use this slide to paste Visio exports or draw lightweight flows linking helium storage, compression, cold box, and distribution headers.",
        font_size=14,
        color=TEXT_COLOR,
    )
    caption.paragraphs[0].font.name = BODY_FONT
    return slide


def _timeline_slide(prs, doc_number):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _title_block(slide, "Schedule & milestones", "Quarterly checkpoints with owner and dependencies")

    milestones = [
        ("Q1", "Finalize P&ID freeze and HAZOP"),
        ("Q2", "Factory acceptance for compression skids"),
        ("Q3", "Cold box delivery to SCK CEN"),
        ("Q4", "Site integration and performance test"),
    ]

    for idx, (label, desc) in enumerate(milestones):
        top = Inches(2.0 + idx * 0.9)
        _text_box(
            slide,
            Inches(0.8),
            top,
            Inches(1.0),
            Inches(0.4),
            text=label,
            font_size=16,
            bold=True,
            color=PRIMARY_COLOR,
        )
        _text_box(
            slide,
            Inches(1.8),
            top,
            prs.slide_width - Inches(2.6),
            Inches(0.4),
            text=desc,
            font_size=16,
        )

    # Dependency note with hyperlink
    note = _text_box(
        slide,
        Inches(0.8),
        Inches(5.0),
        prs.slide_width - Inches(1.6),
        Inches(0.6),
        text="Dependencies documented in the SCK CEN interface matrix (clickable link).",
        font_size=14,
        color=ACCENT_COLOR,
    )
    run = note.paragraphs[0].add_run()
    run.text = "  https://sharepoint.sckcen.be/qplant/interfaces"
    run.hyperlink.address = "https://sharepoint.sckcen.be/qplant/interfaces"
    run.font.color.rgb = ACCENT_COLOR
    run.font.name = BODY_FONT
    run.font.size = Pt(14)
    return slide


def _risk_slide(prs, doc_number):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _title_block(slide, "Risk and mitigation register", "Keep the table; replace rows with your current items")

    rows = [
        ("Cryogenic valve lead time", "Vendor lead time exceeds site window", "Place advance order; keep dual suppliers"),
        ("Interface firmware", "PLC safety libraries misaligned", "Synchronize versions with SCK CEN validation bench"),
        ("Site readiness", "Utility hook-ups delayed", "Stage temporary utilities; pre-commission compressors"),
    ]

    table = slide.shapes.add_table(len(rows) + 1, 3, Inches(0.6), Inches(1.9), prs.slide_width - Inches(1.2), Inches(3.6)).table
    table.columns[0].width = Inches(2.2)
    table.columns[1].width = Inches(3.0)
    table.columns[2].width = Inches(3.0)

    headers = ["Risk", "Impact", "Mitigation"]
    for idx, header in enumerate(headers):
        cell = table.cell(0, idx)
        cell.text = header
        para = cell.text_frame.paragraphs[0]
        para.font.bold = True
        para.font.name = TITLE_FONT
        para.font.size = Pt(16)
        para.font.color.rgb = PRIMARY_COLOR

    for row_idx, row in enumerate(rows, start=1):
        for col_idx, value in enumerate(row):
            cell = table.cell(row_idx, col_idx)
            cell.text = value
            para = cell.text_frame.paragraphs[0]
            para.font.name = BODY_FONT
            para.font.size = Pt(14)
            para.font.color.rgb = TEXT_COLOR
    return slide


def _closing_slide(prs, doc_number):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _title_block(slide, "Next actions", "Update dates, owners, and status for handover")

    checklist = [
        ("Update purge parameter alignment", "Owner: Process team", "Due: 15 Feb"),
        ("Freeze interface signals with controls", "Owner: PLC lead", "Due: 22 Feb"),
        ("Publish installation work-pack", "Owner: Site engineering", "Due: 01 Mar"),
    ]

    for idx, (item, owner, due) in enumerate(checklist):
        _text_box(
            slide,
            Inches(0.8),
            Inches(1.9 + idx * 0.9),
            prs.slide_width - Inches(1.6),
            Inches(0.5),
            text=f"• {item} ({owner}) — {due}",
            font_size=18,
            color=TEXT_COLOR,
        )

    note = _text_box(
        slide,
        Inches(0.8),
        Inches(4.8),
        prs.slide_width - Inches(1.6),
        Inches(0.8),
        text="Reminder: export PDF with embedded fonts before circulating outside SCK CEN.",
        font_size=14,
        color=PRIMARY_COLOR,
    )
    note.paragraphs[0].font.bold = True
    return slide


def build_template(output_path: Path, doc_number: str = "SCK CEN/0000") -> None:
    prs = Presentation()
    prs.slide_width = Inches(13.33)
    prs.slide_height = Inches(7.5)

    global SLIDE_WIDTH, SLIDE_HEIGHT
    SLIDE_WIDTH = prs.slide_width
    SLIDE_HEIGHT = prs.slide_height

    slides = [
        _agenda_slide(prs, doc_number),
        _status_slide(prs, doc_number),
        _architecture_slide(prs, doc_number),
        _timeline_slide(prs, doc_number),
        _risk_slide(prs, doc_number),
        _closing_slide(prs, doc_number),
    ]

    for idx, slide in enumerate(slides, start=1):
        _add_footer(slide, doc_number, idx, len(slides))

    prs.save(output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate the QPLANT/SCK CEN slide template")
    parser.add_argument(
        "--doc-number",
        default="SCK CEN/0000",
        help="Document number to display in the footer on every slide",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).with_name("qplant_sckcen_template.pptx"),
        help="Where to write the generated PowerPoint deck",
    )
    args = parser.parse_args()

    build_template(args.output, doc_number=args.doc_number)
    print(f"Generated {args.output}")
