#!/usr/bin/env python3
"""Partition Bandit JSON into deterministic, disjoint file-owner lanes."""
import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


def partition(report: dict, sha: str) -> dict:
    if not isinstance(report, dict):
        raise ValueError("Bandit JSON shall be an object")
    findings = report.get("results")
    if not isinstance(findings, list):
        raise ValueError("Bandit JSON shall contain a results array")
    lanes = {name: [] for name in ("B2-source", "B3-subprocess", "B4-files-secrets", "B5-tests")}
    seen = set()
    for finding in findings:
        if not isinstance(finding, dict):
            raise ValueError("Bandit finding shall be an object")
        path = finding.get("filename")
        rule = finding.get("test_id")
        line = finding.get("line_number")
        if not isinstance(path, str) or not path or not isinstance(rule, str) or not rule:
            raise ValueError("Finding missing filename or test_id")
        # Reject absolute and traversal paths before collapsing separators.
        raw = path.replace("\\", "/")
        if (raw.startswith("/") or (len(raw) >= 2 and raw[1] == ":")
                or any(part == ".." for part in raw.split("/"))):
            raise ValueError("Unsafe report path")
        normalized = "/".join(part for part in raw.split("/") if part and part != ".")
        if not normalized:
            raise ValueError("Unsafe empty report path")
        if not isinstance(line, int) or isinstance(line, bool) or line < 1:
            raise ValueError("Finding missing positive integer line_number")
        key = (normalized, rule, line, finding.get("issue_text", ""))
        if key in seen:
            continue
        seen.add(key)
        if "/tests/" in f"/{normalized}" or Path(normalized).name.startswith("test_"):
            lane = "B5-tests"
        elif rule in {"B602", "B603", "B604", "B605", "B606", "B607", "B609"}:
            lane = "B3-subprocess"
        elif rule.startswith(("B1", "B3", "B4", "B5", "B6")):
            lane = "B4-files-secrets"
        else:
            lane = "B2-source"
        lanes[lane].append({"path": normalized, "rule": rule, "line": line, "severity": finding.get("issue_severity"), "confidence": finding.get("issue_confidence"), "fingerprint": hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()})
    # Exclusive file ownership: move all findings for a shared file to the
    # highest-priority lane, preserving disjoint worker write sets.
    priority = {"B5-tests": 0, "B3-subprocess": 1, "B4-files-secrets": 2, "B2-source": 3}
    owner = {}
    for lane, rows in lanes.items():
        for row in rows:
            path = row["path"]
            if path not in owner or priority[lane] < priority[owner[path]]:
                owner[path] = lane
    reassigned = {name: [] for name in lanes}
    for rows in lanes.values():
        for row in rows:
            reassigned[owner[row["path"]]].append(row)
    if sum(len(rows) for rows in reassigned.values()) != len(seen):
        raise ValueError("Disjoint partition invariant failed")
    return {"schema": "bandit.disjoint.census.v1", "exact_sha": sha, "total_unique": len(seen), "lanes": {name: {"findings": len(rows), "files": len({r["path"] for r in rows}), "rules": dict(sorted(Counter(r["rule"] for r in rows).items())), "items": sorted(rows, key=lambda r: (r["path"], r["line"] or 0, r["rule"]))} for name, rows in reassigned.items()}, "authority_transfer": False, "security_disposition": "pending independent review"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--exact-sha", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if len(args.exact_sha) != 40 or any(c not in "0123456789abcdef" for c in args.exact_sha):
        parser.error("--exact-sha shall be a lowercase 40-character SHA")
    result = partition(json.loads(args.report.read_text(encoding="utf-8")), args.exact_sha)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
