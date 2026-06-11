"""QPLANT Documentation Quality Analyser.

Assesses documentation for:
- Completeness (required sections, coverage)
- Clarity (readability, sentence complexity)
- Link integrity (internal/external links)
- Example code validation
- Readability scoring (Flesch-Kincaid approximation)
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class DocIssue:
    """A documentation quality finding."""
    file: str
    line: int
    severity: str  # info, warning, error
    category: str  # completeness, clarity, links, examples, readability
    message: str
    suggestion: str = ""


@dataclass
class DocReport:
    """Documentation quality report for a single file."""
    path: str
    format: str  # markdown, html, restructuredtext
    lines: int = 0
    words: int = 0
    headers: int = 0
    code_blocks: int = 0
    links: int = 0
    images: int = 0
    tables: int = 0
    readability_score: float = 0.0
    completeness_score: float = 0.0
    issues: List[DocIssue] = field(default_factory=list)
    overall_score: float = 0.0


class DocQualityAnalyser:
    """Analyses documentation quality."""

    # Expected sections for engineering docs
    EXPECTED_SECTIONS_MD = [
        "overview", "introduction", "setup", "usage",
        "configuration", "architecture", "api", "testing",
        "deployment", "troubleshooting",
    ]

    def analyse_file(self, file_path: str) -> DocReport:
        """Analyse a single documentation file."""
        path = Path(file_path)
        if not path.exists():
            return DocReport(path=str(path), format="unknown")

        content = path.read_text()
        fmt = self._detect_format(path)
        report = DocReport(path=str(path), format=fmt)

        lines = content.split("\n")
        report.lines = len(lines)
        report.words = len(content.split())

        if fmt == "markdown":
            self._analyse_markdown(content, report)
        elif fmt == "html":
            self._analyse_html(content, report)

        # Readability
        report.readability_score = self._calculate_readability(content)

        # Overall score
        report.overall_score = self._calculate_overall(report)

        return report

    def analyse_directory(self, dir_path: str, patterns: List[str] = None) -> Dict[str, Any]:
        """Analyse all documentation files in a directory."""
        if patterns is None:
            patterns = ["**/*.md", "**/*.html"]

        reports = []
        for pattern in patterns:
            for doc_file in Path(dir_path).glob(pattern):
                if "__pycache__" in str(doc_file) or "node_modules" in str(doc_file):
                    continue
                reports.append(self.analyse_file(str(doc_file)))

        total_words = sum(r.words for r in reports)
        avg_score = sum(r.overall_score for r in reports) / len(reports) if reports else 0

        return {
            "summary": {
                "files_analysed": len(reports),
                "total_words": total_words,
                "total_issues": sum(len(r.issues) for r in reports),
                "average_score": round(avg_score, 2),
                "average_readability": round(
                    sum(r.readability_score for r in reports) / len(reports) if reports else 0, 2
                ),
            },
            "files": {
                r.path: {
                    "format": r.format,
                    "lines": r.lines,
                    "words": r.words,
                    "headers": r.headers,
                    "code_blocks": r.code_blocks,
                    "links": r.links,
                    "readability": round(r.readability_score, 2),
                    "overall_score": round(r.overall_score, 2),
                    "issue_count": len(r.issues),
                    "issues": [
                        {"line": i.line, "severity": i.severity,
                         "category": i.category, "message": i.message}
                        for i in r.issues
                    ],
                }
                for r in reports
            },
        }

    def _detect_format(self, path: Path) -> str:
        """Detect document format."""
        if path.suffix in (".md", ".markdown"):
            return "markdown"
        if path.suffix in (".html", ".htm"):
            return "html"
        if path.suffix in (".rst",):
            return "restructuredtext"
        return "unknown"

    def _analyse_markdown(self, content: str, report: DocReport) -> None:
        """Analyse Markdown-specific elements."""
        lines = content.split("\n")

        # Headers
        headers = [l for l in lines if l.startswith("#")]
        report.headers = len(headers)

        # Code blocks
        report.code_blocks = content.count("```") // 2

        # Links
        links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
        report.links = len(links)

        # Images
        images = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', content)
        report.images = len(images)

        # Tables
        table_lines = [l for l in lines if l.strip().startswith("|") and "|" in l[1:]]
        report.tables = max(0, len(table_lines) // 3)  # Approximate

        # Check completeness
        header_texts = [h.lower().strip("# ") for h in headers]
        found = set()
        for expected in self.EXPECTED_SECTIONS_MD:
            for ht in header_texts:
                if expected in ht:
                    found.add(expected)
                    break
        report.completeness_score = len(found) / len(self.EXPECTED_SECTIONS_MD) if self.EXPECTED_SECTIONS_MD else 1.0

        # Issue detection
        # Empty headers
        for i, line in enumerate(lines, 1):
            if re.match(r'^#+\s*$', line):
                report.issues.append(DocIssue(
                    file=report.path, line=i, severity="warning",
                    category="completeness", message="Empty header",
                    suggestion="Add header text or remove the header",
                ))

        # Very long paragraphs
        paragraph = []
        for i, line in enumerate(lines, 1):
            if line.strip():
                paragraph.append(line)
            elif paragraph:
                text = " ".join(paragraph)
                if len(text.split()) > 100:
                    report.issues.append(DocIssue(
                        file=report.path, line=i - len(paragraph), severity="info",
                        category="clarity", message=f"Long paragraph ({len(text.split())} words)",
                        suggestion="Consider breaking into shorter paragraphs",
                    ))
                paragraph = []

        # Broken link patterns
        for match in re.finditer(r'\[([^\]]+)\]\(\s*\)', content):
            line_num = content[:match.start()].count("\n") + 1
            report.issues.append(DocIssue(
                file=report.path, line=line_num, severity="error",
                category="links", message=f"Empty link target for '{match.group(1)}'",
            ))

        # Missing alt text for images
        for match in re.finditer(r'!\[\]\(', content):
            line_num = content[:match.start()].count("\n") + 1
            report.issues.append(DocIssue(
                file=report.path, line=line_num, severity="warning",
                category="completeness", message="Image missing alt text",
            ))

    def _analyse_html(self, content: str, report: DocReport) -> None:
        """Analyse HTML-specific elements."""
        report.headers = len(re.findall(r'<h[1-6][^>]*>', content))
        report.code_blocks = len(re.findall(r'<(pre|code)[^>]*>', content))
        report.links = len(re.findall(r'<a\s+[^>]*href=', content))
        report.images = len(re.findall(r'<img\s+', content))
        report.tables = len(re.findall(r'<table[^>]*>', content))

        # Check for images without alt
        for match in re.finditer(r'<img\s+(?![^>]*alt=)', content):
            line_num = content[:match.start()].count("\n") + 1
            report.issues.append(DocIssue(
                file=report.path, line=line_num, severity="warning",
                category="completeness", message="Image missing alt attribute",
            ))

        report.completeness_score = min(1.0, report.headers / 5) if report.headers else 0.0

    def _calculate_readability(self, content: str) -> float:
        """Calculate approximate Flesch-Kincaid readability score."""
        # Strip markdown/HTML
        text = re.sub(r'<[^>]+>', '', content)
        text = re.sub(r'[#*`\[\]()!|]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()

        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        words = text.split()

        if not sentences or not words:
            return 0.0

        avg_sentence_length = len(words) / len(sentences)

        # Approximate syllable count
        syllables = sum(self._count_syllables(w) for w in words)
        avg_syllables = syllables / len(words) if words else 0

        # Flesch Reading Ease
        score = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables)
        return max(0, min(100, score))

    def _count_syllables(self, word: str) -> int:
        """Approximate syllable count."""
        word = word.lower().strip(".,!?;:")
        if len(word) <= 3:
            return 1
        count = len(re.findall(r'[aeiouy]+', word))
        if word.endswith("e"):
            count -= 1
        return max(1, count)

    def _calculate_overall(self, report: DocReport) -> float:
        """Calculate overall documentation quality score (0-10)."""
        score = 5.0  # Base

        # Readability bonus (0-2 points)
        if report.readability_score > 60:
            score += 2.0
        elif report.readability_score > 40:
            score += 1.0

        # Completeness bonus (0-2 points)
        score += report.completeness_score * 2.0

        # Structure bonus (0-1 point)
        if report.headers >= 3:
            score += 0.5
        if report.code_blocks >= 1:
            score += 0.5

        # Issue penalties
        for issue in report.issues:
            if issue.severity == "error":
                score -= 1.0
            elif issue.severity == "warning":
                score -= 0.3

        return max(0, min(10, score))


if __name__ == "__main__":
    analyser = DocQualityAnalyser()
    result = analyser.analyse_directory("/home/ubuntu", patterns=["*.md"])
    print(json.dumps(result["summary"], indent=2))
    Path("/home/ubuntu/ai_validation/doc_quality_report.json").write_text(
        json.dumps(result, indent=2)
    )
