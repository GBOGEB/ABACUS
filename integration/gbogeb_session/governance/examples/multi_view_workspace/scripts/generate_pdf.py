#!/usr/bin/env python3
"""
PDF Generation Script — WeasyPrint
====================================

Converts the engineering report (Markdown → HTML → PDF) with themed styling
matching the GBOGEB/ABACUS SEMANTIC_THEME tokens.

Usage:
    python generate_pdf.py                          # default output
    python generate_pdf.py --theme corporate        # purple corporate theme
    python generate_pdf.py --output custom.pdf      # custom output path
    python generate_pdf.py --yaml ../output/context/engineering_data.yaml

Dependencies:
    pip install weasyprint markdown pyyaml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

try:
    import markdown
except ImportError:
    print("ERROR: 'markdown' package required. Install: pip install markdown")
    sys.exit(1)

try:
    import yaml
except ImportError:
    print("ERROR: 'pyyaml' package required. Install: pip install pyyaml")
    sys.exit(1)


# ============================================================================
# Theme Definitions — mirrors index.html SEMANTIC_THEME tokens
# ============================================================================
THEMES: dict[str, dict[str, str]] = {
    "userstyle": {
        "primary": "#1a73e8",
        "accent": "#34a853",
        "surface": "#ffffff",
        "surface_alt": "#f8f9fa",
        "on_surface": "#202124",
        "muted": "#5f6368",
        "border": "#dadce0",
        "font": "'Segoe UI', system-ui, sans-serif",
        "font_mono": "'Cascadia Code', 'Consolas', monospace",
    },
    "corporate": {
        "primary": "#6d28d9",
        "accent": "#a78bfa",
        "surface": "#faf5ff",
        "surface_alt": "#f3e8ff",
        "on_surface": "#1e1b4b",
        "muted": "#6b7280",
        "border": "#c4b5fd",
        "font": "'Inter', system-ui, sans-serif",
        "font_mono": "'JetBrains Mono', monospace",
    },
    "focus": {
        "primary": "#60a5fa",
        "accent": "#34d399",
        "surface": "#0f172a",
        "surface_alt": "#1e293b",
        "on_surface": "#f1f5f9",
        "muted": "#94a3b8",
        "border": "#334155",
        "font": "'IBM Plex Sans', system-ui, sans-serif",
        "font_mono": "'IBM Plex Mono', monospace",
    },
}


def build_css(theme_name: str) -> str:
    """Generate CSS for PDF rendering using theme tokens."""
    t = THEMES.get(theme_name, THEMES["userstyle"])
    return f"""
    @page {{
        size: A4;
        margin: 25mm 20mm 25mm 20mm;
        @bottom-center {{
            content: counter(page) " / " counter(pages);
            font-size: 9pt;
            color: {t['muted']};
        }}
    }}
    body {{
        font-family: {t['font']};
        font-size: 11pt;
        line-height: 1.6;
        color: {t['on_surface']};
        background: {t['surface']};
    }}
    h1 {{
        font-size: 20pt;
        color: {t['primary']};
        border-bottom: 2px solid {t['accent']};
        padding-bottom: 6px;
        margin-top: 0;
    }}
    h2 {{
        font-size: 15pt;
        color: {t['primary']};
        border-bottom: 1px solid {t['border']};
        padding-bottom: 4px;
        margin-top: 20px;
    }}
    h3 {{
        font-size: 12pt;
        color: {t['on_surface']};
        margin-top: 14px;
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
        margin: 12px 0;
        font-size: 10pt;
    }}
    th, td {{
        padding: 6px 10px;
        border: 1px solid {t['border']};
        text-align: left;
    }}
    th {{
        background: {t['surface_alt']};
        font-weight: 700;
    }}
    code {{
        background: {t['surface_alt']};
        padding: 1px 4px;
        border-radius: 3px;
        font-family: {t['font_mono']};
        font-size: 9.5pt;
    }}
    pre {{
        background: {t['surface_alt']};
        padding: 12px 16px;
        border-radius: 6px;
        border-left: 3px solid {t['primary']};
        font-family: {t['font_mono']};
        font-size: 9pt;
        overflow-x: auto;
        white-space: pre-wrap;
    }}
    blockquote {{
        border-left: 3px solid {t['accent']};
        padding-left: 12px;
        color: {t['muted']};
        margin: 12px 0;
    }}
    hr {{
        border: none;
        border-top: 1px solid {t['border']};
        margin: 20px 0;
    }}
    strong {{ color: {t['on_surface']}; }}
    a {{ color: {t['primary']}; text-decoration: none; }}
    """


def load_yaml_metadata(yaml_path: Path) -> dict[str, Any]:
    """Load YAML for optional metadata injection."""
    if not yaml_path.exists():
        return {}
    with open(yaml_path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def generate_pdf(
    md_path: Path,
    output_path: Path,
    theme: str = "userstyle",
    yaml_path: Path | None = None,
) -> None:
    """Convert Markdown to themed PDF via WeasyPrint."""
    # Lazy import — WeasyPrint is heavy
    try:
        from weasyprint import HTML
    except ImportError:
        print("ERROR: 'weasyprint' package required. Install: pip install weasyprint")
        sys.exit(1)

    md_text = md_path.read_text(encoding="utf-8")

    # Convert Markdown → HTML
    html_body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "codehilite", "toc"],
    )

    css = build_css(theme)

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><style>{css}</style></head>
<body>{html_body}</body>
</html>"""

    print(f"Generating PDF: {output_path}")
    print(f"  Theme:    {theme}")
    print(f"  Source:   {md_path}")

    HTML(string=full_html).write_pdf(str(output_path))
    size_kb = output_path.stat().st_size / 1024
    print(f"  Output:   {output_path} ({size_kb:.1f} KB)")
    print("  ✓ Done")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="GBOGEB/ABACUS — PDF Report Generator (WeasyPrint)"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path(__file__).parent.parent / "output" / "documents" / "report.md",
        help="Input Markdown file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent.parent / "output" / "documents" / "report.pdf",
        help="Output PDF path",
    )
    parser.add_argument(
        "--theme",
        choices=list(THEMES.keys()),
        default="userstyle",
        help="Theme name (userstyle, corporate, focus)",
    )
    parser.add_argument(
        "--yaml",
        type=Path,
        default=None,
        help="Optional YAML data file for metadata injection",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: Input file not found: {args.input}")
        sys.exit(1)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    generate_pdf(args.input, args.output, args.theme, args.yaml)


if __name__ == "__main__":
    main()
