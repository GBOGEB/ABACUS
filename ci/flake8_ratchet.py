#!/usr/bin/env python3
"""Run full-repo Flake8 as a no-regression debt ratchet."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "ci" / "flake8_baseline.json"
REPORT_PATH = ROOT / "flake8-ratchet-report.json"
DIAG_RE = re.compile(r"^.+?\.py:\d+:\d+:\s+([A-Z]\d+)\s+")


def load_baseline() -> dict:
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def run_flake8(max_line_length: int) -> tuple[int, Counter[str], str]:
    command = [
        sys.executable,
        "-m",
        "flake8",
        ".",
        "--max-line-length",
        str(max_line_length),
    ]
    proc = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    output = "\n".join(part for part in (proc.stdout, proc.stderr) if part)
    counts: Counter[str] = Counter()
    for line in output.splitlines():
        match = DIAG_RE.match(line)
        if match:
            counts[match.group(1)] += 1
    return proc.returncode, counts, output


def main() -> int:
    baseline = load_baseline()
    returncode, counts, raw_output = run_flake8(int(baseline["max_line_length"]))
    total = sum(counts.values())
    baseline_counts = Counter({k: int(v) for k, v in baseline["by_code"].items()})
    regressions = {}

    if total > int(baseline["total"]):
        regressions["total"] = {
            "baseline": int(baseline["total"]),
            "current": total,
        }

    for code, current in sorted(counts.items()):
        allowed = baseline_counts.get(code, 0)
        if current > allowed:
            regressions[code] = {"baseline": allowed, "current": current}

    reductions = {
        code: {"baseline": allowed, "current": counts.get(code, 0)}
        for code, allowed in sorted(baseline_counts.items())
        if counts.get(code, 0) < allowed
    }

    execution_error = returncode not in (0, 1)
    report = {
        "schema_version": 1,
        "baseline_source_sha": baseline["source_sha"],
        "flake8_returncode": returncode,
        "execution_error": execution_error,
        "baseline_total": int(baseline["total"]),
        "current_total": total,
        "delta": total - int(baseline["total"]),
        "by_code": dict(sorted(counts.items())),
        "regressions": regressions,
        "reductions": reductions,
        "raw_output_tail": raw_output.splitlines()[-200:],
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(
        f"Flake8 ratchet: current={total} baseline={baseline['total']} "
        f"delta={report['delta']}"
    )
    if reductions:
        print(f"Reductions: {json.dumps(reductions, sort_keys=True)}")
    if execution_error:
        print(f"Flake8 execution error: return code {returncode}", file=sys.stderr)
        return 2
    if regressions:
        print(f"Flake8 regression: {json.dumps(regressions, sort_keys=True)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
