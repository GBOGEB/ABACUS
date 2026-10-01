#!/usr/bin/env python3
"""Build an exact-head post-B0 coverage union and DAB pressure census.

This tool unions *executed line and branch evidence* from multiple coverage.py
JSON context reports produced from the same repository SHA. It never adds
percentages together. The merged payload is then passed through the canonical
DAB coverage census so MIP ranks the remaining measured pressure after latent
B0 test evidence has been consumed.
"""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

from scripts import coverage_dab_census as dab


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _branch_tuple(value: Any) -> tuple[int, int] | None:
    if (
        isinstance(value, list)
        and len(value) == 2
        and all(type(item) is int for item in value)
    ):
        return value[0], value[1]
    return None


def _merge_context_maps(payloads: list[dict[str, Any]]) -> dict[str, list[str]]:
    merged: dict[str, set[str]] = defaultdict(set)
    for payload in payloads:
        contexts = payload.get("contexts", {})
        if not isinstance(contexts, dict):
            continue
        for line, values in contexts.items():
            if not isinstance(values, list):
                continue
            merged[str(line)].update(str(value) for value in values if value)
    return {line: sorted(values) for line, values in sorted(merged.items())}


def merge_coverage_payloads(
    named_payloads: list[tuple[str, dict[str, Any]]],
) -> dict[str, Any]:
    """Union measured coverage evidence from same-code execution surfaces."""

    if not named_payloads:
        raise ValueError("at least one coverage payload is required")

    all_paths: set[str] = set()
    for _, payload in named_payloads:
        files = payload.get("files", {})
        if not isinstance(files, dict):
            raise ValueError("coverage payload files must be an object")
        all_paths.update(str(path) for path in files)

    merged_files: dict[str, dict[str, Any]] = {}
    surface_stats: dict[str, dict[str, Any]] = {}

    total_statements = 0
    total_covered_lines = 0
    total_branches = 0
    total_covered_branches = 0

    for path in sorted(all_paths):
        statements: set[int] = set()
        executed_lines: set[int] = set()
        excluded_lines: set[int] = set()
        all_branches: set[tuple[int, int]] = set()
        executed_branches: set[tuple[int, int]] = set()
        file_payloads: list[dict[str, Any]] = []
        per_surface: dict[str, Any] = {}

        for label, payload in named_payloads:
            data = payload.get("files", {}).get(path)
            if not isinstance(data, dict):
                per_surface[label] = {
                    "present": False,
                    "covered_lines": 0,
                    "contexts": 0,
                }
                continue

            file_payloads.append(data)
            executed = {
                int(value)
                for value in data.get("executed_lines", [])
                if type(value) is int
            }
            missing = {
                int(value)
                for value in data.get("missing_lines", [])
                if type(value) is int
            }
            excluded = {
                int(value)
                for value in data.get("excluded_lines", [])
                if type(value) is int
            }
            statements.update(executed)
            statements.update(missing)
            executed_lines.update(executed)
            excluded_lines.update(excluded)

            surface_branches: set[tuple[int, int]] = set()
            surface_executed_branches: set[tuple[int, int]] = set()
            for raw in data.get("executed_branches", []):
                branch = _branch_tuple(raw)
                if branch is not None:
                    surface_branches.add(branch)
                    surface_executed_branches.add(branch)
            for raw in data.get("missing_branches", []):
                branch = _branch_tuple(raw)
                if branch is not None:
                    surface_branches.add(branch)
            all_branches.update(surface_branches)
            executed_branches.update(surface_executed_branches)

            per_surface[label] = {
                "present": True,
                "covered_lines": len(executed),
                "contexts": len(dab.measured_contexts(data)),
            }

        missing_lines = sorted(statements - executed_lines)
        missing_branches = sorted(all_branches - executed_branches)
        line_count = len(statements)
        branch_count = len(all_branches)
        covered_line_count = len(executed_lines)
        covered_branch_count = len(executed_branches)
        opportunity_count = line_count + branch_count
        covered_opportunities = covered_line_count + covered_branch_count
        percent = (
            100.0 * covered_opportunities / opportunity_count
            if opportunity_count
            else 100.0
        )

        merged_files[path] = {
            "executed_lines": sorted(executed_lines),
            "missing_lines": missing_lines,
            "excluded_lines": sorted(excluded_lines),
            "contexts": _merge_context_maps(file_payloads),
            "executed_branches": [list(value) for value in sorted(executed_branches)],
            "missing_branches": [list(value) for value in missing_branches],
            "summary": {
                "covered_lines": covered_line_count,
                "num_statements": line_count,
                "percent_covered": percent,
                "missing_lines": len(missing_lines),
                "excluded_lines": len(excluded_lines),
                "num_branches": branch_count,
                "covered_branches": covered_branch_count,
                "missing_branches": len(missing_branches),
            },
        }
        surface_stats[path] = per_surface
        total_statements += line_count
        total_covered_lines += covered_line_count
        total_branches += branch_count
        total_covered_branches += covered_branch_count

    total_opportunities = total_statements + total_branches
    total_covered = total_covered_lines + total_covered_branches
    total_percent = (
        100.0 * total_covered / total_opportunities
        if total_opportunities
        else 100.0
    )

    return {
        "meta": {
            "branch_coverage": any(
                bool(payload.get("meta", {}).get("branch_coverage", False))
                for _, payload in named_payloads
            ),
            "dynamic_context": "test_function",
            "union_method": "executed-line-and-branch-set-union",
            "surfaces": [label for label, _ in named_payloads],
        },
        "totals": {
            "num_statements": total_statements,
            "covered_lines": total_covered_lines,
            "missing_lines": total_statements - total_covered_lines,
            "num_branches": total_branches,
            "covered_branches": total_covered_branches,
            "missing_branches": total_branches - total_covered_branches,
            "percent_covered": total_percent,
        },
        "files": merged_files,
        "_surface_stats": surface_stats,
    }


