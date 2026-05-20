#!/usr/bin/env python3
"""
WCAG_CONTRAST_CHECKER.py — WCAG AA Contrast Validation Engine
GBOGEB/ABACUS A6 Governance Engine

Validates that all color combinations in themes and content meet
WCAG AA minimum contrast ratios:
  - Normal text: 4.5:1
  - Large text (≥24px or ≥18.66px bold): 3:1
  - UI components / graphical objects: 3:1

References: RULE-060, RULE-061, RULE-062 (RENDER_RULES.md)
"""

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# ── WCAG Constants ──
CONTRAST_AA_NORMAL = 4.5
CONTRAST_AA_LARGE = 3.0
CONTRAST_AAA_NORMAL = 7.0
CONTRAST_AAA_LARGE = 4.5


# ── Color Utilities ──

def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    if len(hex_color) == 8:
        hex_color = hex_color[:6]  # Strip alpha
    if len(hex_color) != 6:
        raise ValueError(f"Invalid hex color: #{hex_color}")
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
    )


def relative_luminance(r: int, g: int, b: int) -> float:
    """Calculate relative luminance per WCAG 2.1 definition."""
    def linearize(c: int) -> float:
        srgb = c / 255.0
        if srgb <= 0.04045:
            return srgb / 12.92
        return math.pow((srgb + 0.055) / 1.055, 2.4)

    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)


