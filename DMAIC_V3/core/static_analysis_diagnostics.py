"""Bounded, fail-closed scanner diagnostics for DMAIC deployment receipts.

Diagnostic extraction does not change static-analysis admission decisions.
It preserves file/line/rule identities without embedding the full raw job log.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

FLAKE8_LINE = re.compile(
    r"^(?P<path>.+?):(?P<line>[0-9]+):(?P<column>[0-9]+): "
    r"(?P<rule>[A-Z][0-9]{3,4}) (?P<message>.*)$"
)


def summarize_static_analysis(
    reports: Optional[Dict[str, Any]], *, max_findings: int = 25
) -> Dict[str, Any]:
    """Extract bounded actionable line evidence without granting a green gate."""
    if type(max_findings) is not int or not 1 <= max_findings <= 100:
        raise ValueError("max_findings must be an integer between 1 and 100")
    if not isinstance(reports, dict):
        return {
            "schema": "dmaic.static_analysis_diagnostics.v1",
            "status": "UNKNOWN",
            "cause": "missing scanner result dictionary",
            "findings": [],
            "finding_count": None,
            "truncated": None,
        }

    report = reports.get("flake8")
    if not isinstance(report, dict):
        return {
            "schema": "dmaic.static_analysis_diagnostics.v1",
            "status": "UNKNOWN",
            "cause": "flake8 not executed or result unavailable",
            "findings": [],
            "finding_count": None,
            "truncated": None,
        }

    returncode = report.get("returncode")
    if type(returncode) is not int:
        return {
            "schema": "dmaic.static_analysis_diagnostics.v1",
            "status": "UNKNOWN",
            "cause": "flake8 returncode missing or invalid",
            "findings": [],
            "finding_count": None,
            "truncated": None,
        }

    output = report.get("output")
    findings = []
    count = 0
    if isinstance(output, str):
        for line in output.splitlines():
            match = FLAKE8_LINE.fullmatch(line.strip())
            if match is None:
                continue
            count += 1
            if len(findings) >= max_findings:
                continue
            fields = match.groupdict()
            findings.append(
                {
                    "source_path": fields["path"][:240],
                    "line": int(fields["line"]),
                    "column": int(fields["column"]),
                    "rule": fields["rule"],
                    "message": fields["message"][:200],
                }
            )

    status = "PASS" if returncode == 0 else "FAIL"
    return {
        "schema": "dmaic.static_analysis_diagnostics.v1",
        "status": status,
        "returncode": returncode,
        "cause": (
            "nonzero scanner exit"
            if returncode != 0
            else "scanner exit zero"
        ),
        "findings": findings,
        "finding_count": count if isinstance(output, str) else None,
        "truncated": count > max_findings if isinstance(output, str) else None,
        "finding_detail_complete": isinstance(output, str) and count <= max_findings,
    }
