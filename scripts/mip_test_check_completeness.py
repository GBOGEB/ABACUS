#!/usr/bin/env python3
"""Emit one exact-head TC0-TC4 test/check completeness census and residual queue."""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
from pathlib import Path
from typing import Any

try:
    from scripts import ci_false_green_lint as false_green
    from scripts import coverage_dab_census as dab
except ModuleNotFoundError:  # direct execution: python scripts/mip_test_check_completeness.py
    import ci_false_green_lint as false_green
    import coverage_dab_census as dab

CATEGORY_ORDER = {
    "INFRA/CHECK": 0,
    "TEST_ADMISSION": 1,
    "NO_TEST": 2,
    "COVERAGE": 3,
    "STATIC_ANALYSIS": 4,
}
CRITICALITY_ORDER = {
    "USER_DIRECTED_HIGH": 0,
    "HIGH": 1,
    "MEDIUM": 2,
    "LOW": 3,
    "WITHHELD": 9,
}


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def git_head(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "WITHHELD"


def contains_pytest_tests(path: Path) -> bool:
    try:
        module = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return False
    for node in module.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            return True
        if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            if any(
                isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                and child.name.startswith("test_")
                for child in node.body
            ):
                return True
    return False


def discover_inventory(root: Path) -> dict[str, Any]:
    files = [path for path in root.rglob("*") if path.is_file() and ".git" not in path.parts]
    workflows = sorted(
        path for path in files
        if path.parent == root / ".github" / "workflows" and path.suffix in {".yml", ".yaml"}
    )
    test_like = sorted(
        path for path in files
        if path.suffix == ".py" and contains_pytest_tests(path)
    )
    canonical = [path for path in test_like if path.is_relative_to(root / "tests")]
    report_only = [
        path for path in test_like
        if path.is_relative_to(root / "DMAIC_V3" / "tests")
        or (
            path.is_relative_to(root / "integration")
            and "/tests/" in f"/{path.relative_to(root).as_posix()}"
        )
    ]
    known = set(canonical) | set(report_only)
    orphan = [path for path in test_like if path not in known]
    test_set = set(test_like)
    source = [
        path for path in files
        if path.suffix == ".py"
        and path not in test_set
        and dab.classify_source(path.relative_to(root).as_posix(), {}) == "ACTIVE_SOURCE"
    ]
    return {
        "file_count": len(files),
        "active_source_python_count": len(source),
        "workflow_count": len(workflows),
        "pytest_test_file_count": len(test_like),
        "canonical_test_file_count": len(canonical),
        "report_only_test_file_count": len(report_only),
        "orphan_test_file_count": len(orphan),
        "orphan_test_files": [path.relative_to(root).as_posix() for path in orphan],
        "workflow_paths": [path.relative_to(root).as_posix() for path in workflows],
    }


def top_level_block(lines: list[str], key: str) -> list[str]:
    pattern = re.compile(rf"^['\"]?{re.escape(key)}['\"]?:\s*(.*)$")
    for index, line in enumerate(lines):
        if not pattern.match(line):
            continue
        block = [line]
        for follower in lines[index + 1 :]:
            if follower and not follower[0].isspace():
                break
            block.append(follower)
        return block
    return []


def workflow_triggers(text: str) -> list[str]:
    block = top_level_block(text.splitlines(), "on")
    if not block:
        return []
    first = block[0].split(":", 1)[1].strip()
    events: set[str] = set()
    if first.startswith("[") and first.endswith("]"):
        events.update(item.strip() for item in first[1:-1].split(",") if item.strip())
    elif first and not first.startswith("{"):
        events.add(first)
    for line in block[1:]:
        match = re.match(r"^\s{2}([A-Za-z0-9_-]+):?", line)
        if match:
            events.add(match.group(1))
    return sorted(events)


def workflow_shape(path: Path, root: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    jobs = top_level_block(text.splitlines(), "jobs")
    job_count = sum(bool(re.match(r"^  [A-Za-z0-9_.-]+:\s*(?:#.*)?$", line)) for line in jobs[1:])
    step_count = sum(bool(re.match(r"^\s{4,}-\s+(?:name|uses|run):", line)) for line in jobs[1:])
    reusable = sum(bool(re.match(r"^\s{4}uses:\s+", line)) for line in jobs[1:])
    triggers = workflow_triggers(text)
    return {
        "path": path.relative_to(root).as_posix(),
        "triggers": triggers,
        "job_count": job_count,
        "static_step_count": step_count,
        "reusable_job_count": reusable,
        "static_executable": bool(job_count and (step_count or reusable)),
        "manual_only": triggers == ["workflow_dispatch"],
    }


def false_green_census(root: Path, workflow_paths: list[str]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    for rel in workflow_paths:
        for raw in false_green.scan_file(root / rel):
            row = dict(raw)
            row["path"] = rel
            findings.append(row)
    violations = [row for row in findings if not row["allowed"]]
    return {
        "finding_count": len(findings),
        "allowed_count": len(findings) - len(violations),
        "unguarded_count": len(violations),
        "findings": findings,
    }


def state_counts(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        key = str(row.get(field, "WITHHELD"))
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def residual(
    category: str,
    key: str,
    reason: str,
    *,
    criticality: str = "WITHHELD",
    magnitude: int = 0,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "category": category,
        "key": key,
        "reason": reason,
        "criticality": criticality,
        "magnitude": magnitude,
        "evidence": evidence or {},
    }


def build_report(
    root: Path,
    exact_sha: str,
    coverage_dab: dict[str, Any],
    test_evidence: dict[str, Any],
    admission: dict[str, Any],
    false_green_report: dict[str, Any],
    static_census: dict[str, Any],
    residual_limit: int = 250,
) -> dict[str, Any]:
    inventory = discover_inventory(root)
    workflow_rows = [workflow_shape(root / rel, root) for rel in inventory["workflow_paths"]]
    tc4 = false_green_report or false_green_census(root, inventory["workflow_paths"])
    unguarded = [
        row for row in tc4.get("findings", [])
        if isinstance(row, dict) and not row.get("allowed", False)
    ]
    coverage_rows = [row for row in coverage_dab.get("rows", []) if isinstance(row, dict)]
    active = [row for row in coverage_rows if row.get("source_class") == "ACTIVE_SOURCE"]
    with_context = [row for row in active if row.get("existing_test_surface")]
    without_context = [row for row in active if not row.get("existing_test_surface")]
    evidence_rows = [row for row in test_evidence.get("rows", []) if isinstance(row, dict)]
    admission_rows = [row for row in admission.get("rows", []) if isinstance(row, dict)]

    queue: list[dict[str, Any]] = []
    for row in workflow_rows:
        if not row["triggers"]:
            queue.append(residual("INFRA/CHECK", row["path"], "workflow has no detected trigger", magnitude=1000))
        if not row["static_executable"]:
            queue.append(residual("INFRA/CHECK", row["path"], "workflow has no executable job/step", magnitude=900))
    mip_row = next((row for row in workflow_rows if row["path"].endswith("mip-coverage-evidence.yml")), None)
    if mip_row and "push" not in mip_row["triggers"]:
        queue.append(
            residual(
                "INFRA/CHECK",
                mip_row["path"],
                "MIP does not execute on main push; post-merge exact-head B0 proof is absent",
                magnitude=1500,
            )
        )
    false_by_path: dict[str, int] = {}
    for finding in unguarded:
        path = str(finding.get("path", "WITHHELD"))
        false_by_path[path] = false_by_path.get(path, 0) + 1
    for path, count in false_by_path.items():
        queue.append(
            residual(
                "INFRA/CHECK", path, f"{count} unguarded false-green construct(s)",
                magnitude=count, evidence={"unguarded_count": count},
            )
        )

    for path in inventory["orphan_test_files"]:
        queue.append(
            residual(
                "TEST_ADMISSION", path,
                "pytest test surface exists outside canonical or governed report-only roots",
                magnitude=1,
            )
        )
    for row in admission_rows:
        state = str(row.get("test_state", "WITHHELD"))
        if state != "TEST_GREEN":
            queue.append(
                residual(
                    "TEST_ADMISSION", str(row.get("path", "WITHHELD")),
                    f"report-only admission state is {state}",
                    magnitude=100 if state == "TEST_FAILING" else 10,
                    evidence={"test_state": state, "collection_status": row.get("collection_status")},
                )
            )

    no_test_keys: set[str] = set()
    for row in without_context:
        missed = int(row.get("missed_statements", 0) or 0)
        if not missed:
            continue
        path = str(row.get("path", "WITHHELD"))
        no_test_keys.add(path)
        queue.append(
            residual(
                "NO_TEST", path, "active source has no measured dynamic test context",
                criticality=str(row.get("criticality", "WITHHELD")), magnitude=missed,
                evidence={"coverage_pct": row.get("coverage_pct"), "disposition": row.get("disposition")},
            )
        )

    totals = coverage_dab.get("full_measurement", {})
    missing_lines = int(totals.get("missing_lines", 0) or 0)
    missing_branches = int(totals.get("missing_branches", 0) or 0)
    if missing_lines or missing_branches:
        queue.append(
            residual(
                "COVERAGE", "<repository>", "repository branch/line coverage gap",
                magnitude=missing_lines + missing_branches,
                evidence={
                    "missing_lines": missing_lines,
                    "missing_branches": missing_branches,
                    "percent_covered": totals.get("percent_covered"),
                    "percent_branches_covered": totals.get("percent_branches_covered"),
                },
            )
        )
    for row in active:
        path = str(row.get("path", "WITHHELD"))
        missed = int(row.get("missed_statements", 0) or 0)
        if path in no_test_keys or not missed:
            continue
        queue.append(
            residual(
                "COVERAGE", path,
                "measured test context exists but statement coverage remains incomplete",
                criticality=str(row.get("criticality", "WITHHELD")), magnitude=missed,
                evidence={"coverage_pct": row.get("coverage_pct")},
            )
        )

    static_total = int(static_census.get("total", 0) or 0)
    if static_total:
        queue.append(
            residual(
                "STATIC_ANALYSIS", "flake8:<repository>", "repository-wide Flake8 debt remains",
                magnitude=static_total,
                evidence={"total": static_total, "families": static_census.get("families", {})},
            )
        )

    queue.sort(
        key=lambda row: (
            CATEGORY_ORDER.get(str(row["category"]), 99),
            CRITICALITY_ORDER.get(str(row["criticality"]), 8),
            -int(row["magnitude"]),
            str(row["key"]),
        )
    )
    for rank, row in enumerate(queue, start=1):
        row["rank"] = rank

    non_green = [row for row in admission_rows if row.get("test_state") != "TEST_GREEN"]
    return {
        "schema": "abacus-mip-test-check-completeness/1.0.0",
        "exact_sha": exact_sha,
        "authority_transfer": False,
        "formal_credit_delta": 0,
        "engineering_credit_delta": 0,
        "tc0_inventory": inventory,
        "tc1_completeness": {
            "canonical_test_outcomes": test_evidence.get("outcomes", {}),
            "canonical_test_states": state_counts(evidence_rows, "test_state"),
            "canonical_ratchet_status": test_evidence.get("ratchet_status", "WITHHELD"),
            "report_only_file_count": admission.get("test_file_count", 0),
            "report_only_states": state_counts(admission_rows, "test_state"),
            "report_only_non_green_count": len(non_green),
            "orphan_test_file_count": inventory["orphan_test_file_count"],
        },
        "tc2_dynamic_context_crosswalk": {
            "active_source_rows": len(active),
            "with_measured_test_context": len(with_context),
            "without_measured_test_context": len(without_context),
            "measurement": coverage_dab.get("measurement", {}),
            "user_directed_high_without_context": [
                row.get("path") for row in without_context
                if row.get("criticality") == "USER_DIRECTED_HIGH"
            ],
        },
        "tc3_workflow_census": {
            "workflow_count": len(workflow_rows),
            "static_executable_count": sum(row["static_executable"] for row in workflow_rows),
            "zero_step_or_non_executable_count": sum(not row["static_executable"] for row in workflow_rows),
            "manual_only_count": sum(row["manual_only"] for row in workflow_rows),
            "rows": workflow_rows,
        },
        "tc4_false_green": {
            "finding_count": tc4.get("finding_count", len(tc4.get("findings", []))),
            "allowed_count": tc4.get("allowed_count", 0),
            "unguarded_count": tc4.get("unguarded_count", len(unguarded)),
            "ratchet_status": tc4.get("ratchet_status", "WITHHELD"),
        },
        "coverage_dab": {
            "schema": coverage_dab.get("schema"),
            "active_source": coverage_dab.get("active_source", {}),
            "full_measurement": coverage_dab.get("full_measurement", {}),
        },
        "static_analysis": {
            "total": static_total,
            "families": static_census.get("families", {}),
        },
        "ranked_residual_count": len(queue),
        "ranked_residual": queue[:residual_limit],
        "ranked_residual_truncated": len(queue) > residual_limit,
    }


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - workflow integration owns CLI
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--coverage-dab", type=Path, required=True)
    parser.add_argument("--test-evidence", type=Path, required=True)
    parser.add_argument("--admission-census", type=Path)
    parser.add_argument("--false-green-census", type=Path)
    parser.add_argument("--static-census", type=Path)
    parser.add_argument("--exact-sha", required=True)
    parser.add_argument("--residual-limit", type=int, default=250)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    root = args.root.resolve()
    actual_sha = git_head(root)
    if actual_sha != args.exact_sha:
        raise SystemExit(f"exact-head mismatch: expected={args.exact_sha} actual={actual_sha}")
    report = build_report(
        root, args.exact_sha, load_json(args.coverage_dab), load_json(args.test_evidence),
        load_json(args.admission_census), load_json(args.false_green_census),
        load_json(args.static_census), args.residual_limit,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
