#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path
from typing import Dict, Any


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", required=True)
    args = ap.parse_args()

    idx_path = Path(args.index)
    idx = json.loads(idx_path.read_text(encoding="utf-8"))

    changed = False
    for a in idx.get("artefacts", []):
        p = Path(a["path"])  # required
        if not p.exists():
            print(f"[WARN] missing {p}")
            continue
        h = sha256_file(p)
        if a.get("hash") != h:
            a["hash"] = h
            print(f"[UPDATE] {p} -> {h[:12]}…")
            changed = True

    if changed:
        idx_path.write_text(json.dumps(idx, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"[WROTE] {idx_path}")
    else:
        print("[OK] hashes up to date")


if __name__ == "__main__":
    main()

