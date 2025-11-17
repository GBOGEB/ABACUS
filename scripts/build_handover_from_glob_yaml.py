#!/usr/bin/env python3
import glob
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "handover" / "GLOOB.yaml"
OUT_DIR = ROOT / "handover"

def sha256sum(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    if not SPEC.exists():
        print(f"Spec not found: {SPEC}")
        return 2

    spec = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
    bname = spec.get("bundle", {}).get("name", "DMAIC_V3_3_HANDOVER_GLOOB_MANIFEST")
    include = spec.get("bundle", {}).get("include", [])
    exclude = spec.get("bundle", {}).get("exclude", [])

    files = set()
    for pat in include:
        for m in glob.glob(str(ROOT / pat), recursive=True):
            p = Path(m)
            if p.is_file():
                files.add(p)

    # Exclusions
    ex_files = set()
    for pat in exclude:
        for m in glob.glob(str(ROOT / pat), recursive=True):
            ex_files.add(Path(m))
    files = sorted(f for f in files if f not in ex_files)

    if not files:
        print("No files matched include patterns.")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = OUT_DIR / f"{bname}.zip"
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(f, f.relative_to(ROOT))

    # Checksums manifest
    checksums = {str(f.relative_to(ROOT)): sha256sum(f) for f in files}
    (OUT_DIR / f"{bname}.sha256.json").write_text(json.dumps(checksums, indent=2), encoding="utf-8")
    print(f"✅ Built {zip_path} with {len(files)} files")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
