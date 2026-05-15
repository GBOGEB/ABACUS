#!/usr/bin/env python3
"""
Validate canonical DMAIC contract compliance for JSON artifacts.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))

from dmaic.contract import validate_contract  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate DMAIC canonical metadata contract")
    parser.add_argument(
        "--target",
        default="DMAIC_CANONICAL_OUTPUT",
        help="Directory containing JSON artifacts",
    )
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="Do not fail when target has no JSON files",
    )
    args = parser.parse_args()

    target = (ROOT_DIR / args.target).resolve() if not Path(args.target).is_absolute() else Path(args.target)
    if not target.exists():
        print(f"[WARN] Target does not exist: {target}")
        return 0 if args.allow_empty else 1

    json_files = sorted(target.glob("*.json"))
    if not json_files:
        print(f"[WARN] No JSON files found in {target}")
        return 0 if args.allow_empty else 1

    failures = []
    for file_path in json_files:
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append((str(file_path), [f"invalid JSON: {exc}"]))
            continue

        errors = validate_contract(payload)
        if errors:
            failures.append((str(file_path), errors))

    if failures:
        print("[FAIL] Contract validation errors detected:")
        for file_name, errors in failures:
            print(f"  - {file_name}")
            for err in errors:
                print(f"      * {err}")
        return 1

    print(f"[OK] Contract validation passed for {len(json_files)} artifact(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
