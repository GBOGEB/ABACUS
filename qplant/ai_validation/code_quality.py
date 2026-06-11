"""QPLANT AI-Assisted Code Quality Analyser.

Performs static analysis with intelligent recommendations:
- Cyclomatic complexity analysis
- Documentation coverage checking
- Security vulnerability scanning (basic patterns)
- Performance optimisation hints
- Best practice recommendations
"""

from __future__ import annotations

import ast
import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class QualityIssue:
    """A code quality finding."""
    file: str
    line: int
    severity: str  # info, warning, error, critical
    category: str  # complexity, documentation, security, performance, style
    message: str
    suggestion: str = ""
    confidence: float = 0.8


@dataclass
class FileReport:
    """Quality report for a single file."""
    path: str
    lines: int = 0
    functions: int = 0
    classes: int = 0
    avg_complexity: float = 0.0
    max_complexity: int = 0
    doc_coverage: float = 0.0
    issues: List[QualityIssue] = field(default_factory=list)
    score: float = 10.0  # 0-10 scale


class CodeQualityAnalyser:
    """Analyses Python code for quality issues."""

    # Security patterns to scan for
    SECURITY_PATTERNS = [
        (r"eval\s*\(", "Use of eval() — potential code injection", "critical"),
        (r"exec\s*\(", "Use of exec() — potential code injection", "critical"),
        (r"subprocess\.call.*shell\s*=\s*True", "Shell=True in subprocess — command injection risk", "error"),
        (r"pickle\.loads?\(", "Use of pickle — deserialization vulnerability", "warning"),
        (r"password\s*=\s*['\"]", "Hardcoded password detected", "critical"),
        (r"api_key\s*=\s*['\"]", "Hardcoded API key detected", "critical"),
        (r"secret\s*=\s*['\"]", "Hardcoded secret detected", "error"),
    ]

    # Performance anti-patterns
    PERF_PATTERNS = [
        (r"for\s+.*\s+in\s+range\(len\(", "Use enumerate() instead of range(len())", "info"),
        (r"\.append\(.*\)\s*$", "Consider list comprehension for loop-append patterns", "info"),
        (r"time\.sleep\(", "Blocking sleep — consider async alternatives", "info"),
    ]

    def analyse_file(self, file_path: str) -> FileReport:
        """Analyse a single Python file."""
        path = Path(file_path)
        report = FileReport(path=str(path))

        if not path.exists() or path.suffix != ".py":
            return report

        source = path.read_text()
        lines = source.split("\n")
        report.lines = len(lines)

        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            report.issues.append(QualityIssue(
                file=str(path), line=e.lineno or 0,
                severity="error", category="syntax",
                message=f"Syntax error: {e.msg}",
            ))
            report.score = 0
            return report

        # Analyse AST
        functions, classes = self._count_definitions(tree)
        report.functions = functions
        report.classes = classes

        # Complexity
        complexities = self._analyse_complexity(tree, str(path))
        report.issues.extend(complexities["issues"])
        if complexities["values"]:
            report.avg_complexity = sum(complexities["values"]) / len(complexities["values"])
            report.max_complexity = max(complexities["values"])

        # Documentation coverage
        doc_result = self._check_documentation(tree, str(path))
        report.doc_coverage = doc_result["coverage"]
        report.issues.extend(doc_result["issues"])

        # Security scan
        report.issues.extend(self._security_scan(source, str(path)))

        # Performance patterns
        report.issues.extend(self._performance_scan(source, str(path)))

        # Style checks
        report.issues.extend(self._style_checks(source, str(path)))

        # Calculate score
        report.score = self._calculate_score(report)

        return report

    def analyse_directory(self, dir_path: str, pattern: str = "**/*.py") -> Dict[str, Any]:
        """Analyse all Python files in a directory."""
        reports = []
        for py_file in Path(dir_path).glob(pattern):
            if "__pycache__" in str(py_file):
                continue
            reports.append(self.analyse_file(str(py_file)))

        total_issues = sum(len(r.issues) for r in reports)
        total_lines = sum(r.lines for r in reports)
        avg_score = sum(r.score for r in reports) / len(reports) if reports else 0

        return {
            "summary": {
                "files_analysed": len(reports),
                "total_lines": total_lines,
                "total_issues": total_issues,
                "average_score": round(avg_score, 2),
                "by_severity": self._count_by_severity(reports),
                "by_category": self._count_by_category(reports),
            },
            "files": {
                r.path: {
                    "lines": r.lines,
                    "functions": r.functions,
                    "classes": r.classes,
                    "complexity": round(r.avg_complexity, 2),
                    "doc_coverage": round(r.doc_coverage * 100, 1),
                    "score": round(r.score, 2),
                    "issue_count": len(r.issues),
                    "issues": [
                        {
                            "line": i.line,
                            "severity": i.severity,
                            "category": i.category,
                            "message": i.message,
                            "suggestion": i.suggestion,
                        }
                        for i in r.issues
                    ],
                }
                for r in reports
            },
        }

    def _count_definitions(self, tree: ast.Module) -> Tuple[int, int]:
        """Count function and class definitions."""
        functions = classes = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions += 1
            elif isinstance(node, ast.ClassDef):
                classes += 1
        return functions, classes

    def _analyse_complexity(self, tree: ast.Module, file_path: str) -> Dict[str, Any]:
        """Analyse cyclomatic complexity of functions."""
        values = []
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                complexity = 1
                for child in ast.walk(node):
                    if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                        complexity += 1
                    elif isinstance(child, ast.BoolOp):
                        complexity += len(child.values) - 1

                values.append(complexity)

                if complexity > 15:
                    issues.append(QualityIssue(
                        file=file_path, line=node.lineno,
                        severity="error", category="complexity",
                        message=f"High complexity ({complexity}) in {node.name}",
                        suggestion="Consider breaking into smaller functions",
                    ))
                elif complexity > 10:
                    issues.append(QualityIssue(
                        file=file_path, line=node.lineno,
                        severity="warning", category="complexity",
                        message=f"Moderate complexity ({complexity}) in {node.name}",
                        suggestion="Review for possible simplification",
                    ))

        return {"values": values, "issues": issues}

    def _check_documentation(self, tree: ast.Module, file_path: str) -> Dict[str, Any]:
        """Check documentation coverage."""
        documented = 0
        total = 0
        issues = []

        # Module docstring
        if ast.get_docstring(tree):
            documented += 1
        else:
            issues.append(QualityIssue(
                file=file_path, line=1,
                severity="info", category="documentation",
                message="Missing module-level docstring",
                suggestion="Add a module docstring describing the file's purpose",
            ))
        total += 1

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name.startswith("_") and node.name != "__init__":
                    continue
                total += 1
                if ast.get_docstring(node):
                    documented += 1
                else:
                    issues.append(QualityIssue(
                        file=file_path, line=node.lineno,
                        severity="info", category="documentation",
                        message=f"Missing docstring for {node.name}",
                        suggestion=f"Add docstring to {node.name}",
                    ))

        coverage = documented / total if total > 0 else 1.0
        return {"coverage": coverage, "issues": issues}

    def _security_scan(self, source: str, file_path: str) -> List[QualityIssue]:
        """Scan for security patterns."""
        issues = []
        for pattern, message, severity in self.SECURITY_PATTERNS:
            for i, line in enumerate(source.split("\n"), 1):
                if re.search(pattern, line) and not line.strip().startswith("#"):
                    issues.append(QualityIssue(
                        file=file_path, line=i,
                        severity=severity, category="security",
                        message=message,
                        suggestion="Review and remediate the security concern",
                    ))
        return issues

    def _performance_scan(self, source: str, file_path: str) -> List[QualityIssue]:
        """Scan for performance anti-patterns."""
        issues = []
        for pattern, message, severity in self.PERF_PATTERNS:
            for i, line in enumerate(source.split("\n"), 1):
                if re.search(pattern, line) and not line.strip().startswith("#"):
                    issues.append(QualityIssue(
                        file=file_path, line=i,
                        severity=severity, category="performance",
                        message=message,
                        confidence=0.5,
                    ))
        return issues

    def _style_checks(self, source: str, file_path: str) -> List[QualityIssue]:
        """Basic style checks."""
        issues = []
        for i, line in enumerate(source.split("\n"), 1):
            if len(line) > 120:
                issues.append(QualityIssue(
                    file=file_path, line=i,
                    severity="info", category="style",
                    message=f"Line too long ({len(line)} > 120 chars)",
                    confidence=0.9,
                ))
        return issues

    def _calculate_score(self, report: FileReport) -> float:
        """Calculate quality score (0-10)."""
        score = 10.0
        for issue in report.issues:
            if issue.severity == "critical":
                score -= 2.0
            elif issue.severity == "error":
                score -= 1.0
            elif issue.severity == "warning":
                score -= 0.5
            elif issue.severity == "info":
                score -= 0.1

        # Bonus for good documentation
        if report.doc_coverage > 0.8:
            score += 0.5

        return max(0.0, min(10.0, score))

    def _count_by_severity(self, reports: List[FileReport]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for r in reports:
            for i in r.issues:
                counts[i.severity] = counts.get(i.severity, 0) + 1
        return counts

    def _count_by_category(self, reports: List[FileReport]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for r in reports:
            for i in r.issues:
                counts[i.category] = counts.get(i.category, 0) + 1
        return counts


if __name__ == "__main__":
    analyser = CodeQualityAnalyser()
    result = analyser.analyse_directory("/home/ubuntu/handover_dashboard/src")
    print(json.dumps(result["summary"], indent=2))
    Path("/home/ubuntu/ai_validation/code_quality_report.json").write_text(
        json.dumps(result, indent=2)
    )
