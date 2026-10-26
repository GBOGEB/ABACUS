#!/usr/bin/env python3
"""Standalone smoke test for the MYRRHA WCS handover snapshot.

Runs the same checks as ci/myrrha-handover-smoke.yml without needing GitHub
Actions. From the repo root (or anywhere), run:

    python3 myrrha_handover/ci/smoke_test.py

Exit code 0 = all checks passed, non-zero = at least one failure.
"""
from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)  # myrrha_handover/


def _check_json() -> int:
    fail = 0
    for f in glob.glob(PKG + "/**/*.json", recursive=True):
        try:
            json.load(open(f, encoding="utf-8"))
            print("OK   JSON", os.path.relpath(f, PKG))
        except Exception as exc:  # noqa: BLE001
            print("FAIL JSON", os.path.relpath(f, PKG), exc)
            fail = 1
    return fail


def _check_yaml() -> int:
    try:
        import yaml  # noqa: WPS433
    except ImportError:
        print("SKIP YAML (PyYAML not installed)")
        return 0
    fail = 0
    for f in glob.glob(PKG + "/**/*.y*ml", recursive=True):
        try:
            list(yaml.safe_load_all(open(f, encoding="utf-8")))
            print("OK   YAML", os.path.relpath(f, PKG))
        except Exception as exc:  # noqa: BLE001
            print("FAIL YAML", os.path.relpath(f, PKG), exc)
            fail = 1
    return fail


def _check_python() -> int:
    fail = 0
    for f in glob.glob(PKG + "/**/*.py", recursive=True):
        rc = subprocess.run(
            [sys.executable, "-m", "py_compile", f],
            capture_output=True,
        ).returncode
        print(("OK   PY  " if rc == 0 else "FAIL PY  "), os.path.relpath(f, PKG))
        fail |= rc
    return 1 if fail else 0


def _check_render() -> int:
    master = os.path.join(PKG, "master", "render_all.py")
    if not os.path.exists(master):
        print("SKIP render (master/render_all.py missing)")
        return 0
    rc = subprocess.run(
        [sys.executable, "render_all.py"],
        cwd=os.path.join(PKG, "master"),
        capture_output=True,
        text=True,
    )
    print(("OK   render" if rc.returncode == 0 else "FAIL render"), rc.stdout.strip()[:120])
    return rc.returncode


def _check_links() -> int:
    broken = []
    for h in glob.glob(PKG + "/**/*.html", recursive=True):
        d = os.path.dirname(h)
        txt = open(h, encoding="utf-8", errors="ignore").read()
        for m in re.findall(r'(?:href|src)="([^"#:]+)"', txt):
            if m.startswith(("http", "//", "mailto", "data:", "javascript", "${")):
                continue
            tgt = os.path.normpath(os.path.join(d, m.split("?")[0]))
            if not os.path.exists(tgt):
                broken.append((os.path.relpath(h, PKG), m))
    print(f"Broken local links/assets: {len(broken)}")
    for b in broken:
        print("  BROKEN:", b[0], "->", b[1])
    return 1 if broken else 0


def main() -> int:
    rc = 0
    for name, fn in [
        ("JSON", _check_json),
        ("YAML", _check_yaml),
        ("Python", _check_python),
        ("Render", _check_render),
        ("Links", _check_links),
    ]:
        print(f"\n=== {name} ===")
        rc |= fn()
    print("\n=== RESULT:", "PASS" if rc == 0 else "FAIL", "===")
    return rc


if __name__ == "__main__":
    sys.exit(main())
