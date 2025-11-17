#!/usr/bin/env python3
import argparse
import glob
import json
import tarfile
from zipfile import ZipFile, ZIP_DEFLATED
from pathlib import Path
from typing import Iterable, List, Set

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "handover"

def expand_globs(patterns: Iterable[str]) -> List[Path]:
    files: Set[Path] = set()
    for pat in patterns:
        for m in glob.glob(str(ROOT / pat), recursive=True):
            p = Path(m)
            if p.is_file():
                files.add(p)
    return sorted(files)

def expand_exclusions(files: List[Path], excludes: Iterable[str]) -> List[Path]:
    ex: Set[Path] = set()
    for pat in excludes:
        for m in glob.glob(str(ROOT / pat), recursive=True):
            ex.add(Path(m))
    return [f for f in files if f not in ex]

def load_spec(spec_path: Path) -> List[Path]:
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    bundle = spec.get("bundle", {})
    include = bundle.get("include", []) or []
    exclude = bundle.get("exclude", []) or []
    files = expand_globs(include)
    files = expand_exclusions(files, exclude)
    return files

def load_copy_list(copy_list_path: Path) -> List[Path]:
    pats: List[str] = []
    for line in copy_list_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        pats.append(line)
    return expand_globs(pats)

def write_zip(files: List[Path], out_zip: Path) -> None:
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(out_zip, "w", compression=ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(f, f.relative_to(ROOT))

def write_targz(files: List[Path], out_tgz: Path) -> None:
    out_tgz.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(out_tgz, "w:gz") as tf:
        for f in files:
            tf.add(f, arcname=str(f.relative_to(ROOT)))

def main():
    ap = argparse.ArgumentParser(description="Build handover archives (.zip and .tar.gz) with correct relative paths.")
    ap.add_argument("--spec", default=str(OUT_DIR / "GLOOB.yaml"), help="Path to GLOOB.yaml")
    ap.add_argument("--copy", default=str(OUT_DIR / "COPY_GLOBS.txt"), help="Path to COPY_GLOBS.txt")
    ap.add_argument("--name", default="DMAIC_V3_3_HANDOVER_ALL", help="Base name for archives (without extension)")
    args = ap.parse_args()

    files: List[Path] = []
    spec_path = Path(args.spec)
    copy_path = Path(args.copy)

    if spec_path.exists():
        files = load_spec(spec_path)
    elif copy_path.exists():
        files = load_copy_list(copy_path)
    else:
        print(f"No spec or copy list found at:\n - {spec_path}\n - {copy_path}")
        return 2

    if not files:
        print("No files matched; nothing to archive.")
        return 1

    zip_path = OUT_DIR / f"{args.name}.zip"
    tgz_path = OUT_DIR / f"{args.name}.tar.gz"

    write_zip(files, zip_path)
    write_targz(files, tgz_path)

    print(json.dumps({
        "root": str(ROOT),
        "count": len(files),
        "zip": str(zip_path),
        "tar_gz": str(tgz_path)
    }, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
