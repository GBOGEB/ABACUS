#!/usr/bin/env python3
"""
SLIDE_ID_ENFORCER.py — Deterministic Slide ID Validation Engine
GBOGEB/ABACUS A6 Governance Engine

Ensures all slides have deterministic IDs following the pattern:
  {deck}-{section}-{sequence}

Examples: arch-overview-001, perf-metrics-012, design-layout-003

References: RULE-110, RULE-111, RULE-112 (RENDER_RULES.md)
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# ── Slide ID Pattern ──
SLIDE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9]+-[a-zA-Z0-9]+-[0-9]+$")


@dataclass
class EnforcerFinding:
    file: str
    slide_id: str | None
    valid: bool
    message: str
    line: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "slide_id": self.slide_id,
            "valid": self.valid,
            "message": self.message,
            "line": self.line,
        }

    def __str__(self) -> str:
        status = "VALID" if self.valid else "INVALID"
        loc = self.file
        if self.line:
            loc += f":{self.line}"
        return f"[{status}] {loc} — {self.message}"


@dataclass
class EnforcerResults:
    findings: list[EnforcerFinding] = field(default_factory=list)

    @property
    def violations(self) -> list[EnforcerFinding]:
        return [f for f in self.findings if not f.valid]

    @property
    def passed(self) -> bool:
        return len(self.violations) == 0

    def add(self, finding: EnforcerFinding) -> None:
        self.findings.append(finding)

    @property
    def all_ids(self) -> list[str]:
        return [f.slide_id for f in self.findings if f.slide_id]

    def summary(self) -> str:
        total = len(self.findings)
        valid = total - len(self.violations)
        invalid = len(self.violations)
        status = "PASS" if self.passed else "FAIL"

        # Check for duplicates
        ids = self.all_ids
        dupes = {x for x in ids if ids.count(x) > 1}

        lines = [
            f"\n{'='*60}",
            f"SLIDE ID ENFORCER: {status}",
            f"{'='*60}",
            f"  Valid:      {valid}",
            f"  Invalid:    {invalid}",
            f"  Total:      {total}",
        ]
        if dupes:
            lines.append(f"  Duplicates: {', '.join(sorted(dupes))}")
        lines.append(f"{'='*60}\n")
        return "\n".join(lines)

    def to_json(self) -> str:
        ids = self.all_ids
        dupes = sorted({x for x in ids if ids.count(x) > 1})
        return json.dumps(
            {
                "passed": self.passed,
                "total": len(self.findings),
                "violations": len(self.violations),
                "duplicates": dupes,
                "findings": [f.to_dict() for f in self.findings],
            },
            indent=2,
        )


def validate_slide_id(slide_id: str) -> tuple[bool, str]:
    """Validate a single slide ID against the pattern."""
    if not slide_id:
        return False, "Empty slide_id"
    if not SLIDE_ID_PATTERN.match(slide_id):
        return False, (
            f"slide_id '{slide_id}' does not match pattern "
            "{{deck}}-{{section}}-{{sequence}} (e.g., arch-overview-001)"
        )
    parts = slide_id.split("-")
    if len(parts) < 3:
        return False, f"slide_id '{slide_id}' must have at least 3 segments"
    return True, f"slide_id '{slide_id}' is valid"


def check_markdown_file(filepath: str) -> list[EnforcerFinding]:
    """Check a Markdown file for slide_id in YAML front matter."""
    findings = []
    path = Path(filepath)
    content = path.read_text(encoding="utf-8")

    # Check YAML front matter
    yaml_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if yaml_match:
        try:
            front_matter = yaml.safe_load(yaml_match.group(1))
            if isinstance(front_matter, dict):
                slide_id = front_matter.get("slide_id")
                if slide_id:
                    valid, msg = validate_slide_id(str(slide_id))
                    findings.append(EnforcerFinding(
                        file=filepath,
                        slide_id=str(slide_id),
                        valid=valid,
                        message=msg,
                        line=1,
                    ))
                else:
                    findings.append(EnforcerFinding(
                        file=filepath,
                        slide_id=None,
                        valid=False,
                        message="No slide_id found in YAML front matter (RULE-110)",
                        line=1,
                    ))
        except yaml.YAMLError as e:
            findings.append(EnforcerFinding(
                file=filepath,
                slide_id=None,
                valid=False,
                message=f"Invalid YAML front matter: {e}",
                line=1,
            ))
    else:
        # Only flag slide-like content files
        if "slide" in filepath.lower():
            findings.append(EnforcerFinding(
                file=filepath,
                slide_id=None,
                valid=False,
                message="No YAML front matter found — cannot verify slide_id (RULE-110)",
            ))

    return findings


def check_yaml_file(filepath: str) -> list[EnforcerFinding]:
    """Check a YAML file for slide_id fields."""
    findings = []
    path = Path(filepath)
    content = path.read_text(encoding="utf-8")

    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError:
        return findings

    def search_dict(d: dict, file_path: str) -> None:
        if "slide_id" in d:
            slide_id = str(d["slide_id"])
            valid, msg = validate_slide_id(slide_id)
            findings.append(EnforcerFinding(
                file=file_path,
                slide_id=slide_id,
                valid=valid,
                message=msg,
            ))
        if "slides" in d and isinstance(d["slides"], list):
            for i, slide in enumerate(d["slides"]):
                if isinstance(slide, dict):
                    if "slide_id" in slide:
                        slide_id = str(slide["slide_id"])
                        valid, msg = validate_slide_id(slide_id)
                        findings.append(EnforcerFinding(
                            file=file_path,
                            slide_id=slide_id,
                            valid=valid,
                            message=msg,
                        ))
                    else:
                        findings.append(EnforcerFinding(
                            file=file_path,
                            slide_id=None,
                            valid=False,
                            message=f"Slide at index {i} missing slide_id (RULE-110)",
                        ))

    if isinstance(data, dict):
        search_dict(data, filepath)
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                search_dict(item, filepath)

    return findings


def check_lineage_manifest(manifest_path: str) -> list[EnforcerFinding]:
    """Validate slide_ids in lineage_manifest.json."""
    findings = []
    path = Path(manifest_path)

    if not path.exists():
        return findings

    with open(path, encoding="utf-8") as f:
        manifest = json.load(f)

    lineage = manifest.get("lineage", [])
    for record in lineage:
        slide_id = record.get("slide_id")
        if slide_id:
            valid, msg = validate_slide_id(slide_id)
            findings.append(EnforcerFinding(
                file=manifest_path,
                slide_id=slide_id,
                valid=valid,
                message=msg,
            ))

    return findings


def enforce_directory(directory: str) -> EnforcerResults:
    """Recursively check all relevant files in a directory."""
    results = EnforcerResults()
    root = Path(directory)

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        # Skip hidden dirs and build artifacts
        if any(part.startswith(".") or part in ("_site", "__pycache__", "node_modules")
               for part in path.parts):
            continue

        rel = str(path.relative_to(root))

        if path.suffix == ".md":
            for finding in check_markdown_file(str(path)):
                results.add(finding)
        elif path.suffix in (".yaml", ".yml"):
            for finding in check_yaml_file(str(path)):
                results.add(finding)
        elif path.name == "lineage_manifest.json":
            for finding in check_lineage_manifest(str(path)):
                results.add(finding)

    # Check for duplicate slide_ids
    seen: dict[str, str] = {}
    for finding in results.findings:
        if finding.slide_id and finding.valid:
            if finding.slide_id in seen:
                results.add(EnforcerFinding(
                    file=finding.file,
                    slide_id=finding.slide_id,
                    valid=False,
                    message=(
                        f"Duplicate slide_id '{finding.slide_id}' — "
                        f"also found in {seen[finding.slide_id]} (RULE-111)"
                    ),
                ))
            else:
                seen[finding.slide_id] = finding.file

    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="GBOGEB/ABACUS Slide ID Enforcer — validates deterministic slide identifiers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Pattern: {deck}-{section}-{sequence}
  deck     — alphanumeric deck identifier (e.g., arch, perf, design)
  section  — alphanumeric section name (e.g., overview, metrics)
  sequence — numeric sequence (e.g., 001, 012)

Examples:
  %(prog)s docs/slides/
  %(prog)s --validate "arch-overview-001"
  %(prog)s --manifest _data/lineage_manifest.json
  %(prog)s --format json docs/
        """,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "paths",
        nargs="*",
        default=[],
        help="Files or directories to check",
    )
    group.add_argument(
        "--validate",
        type=str,
        help="Validate a single slide_id string",
    )
    group.add_argument(
        "--manifest",
        type=str,
        help="Validate slide_ids in a lineage manifest file",
    )

    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    args = parser.parse_args()

    if args.validate:
        valid, msg = validate_slide_id(args.validate)
        if args.format == "json":
            print(json.dumps({"slide_id": args.validate, "valid": valid, "message": msg}, indent=2))
        else:
            print(f"{'VALID' if valid else 'INVALID'}: {msg}")
        return 0 if valid else 1

    results = EnforcerResults()

    if args.manifest:
        for finding in check_lineage_manifest(args.manifest):
            results.add(finding)
    else:
        for target in args.paths:
            path = Path(target)
            if path.is_dir():
                dir_results = enforce_directory(str(path))
                results.findings.extend(dir_results.findings)
            elif path.is_file():
                if path.suffix == ".md":
                    for f in check_markdown_file(str(path)):
                        results.add(f)
                elif path.suffix in (".yaml", ".yml"):
                    for f in check_yaml_file(str(path)):
                        results.add(f)
                elif path.name == "lineage_manifest.json":
                    for f in check_lineage_manifest(str(path)):
                        results.add(f)

    if args.format == "json":
        print(results.to_json())
    else:
        for finding in results.findings:
            print(finding)
        print(results.summary())

    return 0 if results.passed else 1


if __name__ == "__main__":
    sys.exit(main())