def build_post_b0_census(
    named_payloads: list[tuple[str, dict[str, Any]]],
    *,
    exact_sha: str,
    criticality: dict[str, Any] | None = None,
    matrix_baseline: dict[str, Any] | None = None,
    test_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    merged = merge_coverage_payloads(named_payloads)
    surface_stats = merged.pop("_surface_stats")
    census = dab.build_census(
        merged,
        criticality=criticality,
        matrix_baseline=matrix_baseline,
        test_evidence=test_evidence,
        exact_sha=exact_sha,
    )
    census["schema"] = "abacus-post-b0-coverage-dab/1.0.0"
    census["measurement"].update(
        {
            "coverage_union": "EXECUTED_LINE_AND_BRANCH_SET_UNION",
            "surfaces": [label for label, _ in named_payloads],
            "same_sha_required": True,
        }
    )
    for row in census["rows"]:
        row["surface_measurements"] = surface_stats.get(row["path"], {})
        row["post_b0_evidence_class"] = "MEASURED"
    census["authority_transfer"] = False
    census["formal_credit_delta"] = 0
    census["engineering_credit_delta"] = 0
    return census


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--coverage-surface",
        action="append",
        required=True,
        metavar="LABEL=PATH",
        help="Coverage JSON surface. Repeat for canonical and B0.",
    )
    parser.add_argument("--criticality", type=Path)
    parser.add_argument("--matrix-baseline", type=Path)
    parser.add_argument("--test-evidence", type=Path)
    parser.add_argument("--exact-sha", default=os.environ.get("GITHUB_SHA"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    if not args.exact_sha:
        raise SystemExit("--exact-sha or GITHUB_SHA is required")

    named_payloads: list[tuple[str, dict[str, Any]]] = []
    for spec in args.coverage_surface:
        if "=" not in spec:
            raise SystemExit(f"invalid --coverage-surface: {spec!r}")
        label, raw_path = spec.split("=", 1)
        label = label.strip()
        if not label:
            raise SystemExit("coverage surface label cannot be empty")
        named_payloads.append((label, _load_json(Path(raw_path))))

    census = build_post_b0_census(
        named_payloads,
        exact_sha=str(args.exact_sha),
        criticality=_load_json(args.criticality) if args.criticality else {},
        matrix_baseline=(
            _load_json(args.matrix_baseline) if args.matrix_baseline else {}
        ),
        test_evidence=(
            _load_json(args.test_evidence) if args.test_evidence else {}
        ),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(census, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(census, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
