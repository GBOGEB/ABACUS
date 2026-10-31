#!/usr/bin/env python3
"""Local, fail-closed MIP2 testflight with JSON telemetry (stdlib only)."""

import argparse
import datetime
import json
import pathlib
import re
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]


def command(label, argv):
    started = time.monotonic()
    try:
        proc = subprocess.run(
            argv, cwd=ROOT, capture_output=True, text=True, timeout=180
        )
        result = {
            "name": label,
            "status": "PASS" if proc.returncode == 0 else "FAIL",
            "exit_code": proc.returncode,
            "elapsed_s": round(time.monotonic() - started, 3),
        }
        # Never persist subprocess stdout/stderr in uploaded evidence: it can contain secrets.
        # The only permitted output is the validated Git commit identity.
        if label == "git-head" and proc.returncode == 0:
            head = proc.stdout.strip()
            if re.fullmatch(r"[0-9a-f]{40}", head):
                result["head_sha"] = head
            else:
                result["status"] = "FAIL"
                result["error_type"] = "INVALID_GIT_SHA"
        return result
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "name": label,
            "status": "ERROR",
            "elapsed_s": round(time.monotonic() - started, 3),
            "error_type": type(exc).__name__,
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("fast", "full"), default="fast")
    parser.add_argument("--output", default="mip2-local-receipt.json")
    parser.add_argument("--expected-head", help="optional native event PR-head SHA")
    args = parser.parse_args()
    steps = [
        command("syntax", [sys.executable, "-m", "compileall", "-q", "tools/mip2"]),
        command(
            "contracts", [sys.executable, "tools/mip2/validate_method_contracts.py"]
        ),
    ]
    if args.mode == "full":
        steps.append(
            command(
                "seeded-methods",
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "tools/mip2/tests/test_method_qualification.py",
                    "-v",
                    "-rs",
                    "--junitxml=mip2-local-junit.xml",
                ],
            )
        )
    git = command("git-head", ["git", "rev-parse", "HEAD"])
    valid_git = git["status"] == "PASS" and bool(git.get("head_sha"))
    matches_expected = not args.expected_head or (
        valid_git and git["head_sha"] == args.expected_head
    )
    receipt = {
        "schema": "mip2.local-testflight.v1",
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "mode": args.mode,
        "head_sha": git.get("head_sha") if valid_git else None,
        "expected_head_sha": args.expected_head,
        "expected_head_matches": bool(matches_expected),
        "checks": steps + [git],
        "status": (
            "PASS"
            if valid_git
            and matches_expected
            and all(x["status"] == "PASS" for x in steps)
            else "FAIL"
        ),
        "qualification": "LOCAL_ONLY_NOT_MERGE_AUTHORITY",
    }
    output = pathlib.Path(args.output)
    output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "receipt": str(output),
                "checks": [
                    {"name": x["name"], "status": x["status"]} for x in steps + [git]
                ],
            }
        )
    )
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
