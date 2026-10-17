#!/usr/bin/env python3
"""G3A W16 sub-second local/runner gate before dependency installation.

Read-only: checks a new source epoch, canonical workflow classification and
generated inventory. Refuses to infer coverage or source-root closure.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

EPOCH = "G3A_W16_V2_PHASE4_REPAIRED"
SOURCE_BLOBS = {
    "DMAIC_V3/debug_pipeline.py": "730cab72408ac473fb89123d9d76bb7a2edb075e",
    "DMAIC_V3/phases/phase4_improve.py": "18bec722fef537aa74b85295954cf66a002695d0",
    "DMAIC_V3/phases/phase8_todo_management.py": "e9e4edd4c2b5b23a850892efb40b0c256a9ce490",
    "cicd_github_orchestrator.py": "2e0f80b8f476d6f4eab05defb52aae2f77e30c61",
}
EXPECTED_WORKFLOWS = 164


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True, stderr=subprocess.PIPE
    ).strip()


def scan(root: Path, expected_head: str) -> dict:
    errors = []
    if not re.fullmatch(r"[0-9a-f]{40}", expected_head):
        errors.append("EXPECTED_HEAD_INVALID")
    try:
        head = _git(root, "rev-parse", "HEAD")
    except (subprocess.CalledProcessError, OSError):
        head = None
        errors.append("CHECKOUT_NOT_AVAILABLE")
    if head != expected_head:
        errors.append("NOT_EXACT_HEAD")
    blobs = {}
    for path, expected in SOURCE_BLOBS.items():
        source = root / path
        try:
            actual = _git(root, "hash-object", path) if source.is_file() else None
        except (subprocess.CalledProcessError, OSError):
            actual = None
        blobs[path] = {"expected": expected, "actual": actual,
                       "matches": actual == expected}
        if actual != expected:
            errors.append("SOURCE_BLOB_DRIFT:" + path)
    workflows = sorted((root / ".github/workflows").glob("*.y*ml"))
    policy_path = root / "ci/governance/workflow_policy.json"
    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        rules = policy["rules"]
    except (OSError, ValueError, KeyError, TypeError):
        rules = []
        errors.append("WORKFLOW_POLICY_UNREADABLE")
    classified = 0
    for workflow in workflows:
        count = sum(bool(re.search(rule["pattern"], workflow.name)) for rule in rules)
        if count != 1:
            errors.append("WORKFLOW_POLICY_MATCH_COUNT:" + workflow.name + ":" + str(count))
        else:
            classified += 1
    if len(workflows) != EXPECTED_WORKFLOWS:
        errors.append("WORKFLOW_POPULATION_DRIFT")
    if not errors:
        audit = subprocess.run(
            [sys.executable, str(root / "ci/governance/audit_ci_workflows.py"),
             "--check", "--markdown-output",
             str(root / "docs/ci/WORKFLOW_RATIONALIZATION.md")],
            cwd=str(root), capture_output=True, text=True, check=False,
        )
        if audit.returncode:
            errors.append("GENERATED_WORKFLOW_INVENTORY_STALE_OR_INVALID")
    return {
        "schema": "code-purple.g3a.w16.preflight.v1",
        "status": "PASS" if not errors else "HOLD",
        "source_epoch": EPOCH, "expected_head": expected_head,
        "checkout_head": head, "source_blobs": blobs,
        "workflows": len(workflows), "classified": classified,
        "errors": errors, "native_coverage": None, "queue_seconds": None,
        "formal_root_closure": 0, "merge_admission": "HOLD",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    result = scan(root, args.expected_head)
    if args.out:
        dest = args.out if args.out.is_absolute() else root / args.out
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print("G3A_W16_PREFLIGHT=" + result["status"] +
          " source_epoch=" + EPOCH +
          " errors=" + ",".join(result["errors"]))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
