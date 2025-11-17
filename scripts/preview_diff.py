#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path
from typing import Dict, Any


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_index(index_path: Path) -> Dict[str, Any]:
    return json.loads(index_path.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["in", "out", "both"], default="both")
    ap.add_argument("--index", required=True)
    args = ap.parse_args()

    idx_path = Path(args.index)
    idx = load_index(idx_path)
    artifacts = idx.get("artefacts", [])

    had_diff = False
    for a in artifacts:
        path = Path(a["path"])  # required in schema
        if not path.exists():
            print(f"[WARN] missing {path}")
            continue
        computed = sha256_file(path)
        recorded = a.get("hash") or ""
        if not recorded:
            print(f"[INFO] no recorded hash for {path}; will need hash_update")
            continue
        if recorded != computed:
            print(f"[DIFF] {path} hash changed")
            # best-effort content context for text files
            try:
                text = path.read_text(encoding="utf-8", errors="ignore").splitlines()
                print("(content changed; run hash_update after review)")
            except Exception:
                print("(binary or unreadable content changed)")
            had_diff = True

    raise SystemExit(1 if had_diff else 0)


if __name__ == "__main__":
    main()

