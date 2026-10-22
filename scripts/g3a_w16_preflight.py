#!/usr/bin/env python3
"""G3A W16 sub-second local/runner gate before dependency installation.

Read-only: checks the source epoch pinned in the canonical epoch manifest
(``MIP/statistics/g3a_w16_epoch.json``), the workflow population and its
policy sub-categories, and the generated inventory. Refuses to infer coverage
or source-root closure; drift is repaired with ``scripts/g3a_w16_repin.py``.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

MANIFEST = Path("MIP/statistics/g3a_w16_epoch.json")


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
    try:
        epoch = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
        source_blobs = {path: v["blob"] for path, v in epoch["files"].items()}
        census = epoch["workflows"]
        source_epoch = epoch["source_epoch"]
    except (OSError, ValueError, KeyError, TypeError):
        source_blobs, census, source_epoch = {}, {}, None
        errors.append("EPOCH_MANIFEST_UNREADABLE")
    blobs = {}
    for path, expected in source_blobs.items():
        source = root / path
        try:
            actual = _git(root, "hash-object", path) if source.is_file() else None
        except (subprocess.CalledProcessError, OSError):
            actual = None
        blobs[path] = {
            "expected": expected,
            "actual": actual,
            "matches": actual == expected,
        }
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
    by_cluster: dict[str, int] = {}
    by_lifecycle: dict[str, int] = {}
    for workflow in workflows:
        hits = [rule for rule in rules if re.search(rule["pattern"], workflow.name)]
        if len(hits) != 1:
            errors.append(
                "WORKFLOW_POLICY_MATCH_COUNT:" + workflow.name + ":" + str(len(hits))
            )
        else:
            classified += 1
            cluster, lifecycle = hits[0].get("cluster"), hits[0].get("lifecycle")
            by_cluster[cluster] = by_cluster.get(cluster, 0) + 1
            by_lifecycle[lifecycle] = by_lifecycle.get(lifecycle, 0) + 1
    if len(workflows) != census.get("population"):
        errors.append("WORKFLOW_POPULATION_DRIFT")
    for key, actual in (("by_cluster", by_cluster), ("by_lifecycle", by_lifecycle)):
        if census.get(key) is not None and census[key] != actual:
            errors.append("WORKFLOW_SUBCATEGORY_DRIFT:" + key)
    if not errors:
        audit = subprocess.run(
            [
                sys.executable,
                str(root / "ci/governance/audit_ci_workflows.py"),
                "--check",
                "--markdown-output",
                str(root / "docs/ci/WORKFLOW_RATIONALIZATION.md"),
            ],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
        if audit.returncode:
            errors.append("GENERATED_WORKFLOW_INVENTORY_STALE_OR_INVALID")
    return {
        "schema": "code-purple.g3a.w16.preflight.v1",
        "status": "PASS" if not errors else "HOLD",
        "source_epoch": source_epoch,
        "expected_head": expected_head,
        "checkout_head": head,
        "source_blobs": blobs,
        "workflows": len(workflows),
        "classified": classified,
        "workflow_subcategories": {
            "by_cluster": by_cluster,
            "by_lifecycle": by_lifecycle,
        },
        "errors": errors,
        "native_coverage": None,
        "queue_seconds": None,
        "formal_root_closure": 0,
        "merge_admission": "HOLD",
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
        dest.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(
        "G3A_W16_PREFLIGHT="
        + result["status"]
        + " source_epoch="
        + str(result["source_epoch"])
        + " errors="
        + ",".join(result["errors"])
    )
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
