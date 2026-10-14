"""Deterministic secondary labels for canonical BD/LDAB joined observations.

No causal-root promotion, security disposition or merge authority.
"""

from __future__ import annotations

import json

CLASSES = (
    "CONTRACT",
    "GOVERNANCE",
    "CONTENT",
    "FORMAT",
    "SECURITY",
    "COVERAGE",
    "RUNTIME",
    "PRODUCER",
    "INFRA",
    "UNKNOWN",
)

# Only explicit diagnostic codes; do not classify by guessing log text.
CODES = {
    "SUT_H1_CONTRACT": "CONTRACT",
    "STALE_WORKFLOW_INVENTORY": "GOVERNANCE",
    "A10_RESTRICTED_CONTENT": "CONTENT",
    "YAML_LINE_LENGTH": "FORMAT",
    "BANDIT_FINDING": "SECURITY",
    "OSV_ADVISORY": "SECURITY",
    "COVERAGE_DENOMINATOR": "COVERAGE",
    "AUTHENTICATED_RUNTIME_FAILURE": "RUNTIME",
    "OUTPUT_MANIFEST_MISSING": "PRODUCER",
    "RUNNER_UNAVAILABLE": "INFRA",
}


def classify(code: str) -> str:
    """Return a secondary class, preserving unknowns."""
    if not isinstance(code, str):
        raise ValueError("diagnostic code must be text")
    return CODES.get(code, "UNKNOWN")


def annotate_join(report: dict, code_by_root: dict) -> dict:
    """Annotate a canonical join without changing any original root fields."""
    if not isinstance(report, dict):
        raise ValueError("report must be an object")
    if report.get("schema") != "bd.ldab.joined.census.v1":
        raise ValueError("canonical join schema required")
    if (
        report.get("merge_admission") != "HOLD"
        or report.get("authority_transfer") is not False
        or report.get("security_waiver") is not False
    ):
        raise ValueError("admission boundary violated")
    rows = report.get("roots")
    if not isinstance(rows, list) or not isinstance(code_by_root, dict):
        raise ValueError("root rows and diagnostic mapping required")
    ids = [row.get("root_id") for row in rows if isinstance(row, dict)]
    if len(ids) != len(rows) or len(set(ids)) != len(ids):
        raise ValueError("invalid or duplicate canonical root IDs")
    if not all(isinstance(key, str) for key in code_by_root):
        raise ValueError("diagnostic mapping keys must be strings")
    if set(code_by_root) - set(ids):
        raise ValueError("diagnostic mapping refers to absent roots")
    annotations = []
    for root in sorted(ids):
        code = code_by_root.get(root)
        if code is not None and not isinstance(code, str):
            raise ValueError("diagnostic code must be text")
        annotations.append(
            {
                "root_id": root,
                "diagnostic_code": code,
                "secondary_class": classify(code) if code is not None else "UNKNOWN",
                "causal_root_confirmed": None,
            }
        )
    return {
        "schema": "mip.root.taxonomy.annotations.v1",
        "source_schema": report["schema"],
        "annotations": annotations,
        "merge_admission": "HOLD",
        "authority_transfer": False,
        "security_waiver": False,
    }


def canonical_bytes(obj: dict) -> bytes:
    return (
        json.dumps(
            obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        )
        + "\n"
    ).encode()
