#!/usr/bin/env python3
"""Validate Phase-2 reconstruction manifest and optionally emit validated output."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))

from dmaic.reconstruction_manifest import validate_reconstruction_manifest  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate reconstruction manifest payload")
    parser.add_argument("--input", required=True, help="Path to reconstruction manifest JSON")
    parser.add_argument("--output", help="Optional validated artifact output path")
    args = parser.parse_args()

    input_path = ROOT_DIR / args.input if not Path(args.input).is_absolute() else Path(args.input)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    errors = validate_reconstruction_manifest(payload, ROOT_DIR)
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
                    "manifest_version": payload.get("manifest_version"),
                    "artifact_count": len(payload.get("artifacts", [])),
                    "component_count": len(payload.get("component_map", [])),
                    "component_map": payload.get("component_map", []),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"[OK] Wrote validated reconstruction manifest artifact: {output}")

    print(f"[OK] Reconstruction manifest validation passed for {input_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
