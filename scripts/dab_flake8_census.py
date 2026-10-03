#!/usr/bin/env python3
"""Emit an exact, non-mutating repository-wide Flake8 census for DAB control."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

TRACKED = ("E999", "F821", "F601", "F811", "F841", "E722", "E731", "E741", "W293")
STAT_RE = re.compile(r"^\s*(\d+)\s+([A-Z]\d{3})\b")
TOTAL_RE = re.compile(r"^\s*(\d+)\s*$")


def parse_statistics(stdout: str) -> tuple[int, dict[str, int]]:
    counts: dict[str, int] = {}
    total: int | None = None
    for line in stdout.splitlines():
        stat = STAT_RE.match(line)
        if stat:
            counts[stat.group(2)] = int(stat.group(1))
            continue
        raw_total = TOTAL_RE.match(line)
        if raw_total:
            total = int(raw_total.group(1))
    if total is None:
        total = sum(counts.values())
    return total, counts


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def run_census(exact_sha: str | None = None) -> tuple[str, dict]:
    cmd = [
        "flake8",
        ".",
        "--count",
        "--exit-zero",
        "--statistics",
        "--max-line-length=120",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    raw = result.stdout
    total, counts = parse_statistics(raw)
    payload = {
        "schema_version": "1.1",
        "exact_sha": exact_sha or git_head(),
        "command": " ".join(cmd),
        "exit_code": result.returncode,
        "total": total,
        "families": {code: counts.get(code, 0) for code in TRACKED},
        "all_families": dict(sorted(counts.items())),
        "governance": {
            "authority_transfer": False,
            "formal_credit_delta": 0,
            "engineering_credit_delta": 0,
            "product_code_mutated": False,
        },
    }
    return raw, payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path, default=Path("reports/dab_flake8_census.json"))
    parser.add_argument("--text-out", type=Path, default=Path("reports/dab_flake8_census.txt"))
    parser.add_argument("--parse-fixture", type=Path)
    parser.add_argument("--exact-sha")
    args = parser.parse_args()

    if args.parse_fixture:
        raw = args.parse_fixture.read_text(encoding="utf-8")
        total, counts = parse_statistics(raw)
        payload = {
            "exact_sha": args.exact_sha or "PARSE_FIXTURE",
            "total": total,
            "families": {code: counts.get(code, 0) for code in TRACKED},
            "all_families": dict(sorted(counts.items())),
        }
    else:
        raw, payload = run_census(args.exact_sha)

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.text_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.text_out.write_text(raw, encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
