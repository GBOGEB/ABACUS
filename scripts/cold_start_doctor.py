#!/usr/bin/env python3
import sys
import os
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def run(cmd):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, shell=os.name == "nt")
        return {"cmd": cmd, "rc": out.returncode, "stdout": out.stdout.strip(), "stderr": out.stderr.strip()}
    except Exception as e:
        return {"cmd": cmd, "rc": 127, "stdout": "", "stderr": str(e)}

def main():
    report = {
        "cwd": str(Path.cwd()),
        "root": str(ROOT),
        "python": sys.version,
        "python_exe": sys.executable,
        "sys_path_head": sys.path[:5],
        "checks": {},
        "tools": {},
        "actions": []
    }

    # Check repo structure
    report["checks"]["root_exists"] = Path(report["root"]).exists()
    report["checks"]["dmaic_dir_exists"] = (ROOT / "DMAIC_V3").exists()
    report["checks"]["dmaic_init_exists"] = (ROOT / "DMAIC_V3" / "__init__.py").exists()

    # Try importing DMAIC_V3
    try:
        sys.path.insert(0, str(ROOT))
        import DMAIC_V3  # noqa
        report["checks"]["import_DMAIC_V3"] = True
    except Exception as e:
        report["checks"]["import_DMAIC_V3"] = False
        report["actions"].append("Create package marker: DMAIC_V3/__init__.py")
        report["actions"].append("Run from repo root: cd {}".format(report["root"]))
        report["actions"].append("Add repo root to PYTHONPATH if running from elsewhere.")

    # External tools presence
    for tool in ["pandoc", "xelatex", "gh"]:
        report["tools"][tool] = shutil.which(tool) or ""

    # Engine version
    ev = run("python -m DMAIC_V3.dmaic_v3_engine --version")
    report["engine_version"] = ev

    # Knowledge and reports existence
    report["checks"]["knowledge_dir"] = (ROOT / "knowledge_packages").exists()
    report["checks"]["reports_dir"] = (ROOT / "DMAIC_V3_OUTPUT" / "reports").exists()

    print(json.dumps(report, indent=2))
    # Fail if import is broken or engine version invocation fails
    ok = report["checks"]["import_DMAIC_V3"] and ev["rc"] == 0
    return 0 if ok else 2

if __name__ == "__main__":
    raise SystemExit(main())
