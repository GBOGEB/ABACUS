#!/usr/bin/env python3
"""Census and prevent ungoverned false-green constructs in GitHub workflows."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


PATTERNS = {
    "shell_or_true": re.compile(r"\|\|\s*true\b"),
    "shell_or_echo": re.compile(r"\|\|\s*echo\b"),
    "shell_set_plus_e": re.compile(r"\bset\s+\+e\b"),
    "continue_on_error": re.compile(r"continue-on-error\s*:\s*true\b"),
}
ALLOW = "# rex-allow:"


def scan_file(path: Path) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        matched = [name for name, regex in PATTERNS.items() if regex.search(line)]
        if not matched:
            continue
        previous = lines[index - 1] if index else ""
        allowed = ALLOW in line or ALLOW in previous
        rows.append(
            {
                "path": path.as_posix(),
                "line": index + 1,
                "patterns": matched,
                "allowed": allowed,
                "text": line.strip(),
            }
        )
    return rows


def discover(root: Path) -> list[Path]:
    return sorted(
        path
        for pattern in ("*.yml", "*.yaml")
        for path in root.glob(pattern)
        if path.is_file()
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--paths", nargs="*", type=Path)
    parser.add_argument("--mode", choices=("census", "enforce"), default="enforce")
    parser.add_argument("--out", type=Path)
    parser.add_argument(
        "--max-unguarded",
        type=int,
        help="Fail if the unguarded finding count rises above this accepted baseline.",
    )
    args = parser.parse_args(argv)

    paths = list(args.paths or [])
    if args.root:
        paths.extend(discover(args.root))
    paths = sorted(set(path for path in paths if path.exists()))

    rows = [row for path in paths for row in scan_file(path)]
    violations = [row for row in rows if not row["allowed"]]
    pressure: dict[str, dict[str, Any]] = {}
    for row in violations:
        entry = pressure.setdefault(
            row["path"],
            {
                "path": row["path"],
                "unguarded_count": 0,
                "patterns": {},
            },
        )
        entry["unguarded_count"] += 1
        for pattern in row["patterns"]:
            entry["patterns"][pattern] = entry["patterns"].get(pattern, 0) + 1

    pressure_queue = sorted(
        pressure.values(),
        key=lambda item: (-item["unguarded_count"], item["path"]),
    )
    ratchet_exceeded = (
        args.max_unguarded is not None
        and len(violations) > args.max_unguarded
    )
    report = {
        "schema": "abacus-ci-false-green-census/1.1.0",
        "mode": args.mode,
        "scanned_files": len(paths),
        "finding_count": len(rows),
        "allowed_count": len(rows) - len(violations),
        "unguarded_count": len(violations),
        "max_unguarded": args.max_unguarded,
        "ratchet_status": "FAIL" if ratchet_exceeded else "PASS",
        "pressure_queue": pressure_queue,
        "findings": rows,
        "authority_transfer": False,
        "formal_credit_delta": 0,
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    if ratchet_exceeded:
        return 1
    return 1 if args.mode == "enforce" and violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
