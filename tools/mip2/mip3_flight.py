#!/usr/bin/env python3
"""MIP3 preflight and postflight evidence reconciliation; standard library only."""
from __future__ import annotations
import argparse
import hashlib
import json
import pathlib
import platform
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[2]
METHODS = ("black", "isort", "ruff", "flake8", "pylint", "radon", "mypy", "pyright",
           "pytest", "coverage", "bandit", "semgrep", "pip-audit", "osv-scanner",
           "safety", "gitleaks", "detect-secrets", "trivy", "hadolint", "docker",
           "lldb", "gdb", "valgrind", "clang")

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def cmd(argv):
    start = time.monotonic()
    try:
        p = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=120)
        return {"exit_code": p.returncode, "duration_s": round(time.monotonic()-start, 3),
                "stdout_tail": p.stdout[-2000:], "stderr_tail": p.stderr[-2000:]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"exit_code": None, "duration_s": round(time.monotonic()-start, 3),
                "error": type(exc).__name__}

def tool_inventory():
    return [{"tool": name, "present_on_path": shutil.which(name) is not None,
             "qualification": "DISCOVERED_ONLY" if shutil.which(name) else "NOT_FOUND_ON_PATH"}
            for name in METHODS]

def junit(path):
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    return {"tests": sum(int(x.attrib.get("tests", 0)) for x in suites),
            "failures": sum(int(x.attrib.get("failures", 0)) for x in suites),
            "errors": sum(int(x.attrib.get("errors", 0)) for x in suites),
            "skipped": sum(int(x.attrib.get("skipped", 0)) for x in suites)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=("preflight", "postflight"), required=True)
    ap.add_argument("--junit", default="mip2-local-junit.xml")
    ap.add_argument("--receipt", default="mip2-local-receipt.json")
    ap.add_argument("--output", default="mip3-flight-receipt.json")
    args = ap.parse_args()
    git = cmd(["git", "rev-parse", "HEAD"])
    head = git.get("stdout_tail", "").strip() if git["exit_code"] == 0 else None
    data = {"schema": "mip3.flight-receipt.v1", "phase": args.phase,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "repository": str(ROOT), "head_sha": head,
            "environment": {"python": sys.version.split()[0], "os": platform.platform()},
            "tools": tool_inventory(), "artifacts": {}, "checks": {},
            "admission": "NOT_MERGE_AUTHORITY"}
    for name in ("tools/mip2/method_qualification_registry.json",
                 "tools/mip2/method_regression_corpus.json"):
        p = ROOT / name
        data["artifacts"][name] = {"sha256": digest(p), "bytes": p.stat().st_size} if p.is_file() else {"missing": True}
    if args.phase == "preflight":
        data["checks"]["syntax"] = cmd([sys.executable, "-m", "compileall", "-q", "tools/mip2"])
        data["checks"]["contracts"] = cmd([sys.executable, "tools/mip2/validate_method_contracts.py"])
    else:
        for label, name in (("local_receipt", args.receipt), ("junit", args.junit)):
            p = ROOT / name
            data["artifacts"][label] = {"sha256": digest(p), "bytes": p.stat().st_size} if p.is_file() else {"missing": True}
        p = ROOT / args.junit
        if p.is_file():
            try:
                data["junit"] = junit(p)
            except (ET.ParseError, ValueError) as exc:
                data["junit_error"] = type(exc).__name__
        p = ROOT / args.receipt
        if p.is_file():
            try:
                local = json.loads(p.read_text(encoding="utf-8"))
                data["local_flight"] = {"status": local.get("status"), "head_sha": local.get("head_sha"),
                                        "sha_matches": bool(head and local.get("head_sha") == head)}
            except (ValueError, OSError):
                data["local_flight"] = {"status": "INVALID"}
    if args.phase == "preflight":
        ok = bool(head) and all(x.get("exit_code") == 0 for x in data["checks"].values()) and all("sha256" in x for x in data["artifacts"].values())
    else:
        j = data.get("junit", {})
        loc = data.get("local_flight", {})
        ok = bool(head) and bool(j.get("tests", 0)) and j.get("failures") == 0 and j.get("errors") == 0 and j.get("skipped") == 0 and loc.get("status") == "PASS" and loc.get("sha_matches") is True and all("sha256" in x for x in data["artifacts"].values())
    data["status"] = "PASS" if ok else "HOLD"
    pathlib.Path(args.output).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"phase": args.phase, "status": data["status"], "head_sha": head, "output": args.output}))
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
