#!/usr/bin/env python3
"""Build the ABACUS DAB-style coverage census from measured coverage contexts."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


SOURCE_ROOTS = {
    "13_CORE_SYSTEMS",
    "DMAIC_V3",
    "abacus_runtime",
    "core",
    "models",
    "qplant",
    "qplant_presentation_engine",
    "runtime",
    "scripts",
    "src",
    "tools",
    "integration",
    "integration_DOW_KEB_MASTER",
    "local_mcp",
    "qps",
    "renderers",
    "rextools",
    "rich_padding",
}
LEGACY_TOKENS = {"BACKUPS", "11_PREVIOUS_SESSIONS", "ABACUS-v032"}
GENERATED_PARTS = {"build", "dist", "generated", "__pycache__"}
CRITICALITY_ORDER = {
    "USER_DIRECTED_HIGH": 0,
    "HIGH": 1,
    "MEDIUM": 2,
    "LOW": 3,
    "WITHHELD": 9,
}


def normalize_path(value: str) -> str:
    return value.replace("\\", "/").removeprefix("./")


def classify_source(path: str, overrides: dict[str, Any]) -> str:
    norm = normalize_path(path)
    if norm in overrides and "source_class" in overrides[norm]:
        return str(overrides[norm]["source_class"])

    parts = [part for part in norm.split("/") if part]
    if norm.startswith("/tmp/") or "pytest-of-" in norm:
        return "TEST_SUPPORT"
    if "tests" in parts[:-1] or (parts and parts[0] == "tests"):
        return "TEST_SUPPORT"
    if any(part in GENERATED_PARTS for part in parts):
        return "GENERATED"
    if any(token in norm for token in LEGACY_TOKENS) or "_LEGACY_" in norm:
        return "LEGACY_QUARANTINED"
    if parts and parts[0] in SOURCE_ROOTS:
        return "ACTIVE_SOURCE"
    if len(parts) == 1 and norm.endswith(".py"):
        return "ACTIVE_SOURCE"
    return "UNKNOWN"


def measured_contexts(file_data: dict[str, Any]) -> list[str]:
    contexts = file_data.get("contexts", {})
    values: set[str] = set()
    if isinstance(contexts, dict):
        for line_contexts in contexts.values():
            if isinstance(line_contexts, list):
                values.update(
                    str(context)
                    for context in line_contexts
                    if context and str(context).strip()
                )
    return sorted(values)


def _load_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def build_census(
    coverage: dict[str, Any],
    criticality: dict[str, Any] | None = None,
    matrix_baseline: dict[str, Any] | None = None,
    exact_sha: str | None = None,
) -> dict[str, Any]:
    criticality = criticality or {}
    entries = criticality.get("files", criticality)
    if not isinstance(entries, dict):
        entries = {}

    rows: list[dict[str, Any]] = []
    for raw_path, data in sorted(coverage.get("files", {}).items()):
        path = normalize_path(raw_path)
        summary = data.get("summary", {})
        statements = int(summary.get("num_statements", 0) or 0)
        covered = int(summary.get("covered_lines", 0) or 0)
        missed = max(0, statements - covered)
        percent = float(summary.get("percent_covered", 0.0) or 0.0)
        contexts = measured_contexts(data)
        source_class = classify_source(path, entries)
        metadata = entries.get(path, {}) if isinstance(entries.get(path, {}), dict) else {}
        tier = str(metadata.get("criticality", "WITHHELD"))

        if source_class == "ACTIVE_SOURCE" and contexts:
            disposition = "ACTIVE_MEASURED"
            test_state = "TEST_GREEN"
            surface_evidence = "DYNAMIC_CONTEXT (MEASURED)"
        elif source_class == "ACTIVE_SOURCE" and statements and covered == 0:
            disposition = "ADMISSION_PENDING"
            test_state = "NO_TEST"
            surface_evidence = "NONE_MEASURED"
        elif source_class == "ACTIVE_SOURCE":
            disposition = "ACTIVE_MEASURED"
            test_state = "NO_TEST" if not contexts else "TEST_GREEN"
            surface_evidence = "NONE_MEASURED" if not contexts else "DYNAMIC_CONTEXT (MEASURED)"
        elif source_class == "LEGACY_QUARANTINED":
            disposition = "REVIEW_QUARANTINE"
            test_state = "NO_TEST"
            surface_evidence = "NONE_MEASURED"
        else:
            disposition = source_class
            test_state = "NO_TEST"
            surface_evidence = "NONE_MEASURED"

        rows.append(
            {
                "path": path,
                "statements": statements,
                "covered_statements": covered,
                "missed_statements": missed,
                "coverage_pct": round(percent, 4),
                "source_class": source_class,
                "disposition": disposition,
                "test_state": test_state,
                "existing_test_surface": contexts,
                "existing_test_surface_evidence": surface_evidence,
                "criticality": tier,
                "criticality_source": metadata.get("source", "WITHHELD"),
                "skip_dependencies": metadata.get("skip_dependencies", []),
                "warning_dependencies": metadata.get("warning_dependencies", []),
                "evidence_class": "MEASURED",
                "maximum_statement_gain": missed,
                "expected_gain": "WITHHELD",
                "authority_transfer": False,
                "formal_credit_delta": 0,
                "engineering_credit_delta": 0,
            }
        )

    active = [row for row in rows if row["source_class"] == "ACTIVE_SOURCE"]
    active_statements = sum(row["statements"] for row in active)
    active_covered = sum(row["covered_statements"] for row in active)
    active_pct = (
        100.0 * active_covered / active_statements if active_statements else 0.0
    )

    def priority(row: dict[str, Any]) -> tuple[Any, ...]:
        source_rank = 0 if row["source_class"] == "ACTIVE_SOURCE" else 1
        criticality_rank = CRITICALITY_ORDER.get(row["criticality"], 8)
        admission_rank = 0 if row["disposition"] == "ADMISSION_PENDING" else 1
        return (
            source_rank,
            criticality_rank,
            admission_rank,
            -int(row["missed_statements"]),
            row["path"],
        )

    pressure = [
        row["path"]
        for row in sorted(rows, key=priority)
        if row["source_class"] == "ACTIVE_SOURCE" and row["missed_statements"] > 0
    ]

    return {
        "schema": "abacus-coverage-dab/1.0.0",
        "exact_sha": exact_sha or os.environ.get("GITHUB_SHA", "WITHHELD"),
        "measurement": {
            "branch_coverage": bool(coverage.get("meta", {}).get("branch_coverage", False)),
            "dynamic_context": "test_function",
            "test_source_mapping": "DYNAMIC_CONTEXT",
        },
        "active_source": {
            "statements": active_statements,
            "covered_statements": active_covered,
            "missed_statements": active_statements - active_covered,
            "coverage_pct": round(active_pct, 4),
        },
        "full_measurement": coverage.get("totals", {}),
        "legacy_matrix_baseline": matrix_baseline or {},
        "pressure_order": pressure,
        "rows": rows,
        "authority_transfer": False,
        "formal_credit_delta": 0,
        "engineering_credit_delta": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage-json", type=Path, required=True)
    parser.add_argument("--criticality", type=Path)
    parser.add_argument("--matrix-baseline", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--exact-sha")
    args = parser.parse_args(argv)

    coverage = _load_json(args.coverage_json)
    criticality = _load_json(args.criticality)
    matrix_baseline = _load_json(args.matrix_baseline)
    census = build_census(
        coverage,
        criticality=criticality,
        matrix_baseline=matrix_baseline,
        exact_sha=args.exact_sha,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(census, indent=2, sort_keys=True) + "\n")
    print(json.dumps(census, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
