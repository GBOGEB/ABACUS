#!/usr/bin/env python3
"""B0 report-only census for test suites excluded from the canonical pytest lane."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOTS = (ROOT / "DMAIC_V3" / "tests", ROOT / "integration")


def discover_tests(roots: list[Path]) -> list[Path]:
    tests: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        if root.name == "integration":
            tests.update(root.glob("*/tests/test_*.py"))
        else:
            tests.update(root.glob("test_*.py"))
    return sorted(path.resolve() for path in tests if path.is_file())


def run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def junit_counts(path: Path) -> dict[str, int]:
    counts = {"pass": 0, "fail": 0, "error": 0, "skip": 0}
    if not path.exists():
        return counts
    root = ET.parse(path).getroot()
    for case in root.iter("testcase"):
        if case.find("error") is not None:
            counts["error"] += 1
        elif case.find("failure") is not None:
            counts["fail"] += 1
        elif case.find("skipped") is not None:
            counts["skip"] += 1
        else:
            counts["pass"] += 1
    return counts


def _estimated_candidates(test_file: Path) -> list[str]:
    stem = test_file.stem.removeprefix("test_")
    candidates: list[str] = []
    for path in ROOT.rglob(f"{stem}.py"):
        if path.resolve() == test_file:
            continue
        rel = path.relative_to(ROOT).as_posix()
        if "/tests/" in f"/{rel}" or rel.startswith("tests/"):
            continue
        candidates.append(rel)
    return sorted(set(candidates))


def _context_mapping(coverage_json: Path, test_files: list[Path]) -> dict[str, list[str]]:
    result = {path.relative_to(ROOT).as_posix(): [] for path in test_files}
    if not coverage_json.exists():
        return result
    data = json.loads(coverage_json.read_text(encoding="utf-8"))
    for source, payload in data.get("files", {}).items():
        contexts = payload.get("contexts", {})
        flattened = {
            str(context)
            for line_contexts in contexts.values()
            if isinstance(line_contexts, list)
            for context in line_contexts
            if context
        }
        for test_file in test_files:
            rel = test_file.relative_to(ROOT).as_posix()
            stem = test_file.stem
            dotted = rel.removesuffix(".py").replace("/", ".")
            if any(stem in context or dotted in context for context in flattened):
                result[rel].append(source.replace("\\", "/"))
    return {key: sorted(set(value)) for key, value in result.items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--coverage-out", type=Path, required=True)
    parser.add_argument("--junit-dir", type=Path, required=True)
    parser.add_argument("--roots", nargs="*", type=Path)
    args = parser.parse_args(argv)

    roots = [path.resolve() for path in (args.roots or list(DEFAULT_ROOTS))]
    tests = discover_tests(roots)
    args.junit_dir.mkdir(parents=True, exist_ok=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.coverage_out.parent.mkdir(parents=True, exist_ok=True)

    run_command([sys.executable, "-m", "coverage", "erase"])
    rows: list[dict[str, Any]] = []

    for index, test_file in enumerate(tests):
        rel = test_file.relative_to(ROOT).as_posix()
        collect = run_command(
            [
                sys.executable,
                "-m",
                "pytest",
                "-p",
                "scripts.pytest_test_state_plugin",
                "--collect-only",
                "-q",
                rel,
            ]
        )
        row: dict[str, Any] = {
            "path": rel,
            "collection_returncode": collect.returncode,
            "collection_output": collect.stdout[-4000:],
            "report_only": True,
        }
        if collect.returncode != 0:
            row.update(
                {
                    "collection_status": "ERROR",
                    "test_state": "TEST_FAILING",
                    "outcomes": {"pass": 0, "fail": 0, "error": 1, "skip": 0},
                    "measured_source_paths": [],
                    "existing_test_surface_evidence": "UNMEASURED_COLLECTION_ERROR",
                }
            )
            rows.append(row)
            continue

        junit = args.junit_dir / f"{index:03d}-{test_file.stem}.xml"
        run = run_command(
            [
                sys.executable,
                "-m",
                "pytest",
                "-p",
                "scripts.pytest_test_state_plugin",
                "-q",
                "--benchmark-disable",
                "--cov",
                "--cov-append",
                "--cov-report=",
                f"--junitxml={junit}",
                rel,
            ]
        )
        counts = junit_counts(junit)
        if counts["fail"] or counts["error"] or run.returncode not in {0, 5}:
            state = "TEST_FAILING"
        elif counts["pass"]:
            state = "TEST_GREEN"
        elif counts["skip"]:
            state = "TEST_EXISTS_UNCOLLECTED"
        else:
            state = "TEST_EXISTS_UNCOLLECTED"

        row.update(
            {
                "collection_status": "GREEN",
                "run_returncode": run.returncode,
                "run_output": run.stdout[-4000:],
                "outcomes": counts,
                "test_state": state,
            }
        )
        rows.append(row)

    coverage_cmd = run_command(
        [
            sys.executable,
            "-m",
            "coverage",
            "json",
            "--show-contexts",
            "-o",
            str(args.coverage_out),
        ]
    )
    mapping = _context_mapping(args.coverage_out, tests)

    for row in rows:
        measured = mapping.get(row["path"], [])
        row["measured_source_paths"] = measured
        if measured:
            row["existing_test_surface_evidence"] = "DYNAMIC_CONTEXT (MEASURED)"
            row["estimated_source_candidates"] = []
        else:
            row["existing_test_surface_evidence"] = "NAME_MATCH (ESTIMATED)"
            row["estimated_source_candidates"] = _estimated_candidates(ROOT / row["path"])

    report = {
        "schema": "abacus-test-admission-census/1.0.0",
        "exact_sha": os.environ.get("GITHUB_SHA", "WITHHELD"),
        "report_only": True,
        "baseline_test_count_credit": 0,
        "coverage_export_returncode": coverage_cmd.returncode,
        "test_file_count": len(rows),
        "collection_error_count": sum(
            row["collection_status"] == "ERROR" for row in rows
        ),
        "test_failing_file_count": sum(
            row["test_state"] == "TEST_FAILING" for row in rows
        ),
        "rows": rows,
        "authority_transfer": False,
        "formal_credit_delta": 0,
        "engineering_credit_delta": 0,
    }
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))

    # This is deliberately report-only: test failures are measured evidence.
    # Infrastructure failure to emit the report remains fatal.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
