#!/usr/bin/env python3
"""
Local exporter (best-effort):
- Copies Markdown and Mermaid sources to an `out/` tree
- Pandoc/PDF generation is handled in CI via container (see export-docs.yml)
"""
import argparse
import shutil
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="docs")
    ap.add_argument("--out", default="out")
    args = ap.parse_args()

    src = Path(args.src)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    exts = {".md", ".mmd", ".mermaid"}
    for p in src.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            dest = out / p.relative_to(src)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dest)
            print(f"[COPY] {p} -> {dest}")


if __name__ == "__main__":
    main()

