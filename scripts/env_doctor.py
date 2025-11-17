#!/usr/bin/env python3
import sys
import shutil
import json
from pathlib import Path

def main():
    info = {
        "python": sys.version,
        "python_ok": sys.version_info >= (3, 10),
        "deps": {},
        "tools": {},
        "paths": {
            "root": str(Path(__file__).resolve().parents[1]),
            "reports": "DMAIC_V3_OUTPUT/reports",
            "knowledge": "knowledge_packages",
        }
    }
    # Python deps
    try:
        import yaml  # noqa
        info["deps"]["pyyaml"] = True
    except Exception:
        info["deps"]["pyyaml"] = False

    # External tools (best-effort)
    for tool in ["pandoc", "xelatex", "gh"]:
        info["tools"][tool] = shutil.which(tool) is not None

    print(json.dumps(info, indent=2))
    return 0 if info["python_ok"] and info["deps"]["pyyaml"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
