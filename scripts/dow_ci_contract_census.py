#!/usr/bin/env python3
"""Fail-closed source census for Bootstrap Statistics DOW Phase 2/3.

A source-present state is NOT execution, artifact proof, or merge admission.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path, PurePosixPath

SCHEMA = "abacus.dow.bootstrap.phase23.contract.v1"
SOURCES = {
    "phase2": {
        "path": "dow_phase2_statistics.py",
        "invocation": [
            "python", "dow_phase2_statistics.py", "--results-dir", "test_data.csv",
            "--dow-root", "dow_output", "--alpha", "0.05", "--mode", "csv",
        ],
    },
    "phase3": {
        "path": "dow_phase3_reporting.py",
        "invocation": [
            "python", "dow_phase3_reporting.py",
            "--phase2-metadata", "<phase2_metadata_path>",
        ],
    },
}
EXPECTED_OUTPUTS = {
    "phase2": ["dow_output/**/phase2_metadata.json"],
    "phase3": ["phase3_reports/**/*"],
    "upload_patterns": [
        "dow_output/**/*.md", "dow_output/**/*.json", "dow_output/**/*.png",
        "phase3_reports/**/*",
    ],
}


def _source_state(root: Path, relative: str) -> dict:
    """Reject escaped paths and distinguish existence from execution."""
    p = PurePosixPath(relative)
    if p.is_absolute() or ".." in p.parts or not relative.endswith(".py"):
        return {"path": relative, "state": "INVALID_PATH"}
    resolved_root = root.resolve()
    candidate = (resolved_root / relative).resolve()
    if not candidate.is_relative_to(resolved_root):
        return {"path": relative, "state": "INVALID_PATH"}
    if not candidate.is_file():
        return {"path": relative, "state": "MISSING_SOURCE"}
    try:
        ast.parse(candidate.read_text(encoding="utf-8"), filename=relative)
    except (SyntaxError, UnicodeError, OSError):
        return {"path": relative, "state": "UNPARSEABLE_SOURCE"}
    return {"path": relative, "state": "SOURCE_PRESENT_UNVERIFIED"}


def census(root: Path) -> dict:
    """Report workflow expectations without assigning artificial PASS."""
    observed = {
        name: _source_state(root, details["path"])
        for name, details in SOURCES.items()
    }
    failures = {
        name: row["state"]
        for name, row in observed.items()
        if row["state"] != "SOURCE_PRESENT_UNVERIFIED"
    }
    return {
        "schema": SCHEMA,
        "basis": ".github/workflows/ci-cd.yml",
        "required_entrypoints": SOURCES,
        "expected_artifact_locations": EXPECTED_OUTPUTS,
        "observed_sources": observed,
        "source_census_state": (
            "SOURCE_BLOCKED" if failures else "SOURCES_PRESENT_UNVERIFIED"
        ),
        "blocking_sources": failures,
        "phase2_executed": None,
        "phase3_executed": None,
        "metadata_semantics_verified": None,
        "nonempty_artifacts_verified": None,
        "merge_admission": "HOLD",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-sources", action="store_true")
    args = parser.parse_args(argv)
    result = census(args.root)
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    # Source presence is a precondition, not evidence the DOW pipeline passed.
    if (
        args.require_sources
        and result["source_census_state"] != "SOURCES_PRESENT_UNVERIFIED"
    ):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
