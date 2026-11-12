#!/usr/bin/env python3
"""Compare two pytest JUnit reports: what the CoolProp candidate changes in the suite.

    python tools/coolprop_shadow/suite_diff.py --baseline oracle.xml \
        --candidate next.xml --label "8.0.0 on 3.14" --summary diff.md

Both reports come from the same commit and interpreter, differing only in the
installed CoolProp, so every outcome change is attributable to CoolProp:

    BROKEN    passed (or skipped) under the oracle, fails/errors under the candidate
    FIXED     failed/errored under the oracle, passes under the candidate
    STILL_RED fails under both (pre-existing, not caused by the candidate)
    SKIP_SHIFT skipped under exactly one of the two

Without --baseline (no oracle wheel for this interpreter) every candidate
failure is listed as UNBASELINED. Report-only: exits 0, or 2 if a report is
missing or unreadable.
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

RED = ("failed", "error")


def load(path: Path) -> dict[str, tuple[str, str]]:
    root = ET.parse(path).getroot()
    out: dict[str, tuple[str, str]] = {}
    for case in root.iter("testcase"):
        test_id = f"{case.get('classname', '')}::{case.get('name', '')}"
        outcome, message = "passed", ""
        for child in case:
            tag = child.tag
            if tag in ("failure", "error"):
                outcome = "failed" if tag == "failure" else "error"
                message = (child.get("message") or child.text or "").strip()
                break
            if tag == "skipped":
                outcome = "skipped"
                message = (child.get("message") or "").strip()
        out[test_id] = (outcome, message.splitlines()[0][:220] if message else "")
    return out


def classify(baseline: dict | None, candidate: dict) -> list[dict]:
    rows = []
    for test_id, (outcome, message) in sorted(candidate.items()):
        if baseline is None:
            if outcome in RED:
                rows.append(
                    {"class": "UNBASELINED", "test": test_id, "message": message}
                )
            continue
        before, before_message = baseline.get(test_id, ("absent", ""))
        if outcome in RED and before not in RED:
            rows.append(
                {"class": "BROKEN", "test": test_id, "message": message, "was": before}
            )
        elif before in RED and outcome not in RED:
            rows.append(
                {
                    "class": "FIXED",
                    "test": test_id,
                    "message": before_message,
                    "now": outcome,
                }
            )
        elif before in RED and outcome in RED:
            rows.append({"class": "STILL_RED", "test": test_id, "message": message})
        elif (before == "skipped") != (outcome == "skipped") and before != "absent":
            rows.append(
                {
                    "class": "SKIP_SHIFT",
                    "test": test_id,
                    "message": message or before_message,
                    "was": before,
                    "now": outcome,
                }
            )
    return rows


def summarise(rows: list[dict], label: str, totals: dict) -> str:
    counts = Counter(r["class"] for r in rows)
    lines = [f"### CoolProp candidate test-suite diff: {label}", ""]
    lines.append(" · ".join(f"{k} {v}" for k, v in totals.items()))
    lines += ["", "| Class | Tests |", "|---|---:|"]
    for key in ("BROKEN", "UNBASELINED", "SKIP_SHIFT", "FIXED", "STILL_RED"):
        if counts.get(key):
            lines.append(f"| {key} | {counts[key]} |")
    for key in ("BROKEN", "UNBASELINED", "SKIP_SHIFT", "FIXED"):
        chosen = [r for r in rows if r["class"] == key]
        if not chosen:
            continue
        lines += [
            "",
            f"<details><summary>{key} ({len(chosen)})</summary>",
            "",
            "| Test | First line of the message |",
            "|---|---|",
        ]
        for r in chosen[:150]:
            message = r["message"].replace("|", "\\|")
            lines.append(f"| `{r['test'][:140]}` | {message[:200]} |")
        lines += ["", "</details>"]
    return "\n".join(lines) + "\n"


def totals_of(report: dict) -> dict:
    counts = Counter(outcome for outcome, _ in report.values())
    return {k: counts.get(k, 0) for k in ("passed", "failed", "error", "skipped")}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--label", default="candidate")
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args(argv)
    try:
        candidate = load(args.candidate)
        baseline = load(args.baseline) if args.baseline else None
    except (OSError, ET.ParseError) as exc:
        print(f"cannot read JUnit report: {exc}", file=sys.stderr)
        return 2
    if not candidate:
        print("candidate report holds no test cases", file=sys.stderr)
        return 2
    rows = classify(baseline, candidate)
    text = summarise(rows, args.label, totals_of(candidate))
    if args.summary:
        args.summary.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
