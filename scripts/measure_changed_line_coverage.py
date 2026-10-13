"""Compute exact-base changed executable-line coverage from coverage.py XML.

A measured zero denominator is reported as N/A, never as 100% coverage.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def measure(xml: Path, base: str, root: Path) -> dict:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    diff = subprocess.check_output(
        ["git", "diff", "--unified=0", f"{base}...HEAD", "--", "*.py"],
        cwd=root, text=True,
    )
    changes: dict[str, set[int]] = {}
    path = None
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            path = line[6:]
        elif line.startswith("@@ ") and path:
            match = re.search(r"\+(\d+)(?:,(\d+))?", line)
            if match:
                start = int(match.group(1))
                count = int(match.group(2) or "1")
                changes.setdefault(path, set()).update(range(start, start + count))
    tree = ET.parse(xml)
    eligible, covered = [], []
    for cls in tree.findall(".//class"):
        filename = cls.get("filename", "")
        candidates = [filename, f"src/{filename}"]
        matched = next((x for x in candidates if x in changes), None)
        if matched is None:
            continue
        for element in cls.findall("./lines/line"):
            number = int(element.get("number", "0"))
            if number in changes[matched]:
                eligible.append((matched, number))
                if int(element.get("hits", "0")) > 0:
                    covered.append((matched, number))
    total = len(eligible)
    return {
        "schema": "changed-line-coverage/1",
        "exact_sha": commit,
        "base_sha": base,
        "eligible_lines": total,
        "covered_lines": len(covered),
        "percent": round(100 * len(covered) / total, 2) if total else None,
        "status": "MEASURED" if total else "NO_ELIGIBLE_CHANGED_LINES",
        "uncovered": [f"{p}:{n}" for p, n in eligible if (p, n) not in set(covered)],
    }


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: measure_changed_line_coverage.py coverage.xml BASE_SHA out.json")
    result = measure(Path(sys.argv[1]), sys.argv[2], Path.cwd())
    output = Path(sys.argv[3])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
