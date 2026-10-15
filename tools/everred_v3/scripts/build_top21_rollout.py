#!/usr/bin/env python3
"""Deterministic read-only TOP21 census, fail-closed --check mode."""

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from top21_rollout import rollout_census


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--contract", required=True, type=pathlib.Path)
    p.add_argument("--output", required=True, type=pathlib.Path)
    p.add_argument("--ranking", type=pathlib.Path)
    p.add_argument("--receipts", type=pathlib.Path)
    p.add_argument("--check", action="store_true")
    a = p.parse_args(argv)

    def read(path):
        return json.loads(path.read_text(encoding="utf-8")) if path else None

    result = rollout_census(read(a.contract), read(a.receipts), read(a.ranking))
    encoded = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if a.check:
        if not a.output.exists() or a.output.read_text(encoding="utf-8") != encoded:
            print("TOP21 report absent or stale", file=sys.stderr)
            return 1
        return 0
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(encoded, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
