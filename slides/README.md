# QPLANT / SCK CEN Slide Template

This folder contains a reusable PowerPoint template generator that creates presentations matching the SCK CEN corporate style guide. The generated decks feature the official SCK CEN look-and-feel with blue title bars, Calibri typography, and numbered footers with document codes (e.g., `SCK CEN/####`).

## What is included

- **Template generator** (`qplant_sckcen_template.py`): A Python script that builds a six-slide starter deck with:
  - Agenda slide with section outline
  - Status slide with highlights and KPI metrics
  - Architecture slide with placeholder diagrams
  - Schedule & milestones slide with quarterly checkpoints
  - Risk & mitigation register table
  - Next actions checklist with owners and dates

- **Corporate style guide compliance**:
  - **Typography**: Calibri for all headings and body text
  - **Colors**: Deep blue (`#003F72`) for title bands, cyan (`#0086C0`) for accents
  - **Layout**: 16:9 aspect ratio (13.33" × 7.5"), consistent spacing optimized for engineering presentations
  - **Footers**: Document code on every slide with automatic page numbering

> **Note**: Generated `.pptx` files are not committed to the repository to avoid binary diffs. Always regenerate the template locally when needed.

## Quick start

### 1. Generate a new presentation

Run the generator to create a fresh deck with default settings:

```bash
# Basic usage - creates qplant_sckcen_template.pptx in the slides directory
python slides/qplant_sckcen_template.py

# Specify a custom document number for the footer
python slides/qplant_sckcen_template.py --doc-number "SCK CEN/1427"

# Generate to a custom location
python slides/qplant_sckcen_template.py --doc-number "SCK CEN/1427" --output myproject/slides.pptx
```

### 2. Customize the content

1. Open the generated `.pptx` file in PowerPoint or LibreOffice
2. Replace placeholder text, tables, and diagrams with your project-specific content
3. Update the document code in the footer if needed (every slide shows the footer and page number)
4. Add or remove slides as required for your presentation
5. Export to PDF with embedded fonts before sharing externally

### 3. Regenerate when needed

The template is designed to be regenerated fresh each time. If you need to update the document code or start a new presentation:

```bash
# Generate a new template with updated document number
python slides/qplant_sckcen_template.py --doc-number "SCK CEN/1428"
```

## Advanced usage

### Creating custom templates

You can modify `qplant_sckcen_template.py` to create your own custom slide templates. The script is well-structured with reusable functions:

#### Color customization

Edit the color constants at the top of the file:

```python
PRIMARY_COLOR = RGBColor(0, 63, 114)   # Deep blue for title bars
ACCENT_COLOR = RGBColor(0, 134, 192)   # Cyan for callouts
SAND_COLOR = RGBColor(232, 231, 226)   # Light neutral backgrounds
TEXT_COLOR = RGBColor(34, 34, 34)      # Dark gray for body text
```

#### Font customization

Update the font family constants:

```python
TITLE_FONT = "Calibri"  # Font for slide titles
BODY_FONT = "Calibri"   # Font for body text
```

#### Adding new slide types

The template uses helper functions to build slides:

- `_title_block(slide, title, subtitle)` - Creates the blue header band
- `_add_footer(slide, doc_number, slide_idx, total_slides)` - Adds footer with page numbers
- `_text_box(slide, left, top, width, height, text, ...)` - Creates formatted text boxes

Example of adding a custom slide:

```python
def _custom_slide(prs, doc_number):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _title_block(slide, "Your Title", "Optional subtitle")
    
    # Add your content using _text_box or other shape methods
    _text_box(
        slide,
        Inches(1.0),
        Inches(2.0),
        prs.slide_width - Inches(2.0),
        Inches(1.0),
        text="Your content here",
        font_size=18
    )
    return slide

# Then add it to the slides list in build_template():
slides = [
    _agenda_slide(prs, doc_number),
    _status_slide(prs, doc_number),
    _custom_slide(prs, doc_number),  # Your new slide
    # ... other slides
]
```

### Integrating with existing style guides

#### Using as a Pandoc reference

