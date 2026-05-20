#!/usr/bin/env python3
"""
RENDER_LINTER.py — ESLint-style Linter for Engineering Decks
GBOGEB/ABACUS A6 Governance Engine

Enforces rendering governance rules defined in RENDER_RULES.md.

Rules:
  no_overflow            — Content must not exceed container bounds
  no_low_contrast        — WCAG AA 4.5:1 minimum contrast ratio
  no_orphan_bullets      — Single-item lists are prohibited
  stable_heading_hierarchy — Heading levels must be sequential (no skipping)
  figure_reference_required — All figures must be referenced in text
  speaker_notes_required — All slides must have speaker notes (≥50 chars)
  semantic_card_required — All slides must have a semantic card
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


# ── Severity Levels ──
class Severity(Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


# ── Lint Finding ──
@dataclass
class LintFinding:
    rule: str
    severity: Severity
    file: str
    line: int | None
    message: str
    context: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule,
            "severity": self.severity.value,
            "file": self.file,
            "line": self.line,
            "message": self.message,
            "context": self.context,
        }

    def __str__(self) -> str:
        loc = f"{self.file}"
        if self.line:
            loc += f":{self.line}"
        return f"[{self.severity.value}] {loc} — {self.rule}: {self.message}"


# ── Lint Results ──
@dataclass
class LintResults:
    findings: list[LintFinding] = field(default_factory=list)

    @property
    def errors(self) -> list[LintFinding]:
        return [f for f in self.findings if f.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[LintFinding]:
        return [f for f in self.findings if f.severity == Severity.WARNING]

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0

    def add(self, finding: LintFinding) -> None:
        self.findings.append(finding)

    def summary(self) -> str:
        total = len(self.findings)
        errors = len(self.errors)
        warnings = len(self.warnings)
        infos = total - errors - warnings
        status = "PASS" if self.passed else "FAIL"
        return (
            f"\n{'='*60}\n"
            f"RENDER LINTER RESULTS: {status}\n"
            f"{'='*60}\n"
            f"  Errors:   {errors}\n"
            f"  Warnings: {warnings}\n"
            f"  Info:     {infos}\n"
            f"  Total:    {total}\n"
            f"{'='*60}\n"
        )

    def to_json(self) -> str:
        return json.dumps(
            {
                "passed": self.passed,
                "total": len(self.findings),
                "errors": len(self.errors),
                "warnings": len(self.warnings),
                "findings": [f.to_dict() for f in self.findings],
            },
            indent=2,
        )


# ── Rule Implementations ──

def rule_no_overflow(content: str, filepath: str, results: LintResults) -> None:
    """RULE-010: Detect potential overflow indicators in content."""
    lines = content.split("\n")
    for i, line in enumerate(lines, 1):
        # Check for extremely long lines (potential overflow)
        if len(line) > 200:
            results.add(LintFinding(
                rule="no_overflow",
                severity=Severity.WARNING,
                file=filepath,
                line=i,
                message=f"Line exceeds 200 characters ({len(line)} chars) — potential overflow risk.",
                context=line[:80] + "...",
            ))
        # Check for CSS overflow: hidden (masking overflow)
        if re.search(r"overflow\s*:\s*hidden", line, re.IGNORECASE):
            results.add(LintFinding(
                rule="no_overflow",
                severity=Severity.ERROR,
                file=filepath,
                line=i,
                message="CSS 'overflow: hidden' detected — content must paginate, not truncate (RULE-011).",
                context=line.strip(),
            ))


def rule_no_orphan_bullets(content: str, filepath: str, results: LintResults) -> None:
    """RULE-080: Single-item lists are prohibited."""
    lines = content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # Detect unordered list items
        if re.match(r"^[-*+]\s+", line):
            list_start = i
            count = 0
            while i < len(lines) and re.match(r"^[-*+]\s+", lines[i].strip()):
                count += 1
                i += 1
            if count == 1:
                results.add(LintFinding(
                    rule="no_orphan_bullets",
                    severity=Severity.WARNING,
                    file=filepath,
                    line=list_start + 1,
                    message="Orphan bullet — single-item list detected (RULE-080).",
                    context=lines[list_start].strip(),
                ))
            continue
        # Detect ordered list items
        if re.match(r"^\d+\.\s+", line):
            list_start = i
            count = 0
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i].strip()):
                count += 1
                i += 1
            if count == 1:
                results.add(LintFinding(
                    rule="no_orphan_bullets",
                    severity=Severity.WARNING,
                    file=filepath,
                    line=list_start + 1,
                    message="Orphan numbered item — single-item ordered list detected.",
                    context=lines[list_start].strip(),
                ))
            continue
        i += 1


def rule_stable_heading_hierarchy(content: str, filepath: str, results: LintResults) -> None:
    """RULE-030: Heading levels must be strictly sequential."""
    lines = content.split("\n")
    last_level = 0
    h1_count = 0

    for i, line in enumerate(lines, 1):
        match = re.match(r"^(#{1,6})\s+", line)
        if match:
            level = len(match.group(1))
            if level == 1:
                h1_count += 1
            # Check for skipped levels
            if last_level > 0 and level > last_level + 1:
                results.add(LintFinding(
                    rule="stable_heading_hierarchy",
                    severity=Severity.ERROR,
                    file=filepath,
                    line=i,
                    message=f"Heading level skipped: H{last_level} → H{level} (RULE-030).",
                    context=line.strip(),
                ))
            last_level = level

    # Check for multiple H1s (only for slide-like content)
    if filepath.endswith(".md") and h1_count > 1:
        results.add(LintFinding(
            rule="stable_heading_hierarchy",
            severity=Severity.INFO,
            file=filepath,
            line=None,
            message=f"Multiple H1 headings detected ({h1_count}). Ensure each slide has exactly one H1 (RULE-031).",
        ))


def rule_figure_reference_required(content: str, filepath: str, results: LintResults) -> None:
    """RULE-090/091: Every figure must be referenced and every reference must exist."""
    # Find figure definitions (Markdown image syntax or HTML fig tags)
    fig_defs = set(re.findall(r'fig-id[=:]\s*["\']?(\w+)', content))
    fig_defs.update(re.findall(r'!\[([^\]]*)\]\(', content))

    # Find figure references in text
    fig_refs = set(re.findall(r'(?:Figure|Fig\.?)\s+(\w+)', content, re.IGNORECASE))

    # Figures defined but not referenced
    for fig_id in fig_defs - fig_refs:
        if fig_id:  # skip empty alt texts
            results.add(LintFinding(
                rule="figure_reference_required",
                severity=Severity.WARNING,
                file=filepath,
                line=None,
                message=f"Figure '{fig_id}' is defined but not referenced in text (RULE-091).",
            ))

    # Figures referenced but not defined
    for fig_id in fig_refs - fig_defs:
        if fig_id and not fig_id.isdigit():
            results.add(LintFinding(
                rule="figure_reference_required",
                severity=Severity.ERROR,
                file=filepath,
                line=None,
                message=f"Figure '{fig_id}' is referenced but not defined (RULE-091).",
            ))


def rule_speaker_notes_required(content: str, filepath: str, results: LintResults) -> None:
    """RULE-100: Every slide must have speaker notes ≥50 characters."""
    # Check YAML front matter for speaker_notes
    yaml_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if yaml_match:
        try:
            front_matter = yaml.safe_load(yaml_match.group(1))
            if isinstance(front_matter, dict):
                notes = front_matter.get("speaker_notes", "")
                if not notes or len(str(notes)) < 50:
                    results.add(LintFinding(
                        rule="speaker_notes_required",
                        severity=Severity.WARNING,
                        file=filepath,
                        line=1,
                        message=f"Speaker notes missing or too short ({len(str(notes or ''))} chars, minimum 50) (RULE-100).",
                    ))
                return
        except yaml.YAMLError:
            pass

    # Check for speaker notes HTML comment pattern
    notes_pattern = re.findall(r"<!--\s*speaker[_-]?notes?\s*:?\s*(.*?)-->", content, re.DOTALL | re.IGNORECASE)
    if not notes_pattern:
        # Only flag for slide-like Markdown files
        if filepath.endswith(".md") and "slide" in filepath.lower():
            results.add(LintFinding(
                rule="speaker_notes_required",
                severity=Severity.WARNING,
                file=filepath,
                line=None,
                message="No speaker notes detected (RULE-100).",
            ))


def rule_semantic_card_required(content: str, filepath: str, results: LintResults) -> None:
    """RULE-101: Every slide must include a semantic card."""
    yaml_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if yaml_match:
        try:
            front_matter = yaml.safe_load(yaml_match.group(1))
            if isinstance(front_matter, dict):
                required_fields = ["slide_id", "purpose", "audience"]
                missing = [f for f in required_fields if f not in front_matter]
                if missing:
                    results.add(LintFinding(
                        rule="semantic_card_required",
                        severity=Severity.ERROR,
                        file=filepath,
                        line=1,
                        message=f"Semantic card missing fields: {', '.join(missing)} (RULE-101).",
                    ))
                return
        except yaml.YAMLError:
            pass

    if filepath.endswith(".md") and "slide" in filepath.lower():
        results.add(LintFinding(
            rule="semantic_card_required",
            severity=Severity.ERROR,
            file=filepath,
            line=None,
            message="No semantic card (YAML front matter) detected (RULE-101).",
        ))


def rule_no_low_contrast(content: str, filepath: str, results: LintResults) -> None:
    """RULE-060: Check inline styles for potential low-contrast issues."""
    lines = content.split("\n")
    # Pattern: detect inline color + background combos that might be low contrast
    color_pattern = re.compile(
        r'(?:color|background(?:-color)?)\s*:\s*(#[0-9a-fA-F]{3,8}|rgb\([^)]+\))',
        re.IGNORECASE,
    )
    for i, line in enumerate(lines, 1):
        matches = color_pattern.findall(line)
        if len(matches) >= 2:
            results.add(LintFinding(
                rule="no_low_contrast",
                severity=Severity.INFO,
                file=filepath,
                line=i,
                message="Inline color definitions detected — run WCAG_CONTRAST_CHECKER.py for validation (RULE-060).",
                context=line.strip()[:100],
            ))


# ── Rule Registry ──
RULES = {
    "no_overflow": rule_no_overflow,
    "no_low_contrast": rule_no_low_contrast,
    "no_orphan_bullets": rule_no_orphan_bullets,
    "stable_heading_hierarchy": rule_stable_heading_hierarchy,
    "figure_reference_required": rule_figure_reference_required,
    "speaker_notes_required": rule_speaker_notes_required,
    "semantic_card_required": rule_semantic_card_required,
}

# File extensions to lint
LINTABLE_EXTENSIONS = {".md", ".html", ".htm", ".yaml", ".yml", ".css"}


def lint_file(filepath: str, enabled_rules: list[str] | None = None) -> LintResults:
    """Lint a single file against all enabled rules."""
    results = LintResults()
    path = Path(filepath)

    if not path.exists():
        results.add(LintFinding(
            rule="file_access",
            severity=Severity.ERROR,
            file=filepath,
            line=None,
            message=f"File not found: {filepath}",
        ))
        return results

    if path.suffix not in LINTABLE_EXTENSIONS:
        return results

    try:
        content = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError) as e:
        results.add(LintFinding(
            rule="file_access",
            severity=Severity.ERROR,
            file=filepath,
            line=None,
            message=f"Cannot read file: {e}",
        ))
        return results

    rules_to_run = enabled_rules or list(RULES.keys())

    for rule_name in rules_to_run:
        if rule_name in RULES:
            RULES[rule_name](content, filepath, results)

    return results


def lint_directory(directory: str, enabled_rules: list[str] | None = None) -> LintResults:
    """Recursively lint all files in a directory."""
    results = LintResults()
    root = Path(directory)

    if not root.exists():
        results.add(LintFinding(
            rule="directory_access",
            severity=Severity.ERROR,
            file=directory,
            line=None,
            message=f"Directory not found: {directory}",
        ))
        return results

    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix in LINTABLE_EXTENSIONS:
            # Skip build artifacts and hidden directories
            rel = str(path.relative_to(root))
            if any(part.startswith(".") or part in ("_site", "node_modules", "vendor", "__pycache__")
                   for part in path.parts):
                continue
            file_results = lint_file(str(path), enabled_rules)
            results.findings.extend(file_results.findings)

    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="GBOGEB/ABACUS Render Linter — ESLint-style governance for engineering decks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Rules:
  no_overflow                Content must not exceed container bounds
  no_low_contrast            WCAG AA contrast validation reference
  no_orphan_bullets          Single-item lists prohibited
  stable_heading_hierarchy   Heading levels must be sequential
  figure_reference_required  All figures must be cross-referenced
  speaker_notes_required     Slides must have speaker notes (≥50 chars)
  semantic_card_required     Slides must have semantic card metadata

Examples:
  %(prog)s docs/
  %(prog)s --rules no_overflow,no_orphan_bullets docs/slides/
  %(prog)s --format json content.md
        """,
    )

    parser.add_argument(
        "paths",
        nargs="+",
        help="Files or directories to lint",
    )
    parser.add_argument(
        "--rules",
        type=str,
        default=None,
        help="Comma-separated list of rules to enable (default: all)",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors",
    )

    args = parser.parse_args()

    enabled_rules = args.rules.split(",") if args.rules else None
    all_results = LintResults()

    for target in args.paths:
        path = Path(target)
        if path.is_dir():
            dir_results = lint_directory(str(path), enabled_rules)
            all_results.findings.extend(dir_results.findings)
        elif path.is_file():
            file_results = lint_file(str(path), enabled_rules)
            all_results.findings.extend(file_results.findings)
        else:
            all_results.add(LintFinding(
                rule="path_access",
                severity=Severity.ERROR,
                file=str(path),
                line=None,
                message=f"Path not found: {target}",
            ))

    # Promote warnings to errors in strict mode
    if args.strict:
        for finding in all_results.findings:
            if finding.severity == Severity.WARNING:
                finding.severity = Severity.ERROR

    # Output results
    if args.format == "json":
        print(all_results.to_json())
    else:
        for finding in all_results.findings:
            print(finding)
        print(all_results.summary())

    return 0 if all_results.passed else 1


if __name__ == "__main__":
    sys.exit(main())
