#!/usr/bin/env python3
"""Run one G-lane test family and guard its collected count.

CODE PURPLE vector G (2026-10-31): these test files lived outside every
main-branch CI job. Each family runs in its own pytest process, so its
rootdir-relative module names cannot collide with ``tests/`` and the repo
``--maxfail=3`` addopt cannot hide later failures.

The guard fails when:
- pytest exits non-zero (failures or collection errors);
- zero tests are collected (a vacuous run is a failure, never a pass);
- fewer than ``--expected-min`` tests are collected;
- any test is xfailed or xpassed (ABACUS runs with ``--max-xfails 0``).

Usage:
    python scripts/ci/family_collect_guard.py --family NAME \
        --expected-min N [--junit PATH] -- PATH [PATH ...] [PYTEST_OPTION ...]
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def pytest_collection_modifyitems(items: list) -> None:
    """Make every xfail strict, including explicitly non-strict markers."""
    for item in items:
        for marker in item.iter_markers(name="xfail"):
            marker.kwargs["strict"] = True


def run_pytest(pytest_args: list[str], junit: Path) -> int:
    junit.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-p",
        "no:cacheprovider",
        "-p",
        "family_collect_guard",
        "-o",
        "addopts=",
        "--strict-markers",
        "--tb=short",
        "-q",
        "-rfE",
        f"--junitxml={junit}",
        *pytest_args,
    ]
    print("+ " + " ".join(cmd), flush=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(Path(__file__).resolve().parent), env.get("PYTHONPATH")))
    )
    return subprocess.call(cmd, env=env)


def tally(junit: Path) -> dict[str, int]:
    counts = {
        "collected": 0,
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "xfailed": 0,
        "xpassed": 0,
    }
    if not junit.exists():
        return counts
    for case in ET.parse(junit).getroot().iter("testcase"):
        counts["collected"] += 1
        failure = case.find("failure")
        error = case.find("error")
        skipped = case.find("skipped")
        if failure is not None:
            message = failure.get("message", "")
            if "XPASS" in message:
                counts["xpassed"] += 1
            else:
                counts["failed"] += 1
        elif error is not None:
            counts["errors"] += 1
        elif skipped is not None:
            if skipped.get("type") == "pytest.xfail":
                counts["xfailed"] += 1
            else:
                counts["skipped"] += 1
        else:
            counts["passed"] += 1
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--family", required=True)
    parser.add_argument("--expected-min", type=int, required=True)
    parser.add_argument("--junit", type=Path)
    parser.add_argument("pytest_args", nargs="+", help="paths and pytest options")
    args = parser.parse_args(argv)
    if args.expected_min < 1:
        parser.error("--expected-min must be at least 1")

    slug = args.family.replace("/", "_")
    junit = args.junit or Path("ci-evidence") / f"g-family-{slug}.xml"
    rc = run_pytest(args.pytest_args, junit)
    counts = tally(junit)

    reasons = []
    if rc != 0:
        reasons.append(f"pytest exit code {rc}")
    if counts["collected"] == 0:
        reasons.append("zero tests collected")
    elif counts["collected"] < args.expected_min:
        reasons.append(
            f"collected {counts['collected']} < EXPECTED_MIN {args.expected_min}"
        )
    if counts["xfailed"] or counts["xpassed"]:
        reasons.append("xfail/xpass present (ABACUS --max-xfails 0)")

    verdict = "FAIL" if reasons else "PASS"
    cells = " | ".join(str(counts[k]) for k in counts)
    rows = [
        f"### G family `{args.family}`: {verdict}",
        "",
        "| expected_min | " + " | ".join(counts) + " |",
        "|---" * (len(counts) + 1) + "|",
        f"| {args.expected_min} | {cells} |",
    ]
    rows.extend(f"- {reason}" for reason in reasons)
    report = "\n".join(rows) + "\n"
    print(report)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(report)
    return 1 if reasons else 0


if __name__ == "__main__":
    sys.exit(main())
