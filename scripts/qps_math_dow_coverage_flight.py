#!/usr/bin/env python3
"""Measure DOW fixture-test yield on one exact source head, without promotion."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TARGET = "runtime/federation/qps_math_wormhole_dow.py"
TOOL_VERSION = "7.16.2"


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def source_head() -> str:
    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    if re.fullmatch(r"[a-f0-9]{40}", sha) is None:
        raise ValueError("missing exact git SHA")
    return sha


def parse_coverage(obj: Any, *, tests: int) -> dict[str, Any]:
    """Fail closed if the requested module is missing or unmeasured."""
    if not isinstance(obj, dict):
        raise ValueError("missing coverage report")
    meta = obj.get("meta", {})
    if not isinstance(meta, dict) or not meta.get("branch_coverage"):
        raise ValueError("coverage branch mode missing")
    if meta.get("version") != TOOL_VERSION:
        raise ValueError("coverage tool version drift")
    files = obj.get("files")
    if not isinstance(files, dict) or len(files) != 1:
        raise ValueError("expected exactly one source module")
    name, details = next(iter(files.items()))
    if name != TARGET:
        raise ValueError("source module scope mismatch")
    values = details.get("summary", {})
    counts = (
        "num_statements", "covered_lines", "num_branches",
        "covered_branches",
    )
    if not isinstance(values, dict) or any(
        type(values.get(k)) is not int or values[k] < 0 for k in counts
    ):
        raise ValueError("invalid coverage numerators or denominators")
    total_lines = values["num_statements"]
    branch_total = values["num_branches"]
    covered_lines = values["covered_lines"]
    covered_branches = values["covered_branches"]
    if (
        tests <= 0 or total_lines <= 0 or branch_total <= 0
        or covered_lines > total_lines or covered_branches > branch_total
    ):
        raise ValueError("ineligible zero or inconsistent measurement")
    return {
        "source": TARGET,
        "tests_executed": tests,
        "lines_covered": covered_lines,
        "lines_eligible": total_lines,
        "branches_covered": covered_branches,
        "branches_eligible": branch_total,
        "combined_percent": round(
            100 * (covered_lines + covered_branches)
            / (total_lines + branch_total), 4
        ),
    }


def run_suite(pattern: str, output: Path) -> dict[str, Any]:
    environment = dict(os.environ)
    environment["COVERAGE_RCFILE"] = os.devnull
    def execute(args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "coverage", *args],
            cwd=ROOT, env=environment, capture_output=True, text=True,
            check=False,
        )
    erased = execute(["erase"])
    if erased.returncode:
        raise RuntimeError("coverage erase failed: " + erased.stderr)
    tested = execute([
        "run", "--branch", "-m", "unittest", "discover",
        "-s", "tests", "-p", pattern, "-v",
    ])
    print(tested.stdout, end="")
    print(tested.stderr, end="", file=sys.stderr)
    if tested.returncode:
        raise RuntimeError("focused unittest suite failed")
    counts = re.findall(r"Ran\s+(\d+)\s+tests?\s+in", tested.stderr)
    if len(counts) != 1:
        raise ValueError("missing or ambiguous executed test denominator")
    report = execute([
        "json", "--include", TARGET,
        "-o", str(output),
    ])
    if report.returncode:
        raise RuntimeError("coverage JSON generation failed: " + report.stdout + report.stderr)
    raw = output.read_bytes()
    result = parse_coverage(json.loads(raw), tests=int(counts[0]))
    return {**result, "coverage_sha256": digest(raw)}


def pulse(out: Path, *, expected_head: str | None) -> dict[str, Any]:
    sha = source_head()
    if expected_head and sha != expected_head:
        raise ValueError("checked-out SHA != expected PR head")
    out.mkdir(parents=True, exist_ok=True)
    baseline = run_suite(
        "test_qps_math_wormhole_dow.py", out / "coverage_baseline.json"
    )
    expanded = run_suite(
        "test_qps_math_wormhole_dow*.py", out / "coverage_expanded.json"
    )
    if any(
        baseline[key] != expanded[key] for key in (
            "source", "lines_eligible", "branches_eligible",
        )
    ):
        raise ValueError("not a source-matched coverage comparison")
    if expanded["tests_executed"] <= baseline["tests_executed"]:
        raise ValueError("test coverage expansion not executed")
    if (
        expanded["lines_covered"] < baseline["lines_covered"]
        or expanded["branches_covered"] < baseline["branches_covered"]
    ):
        raise ValueError("expanded selection lost covered obligations")
    report = {
        "schema": "abacus.qps_dow.coverage_pulse/v1",
        "repo": "GBOGEB/ABACUS",
        "exact_source_sha": sha,
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "github_run_attempt": os.getenv("GITHUB_RUN_ATTEMPT"),
        "github_job": os.getenv("GITHUB_JOB"),
        "tool": {"name": "coverage", "version": TOOL_VERSION},
        "scope": "SAME_HEAD_DOW_MODULE_TEST_SELECTION_ONLY",
        "baseline": baseline,
        "expanded": expanded,
        "additional_tests": (
            expanded["tests_executed"] - baseline["tests_executed"]
        ),
        "additional_covered_lines": (
            expanded["lines_covered"] - baseline["lines_covered"]
        ),
        "additional_covered_branches": (
            expanded["branches_covered"] - baseline["branches_covered"]
        ),
        "combined_delta_percentage_points": round(
            expanded["combined_percent"] - baseline["combined_percent"], 4
        ),
        "native_cross_repository_attested": False,
        "qps_disposition": "DEFER",
        "merge_authorized": False,
        "formal_credit_delta": 0,
    }
    canonical = json.dumps(
        report, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    report["receipt_sha256"] = digest(canonical)
    (out / "coverage_pulse.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--expected-head", default=None)
    args = parser.parse_args()
    report = pulse(args.out, expected_head=args.expected_head)
    print(json.dumps({
        "sha": report["exact_source_sha"],
        "additional_tests": report["additional_tests"],
        "delta_points": report["combined_delta_percentage_points"],
        "qps_disposition": report["qps_disposition"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
