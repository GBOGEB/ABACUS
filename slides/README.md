# QPLANT / SCK CEN slide template

This folder packages a reusable PowerPoint deck that mirrors the SCK CEN look-and-feel (blue title bar, Calibri typography, numbered footer with a `SCK CEN/####` document code). Use it as a corporate-safe starting point for new QPLANT presentations.

## What is included
- **Template generator** (`qplant_sckcen_template.py`): builds a six-slide starter deck with agenda, status, architecture placeholder, schedule, risk table, and next-actions checklist.
- **Styling choices**: Calibri headings/body, deep-blue title band, cyan accents, light neutral content panels, left-aligned bullet spacing sized for short, high-density engineering notes.

> The generated `.pptx` is not committed to the repository to avoid binary diffs. Run the script locally to produce the file.

## Quick use
1. Run the generator to produce a fresh deck: `python slides/qplant_sckcen_template.py --doc-number "SCK CEN/1427" --output qplant_sckcen_template.pptx`.
2. Open the resulting `.pptx` in PowerPoint or LibreOffice.
3. Replace the placeholder bullets, tables, and callouts with your project content.
4. Update the document code in the footer (e.g., `SCK CEN/1427`). Every slide already displays the footer and page number.
5. Export to PDF with embedded fonts when circulating externally.

## Regenerate or customize
Run the generator to rebuild the deck or change the document code:

```bash
python slides/qplant_sckcen_template.py            # writes slides/qplant_sckcen_template.pptx
python slides/qplant_sckcen_template.py --doc-number "SCK CEN/1427"  # update footer text
```

The script defaults to a 16:9 canvas (13.33" x 7.5") and applies the same colors/fonts everywhere to keep layouts consistent.

## Pandoc reference workflow
You can also treat `qplant_sckcen_template.pptx` as a Pandoc reference for Markdown-to-PowerPoint conversion:

```bash
pandoc report.md \
  --reference-doc=slides/qplant_sckcen_template.pptx \
  -o qplant_report.pptx
```

Pandoc will reuse the title bar, footer, and font sizing from the reference deck so new slides stay aligned with the corporate style.