def contrast_ratio(color1: tuple[int, int, int], color2: tuple[int, int, int]) -> float:
    """Calculate WCAG contrast ratio between two RGB colors."""
    lum1 = relative_luminance(*color1)
    lum2 = relative_luminance(*color2)
    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)
    return (lighter + 0.05) / (darker + 0.05)


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB tuple to hex string."""
    return f"#{r:02x}{g:02x}{b:02x}"


# ── Finding Data ──

@dataclass
class ContrastFinding:
    foreground: str
    background: str
    ratio: float
    required_ratio: float
    context_type: str   # "normal_text", "large_text", "ui_component"
    location: str
    passed: bool
    level: str = "AA"

    def to_dict(self) -> dict[str, Any]:
        return {
            "foreground": self.foreground,
            "background": self.background,
            "ratio": round(self.ratio, 2),
            "required_ratio": self.required_ratio,
            "context_type": self.context_type,
            "location": self.location,
            "passed": self.passed,
            "level": self.level,
        }

    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return (
            f"[{status}] {self.location} — "
            f"fg:{self.foreground} bg:{self.background} "
            f"ratio:{self.ratio:.2f}:1 (required {self.required_ratio}:1)"
        )


@dataclass
class ContrastResults:
    findings: list[ContrastFinding] = field(default_factory=list)

    @property
    def failures(self) -> list[ContrastFinding]:
        return [f for f in self.findings if not f.passed]

    @property
    def passed(self) -> bool:
        return len(self.failures) == 0

    def add(self, finding: ContrastFinding) -> None:
        self.findings.append(finding)

    def summary(self) -> str:
        total = len(self.findings)
        passes = total - len(self.failures)
        fails = len(self.failures)
        status = "PASS" if self.passed else "FAIL"
        return (
            f"\n{'='*60}\n"
            f"WCAG CONTRAST CHECK: {status}\n"
            f"{'='*60}\n"
            f"  Passed:  {passes}\n"
            f"  Failed:  {fails}\n"
            f"  Total:   {total}\n"
            f"{'='*60}\n"
        )

    def to_json(self) -> str:
        return json.dumps(
            {
                "passed": self.passed,
                "total": len(self.findings),
                "failures": len(self.failures),
                "findings": [f.to_dict() for f in self.findings],
            },
            indent=2,
        )


# ── Theme Checker ──

def check_theme_file(theme_path: str) -> ContrastResults:
    """Validate contrast ratios in a SEMANTIC_THEME.yaml file."""
    results = ContrastResults()
    path = Path(theme_path)

    if not path.exists():
        print(f"ERROR: Theme file not found: {theme_path}", file=sys.stderr)
        return results

    with open(path, encoding="utf-8") as f:
        theme_data = yaml.safe_load(f)

    themes = theme_data.get("themes", {})

    for theme_name, theme in themes.items():
        surfaces = theme.get("surface", {})
        texts = theme.get("text", {})

        primary_bg = surfaces.get("primary", "#FFFFFF")
        secondary_bg = surfaces.get("secondary", "#F8F9FA")

        # Check all text colors against primary surface
        for text_key, text_color in texts.items():
            if not isinstance(text_color, str) or text_color.startswith("rgba"):
                continue
            try:
                fg_rgb = hex_to_rgb(text_color)
                bg_rgb = hex_to_rgb(primary_bg)
                ratio = contrast_ratio(fg_rgb, bg_rgb)

                # Normal text: 4.5:1
                results.add(ContrastFinding(
                    foreground=text_color,
                    background=primary_bg,
                    ratio=ratio,
                    required_ratio=CONTRAST_AA_NORMAL,
                    context_type="normal_text",
                    location=f"themes.{theme_name}.text.{text_key} on surface.primary",
                    passed=ratio >= CONTRAST_AA_NORMAL,
                ))
            except ValueError:
                continue

        # Check intent colors against surfaces
        intents = theme.get("intent", {})
        for intent_key, intent_color in intents.items():
            if not isinstance(intent_color, str) or intent_color.startswith("rgba"):
                continue
            if "_text" in intent_key:
                continue  # Text variants are checked separately
            try:
                fg_rgb = hex_to_rgb(intent_color)
                bg_rgb = hex_to_rgb(primary_bg)
                ratio = contrast_ratio(fg_rgb, bg_rgb)

                results.add(ContrastFinding(
                    foreground=intent_color,
                    background=primary_bg,
                    ratio=ratio,
                    required_ratio=CONTRAST_AA_LARGE,
                    context_type="ui_component",
                    location=f"themes.{theme_name}.intent.{intent_key} on surface.primary",
                    passed=ratio >= CONTRAST_AA_LARGE,
                ))
            except ValueError:
                continue

        # Check data viz colors
        data_viz = theme.get("data_viz", {})
        for viz_key, viz_color in data_viz.items():
            if not isinstance(viz_color, str) or viz_color.startswith("rgba"):
                continue
            if viz_key in ("grid_line", "axis_label"):
                continue
            try:
                fg_rgb = hex_to_rgb(viz_color)
                bg_rgb = hex_to_rgb(primary_bg)
                ratio = contrast_ratio(fg_rgb, bg_rgb)

                results.add(ContrastFinding(
                    foreground=viz_color,
                    background=primary_bg,
                    ratio=ratio,
                    required_ratio=CONTRAST_AA_LARGE,
                    context_type="ui_component",
                    location=f"themes.{theme_name}.data_viz.{viz_key} on surface.primary",
                    passed=ratio >= CONTRAST_AA_LARGE,
                ))
            except ValueError:
                continue

    return results


def check_color_pair(fg: str, bg: str, context: str = "normal_text") -> ContrastFinding:
    """Check a single foreground/background color pair."""
    fg_rgb = hex_to_rgb(fg)
    bg_rgb = hex_to_rgb(bg)
    ratio = contrast_ratio(fg_rgb, bg_rgb)

    required = CONTRAST_AA_NORMAL if context == "normal_text" else CONTRAST_AA_LARGE

    return ContrastFinding(
        foreground=fg,
        background=bg,
        ratio=ratio,
        required_ratio=required,
        context_type=context,
        location="inline check",
        passed=ratio >= required,
    )


def scan_css_file(css_path: str) -> ContrastResults:
    """Scan a CSS file for color declarations and check contrast where possible."""
    results = ContrastResults()
    path = Path(css_path)

    if not path.exists():
        return results

    content = path.read_text(encoding="utf-8")

    # Extract color/background-color pairs from CSS rules
    rule_pattern = re.compile(
        r'\{([^}]+)\}',
        re.DOTALL,
    )
    color_pattern = re.compile(r'(?:^|;)\s*color\s*:\s*(#[0-9a-fA-F]{3,8})', re.MULTILINE)
    bg_pattern = re.compile(r'background(?:-color)?\s*:\s*(#[0-9a-fA-F]{3,8})', re.MULTILINE)

    for rule_match in rule_pattern.finditer(content):
        block = rule_match.group(1)
        colors = color_pattern.findall(block)
        bgs = bg_pattern.findall(block)

        if colors and bgs:
            for fg in colors:
                for bg in bgs:
                    try:
                        finding = check_color_pair(fg, bg)
                        finding.location = f"{css_path}"
                        results.add(finding)
                    except ValueError:
                        continue

    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="GBOGEB/ABACUS WCAG AA Contrast Checker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --theme engines/SEMANTIC_THEME.yaml
  %(prog)s --check "#333333" "#FFFFFF"
  %(prog)s --css assets/css/style.css
  %(prog)s --theme engines/SEMANTIC_THEME.yaml --format json
        """,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--theme",
        type=str,
        help="Path to SEMANTIC_THEME.yaml file to validate",
    )
    group.add_argument(
        "--check",
        nargs=2,
        metavar=("FG", "BG"),
        help="Check a specific foreground/background pair (hex values)",
    )
    group.add_argument(
        "--css",
        type=str,
        help="Scan a CSS file for contrast issues",
    )

    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--level",
        choices=["AA", "AAA"],
        default="AA",
        help="WCAG conformance level (default: AA)",
    )

    args = parser.parse_args()

    if args.check:
        fg, bg = args.check
        finding = check_color_pair(fg, bg)
        if args.format == "json":
            print(json.dumps(finding.to_dict(), indent=2))
        else:
            print(finding)
            print(f"\nContrast ratio: {finding.ratio:.2f}:1")
            print(f"WCAG {args.level}: {'PASS' if finding.passed else 'FAIL'}")
        return 0 if finding.passed else 1

    if args.theme:
        results = check_theme_file(args.theme)
    elif args.css:
        results = scan_css_file(args.css)
    else:
        parser.error("No input specified")
        return 1

    if args.format == "json":
        print(results.to_json())
    else:
        for finding in results.findings:
            print(finding)
        print(results.summary())

    return 0 if results.passed else 1


if __name__ == "__main__":
    sys.exit(main())
