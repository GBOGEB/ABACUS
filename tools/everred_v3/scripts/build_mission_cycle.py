#!/usr/bin/env python3
"""Build the HTML-first mission cycle from the existing EVERRED BD evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mission_cycle import project

SOURCE = ROOT / "data/bd_queue_20261014.json"
TEMPLATE = ROOT / "dashboard/mission_cycle_template.html"
OUTPUT = ROOT / "dashboard/mission_cycle.html"


def build(data, template):
    if data.get("schema") != "abacus.everred.bd-queue.observation.v1":
        raise ValueError("wrong source evidence schema")
    if data.get("mode") != "FROZEN_HISTORICAL_EVIDENCE_NOT_LIVE":
        raise ValueError("unqualified source status")
    if data.get("disposition") != "ADMISSION_HOLD":
        raise ValueError("admission authority cannot be inherited")
    marker = "@@GUIDANCE_JSON@@"
    if template.count(marker) != 1:
        raise ValueError("missing or duplicate data marker")
    guidance = project(data)
    encoded = json.dumps(
        guidance,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).replace("</", "<\\/")
    return template.replace(marker, encoded)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--template", type=Path, default=TEMPLATE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    result = build(
        json.loads(args.source.read_text(encoding="utf-8")),
        args.template.read_text(encoding="utf-8"),
    )
    if args.check:
        if (
            not args.output.exists()
            or args.output.read_text(encoding="utf-8") != result
        ):
            raise SystemExit("stale Mission Cycle HTML")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(result, encoding="utf-8")
    print("Rendered", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
