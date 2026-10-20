#!/usr/bin/env python3
"""Read-only, fail-closed native JUnit receipt; never a remote Crew/REX claim."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess

from scripts.ci.ariana_dow_evidence import read_junit

FULL_SHA = re.compile(r"[0-9a-f]{40}\Z")
VALID_OS = frozenset({"ubuntu-24.04", "windows-2022", "macos-14"})
VALID_PY = frozenset({"3.10", "3.11", "3.12"})


def build_receipt(*, expected_head, observed_head, run_id, attempt, os_cell,
                  python_cell, junit_path):
    """Qualify one native test cell, rejecting UNKNOWN/skips/missing evidence."""
    if not isinstance(expected_head, str) or not FULL_SHA.fullmatch(expected_head):
        raise ValueError("full 40-character source head SHA required")
    if observed_head != expected_head:
        raise ValueError("stale or mismatched exact-head checkout")
    if not isinstance(run_id, str) or not run_id.isascii() or not run_id.isdecimal() or int(run_id) < 1:
        raise ValueError("authenticated host-provided numeric run id required")
    if type(attempt) is not int or attempt < 1:
        raise ValueError("positive integer run attempt required")
    if os_cell not in VALID_OS or python_cell not in VALID_PY:
        raise ValueError("unrecognised OS/Python cell")
    result = read_junit(Path(junit_path))
    if result is None:
        raise ValueError("missing native JUnit receipt")
    if result["total"] < 8:
        raise ValueError("unexpectedly reduced test-case population")
    if (result["passed"] != result["total"] or result["failures"] != 0
            or result["errors"] != 0 or result["skipped"] != 0):
        raise ValueError("nonzero JUnit failure/error/skip or incomplete passing population")
    return {
        "schema": "abacus.w3.native_junit_receipt.v1",
        "source_repo": "GBOGEB/ABACUS",
        "head_sha": expected_head,
        "observed_git_head": observed_head,
        "native_run_id": int(run_id),
        "native_run_attempt": attempt,
        "native_os_cell": os_cell,
        "native_python_cell": python_cell,
        "native_numeric_job_id": None,
        "junit": result,
        "qualification": "FOCUSED_TEST_PASS_ONLY",
        "merge_admission": "HOLD",
        "formal_credit_delta": 0,
        "engineering_credit_delta": 0,
        "remote_worker_launch_id": None,
        "accepted_rex": None,
        "security_waiver": False,
        "authority_transfer": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--os-cell", required=True)
    parser.add_argument("--python-cell", required=True)
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    observed = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True, timeout=10
    ).strip()
    receipt = build_receipt(
        expected_head=args.expected_head,
        observed_head=observed,
        run_id=os.environ.get("GITHUB_RUN_ID", ""),
        attempt=int(os.environ.get("GITHUB_RUN_ATTEMPT", "0")),
        os_cell=args.os_cell,
        python_cell=args.python_cell,
        junit_path=args.junit,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "schema": receipt["schema"],
        "head_sha": receipt["head_sha"],
        "native_run_id": receipt["native_run_id"],
        "native_run_attempt": receipt["native_run_attempt"],
        "os": receipt["native_os_cell"],
        "python": receipt["native_python_cell"],
        "passed": receipt["junit"]["passed"],
        "skipped": receipt["junit"]["skipped"],
        "qualification": receipt["qualification"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
