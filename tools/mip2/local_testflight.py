#!/usr/bin/env python3
"""Local, fail-closed MIP2 testflight with JSON telemetry (stdlib only)."""
import argparse
import datetime
import json
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]

def command(label, argv):
    started = time.monotonic()
    try:
        proc = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=180)
        return {"name": label, "status": "PASS" if proc.returncode == 0 else "FAIL",
                "exit_code": proc.returncode, "elapsed_s": round(time.monotonic()-started, 3),
                "stdout_tail": proc.stdout[-1200:], "stderr_tail": proc.stderr[-1200:]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"name": label, "status": "ERROR", "elapsed_s": round(time.monotonic()-started, 3),
                "error": str(exc)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("fast", "full"), default="fast")
    parser.add_argument("--output", default="mip2-local-receipt.json")
    args = parser.parse_args()
    steps = [
        command("syntax", [sys.executable, "-m", "compileall", "-q", "tools/mip2"]),
        command("contracts", [sys.executable, "tools/mip2/validate_method_contracts.py"])
    ]
    if args.mode == "full":
        steps.append(command("seeded-methods", [sys.executable, "-m", "pytest",
            "tools/mip2/tests/test_method_qualification.py", "-v", "-rs", "--junitxml=mip2-local-junit.xml"]))
    git = command("git-head", ["git", "rev-parse", "HEAD"])
    receipt = {"schema": "mip2.local-testflight.v1", "timestamp_utc": datetime.datetime.now(
        datetime.timezone.utc).isoformat(), "mode": args.mode,
        "head_sha": git.get("stdout_tail", "").strip() if git["status"] == "PASS" else None,
        "checks": steps, "status": "PASS" if all(x["status"] == "PASS" for x in steps) else "FAIL",
        "qualification": "LOCAL_ONLY_NOT_MERGE_AUTHORITY"}
    output = pathlib.Path(args.output)
    output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "receipt": str(output),
                      "checks": [{"name": x["name"], "status": x["status"]} for x in steps]}))
    return 0 if receipt["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
