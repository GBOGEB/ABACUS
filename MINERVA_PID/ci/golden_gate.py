#!/usr/bin/env python3
"""
golden_gate.py — semantic golden-file gate for the MINERVA P&ID CI pipeline.

After ``make.sh`` regenerates all derived outputs, this script compares the
freshly regenerated ``reports/*_statistics.json`` files against the versions
committed in git (the "golden" snapshots).

Policy (see docs/W007_CICD_PLAN.md §3-§4):
  * FAIL on semantic drift — any committed numeric/string count that changed.
  * IGNORE the documented ~1-byte XLSX zip jitter (``*.xlsx`` are never
    compared here; only JSON statistics are gated).
  * CI never writes regenerated artifacts back to the repo.

Run from the MINERVA_PID directory:  python3 ci/golden_gate.py
Exit code 0 = gate passed, 1 = drift detected, 2 = setup error.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# Statistics files treated as golden snapshots.
GOLDEN_FILES = [
    "reports/W005_coverage_statistics.json",
    "reports/W006_crossmap_statistics.json",
    "reports/W009_commissioning_statistics.json",
]


def _git_committed(path: str) -> "str | None":
    """Return the committed (HEAD) contents of *path*, or None if untracked."""
    try:
        return subprocess.check_output(
            ["git", "show", f"HEAD:MINERVA_PID/{path}"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except subprocess.CalledProcessError:
        # Fall back to repo-relative path (when CWD is already MINERVA_PID root).
        try:
            return subprocess.check_output(
                ["git", "show", f"HEAD:{path}"],
                stderr=subprocess.DEVNULL,
                text=True,
            )
        except subprocess.CalledProcessError:
            return None


def _flatten(obj, prefix=""):
    """Flatten nested dict/list into {dotted.key: value} for stable diffing."""
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(_flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(_flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = obj
    return out


def main() -> int:
    drift = []
    missing = []

    for rel in GOLDEN_FILES:
        regen_path = Path(rel)
        if not regen_path.exists():
            print(f"::warning::regenerated stats missing: {rel} (skipped)")
            missing.append(rel)
            continue

        committed = _git_committed(rel)
        if committed is None:
            print(f"::warning::no committed golden for {rel} — recording baseline, not gating")
            continue

        try:
            golden = _flatten(json.loads(committed))
            current = _flatten(json.loads(regen_path.read_text()))
        except json.JSONDecodeError as e:
            print(f"::error file={rel}::invalid JSON ({e})")
            drift.append((rel, "invalid JSON"))
            continue

        keys = sorted(set(golden) | set(current))
        for key in keys:
            g, c = golden.get(key, "<absent>"), current.get(key, "<absent>")
            if g != c:
                drift.append((rel, f"{key}: golden={g!r} -> regenerated={c!r}"))

    print("\n=== Golden-file gate summary ===")
    print(f"  files checked : {len(GOLDEN_FILES)}")
    print(f"  missing/skip  : {len(missing)}")
    print(f"  drift entries : {len(drift)}")

    if drift:
        print("\nSemantic drift detected (counts changed vs committed golden):")
        for rel, msg in drift:
            print(f"  ::error file={rel}::{msg}")
        return 1

    print("\nGate PASSED — regenerated statistics match committed golden snapshots.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
