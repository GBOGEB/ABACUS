#!/usr/bin/env python3
"""Verify MIP self-index exact-SHA binding and repeatability.

Raw receipts are generated only in a temporary directory.  The durable output is
an intentionally sanitized summary that excludes local paths, remotes, branch
names, dirty-file details, and generated raw receipt payloads.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ROOT_EMITTER = ROOT / "scripts" / "mip_repo_self_index.py"
NESTED_EMITTER = ROOT / "integration" / "codespace_jyperter" / "scripts" / "mip_surface_self_index.py"
NESTED_DIAGNOSTIC = (
    ROOT / "integration" / "codespace_jyperter" / "scripts" / "mip_debug_diagnostic.py"
)


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), *args], text=True, stderr=subprocess.DEVNULL
    ).strip()


def run_emitter(script: Path, output: Path) -> dict[str, Any]:
    subprocess.run(
        [sys.executable, str(script), "--output", str(output)],
        cwd=ROOT,
        check=True,
    )
    return json.loads(output.read_text(encoding="utf-8"))


def normalized(receipt: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(receipt)
    value.pop("generated_at", None)
    if "repo" in value:
        for key in ("root", "remote", "branch", "dirty_summary"):
            value["repo"].pop(key, None)
    if "surface" in value:
        for key in ("parent_repo_root", "parent_remote", "parent_branch", "dirty_summary"):
            value["surface"].pop(key, None)
    return value


def digest(value: dict[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def status_map(receipt: dict[str, Any]) -> dict[str, str]:
    return {
        lane: str(details.get("status", "unknown")).upper()
        for lane, details in receipt.get("assessments", {}).items()
    }


def verify_pair(
    emitter: Path,
    first_path: Path,
    second_path: Path,
    actual_sha: str,
    sha_container: str,
    sha_key: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    first = run_emitter(emitter, first_path)
    second = run_emitter(emitter, second_path)

    first_sha = first.get(sha_container, {}).get(sha_key)
    second_sha = second.get(sha_container, {}).get(sha_key)
    if first_sha != actual_sha or second_sha != actual_sha:
        raise SystemExit(
            f"self-index SHA mismatch: runtime={actual_sha} first={first_sha} second={second_sha}"
        )

    n1 = normalized(first)
    n2 = normalized(second)
    if n1 != n2:
        raise SystemExit("normalized self-index output is not repeatable across two invocations")
    return first, n1


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify exact-SHA MIP self-index evidence.")
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()

    actual_sha = git("rev-parse", "HEAD")
    expected_sha = os.environ.get("EXPECTED_SHA", actual_sha).strip()
    if expected_sha != actual_sha:
        raise SystemExit(f"checkout SHA mismatch: expected={expected_sha} actual={actual_sha}")

    with tempfile.TemporaryDirectory(prefix="mip-n2-") as temp:
        tmp = Path(temp)
        root_receipt, root_norm = verify_pair(
            ROOT_EMITTER,
            tmp / "root-1.json",
            tmp / "root-2.json",
            actual_sha,
            "repo",
            "sha",
        )

        summary: dict[str, Any] = {
            "schema_version": "0.1",
            "program": "MIP",
            "verification": "PASS",
            "repository": os.environ.get("GITHUB_REPOSITORY", ROOT.name),
            "head_sha": actual_sha,
            "root_self_index": {
                "runs": 2,
                "normalized_equal": True,
                "digest_sha256": digest(root_norm),
                "file_count": root_receipt.get("census", {}).get("file_count"),
                "assessments": status_map(root_receipt),
            },
            "raw_receipt_retention": "transient_runner_only",
        }

        if NESTED_EMITTER.exists():
            nested_receipt, nested_norm = verify_pair(
                NESTED_EMITTER,
                tmp / "nested-1.json",
                tmp / "nested-2.json",
                actual_sha,
                "surface",
                "parent_sha",
            )
            nested_assessments = status_map(nested_receipt)
            summary["nested_surface"] = {
                "path": "integration/codespace_jyperter",
                "runs": 2,
                "normalized_equal": True,
                "digest_sha256": digest(nested_norm),
                "file_count": nested_receipt.get("census", {}).get("file_count"),
                "assessments": nested_assessments,
            }

            if NESTED_DIAGNOSTIC.exists():
                diagnostic = run_emitter(
                    NESTED_DIAGNOSTIC,
                    tmp / "nested-debug-diagnostic.json",
                )
                if diagnostic.get("parent_sha") != actual_sha:
                    raise SystemExit(
                        "nested diagnostic SHA mismatch: "
                        f"runtime={actual_sha} diagnostic={diagnostic.get('parent_sha')}"
                    )
                if diagnostic.get("verification") != "PASS":
                    failed = ", ".join(diagnostic.get("failed_checks", [])) or "unknown"
                    raise SystemExit(f"nested diagnostic failed: {failed}")
                if nested_assessments.get("repo_self_assess_debug_ldab") != "GREEN":
                    raise SystemExit(
                        "nested diagnostic exists and passes but debug/LDAB assessment is not GREEN"
                    )
                summary["nested_diagnostic"] = {
                    "diagnostic": diagnostic.get("diagnostic"),
                    "verification": diagnostic.get("verification"),
                    "parent_sha": diagnostic.get("parent_sha"),
                    "source_contract": diagnostic.get("source_contract"),
                    "source_contract_sha256": diagnostic.get("source_contract_sha256"),
                    "passed_checks": sorted(
                        name
                        for name, passed in diagnostic.get("checks", {}).items()
                        if passed
                    ),
                    "raw_receipt_retention": diagnostic.get("raw_receipt_retention"),
                }

    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
