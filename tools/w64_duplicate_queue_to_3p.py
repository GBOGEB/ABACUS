#!/usr/bin/env python3
"""Convert W64 P2 duplicate-authority findings into generic 3P root items."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

TYPE = "duplicate_or_competing_authority"


def convert(report: dict[str, object]) -> dict[str, object]:
    findings = report.get("findings", [])
    if not isinstance(findings, list):
        raise TypeError("findings must be a list")
    items = []
    for finding in findings:
        if not isinstance(finding, dict) or finding.get("type") != TYPE:
            continue
        paths = sorted(str(p) for p in finding.get("paths", []) or [])
        items.append({
            "scope": "GBOGEB/ABACUS",
            "type": TYPE,
            "cluster": finding.get("family"),
            "members": paths,
            "source_severity": finding.get("severity"),
        })
    return {
        "schema_version": "W64-DUPLICATE-3P-INPUT-1.0.0",
        "source_finding_type": TYPE,
        "item_count": len(items),
        "items": items,
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--p2", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)
    report = json.loads(Path(args.p2).read_text(encoding="utf-8"))
    result = convert(report)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"item_count": result["item_count"], "out": str(out)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
