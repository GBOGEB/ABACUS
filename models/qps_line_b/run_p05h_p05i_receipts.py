#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = ROOT / "models/qps_line_b/p05h_p05i_source_payload.json"
DEFAULT_OUTPUT = ROOT / "docs/qps_line_b/generated"


def load_payload(path: Path) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data:
        raise ValueError("source payload must be a non-empty object")
    return data


def emit(source: Path, out_dir: Path) -> list[Path]:
    payload = load_payload(source)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, value in sorted(payload.items()):
        if not name.endswith(".json") or not isinstance(value, dict):
            raise ValueError(f"invalid generated receipt entry: {name}")
        target = out_dir / name
        target.write_text(
            json.dumps(value, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        written.append(target)
    return written


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    files = emit(args.source, args.out_dir)
    print(json.dumps({"generated": [str(p) for p in files]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
