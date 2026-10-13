#!/usr/bin/env python3
"""Partition Bandit JSON into deterministic, disjoint file-owner lanes."""
import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


def partition(report: dict, sha: str) -> dict:
    findings = report.get("results")
    if not isinstance(findings, list):
        raise ValueError("Bandit JSON shall contain a results array")
    lanes = {name: [] for name in ("B2-source", "B3-subprocess", "B4-files-secrets", "B5-tests")}
    seen = set()
    for finding in findings:
        path = finding.get("filename")
        rule = finding.get("test_id")
        line = finding.get("line_number")
        if not isinstance(path, str) or not path or not isinstance(rule, str):
            raise ValueError("Finding missing filename or test_id")
        normalized = path.replace("\\", "/").lstrip("./")
        if normalized.startswith("../") or normalized.startswith("/"):
            raise ValueError("Unsafe report path")
        key = (normalized, rule, line, finding.get("issue_text", ""))
        if key in seen:
            continue
        seen.add(key)
        if "/tests/" in f"/{normalized}" or Path(normalized).name.startswith("test_"):
            lane = "B5-tests"
        elif rule in {"B602", "B603", "B604", "B605", "B606", "B607", "B609"}:
            lane = "B3-subprocess"
        elif rule in {"B102", "B103", "B105", "B106", "B107", "B108", "B110", "B301", "B302", "B303", "B306", "B307", "B308", "B310", "B311", "B312", "B313", "B314", "B315", "B316", "B317", "B318", "B319", "B320", "B321", "B323", "B324", "B325", "B401", "B402", "B403", "B404", "B405", "B406", "B407", "B408", "B409", "B410", "B411", "B412", "B413", "B501", "B502", "B503", "B504", "B505", "B506", "B507", "B508", "B509", "B610", "B611", "B612", "B613", "B614", "B615", "B616", "B617", "B618", "B619", "B620", "B621", "B622", "B623", "B624", "B625", "B626", "B627", "B628", "B629", "B630", "B631", "B632", "B633", "B634", "B635", "B636", "B637", "B638", "B639", "B640", "B641", "B642", "B643", "B644", "B645", "B646", "B647", "B648", "B649", "B650", "B651", "B652", "B653", "B654", "B655", "B656", "B657", "B658", "B659", "B660", "B661", "B662", "B663", "B664", "B665", "B666", "B667", "B668", "B669", "B670", "B671", "B672", "B673", "B674", "B675", "B676", "B677", "B678", "B679", "B680", "B681", "B682", "B683", "B684", "B685", "B686", "B687", "B688", "B689", "B690", "B691", "B692", "B693", "B694", "B695", "B696", "B697", "B698", "B699"}:
            lane = "B4-files-secrets"
        else:
            lane = "B2-source"
        lanes[lane].append({"path": normalized, "rule": rule, "line": line, "severity": finding.get("issue_severity"), "confidence": finding.get("issue_confidence"), "fingerprint": hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()})
    # Exclusive file ownership: move all findings for a shared file to the
    # highest-priority lane, preserving disjoint worker write sets.
    priority = {"B3-subprocess": 0, "B4-files-secrets": 1, "B5-tests": 2, "B2-source": 3}
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
