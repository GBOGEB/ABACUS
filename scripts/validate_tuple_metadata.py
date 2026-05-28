#!/usr/bin/env python3
"""Validate tuple metadata payload and optionally emit normalized artifact."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))

from dmaic.tuple_metadata import validate_tracker_payload  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate tuple metadata payload")
    parser.add_argument("--input", required=True, help="Path to tracker JSON")
    parser.add_argument("--output", help="Optional validated artifact output path")
    args = parser.parse_args()

    input_path = ROOT_DIR / args.input if not Path(args.input).is_absolute() else Path(args.input)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    errors = validate_tracker_payload(payload)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    if args.output:
        output = ROOT_DIR / args.output if not Path(args.output).is_absolute() else Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(
                {
                    "source": str(input_path),
                    "validated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "status_schema": payload.get("status_schema", []),
                    "tuple_metadata": payload.get("tuple_metadata", []),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"[OK] Wrote validated tuple artifact: {output}")

    print(f"[OK] Tuple metadata validation passed for {input_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
