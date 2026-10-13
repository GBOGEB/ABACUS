#!/usr/bin/env python3
"""Compare two same-configuration Bandit reports without hiding regressions."""
import argparse
import json
from collections import Counter
from pathlib import Path


def fingerprint(item):
    return (
        item["filename"].replace("\\", "/").removeprefix("./"),
        item["test_id"],
        item["line_number"],
        item.get("issue_text", ""),
    )


def compare(before, after, *, before_sha, after_sha, before_config, after_config):
    if before_config != after_config:
        raise ValueError("Scan configuration mismatch; delta is not comparable")
    if before_sha == after_sha:
        raise ValueError("Before and after SHA shall differ")
    for report in (before, after):
        if not isinstance(report, dict) or not isinstance(report.get("results"), list):
            raise ValueError("Bandit report missing results")
    a = {fingerprint(item) for item in before["results"]}
    b = {fingerprint(item) for item in after["results"]}
    added = sorted(b - a)
    resolved = sorted(a - b)
    return {
        "schema": "bandit.comparable.delta.v1",
        "before_sha": before_sha,
        "after_sha": after_sha,
        "scan_configuration": before_config,
        "before_unique": len(a),
        "after_unique": len(b),
        "new": len(added),
        "resolved": len(resolved),
        "net_reduction": len(a) - len(b),
        "new_by_rule": dict(sorted(Counter(x[1] for x in added).items())),
        "resolved_by_rule": dict(sorted(Counter(x[1] for x in resolved).items())),
        "introduced": [list(x) for x in added],
        "removed": [list(x) for x in resolved],
        "security_clearance": False,
    }


def main():
    p = argparse.ArgumentParser()
    for name in ("before", "after"):
        p.add_argument("--" + name, type=Path, required=True)
        p.add_argument("--" + name + "-sha", required=True)
        p.add_argument("--" + name + "-config", required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    for sha in (args.before_sha, args.after_sha):
        if len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha):
            p.error("SHA shall be a lowercase 40-character hex digest")
    result = compare(
        json.loads(args.before.read_text(encoding="utf-8")),
        json.loads(args.after.read_text(encoding="utf-8")),
        before_sha=args.before_sha,
        after_sha=args.after_sha,
        before_config=args.before_config,
        after_config=args.after_config,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