Treat the generated `.pptx` as a reference template for Pandoc to convert Markdown to PowerPoint:

```bash
# First, generate the base template
python slides/qplant_sckcen_template.py --output reference.pptx

# Then use it as a reference for Pandoc conversions
pandoc report.md \
  --reference-doc=reference.pptx \
  -o final_report.pptx
```

Pandoc will automatically apply the title bars, footers, fonts, and colors from the reference template to your Markdown content.

#### Extracting styles from existing presentations

If you have an existing corporate template in `.pptx` format, you can use it as a reference:

1. Generate the base template with `qplant_sckcen_template.py`
2. Open both files in PowerPoint
3. Use PowerPoint's "Slide Master" view to copy layouts from your corporate template
4. Save the combined template and use it as your Pandoc reference

### Style guide compliance tips

- **Fonts**: Always use Calibri for consistency with SCK CEN branding
- **Colors**: Stick to the defined color palette (blue #003F72, cyan #0086C0, neutral backgrounds)
- **Spacing**: Use consistent margins (0.6" - 0.8" from edges)
- **Text size**: Titles at 38pt, subtitles at 18-20pt, body text at 14-18pt
- **Document codes**: Always include the SCK CEN document code in the footer

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

## Troubleshooting

### Installation issues

If you get an error about missing `pptx` module:

```bash
pip install python-pptx
```

The script requires Python 3.8 or later and the `python-pptx` library.

### Font issues

**Problem**: Fonts don't display correctly in PowerPoint

**Solution**: 
- Ensure Calibri is installed on your system (included with Microsoft Office)
- On Linux, install Microsoft fonts: `sudo apt-get install ttf-mscorefonts-installer`
- Alternatively, update `TITLE_FONT` and `BODY_FONT` constants to use system fonts like "Arial" or "Liberation Sans"

### Generated files not appearing

**Problem**: The `.pptx` file isn't in the expected location

**Solution**:
- Check the output path specified with `--output`
- Ensure you have write permissions to the target directory
- The default output is `slides/qplant_sckcen_template.pptx` relative to where you run the command

### Pandoc conversion issues

**Problem**: Pandoc doesn't preserve the template styling

**Solution**:
- Ensure you're using a recent version of Pandoc (2.0+): `pandoc --version`
- Use `--reference-doc` (not the older `--reference-docx`)
- Generate a fresh reference template before conversion

### Customization not working

**Problem**: Changes to colors or fonts don't appear in the generated slides

**Solution**:
- Make sure you're editing the constants at the top of the file (lines 35-38)
- RGB values must be in the range 0-255
- Regenerate the template after making changes

## Examples

### Quick presentation for a weekly meeting

```bash
# Generate template with current date in doc number
python slides/qplant_sckcen_template.py --doc-number "SCK CEN/$(date +%Y%m%d)"
```

### Batch generation for multiple projects

```bash
# Create presentations for different project codes
for code in 1427 1428 1429; do
    python slides/qplant_sckcen_template.py \
        --doc-number "SCK CEN/$code" \
        --output "presentations/project_$code.pptx"
done
```

### Integration with CI/CD

```yaml
# Example GitHub Actions workflow
- name: Generate presentation
  run: |
    pip install python-pptx
    python slides/qplant_sckcen_template.py \
      --doc-number "SCK CEN/${{ github.run_number }}" \
      --output artifacts/slides.pptx
    
- name: Upload presentation
  uses: actions/upload-artifact@v3
  with:
    name: presentation
    path: artifacts/slides.pptx
```

## Dependencies

- Python 3.8+
- python-pptx >= 0.6.21
- Pillow (automatically installed with python-pptx)
- lxml (automatically installed with python-pptx)

Install all dependencies:

```bash
pip install python-pptx
```

## Contributing

To modify or extend the template generator:

1. Test your changes by generating a sample deck
2. Verify the output in PowerPoint or LibreOffice
3. Ensure all slides maintain the corporate style guide
4. Document any new parameters or customization options
5. Add examples for new features

## License

This template follows the SCK CEN corporate style guide. Use it for official SCK CEN and QPLANT project presentations.
